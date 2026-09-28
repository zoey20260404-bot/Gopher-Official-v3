# feat007：用户档案驱动的岗位硬条件匹配闭环需求

## 1. 背景

feat004 已提供客观岗位检索，feat006 已建立“解析草稿 → 用户确认 → 权威档案”闭环，但当前两项能力彼此独立。
用户仍需自行阅读每个岗位的学历、专业、政治面貌、应届生、工作经验、年龄、性别和户籍要求，Agent 也只能查询岗位，
不能基于可信档案给出可解释的资格判断。

岗位硬条件判断必须保守且可复现。未知信息、自由文本限制和缺少权威专业目录的情况不能被当作符合，也不能由 LLM
凭语义相似度放行。

## 2. 目标

- 提供受 Bearer 认证保护的 `GET /api/v1/positions/matches`；
- 使用当前用户已确认的 `UserProfile` 匹配岗位硬条件；
- 对每个岗位返回 `eligible`、`ineligible` 或 `uncertain` 三态结论；
- 返回逐字段、可验证的判断依据，不只返回布尔值；
- 提供独立的 `match_positions` Agent tool，不改变 `query_positions` 的客观查询语义；
- 保证匹配后分页的 `items` 和 `total` 正确；
- 全部规则确定性执行，不调用 LLM。

## 3. 范围

### 包含

- 已确认档案存在性校验；
- 考试类型、年份、地区和关键词候选岗位粗筛；
- 学历、专业、政治面貌、应届生、工作经验、性别、年龄和户籍规则；
- `other_restrictions` 和 `remarks` 的人工复核标记；
- 三态规则聚合和逐项 reason；
- 候选集上限与正确分页；
- `GET /api/v1/positions/matches`；
- `match_positions` tool adapter 与 LangGraph 白名单注册；
- rule、service、repository、HTTP、tool 和 graph 测试。

### 不包含

- LLM 判断、解释或放行硬条件；
- 官方专业目录导入、专业到专业大类映射和专业同义词库；
- 对 `other_restrictions`、`remarks` 做自由文本资格推断；
- 推荐排序、竞争力评分和冲稳保报告；
- 多轮 Interviewer 自动追问；
- 收藏；
- 新增或修改数据库表结构。

## 4. 三态契约

### 4.1 Rule result

每条规则返回：

- `pass`：已知信息明确满足该项要求；
- `fail`：已知信息明确不满足该项要求；
- `unknown`：用户信息缺失、岗位要求缺失/无法解析，或本期没有可靠数据支持判断。

reason 至少包含：

```json
{
  "field": "education",
  "result": "pass",
  "code": "education_level_satisfied",
  "message": "用户学历满足岗位要求",
  "profile_value": "本科",
  "requirement": "本科及以上"
}
```

`message` 是稳定、非 LLM 生成的用户提示；`code` 用于客户端展示和测试，不依赖中文文本判断逻辑。

### 4.2 Position result

逐岗位聚合优先级固定为：

1. 任意规则 `fail` → `ineligible`；
2. 没有 `fail`，但至少一条 `unknown` → `uncertain`；
3. 全部规则 `pass` → `eligible`。

缺失信息永远不能产生 `pass`。即使存在 `unknown`，只要另一个条件已经明确失败，最终仍为 `ineligible`。

## 5. 规则矩阵

| 条件 | 明确通过 | 明确失败 | 返回 uncertain |
| --- | --- | --- | --- |
| 学历 | 等级满足“及以上/及以下”，或满足“仅限” | 等级明确越界 | 用户/岗位学历无法规范化或要求有歧义 |
| 专业 | “不限”，或用户专业命中明确专业列表 | 明确专业列表存在但未命中 | 仅有专业大类、要求为空或格式无法可靠拆分 |
| 政治面貌 | “不限”或命中明确允许集合 | 明确集合存在但未命中 | 用户信息缺失或岗位文本无法解析 |
| 应届生 | 岗位不限，或用户值满足布尔要求 | 用户值与明确要求冲突 | 岗位有要求但用户未填写 |
| 工作经验 | 岗位要求 0 年，或用户年限达到要求 | 用户年限低于要求 | 岗位要求大于 0 但用户未填写 |
| 性别 | “不限”或规范化后相等 | 明确要求与用户值不同 | 用户信息缺失或岗位文本无法解析 |
| 年龄 | 岗位无年龄上限，或用户年龄不超过上限 | 用户年龄超过上限 | 岗位有上限但用户未填写 |
| 户籍 | “不限”，或规范化后的省/市层级明确匹配 | 省级要求明确且用户属于其他省份 | 用户信息缺失、岗位要求为空或无法可靠解析 |
| 其他限制 | 无结构化限制 | 本期不据此判定 fail | `other_restrictions` 非空时需人工复核 |
| 备注 | 备注为空 | 本期不据此判定 fail | 备注非空时需人工复核 |

