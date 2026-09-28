# feat008 问题与决策记录

## LLM 调用不能占用数据库行锁

外部模型延迟不可控。如果在持有 `FOR UPDATE` 锁时等待 LLM，会放大连接占用和同 session 请求阻塞。因此 Answer 拆为“锁定读取—事务外解析—再次锁定提交”，第二阶段用 `question_id` 进行乐观复核。

## JSONB 原地修改可能不被 ORM 追踪

每次状态变化都构造并整体赋值新的 `dict`，不对已加载的 JSONB 对象原地修改，确保 SQLAlchemy 能检测变更。

## 跳过必须是显式动作

“不知道”“暂时不说”等自然语言可能存在歧义，不能由 LLM 擅自永久跳过字段。只有请求中的 `skip=true` 才写入 `skipped_fields`。

## Interview 与最终确认分离

`ready_to_confirm` 只表示提问结束，不会写入 `user_profiles`。这样用户仍有机会检查或修正完整档案，并保持 feat006 已建立的确认语义和幂等行为。

