# feat005：问题与解决记录

## 记录约定

开发与验证中发现的代表性问题、原因、解决方案和防回归措施记录于此。

## 2026-09-19：全局 graph 不能捕获请求级数据库 session

- 现象：模型和 checkpointer 适合在 lifespan 中复用，但岗位 tool 所用 Service 持有请求级 `AsyncSession`；
- 风险：把完整 graph 做成应用单例会在请求结束后继续引用已关闭 session；
- 解决：lifespan 只共享模型和 saver，每个 Chat 请求使用当前 Position Service 绑定 tool 并编译轻量 graph；
- 防回归：任何全局 Agent 资源不得直接持有 FastAPI 请求级 dependency。

## 2026-09-19：非流式兼容模型不产生 AIMessageChunk

- 现象：真实 graph 配合 deterministic fake model 时收到完整 `AIMessage`，最初的 SSE 转换只识别
  `AIMessageChunk`，因此最终答案被静默丢弃；
- 原因：部分模型适配器不支持 token streaming，会在 messages stream 中一次返回完整消息；
- 解决：`ChatService` 同时接受 `AIMessageChunk` 和 `AIMessage`，前者逐 token 输出，后者输出单个完整 delta；
- 防回归：保留真实 compiled graph → ChatService 的流映射测试，不只测试人工构造的 stream。
