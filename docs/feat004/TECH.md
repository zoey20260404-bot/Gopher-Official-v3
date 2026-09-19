# feat004：岗位检索能力闭环技术设计

## 1. 调用链

```text
GET /api/v1/positions             Agent graph（后续需求）
  → Bearer get_current_user         → PositionQueryTool
  → PositionSearchParams            → PositionQuery
  └──────────────┬───────────────────┘
                 ↓
          PositionSearchService
                 ↓
       PositionRepositoryProtocol
                 ↓
        SQLAlchemy AsyncSession
                 ↓
             PostgreSQL
```

## 2. 分层约定

- Repository 接收 `PositionQuery`，返回 ORM model 与总数，只负责持久化查询；
- Service 将 ORM model 映射为不可变 `PositionItem`，避免上层依赖 SQLAlchemy；
- HTTP 层将 query parameter 转换为 `PositionQuery`，再将 service DTO 转换为 Pydantic response；
- `PositionQueryTool` 只依赖 Service，使用 `name = "query_positions"` 作为后续 Agent 注册标识；
- 当前用户只用于建立可信请求边界，本期通用岗位过滤不读取用户档案。

## 3. 查询与分页

- `exam_type`、`year` 精确匹配；
- `province` 匹配指定省份或全国岗位；
- `city` 对城市执行 `ILIKE` 包含查询；
- `keyword` 对岗位名称和部门执行 `ILIKE` 包含查询；
- 排序固定为 `year DESC, id DESC`，保证分页顺序稳定；
- API 在 Pydantic 层拒绝非法分页，Repository 的规范化属性继续作为内部防御。

## 4. 输出边界

公开岗位展示和资格条件字段，但不公开 `source_url`、`data_version`、`created_at`、`updated_at`。
Service 结果不复用 API schema，使未来 CLI、Agent 或批处理调用不依赖 FastAPI/Pydantic transport 层。

## 5. Transaction

岗位检索是只读用例，不开启显式写 transaction，不执行 `commit`。请求结束时由 `get_session` 关闭 session。

## 6. 测试策略

- schema：空白规范化、分页边界和非法输入；
- service：Repository 调用与 ORM 到 DTO 的映射；
- tool：名称、参数传递和结构化结果；
- HTTP：认证依赖、组合查询、分页响应、空结果、422 和 OpenAPI；
- Repository：继续验证参数绑定、全国岗位语义与稳定排序；
- 数据库集成：使用本地隔离 PostgreSQL fixture，不连接生产环境。

## 7. 实施记录

- 2026-09-19：确认 feat004 聚焦岗位检索闭环，不纳入 LangGraph、LLM、SSE 和 checkpoint；
- 2026-09-19：从 `main` 创建 `feature/zoey/feat004`。
- 2026-09-19：完成岗位查询 Service/DTO、受保护 HTTP API 和 `query_positions` tool adapter；
- 2026-09-19：通过 Ruff、mypy strict、HTTP/单元测试、本地 PostgreSQL 集成测试和 Alembic drift 检查。
