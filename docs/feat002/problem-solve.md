# feat002：问题与解决记录

开发和验证过程中出现的代表性问题记录于此。

## 1. ORM metadata 为空

### 现象

首次定义 model 时只继承普通 mixin，没有任何类进入 SQLAlchemy 的声明式继承树，导致
`Base.metadata` 为空，model 也没有 SQLAlchemy 自动生成的构造器。

### 解决

让抽象的 `BigIntPrimaryKeyMixin` 继承 `Base` 并设置 `__abstract__ = True`，业务 model 再继承该
mixin。这样共享主键字段和声明式映射同时生效。

## 2. Alembic downgrade 后版本表仍存在

### 现象

集成测试最初假设 downgrade 到 `base` 后数据库不存在任何表，实际仍保留
`alembic_version`。

### 解决

修正测试预期。`alembic_version` 属于 Alembic 自身的迁移状态表，不是业务表；业务表全部删除、
vector extension 按设计保留即视为 downgrade 成功。

## 3. 异步测试中运行 Alembic 冲突

### 现象

在 pytest 的 async test 中调用 Alembic 时，`migrations/env.py` 再次执行 `asyncio.run()`，触发
“event loop is already running”。

### 解决

将 migration 准备放在同步测试入口，再用独立 `asyncio.run()` 执行 Repository 场景，避免嵌套
event loop，同时保持生产 migration 入口简单明确。

## 4. 唯一性定义产生 schema drift

### 现象

`users.username` 和 `user_profiles.user_id` 同时存在 unique constraint 与 unique index，虽然约束
正确，但产生冗余结构，`alembic check` 报告 metadata 与数据库不一致。

### 解决

删除 migration 中重复的匿名 unique constraint，保留 ORM 对应的具名 unique index。重新执行
upgrade → downgrade → upgrade 后，`alembic check` 无新增操作。

## 5. Docker Desktop 要求更新 WSL

### 现象

首次启动 Docker Desktop 时 engine 未运行，日志显示 `wslUpdateRequired`。

### 解决

执行 `wsl.exe --update` 并重启 Docker Desktop，随后 PostgreSQL/pgvector 和 Redis 容器均通过
health check。
