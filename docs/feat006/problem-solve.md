# feat006：问题与解决记录

## 记录约定

开发与验证中发现的代表性问题、原因、解决方案和防回归措施记录于此。

## 2026-09-28：认证查询与写 transaction 不能共用隐式 transaction

- 现象：`get_current_user` 会使用请求级 `AsyncSession` 查询用户，SQLAlchemy 因此自动开启 transaction；若档案写接口随后
  对同一 session 再执行 `session.begin()`，会出现 transaction 已开启错误；
- 风险：直接 commit 或 rollback 认证 dependency 产生的 transaction，会让 Application Service 隐式依赖 dependency 的执行顺序；
- 解决：档案写 Service 使用独立 repository context，为每个写用例创建短 transaction；认证 session 继续只负责请求身份读取；
- 防回归：需要显式提交的写用例不得假定请求级 session 尚未 autobegin。

## 2026-09-28：模型调用不能占用数据库 transaction

- 现象：自然语言解析依赖外部模型，响应时间和失败模式均不可控；
- 风险：先创建 `parsing` session 再等待模型会长期占用数据库连接和行锁，并留下不可确认的半成品；
- 解决：先完成 structured output 调用和 Pydantic 校验，成功后才开启短 transaction 创建 session 并保存草稿；
- 防回归：任何 LLM、HTTP 或其他慢速外部调用都必须位于数据库 transaction 之外。

## 2026-09-28：子集测试触发全局 coverage 门禁

- 现象：单独执行三个真实集成测试时用例全部通过，但 pytest 因只覆盖 31% 源码而返回失败；
- 原因：项目在 pytest 全局参数中启用了 `--cov=gopher_agent` 和 `fail_under=80`；
- 解决：最终验收在同一隔离 PostgreSQL/Redis 环境执行完整测试套件，80 个测试全部通过，覆盖率 94.55%；
- 防回归：带全局 coverage 门禁的项目不能用测试子集的进程退出码代表集成用例结果，最终应运行完整套件。
