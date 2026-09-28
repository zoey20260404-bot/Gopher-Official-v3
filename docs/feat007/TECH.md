# feat007：用户档案驱动的岗位硬条件匹配闭环技术设计

## 1. 调用链

```text
GET /api/v1/positions/matches
  → get_current_user
  → load confirmed UserProfile
  → merge query filters with profile targets
  → PositionMatchService
       → PositionRepository.count_candidates
       → PositionRepository.list_candidates（bounded）
       → PositionEligibilityEvaluator
            → deterministic field rules
       → status filter
       → in-memory pagination
  → PositionMatchListResponse

LangGraph
  → match_positions tool
  → 同一个 PositionMatchService
```

## 2. 分层与类型

### 2.1 Domain

新增稳定枚举与不可变结果类型：

- `RuleResult`：`pass` / `fail` / `unknown`；
- `PositionMatchStatus`：`eligible` / `ineligible` / `uncertain`；
- `PositionMatchFilter`：`potential` / `eligible` / `uncertain` / `ineligible` / `all`；
- `MatchReason`：field、result、code、message、profile value、requirement；
- `PositionMatch`：PositionItem、最终 status、reasons、missing profile fields。

枚举使用稳定英文值，中文只出现在展示 message。规则和测试断言使用 code/enum，不依赖 message 文案。

### 2.2 Rule engine

`PositionEligibilityEvaluator` 是无 I/O 的纯函数对象：

```text
evaluate(profile, position) -> PositionEligibility
```

它不读取数据库、不调用 LLM、不访问全局配置。每个字段规则是独立私有函数或实现统一 Protocol 的对象，聚合器只处理
三态优先级。规则输入使用 `ProfileData` 和 transport 无关的 `PositionItem`。

### 2.3 Service

`PositionMatchService` 负责：

- 确认权威档案存在；
- 合并显式 query 与 profile target 默认值；
- 检查候选数量上限；
- 调用 evaluator；
- 应用 match status filter；
- 在匹配后计算 total 并分页。

Service 不依赖 FastAPI schema。HTTP route 和 tool adapter 复用同一个 Service。

## 3. Repository 扩展

保留现有 `list(PositionQuery)` 行为，避免改变 `query_positions`。为匹配用例新增：

```python
async def count_candidates(query: PositionCandidateQuery) -> int: ...
async def list_candidates(
    query: PositionCandidateQuery,
    *,
    limit: int,
) -> list[Position]: ...
```

`PositionCandidateQuery` 只包含粗筛字段，不包含 page/page_size/match status。`build_position_statement` 继续作为两类查询的
共同参数化 SQL builder。候选读取固定排序并带 `LIMIT candidate_limit + 1` 作为 repository 防御；Service 在 count 已超过上限时
直接拒绝。

候选岗位只读，不开启显式写 transaction，不执行 commit。

## 4. 规则实现

### 4.1 通用 normalization

- Unicode 全半角标点只用于分隔符归一化；
- 去除首尾和重复空白；
- “不限”“无要求”“不限制”映射为 unlimited；
- 不删除会改变业务含义的词，不进行拼音、编辑距离、embedding 或语义相似度处理；
- 未识别格式返回 unknown，禁止 fallback 为 pass。

### 4.2 学历

内部等级顺序：

```text
高中/中专 < 大专 < 本科 < 硕士研究生 < 博士研究生
```

- 识别“及以上”“以上”“及以下”“以下”和“仅限”；
- “本科及以上”使用范围比较；
- “仅限本科”只允许相同等级；
- 同时出现互相冲突的限定词、无法识别学历或多个不明确范围时返回 unknown；
- 不从学位推断学历。

### 4.3 专业

- 对 `major_req_exact` 只按逗号、顿号、分号、斜杠和换行拆分；
- 去除 token 首尾空白后执行完整字符串相等；
- 明确列表存在且无命中返回 fail；
- 精确字段为空、仅有 `major_req_category` 时返回 unknown；
- 不把用户专业映射到专业大类，不使用 `in` 子串判断。

### 4.4 政治面貌、性别

- 只维护明确、有限的规范别名；
- 岗位允许多个值时拆分为集合并精确匹配；
- “中共党员（含预备党员）”可以显式展开；普通“中共党员”不自动推断包含预备党员；
- 任一侧无法规范化时返回 unknown。

### 4.5 数值与布尔规则

- fresh graduate：岗位 `None` 为不限；有明确要求但用户为 `None` 时 unknown；
- work experience：要求 0 年为不限；否则执行 `user_years >= required_years`；
- age：`age_limit is None` 为不限；否则执行 `user_age <= age_limit`。

### 4.6 户籍

- 去除“户籍”“生源”等要求词以及省/市的标准行政后缀后，比较明确行政层级；
- 省级要求明确属于不同省时 fail；
- 同省且岗位只要求省级时 pass；
- 市级要求必须明确命中对应城市；
- 无法拆出可靠省/市层级时 unknown，不使用任意子串包含放行。

首版仅维护规则测试所需的有限行政后缀处理，不内置不完整的全国行政区划表。若无法区分省市归属，返回 unknown。

### 4.7 自由文本限制