### 5.1 通用约定

- 显式“不限”“无要求”“不限制”表示该规则 `pass`；
- 自由文本字段为空表示数据缺失，返回 `unknown`，不能等同于“不限”；
- `fresh_graduate_req is None`、`work_experience_years_req == 0` 和 `age_limit is None` 是现有结构化字段约定的
  无限制值，可返回 `pass`；
- 规范化只处理空白、常见全半角分隔符和明确别名，不做模糊相似度比较；
- `target_exam_type`、`target_province`、`target_city` 用于候选岗位默认粗筛，不参与资格 rule。

### 5.2 专业保守规则

- `major_req_exact` 为“不限”时返回 `pass`；
- `major_req_exact` 能拆分为明确允许列表时，仅规范化后完全相等才算命中；
- 明确列表未命中返回 `fail`，不使用子串、编辑距离、embedding 或 LLM；
- `major_req_exact` 为空而 `major_req_category` 非空时返回 `unknown`；
- 精确专业和专业大类都为空时返回 `unknown`；
- 本期不从用户 `major` 猜测其所属专业大类。

## 6. API 契约

### 6.1 请求

```text
GET /api/v1/positions/matches
```

查询参数：

- `exam_type`、`year`、`province`、`city`、`keyword`：与岗位查询一致；
- `match_status`：`potential`、`eligible`、`uncertain`、`ineligible`、`all`，默认 `potential`；
- `page`：最小 1；
- `page_size`：1～100。

`potential` 表示同时返回 `eligible` 和 `uncertain`，避免因档案缺失或规则能力不足而静默漏掉可能符合的岗位。

请求未提供 `exam_type`、`province` 或 `city` 时，分别使用 profile 中对应 target 字段作为默认粗筛条件；显式 query
parameter 优先。`year` 和 `keyword` 不从 profile 推断。

### 6.2 响应

```json
{
  "items": [
    {
      "position": {},
      "match_status": "uncertain",
      "reasons": [],
      "missing_profile_fields": ["household_registration"]
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

- `total` 是应用 `match_status` 后的匹配结果总数，不是粗筛候选总数；
- `missing_profile_fields` 只列出本岗位实际需要、但用户尚未填写的字段；
- 不公开岗位来源元数据、数据库字段或完整用户档案。

### 6.3 错误

- 缺失或无效 Bearer token：HTTP 401；
- query parameter 非法：HTTP 422；
- 用户尚未确认权威档案：HTTP 409；
- 粗筛候选岗位超过配置上限：HTTP 422，提示用户增加考试、年份或地区过滤条件。

## 7. 候选集与分页

禁止先按数据库 page 分页再执行资格过滤。正确流程是：

```text
SQL 粗筛并计数
  → 候选数超过上限则拒绝
  → 稳定顺序读取全部有界候选
  → 对每个候选运行 rule engine
  → 应用 match_status
  → 计算正确 total
  → 最后执行内存分页
```

候选集默认上限为 2000，通过 `POSITION_MATCH_CANDIDATE_LIMIT` 配置，最小 100、最大 10000，并同步维护
`.env.example`。Repository 查询仍使用 SQLAlchemy 参数绑定，候选顺序固定为 `year DESC, id DESC`。

## 8. Agent tool 契约

- tool 名称固定为 `match_positions`；
- 只接受岗位过滤、match status 和最多 10 条结果，不接受 `user_id` 或 profile；
- 当前用户身份和权威档案由服务端请求级 dependency 注入；
- tool 返回结构化匹配状态和精简 reasons；
- `query_positions` 保持原有语义，两个 tool 同时加入岗位咨询 graph 白名单；
- system prompt 要求涉及“我是否符合/能否报考”时使用 `match_positions`，不得自行推断。

## 9. 验收标准

1. 已确认档案用户能够获得正确分页的三态岗位结果；
2. 未确认档案返回 409，不把全空档案当作已确认；
3. 明确失败优先于未知，缺失信息不被错误放行；
4. 学历“仅限”和“及以上”语义不同且有回归测试；
5. 专业精确列表未命中可以失败，专业大类无法映射时返回 uncertain；
6. 户籍缺失和自由文本限制返回 uncertain；
7. 候选集超过上限时拒绝无界扫描，匹配分页 total 正确；
8. `match_positions` 不接受用户身份或档案参数，并与 `query_positions` 同时可用；
9. 不调用真实 LLM，不修改数据库 schema；
10. Ruff、mypy strict、pytest、coverage、pre-commit 和 Alembic drift 检查通过。
