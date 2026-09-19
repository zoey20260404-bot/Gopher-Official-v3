# feat005：最小 Agent 对话闭环技术设计

## 1. 调用链

```text
POST /api/v1/chat
  → get_current_user
  → ChatService
  → LangGraph StateGraph
       agent/model ──tool call──→ query_positions ──→ agent/model
  → messages/custom stream
  → SSE delta/tool events
```

## 2. Graph

使用 `MessagesState`、一个 model node、一个 `ToolNode` 和 conditional edge 构造 ReAct loop。当前只有一个
业务 Agent，不增加没有路由价值的独立 Router。模型只绑定经过 Pydantic 输入约束的 `query_positions`。

## 3. Checkpoint

运行时使用 `AsyncShallowRedisSaver`，测试使用 `InMemorySaver`。thread ID 格式为：

```text
user:{user_id}:session:{session_id}
```

Redis checkpoint 默认 1440 分钟 TTL，读取时刷新。项目 Redis 镜像升级到包含 RedisJSON 和 Search 的 Redis 8。
现有 `UserSession` 的状态属于档案解析流程，本需求不错误复用该表。

## 4. 生命周期与配置

FastAPI lifespan 在 `AGENT_ENABLED=true` 时初始化 ChatOpenAI 和 Redis saver；关闭时退出 saver context。由于岗位
Service 绑定请求级 SQLAlchemy session，每次 Chat 请求使用共享模型/saver 和当前 Service 编译轻量 graph，避免全局对象
持有已经关闭的 session。配置为空或初始化失败时记录不可用状态，其他 API 仍能启动，Chat dependency 返回 503。

## 5. SSE 映射

- graph `messages` stream 中的 AI text chunk → `delta`；
- tool 内通过 custom stream writer 发出的生命周期 → `tool`；
- graph 开始 → `status`；
- 正常结束 → `done`；
- 流中异常 → 脱敏后的 `error`。

## 6. 测试

- 使用 deterministic fake chat model 验证无 tool 和 tool loop；
- 使用 fake graph 验证 SSE framing、事件顺序和异常；
- 使用 FastAPI dependency override 验证 HTTP 契约；
- 使用本地 Redis 8 验证 checkpoint 恢复和用户隔离；
- 不调用真实模型 API。

## 7. 实施记录

- 2026-09-19：确认 feat005 实现 Chat、LangGraph、岗位 tool、SSE 与 Redis checkpoint；
- 2026-09-19：从 `main` 创建 `feature/zoey/feat005`；
- 2026-09-19：引入 `langchain-openai` 与 `langgraph-checkpoint-redis`。
- 2026-09-19：完成显式 ReAct graph、岗位 structured tool、SSE Chat API 和安全降级生命周期；
- 2026-09-19：使用本地 Redis 8 验证 shallow checkpoint 多轮恢复与用户隔离。
- 2026-09-19：60 个测试通过，覆盖率 94.97%；Ruff、mypy strict、pre-commit 和 Alembic drift 检查通过。