`other_restrictions` 非空或 `remarks` 非空分别追加 unknown reason。它们不覆盖已经产生的 fail，但会使原本全部通过的岗位
降为 uncertain，提示用户人工复核。

## 5. Profile target 默认值

Service 按字段执行：

```text
effective value = explicit query value or profile target value
```

仅 `exam_type`、`province`、`city` 使用 profile 默认值。空白已在 API/Profile schema 层规范化为 `None`。响应无需暴露完整
effective query，但测试必须验证显式 query 优先。

## 6. 分页与复杂度

配置新增：

```text
POSITION_MATCH_CANDIDATE_LIMIT=2000
```

Pydantic Settings 约束为 100～10000，并同步 `.env.example`。处理复杂度为 `O(candidate_count × rule_count)`，内存上界由候选
限制保证。匹配完成后：

1. 按 `PositionMatchFilter` 过滤；
2. `total = len(filtered_matches)`；
3. 使用 `(page - 1) * page_size : page * page_size` 切片；
4. 保留 Repository 的稳定顺序。

不允许返回截断但看似完整的结果。候选超过上限时抛出 `PositionCandidateLimitExceededError`，HTTP 映射为 422，tool 返回可操作
的缩小条件提示。

## 7. HTTP 与错误映射

- `PositionMatchParams` 扩展现有粗筛字段，新增 match status 和分页校验；
- response 复用 `PositionItemResponse` 作为嵌套 position，不复制岗位公开字段；
- `UserProfileNotConfirmedError` → HTTP 409；
- `PositionCandidateLimitExceededError` → HTTP 422；
- 认证继续由 `get_current_user` 负责，body/query 不接受 user ID。

读取 profile 和岗位必须使用同一个请求级 `AsyncSession`，保证 dependency 生命周期简单；本用例全程只读，无 commit。

## 8. Agent tool 与 graph

新增 `PositionMatchTool` adapter 和 LangChain `StructuredTool` wrapper：

- Pydantic tool input 不包含 user ID、profile 或 candidate limit；
- `page_size` 最大 10；
- tool 输出最多 10 条岗位和精简 reason；
- started/completed custom stream event 使用 tool 名 `match_positions`；
- completed event 包含 result count，不包含用户档案；
- graph builder 接收 tool sequence，同时绑定 `query_positions` 与 `match_positions`；
- `ToolNode` 使用相同白名单；
- system prompt 区分客观查询和资格匹配意图。

每个 Chat 请求继续构造请求级 graph，使 match tool 可以安全持有当前请求的 Repository/Service，不把请求级 session 放入应用
全局资源。

## 9. 测试策略

- normalization：不限、空值、分隔符和未知格式；
- rule engine：每项 pass/fail/unknown、fail 优先级和 missing fields；
- 学历：本科、本科及以上、仅限本科、冲突格式；
- 专业：精确命中、明确未命中、仅专业大类、空要求，证明不做模糊匹配；
- 户籍：省级、市级、跨省、缺失和无法解析；
- service：profile 不存在、target 默认值、query 优先、候选上限、status filter、total 和分页；
- repository：参数绑定、count、bounded candidate query 和稳定排序；
- HTTP：401、409、422、三态 response 和 OpenAPI；
- tool/graph：两个白名单 tool、身份参数不可见、调用路由和 stream event；
- PostgreSQL 集成：真实候选读取顺序和上限；
- 不调用真实 LLM，不连接生产数据库。

## 10. 预计文件变更

```text
.env.example
README.md
src/gopher_agent/
├── agents/graph.py
├── agents/tools.py
├── api/dependencies/positions.py
├── api/routes/positions.py
├── api/schemas/positions.py
├── core/config.py
├── domain/matching.py
├── repositories/protocols.py
├── repositories/sqlalchemy/position.py
├── repositories/types.py
├── services/exceptions.py
├── services/matching.py
└── tools/positions.py
tests/
├── integration/test_agent_checkpoint.py
├── integration/test_positions_api.py
├── integration/test_repositories_db.py
├── unit/test_agent_graph.py
├── unit/test_config.py
├── unit/test_matching_rules.py
├── unit/test_matching_service.py
├── unit/test_position_service.py
└── unit/test_repositories.py
```

现有表字段能够承载本需求，预期不新增 Alembic revision；实现完成后仍执行 migration 往返与 schema drift 检查。

## 11. 实施记录

- 2026-09-28：确认 feat007 聚焦用户档案驱动的岗位硬条件匹配；
- 2026-09-28：确认专业大类缺少权威映射时返回 uncertain，不做模糊匹配；
- 2026-09-28：从 feat006 完成 commit 创建 `feature/zoey/feat007`；
- 2026-09-28：完成 PRODUCT/TECH 设计并通过实现前审核；
- 2026-09-28：完成确定性三态 rule engine、正确匹配分页、候选上限、matches API 和 `match_positions` tool；
- 2026-09-28：专业精确列表仅允许完整匹配，专业大类缺少映射时保持 uncertain；
- 2026-09-28：在隔离 PostgreSQL/pgvector 与 Redis 上通过 migration、候选 Repository、checkpoint 集成测试和
  Alembic schema drift 检查。
- 2026-09-28：126 个测试通过，覆盖率 95.22%，Ruff 和 mypy strict 通过。
