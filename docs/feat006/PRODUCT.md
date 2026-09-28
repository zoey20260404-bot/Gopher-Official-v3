# feat006：用户档案解析与确认闭环需求

## 1. 背景

feat003 已建立可信用户身份，feat005 已完成可持续多轮的岗位咨询，但系统尚不能把用户的自然语言条件转换为
可信、可复用的结构化档案。数据库虽然预留了 `user_profiles` 和 `user_sessions`，当前只有档案读取接口，缺少
“解析草稿 → 用户确认 → 权威档案”的写入闭环。

## 2. 目标

- 提供受 Bearer 认证保护的 `POST /api/v1/parse`；
- 支持自然语言 `beginner` 模式和结构化 `advanced` 模式；
- 使用 LLM structured output 提取档案草稿，不允许模型猜测未知信息；
- 由服务端创建解析 session，并保存待确认的档案快照；
- 提供 `POST /api/v1/parse/confirm`，由用户确认或修正后写入权威档案；
- 保证 session、草稿和权威档案均按认证用户隔离；
- 测试不连接真实 LLM 或外部服务。

## 3. 范围

### 包含

- `POST /api/v1/parse`；
- `POST /api/v1/parse/confirm`；
- 用户档案的强类型 schema 和业务校验；
- Parser model adapter、Application Service 和 Repository；
- `UserSession` 创建、状态流转和归属校验；
- `UserProfile` transaction 内 upsert；
- deterministic fake model 的单元测试和隔离数据库集成测试；
- 更新 `GET /api/v1/profile` 的强类型档案响应。

### 不包含

- 多轮 Interviewer、自动追问和 SSE 解析流程；
- 使用档案自动筛除或推荐岗位；
- 学历“仅限”、专业目录、户籍等岗位资格匹配规则；
- PDF、图片、简历文件上传和 OCR；
- 长期 memory、embedding 和语义召回；
- 收藏、报告或多 Agent Router；
- 新增或修改数据库表结构。

## 4. 档案契约

档案字段如下，无法确定的信息必须为 `null`，不得根据常识补全：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `education` | `string \| null` | 当前或最高学历 |
| `major` | `string \| null` | 专业名称 |
| `political_status` | `string \| null` | 政治面貌 |
| `fresh_graduate` | `boolean \| null` | 是否应届毕业生 |
| `work_experience_years` | `integer \| null` | 基层或相关工作年限，最小为 0 |
| `gender` | `string \| null` | 性别 |
| `age` | `integer \| null` | 当前年龄，范围 16～100 |
| `household_registration` | `string \| null` | 户籍所在地 |
| `target_exam_type` | `string \| null` | 目标考试类型 |
| `target_province` | `string \| null` | 目标省份 |
| `target_city` | `string \| null` | 目标城市 |

空白字符串统一规范化为 `null`。本期不把业务值固化为枚举，避免不完整枚举拒绝合法用户信息。

## 5. API 契约

### 5.1 自然语言解析

`beginner` 模式接收 1～8000 字符的 `content`，不接收客户端提供的 profile：

```json
{
  "mode": "beginner",
  "content": "我今年24岁，计算机专业本科，应届生，想报考浙江杭州的省考"
}
```

系统使用 Parser structured output 生成草稿。Agent 未启用或模型资源不可用时，在创建 session 前返回 HTTP 503。

### 5.2 结构化录入

`advanced` 模式接收 `profile`，不调用 LLM：

```json
{
  "mode": "advanced",
  "profile": {
    "education": "本科",
    "major": "计算机科学与技术",
    "fresh_graduate": true,
    "age": 24,
    "target_province": "浙江省",
    "target_city": "杭州市"
  }
}
```

两种模式都返回服务端生成的 UUID `session_id`、`confirming` 状态、规范化后的 `profile`、
`missing_fields` 和非阻断性 `warnings`。原始自然语言不写入数据库。

### 5.3 确认档案

确认请求包含 `session_id` 和用户最终确认的完整 profile 快照：

```json
{
  "session_id": "5e6db8e4-b01c-4dbd-bdf8-b9220a22191c",
  "profile": {
    "education": "本科",
    "major": "计算机科学与技术",
    "fresh_graduate": true,
    "age": 24,
    "target_province": "浙江省",
    "target_city": "杭州市"
  }
}
```

- 只能确认属于当前认证用户且状态为 `confirming` 的 session；
- 确认在同一数据库 transaction 内更新 session snapshot、upsert `UserProfile` 并把 session 标记为
  `completed`；
- session 不存在或不属于当前用户时统一返回 HTTP 404，避免泄露其他用户 session；
- session 已完成且提交内容与已保存快照相同时按幂等成功处理；内容不同时返回 HTTP 409；
- profile 允许保留 `null` 字段，由用户决定是否在信息不完整时确认。

## 6. 状态流转与安全边界

```text
parse request
  → parsing（服务端内部创建）
  → confirming（草稿解析或校验成功）
  → completed（用户确认成功）
```

- 用户身份只从 Bearer token 获取，request body 和模型输出不能指定 `user_id`；
- Parser 不注册任何 tool，不执行用户文本中的指令；
- LLM 输出必须通过 Pydantic schema 校验后才能保存；
- Parser 失败时不留下可确认的 session；
- API 错误不返回 prompt、模型原始响应、traceback 或其他用户信息。

## 7. 验收标准

1. 已认证用户能够通过自然语言或结构化输入获得待确认档案；
2. 未知字段保持 `null`，响应准确列出 `missing_fields`；
3. 确认后 `GET /api/v1/profile` 返回最新权威档案；
4. session 不能被其他用户读取或确认；
5. 同一 transaction 完成 profile upsert 和 session 状态更新，异常时全部回滚；
6. beginner 模式未配置 Agent 时返回 503，advanced 模式仍可使用；
7. 重复确认遵守相同内容成功、不同内容冲突的幂等契约；
8. 不修改数据库 schema，不连接真实 LLM 或生产数据库；
9. Ruff、mypy strict、pytest、coverage、pre-commit 和 Alembic drift 检查通过。
