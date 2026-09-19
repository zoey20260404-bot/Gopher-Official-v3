# feat003：最小身份认证闭环需求

## 1. 背景

feat001 已建立 FastAPI 工程基础，feat002 已建立用户模型、Repository 和 transaction 约定。后续岗位查询、
Agent 对话、收藏、报告和 memory 都必须从可信身份获得 `user_id`，不能允许客户端或模型自行指定用户身份。

## 2. 目标

- 提供注册、登录和当前用户档案读取接口；
- 使用强密码哈希保存凭据，不保存或返回明文密码；
- 使用有过期时间的 JWT access token 建立 Bearer 身份；
- 通过 FastAPI dependency 向后续业务注入当前用户；
- 保持 Repository 不提交事务，由用例边界管理 commit/rollback；
- 在数据库层保证用户名大小写不敏感唯一。

## 3. 范围

### 包含

- `POST /auth/register`；
- `POST /auth/login`；
- `GET /api/v1/profile`；
- 用户名去空白、转小写和格式校验；
- Argon2 密码哈希；
- JWT HS256 access token；
- Bearer token 解析与 `get_current_user` dependency；
- 用户名大小写不敏感唯一 migration；
- schema、service、security、HTTP 契约与 migration 测试。

### 不包含

- refresh token、登出、token 黑名单和会话撤销；
- RBAC、第三方 OAuth、验证码、找回密码与登录限流；
- profile 创建和编辑；
- Redis session、Agent、LLM、SSE 与 checkpoint。

## 4. 产品契约

- 用户名长度 3～64，只允许英文字母、数字和下划线，保存前转小写；
- 密码长度 8～128，数据库只保存 Argon2 hash；
- 重复用户名返回 HTTP 409；
- 用户不存在和密码错误统一返回 HTTP 401；
- token 缺失、伪造、过期或对应用户不存在统一返回 HTTP 401；
- 用户尚无档案时，profile 接口返回空对象而不是 404；
- HTTP response 和 OpenAPI schema 不暴露 `password_hash`。

## 5. 验收标准

1. 注册、登录和受保护 profile 链路可用；
2. JWT 仅以字符串 `sub` 标识用户，并包含 `iat`、`exp`；
3. Argon2 操作不阻塞 asyncio event loop；
4. 并发注册最终由 PostgreSQL unique index 防止大小写重复用户名；
5. 注册 transaction 正常提交、异常回滚，Repository 不自行 commit；
6. 配置模板包含 JWT 配置且不提交真实 secret；
7. Ruff、mypy strict、pytest 和覆盖率门禁通过；
8. 不连接生产数据库、真实外部服务或 LLM。
