# feat009 技术设计

## 状态与职责

- PostgreSQL `reports`：业务权威状态、用户归属、请求快照、审批结果、最终报告和幂等键。
- Redis LangGraph checkpoint：保存 graph execution state 和 `interrupt` 暂停点。
- feat007 `PositionMatchService`：候选岗位和资格结论的唯一来源。
- LLM：只生成已批准岗位的摘要与行动建议，不决定资格状态或扩大候选范围。

报告状态：

```text
processing → pending_approval → processing → completed
                            └→ rejected
任意执行失败 → failed
```

## Graph

```text
START → human_review(interrupt)
                    ├─ approve → generate_report → END
                    └─ reject  → reject_report   → END
```

`interrupt` 位于候选方案已确定、最终 LLM 报告尚未生成的位置。这样用户能先检查资格依据和候选集合，也避免为被拒绝的方案消耗生成成本。

恢复时使用同一 `thread_id`：

```text
user:{user_id}:report:{report_id}
```

## 并发与幂等

审批采用短事务：

1. 加锁读取本人报告，校验 `pending_approval`、候选代码和 `request_id`。
2. 将报告原子转换为 `processing` 并提交，阻止并发恢复。
3. 在数据库事务外执行 `Command(resume=...)` 和 LLM。
4. 再次短事务写入 `completed`、`rejected` 或 `failed`。

同一 `request_id` 在流程完成后返回已有结果；其他并发决策返回 `409`。数据库事务不会覆盖整个模型调用。

## Grounding

Graph state 只包含档案快照、候选岗位事实、确定性 match status/reasons 和用户批准的岗位代码。structured output 必须且只能覆盖全部批准岗位，Service 复核岗位代码集合后才持久化。

最终 `result` 同时保存：

- proposal：确定性候选方案；
- approval：用户决策和批准代码；
- generated_report：LLM structured output；
- source facts：用于审计的岗位与资格依据。

## Migration

- 扩展 `reports.status` 约束，增加 `pending_approval` 和 `rejected`。
- 增加 `request_snapshot JSONB`。
- 增加可空 `last_request_id`，支持审批幂等。

## 实施记录

- 2026-09-28：确认 feat009 为“候选方案 → interrupt 审批 → 恢复生成报告”闭环。
- 2026-09-28：基于本地 LangGraph 1.2.11 验证 `interrupt(value)` 与 `Command(resume=...)`。
- 2026-09-28：完成报告 API、确定性 proposal、审批幂等、structured report 和 PostgreSQL Repository。
- 2026-09-28：真实 PostgreSQL upgrade/downgrade、带业务状态 downgrade、Redis checkpoint 恢复验证通过。
- 2026-09-28：全量测试 161 个通过，覆盖率 91.32%；Ruff、mypy 和 pre-commit 检查通过。
