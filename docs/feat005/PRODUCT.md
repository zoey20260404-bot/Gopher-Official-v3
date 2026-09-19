# feat005：最小 Agent 对话闭环需求

## 1. 背景

feat003 已提供可信身份，feat004 已提供可复用的岗位查询 tool。本需求把这些能力接入 LangGraph，通过 SSE
向客户端提供可持续多轮的岗位咨询对话，并使用 Redis 保存短期 checkpoint。

## 2. 目标

- 提供受 Bearer 认证保护的 `POST /api/v1/chat`；
- 使用显式 LangGraph ReAct loop 调用白名单 `query_positions` tool；
- 通过 SSE 输出 `status`、`tool`、`delta`、`done`、`error`；
- 以认证用户和服务端 session ID 隔离 checkpoint；
- Redis 保存带 TTL 的最新对话状态；
- 测试不连接真实 LLM 或外部服务。

## 3. 产品契约

- 请求包含 1～4000 字符的 `message` 和可选 UUID `session_id`；
- 未提供 session ID 时由服务端生成，并在首个 `status` 事件返回；
- checkpoint thread key 由服务端组合 `user_id` 和 `session_id`，客户端不能指定用户身份；
- Agent 未启用或配置不完整时，在开始流式响应前返回 HTTP 503；
- 流开始后的内部异常转换成通用 `error` 事件，不暴露 traceback；
- Agent tool 单次最多向模型返回 10 条岗位；
- `done` 表示本轮完整结束，`error` 表示本轮失败，两者互斥。

## 4. 范围外

- 多 Agent Router、档案解析、收藏和报告；
- 长期 memory、embedding 与语义召回；
- 对话列表、标题、归档和删除；
- checkpoint time travel 和完整步骤历史；
- 真实 LLM 联调与生产部署。

## 5. 验收标准

1. 已认证用户可以获得合法 SSE 对话事件；
2. 模型能够调用 `query_positions` 并继续生成回答；
3. 同一用户/session 可恢复上下文，不同用户相互隔离；
4. 未认证、非法请求和未配置 Agent 分别返回 401、422、503；
5. Redis 使用异步 shallow saver 和 TTL；
6. 应用关闭时释放 checkpoint 连接；
7. Ruff、mypy strict、pytest、coverage 和 pre-commit 通过。
