# feat007：问题与解决记录

## 记录约定

开发与验证中发现的代表性问题、原因、解决方案和防回归措施记录于此。

## 2026-09-28：资格过滤不能发生在数据库分页之后

- 现象：现有岗位 Repository 先计算 total 再执行 SQL offset/limit，适合客观岗位查询，但资格判断依赖多项 Python 规则；
- 风险：先取得一页岗位再删除不符合项，会导致页面条数、total 和后续页边界全部失真；
- 解决：Repository 先计数并有界读取全部粗筛候选，Service 对完整候选集匹配并应用状态过滤，最后计算 total 和切片；
- 防回归：保留包含 eligible、uncertain、ineligible 混合候选的第二页分页测试。

## 2026-09-28：计数与读取之间仍可能发生候选数量竞争

- 现象：Service 完成 count 后到 list 之前，数据库可能插入新的符合粗筛条件的岗位；
- 风险：只按上限读取会静默截断，并错误地把部分结果当作完整结果；
- 解决：Repository 最多读取 `candidate_limit + 1` 条，Service 同时检查 count 和实际列表长度，任一越界都拒绝请求；
- 防回归：分别测试 count 已超限和 count 后读取越限两个分支。

## 2026-09-28：Redis Search checkpoint 只能使用 DB 0

- 现象：为隔离集成测试最初使用 Redis DB 15，Redis Search 创建索引时报 `Cannot create index on db != 0`；
- 原因：Redis Search 索引仅支持 DB 0，逻辑 DB 不能用于 checkpoint 索引隔离；
- 解决：确认本地 Redis DB 0 和索引列表为空后执行 checkpoint 测试，完成后精确删除测试创建的 `checkpoint` 与
  `checkpoint_write` 索引；PostgreSQL 仍使用独立临时数据库；
- 防回归：运行 checkpoint 集成测试前检查 DB 0 和索引状态，禁止在存在未知数据时清库或覆盖索引。
