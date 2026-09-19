# feat003：最小身份认证闭环技术设计

## 1. 请求链路

```text
HTTP JSON
  → Pydantic schema 规范化与校验
  → FastAPI dependency 组装 AuthService
  → UserRepositoryProtocol
  → SQLAlchemy AsyncSession
  → PostgreSQL
```

认证后请求：

```text
Authorization: Bearer <JWT>
  → HTTPBearer
  → TokenManager 验证签名/必需 claims/过期时间
  → sub 转为正整数 user_id
  → Repository 加载 User
  → get_current_user 注入业务接口
```

## 2. 安全决策

- 使用 FastAPI 官方当前推荐的 `pwdlib` 与 Argon2；
- Argon2 属于 CPU 密集操作，通过 `asyncio.to_thread` 执行，避免阻塞 event loop；
- 用户不存在时仍验证 dummy hash，减少用户名枚举的计时差异；
- 使用 PyJWT，decode 时固定算法列表并要求 `sub`、`iat`、`exp`；
- 当前仅允许 HS256，secret 少于 32 字符时拒绝创建 TokenManager；
- JWT 不保存 profile 和密码等可变或敏感数据；
- 登录失败使用统一响应，response schema 与 ORM model 分离。

## 3. 数据与 transaction

应用层在校验前将 username 执行 `strip().lower()`。数据库新增：

```sql
CREATE UNIQUE INDEX uq_users_username_lower ON users (lower(username));
```

Repository 通过 `lower(username)` 查询，以兼容可能包含大写字母的 v1 历史数据；函数索引同时服务查询并阻止
绕过应用写入的大小写冲突。原精确匹配索引暂时保留以避免修改 feat002 历史 migration。注册 route 使用
`session.begin()` 管理一次写入 transaction；Repository 只 `flush`。预查询改善错误响应，数据库约束解决
并发竞态，Repository 将用户 INSERT 的 `IntegrityError` 转换为业务冲突。

## 4. API

| Method | Path | 成功状态 | 认证 |
| --- | --- | --- | --- |
| POST | `/auth/register` | 201 | 否 |
| POST | `/auth/login` | 200 | 否 |
| GET | `/api/v1/profile` | 200 | Bearer |

登录使用 JSON 请求体，与 v1 路径和现有客户端语义保持一致；本需求不宣称实现完整 OAuth2 password flow。

## 5. 测试策略

- schema：用户名规范化、格式和密码长度；
- security：Argon2、JWT 往返、过期 token、不安全配置；
- service：注册、重复用户、登录成功与模糊失败；
- repository：flush、查询和 profile 查询；
- HTTP：路径、状态码、transaction 进入、响应脱敏、空 profile 和 OpenAPI Bearer scheme；
- migration：继续执行 upgrade → downgrade → upgrade，并用 Alembic drift check 验证 metadata 一致。

## 6. 实施记录

- 2026-09-19：确认 feat003 采用最小认证闭环范围；
- 2026-09-19：创建 `feature/zoey/feat003` 分支；
- 2026-09-19：引入 pwdlib/Argon2 与 PyJWT，完成认证分层、API 和 username migration。
- 2026-09-19：本地隔离 PostgreSQL 完成 migration 往返、schema drift、大小写唯一约束和 Repository 验证；
- 2026-09-19：实际启动 API，跑通注册、登录、Bearer profile、重复注册 409 和无凭据 401。
