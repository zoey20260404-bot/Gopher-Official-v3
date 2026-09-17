# feat002：数据模型与 v1 兼容基线技术设计

## 1. 架构决策

### 1.1 统一 PostgreSQL

v1 使用 MySQL 保存业务数据、PostgreSQL/pgvector 保存长期记忆。Python 版统一使用 PostgreSQL：

- 降低双数据库部署、事务和迁移复杂度；
- 使用 JSONB 表达档案快照和 Agent 结构化结果；
- 在同一数据库中使用 pgvector；
- 保留 Redis 作为短期会话和缓存，不将其作为权威数据源。

### 1.2 模型与 API Schema 分离

SQLAlchemy model 只表达持久化结构；Pydantic API schema 随后续具体接口需求创建。禁止将 ORM 对象
直接作为 HTTP 响应，避免数据库字段成为不可变的外部协议。

### 1.3 Transaction 边界

Repository 允许 `flush` 以获取数据库生成值，但不执行 `commit`。Application Service 或显式
transaction context 负责一次用例的提交和回滚。

## 2. 数据模型

| 表 | 职责 | 关键约束 |
| --- | --- | --- |
| users | 登录主体 | username 唯一 |
| user_profiles | 当前权威档案 | user_id 唯一，JSONB |
| user_sessions | 解析/业务会话元数据 | session_id 唯一 |
| positions | 岗位及竞争数据 | year + position_code 唯一 |
| reports | 冲稳保报告 | report_id 唯一，归属用户 |
| favorites | 用户收藏 | user_id + position_id 唯一 |
| memories | 长期画像/经验 | scope 约束，vector(1024) |

主键保留 bigint，便于迁移 v1 数据；对外 session/report 标识继续使用不可预测字符串。档案、报告结果、
其他限制和 metadata 使用 JSONB。

## 3. v1 兼容基线

### API 路径

后续需求保持 `/auth/register`、`/auth/login`、`/api/v1/parse`、`/api/v1/parse/confirm`、
`/api/v1/profile`、`/api/v1/positions`、`/api/v1/favorites`、`/api/v1/chat`、
`/api/v1/reports` 和 `/api/v1/reports/{id}` 的业务语义。

### SSE 事件

保留 `status`、`tool`、`delta`、`done`、`error`。本需求仅记录契约，不实现 SSE。

### 枚举

- mode：`beginner` / `advanced`；
- session status：`parsing` / `confirming` / `completed`；
- report status：`processing` / `completed` / `failed`；
- favorite category：`rush` / `stable` / `safe` / `custom`；
- memory scope：`session` / `user` / `agent`。

## 4. 已知差异

- v1 用 Unix int 时间；Python 版改为 PostgreSQL `timestamptz`；
- v1 把 JSON 保存为 text/json 字符串；Python 版使用 JSONB；
- v1 的业务数据位于 MySQL；Python 版统一到 PostgreSQL；
- 本需求不复制 v1 已知有问题的学历“仅限”、专业误放行和户籍缺失逻辑。

## 5. Migration 策略

首个 revision：

1. `CREATE EXTENSION IF NOT EXISTS vector`；
2. 按依赖顺序创建核心表；
3. 建立唯一约束、check constraint、外键和查询索引；
4. downgrade 逆序删除表；
5. downgrade 保留 vector extension，避免影响同库的其他应用。

## 6. 测试策略

- 单元测试：metadata、PostgreSQL DDL、Repository 行为和 transaction 回滚；
- 集成测试：在显式启用时连接本地 pgvector，执行 upgrade → downgrade → upgrade；
- 不使用真实模型、外部 API 或生产数据库。

## 7. 实施记录

- 2026-09-17：从 `main` 创建 `feature/zoey/feat002`；
- 2026-09-17：确认统一 PostgreSQL、API 兼容和增量 Repository 范围。
- 2026-09-17：完成 7 张核心表的 ORM model、枚举、约束和首个 Alembic revision；
- 2026-09-17：完成 User/Position Repository、显式 transaction 基础设施和查询分页；
- 2026-09-17：在本地 PostgreSQL 17 + pgvector、Redis 7 上通过 migration 往返、
  schema drift、Repository 提交/查询和异常回滚验证。
