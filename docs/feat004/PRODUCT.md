# feat004：岗位检索能力闭环需求

## 1. 背景

feat003 已建立可信用户身份，feat002 已建立岗位模型和基础 Repository。首个 Agent 垂直链路还缺少可独立验证、可被
HTTP 和 Agent 共同复用的岗位检索能力。若直接接入 LangGraph、LLM、SSE 和 checkpoint，查询规则与编排问题会相互耦合。

## 2. 目标

- 提供受 Bearer 认证保护的岗位分页查询接口；
- 通过 Application Service 隔离 HTTP、Agent 与 SQLAlchemy；
- 提供名为 `query_positions` 的 Agent tool adapter，为后续 LangGraph 注册保留稳定边界；
- 对分页和过滤输入进行规范化与校验；
- 仅公开岗位业务字段，不暴露 ORM、来源元数据和内部时间字段。

## 3. 范围

### 包含

- `GET /api/v1/positions`；
- `exam_type`、`year`、`province`、`city`、`keyword` 查询；
- `page`、`page_size` 分页；
- 岗位查询 Application Service 与不可变结果 DTO；
- `query_positions` tool adapter；
- schema、service、tool、HTTP 与 Repository 测试。

### 不包含

- 根据用户档案执行学历、专业、户籍、应届生等资格匹配；
- 岗位收藏、报告、档案解析与确认；
- Excel/CSV 正式岗位导入与外部岗位数据源；
- LLM、LangGraph graph、SSE、Redis 与 checkpoint；
- 新增或修改数据库表结构。

## 4. 产品契约

- 接口必须携带有效 Bearer token；
- `page` 最小为 1，`page_size` 范围为 1～100，非法输入返回 HTTP 422；
- 空白过滤参数按未提供处理；
- `province` 同时匹配指定省份和“国家”岗位；
- `city`、`keyword` 使用不区分大小写的包含查询，`keyword` 匹配岗位名称或部门；
- 返回 `items`、`total`、`page`、`page_size`；
- 空查询返回空列表和总数 0，不返回 404；
- 不返回 `source_url`、`data_version`、数据库时间字段和其他内部字段。

## 5. 验收标准

1. 已认证用户能够组合条件查询岗位并获得稳定分页响应；
2. 缺失或无效身份凭据返回 HTTP 401；
3. HTTP route 和 tool adapter 复用同一个 Application Service；
4. tool 名称固定为 `query_positions`，返回结构化结果；
5. 查询使用 SQLAlchemy 参数绑定，不拼接用户输入 SQL；
6. OpenAPI 正确展示查询参数、响应结构和 Bearer security；
7. Ruff、mypy strict、pytest 与覆盖率门禁通过；
8. 不连接生产数据库、真实外部服务或 LLM。
