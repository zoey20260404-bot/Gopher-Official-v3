# feat002：数据模型与 v1 兼容基线需求

## 1. 背景

Python 项目已完成工程初始化，但尚无业务数据模型。后续认证、档案解析、岗位检索、Agent 对话、
记忆和报告均依赖稳定的数据契约。本需求以 `Gopher-Official-v1` 当前实现为业务基线，先建立
Python 版数据地基，不进行 Go 代码逐文件翻译。

## 2. 目标

- 使用 PostgreSQL 统一承载 v1 的 MySQL 业务数据和 pgvector 长期记忆；
- 建立用户、档案、会话、岗位、收藏、报告和记忆的数据模型；
- 使用 Alembic 管理可升级、可回滚的数据库 schema；
- 建立异步 Repository 边界和 transaction 约定；
- 固化 v1 API、SSE 和业务枚举的兼容基线；
- 为后续需求提供可测试的数据访问基础。

## 3. 用户价值

本需求不直接提供新的用户界面。它通过数据库约束、身份关联和可重复 migration，保证后续功能不会
因数据歧义、跨用户访问或手工建表产生不可控问题。

## 4. 范围

### 包含

- PostgreSQL/pgvector schema；
- SQLAlchemy 2.x async models；
- users、user_profiles、user_sessions、positions、favorites、reports、memories；
- Repository Protocol 及最小 User/Position 实现；
- 首个 Alembic migration；
- v1 兼容矩阵；
- model、repository、migration 测试。

### 不包含

- 注册、登录和 JWT HTTP 接口；
- Parser、LangGraph、LLM、SSE；
- 完整岗位导入和 v1 正式数据迁移；
- 收藏、报告和记忆的业务服务；
- embedding 生成、召回和 checkpoint。

## 5. 验收标准

1. Alembic 可从空库升级到 head、降级到 base，并重新升级；
2. `vector` extension 可用，核心业务表、索引、外键和约束正确；
3. JSON 数据使用 JSONB，不以字符串保存；
4. 所有时间字段使用带时区的 UTC 时间；
5. Repository 不自行 commit，由上层控制 transaction；
6. 用户名、session ID、report ID、收藏关系等唯一约束生效；
7. Ruff、mypy strict、pytest 和覆盖率门禁通过；
8. 不连接真实 LLM，不使用生产数据。
