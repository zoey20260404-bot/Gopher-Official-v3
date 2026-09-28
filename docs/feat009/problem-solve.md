# feat009 问题与决策记录

## 为什么 interrupt 不放在档案逐字段问答中

档案 Interview 是固定顺序、HTTP 驱动的小状态机，数据库状态更直接。报告生成包含明确的 graph 暂停和恢复语义，且审批发生在下游生成前，更符合 LangGraph `interrupt` 的适用场景。

## 为什么 Redis checkpoint 不是业务权威源

Checkpoint 服务于 graph 恢复，不适合作为报告列表、用户归属、幂等状态和最终内容的唯一存储。Redis 数据丢失时报告业务记录仍应可查询并明确显示失败或当前状态。

## 为什么暂不输出冲稳保

现有 profile 没有用户预估分数，岗位历史分数也可能缺失。仅凭资格匹配给出冲稳保会制造伪精度，因此本期使用“优先考虑/需要复核”的可验证分类。

## Migration downgrade 不能只考虑空库

新增 `pending_approval` 和 `rejected` 后，直接恢复旧 check constraint 会被已有数据阻止。downgrade 在重建旧约束前先把这两种状态归并为 `failed`，并通过插入真实新增状态后的完整 downgrade cycle 验证。

## Redis 集成测试清理

测试前确认 Redis DB0 无 key 且无 Search index；测试按 thread 精确删除 checkpoint，结束后仅删除 saver 创建的 `checkpoint` 和 `checkpoint_write` index，不使用全库清空命令。
