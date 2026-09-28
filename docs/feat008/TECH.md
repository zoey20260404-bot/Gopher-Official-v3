# feat008 技术设计

## 架构边界

- PostgreSQL `user_sessions` 是 Interview 流程的权威状态源。
- `profile_snapshot` 始终是纯 `ProfileData`；新增 `interview_state JSONB` 保存流程元数据。
- 确定性状态机选择字段和问题；LLM 只负责当前字段的 structured extraction。
- 最终持久化权威档案继续复用 `/parse/confirm`。

## 状态模型

`interview_state` 包含：

- `status`：`waiting_answer`、`needs_clarification`、`ready_to_confirm`。
- `current_field`：当前待补字段；完成时为 `null`。
- `question_id`：当前问题的 UUID；完成时为 `null`。
- `asked_fields`：已发出问题的字段。
- `skipped_fields`：用户显式跳过的字段。
- `turn`：已发出的不同问题数量。
- `last_request_id`：最近成功处理的 answer 请求，用于幂等重试。

## 一致性与并发

Answer 使用两阶段短事务：

1. 第一阶段对 session `SELECT ... FOR UPDATE`，校验归属、session 状态、`question_id` 和当前字段后释放事务。
2. 在事务外调用 LLM。
3. 第二阶段再次加锁并复核问题；若问题已推进则返回 `409`，否则合并单字段结果并推进状态机。

相同 `request_id` 的重试直接返回当前权威状态，不重复调用 LLM。`question_id` 过期或 session 非 `confirming` 时返回 `409`。

## LLM 边界

输出固定为：

```json
{"understood": true, "value": "本科"}
```

`value` 仅允许字符串、整数、布尔值或 `null`。Service 会把它写入当前字段并通过完整 `ProfileData` 再校验；不合法或未理解时保持同一问题并进入 `needs_clarification`。

Parser 未配置时，开始 Interview 和显式跳过仍可工作；普通回答返回 `503`。Provider 或 structured output 失败返回 `502`。

## Migration

在 `user_sessions` 新增非空 `interview_state JSONB`，默认 `{}`。已有 session 因此保持兼容。

## 为什么本阶段不用 LangGraph interrupt

本流程是字段顺序固定、状态较小且由 HTTP request 驱动的业务状态机，PostgreSQL 行锁、幂等键和显式 API 已能完整表达一致性。`interrupt` 更适合后续报告生成流程中的人工审批：届时暂停点位于昂贵或不可逆的下游动作之前，并由 checkpoint 保存 graph execution state。

