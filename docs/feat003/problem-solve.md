# feat003：问题与解决记录

开发与验证中出现的代表性问题记录于此，后续随实际验证结果更新。

## 1. 密码哈希会阻塞 event loop

### 问题

Argon2 为抵抗暴力破解而刻意消耗 CPU 和内存。直接在 `async def` 中执行虽然语法合法，但会阻塞运行
FastAPI 请求的 event loop。

### 解决

`AuthService` 使用 `asyncio.to_thread` 执行 hash 和 verify。数据库 I/O 继续使用 SQLAlchemy async，CPU 密集
的密码操作进入有界工作线程。

## 2. 先查询再注册不能防止并发重复

### 问题

两个请求可能同时查询到用户名不存在，然后同时 INSERT。只依赖 Service 预查询存在 TOCTOU 竞态。

### 解决

保留预查询以提供清晰错误，同时新增 PostgreSQL `lower(username)` unique index 作为最终一致性边界，并将
INSERT 的完整性冲突转换为 `UsernameAlreadyExistsError`。
