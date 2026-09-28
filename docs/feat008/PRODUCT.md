# feat008：多轮档案 Interviewer 与缺失字段补全闭环

## 目标

为不熟悉结构化表单的用户提供逐项问答式档案补全能力。系统按固定顺序询问岗位硬条件字段，用户可以回答或显式跳过，最终仍通过现有 `/parse/confirm` 确认并写入权威档案。

## 用户流程

1. 用户开始新的 Interview，或继续本人处于 `confirming` 状态的档案 session。
2. 系统基于档案快照和已跳过字段，给出下一个固定问题。
3. 用户提交当前问题的回答，系统仅提取当前字段；无法理解时继续追问同一字段。
4. 用户也可以显式跳过当前字段。
5. 八个硬条件字段均已填写或跳过后，状态变为 `ready_to_confirm`。
6. 客户端使用现有 `/parse/confirm` 提交最终档案，完成权威档案更新。

## 字段范围与顺序

1. `education`
2. `major`
3. `political_status`
4. `fresh_graduate`
5. `work_experience_years`
6. `gender`
7. `age`
8. `household_registration`

本功能不强制询问考试类型、省份、城市等搜索偏好。

## API

- `POST /api/v1/parse/interview/start`：开始或继续 Interview。
- `POST /api/v1/parse/interview/answer`：回答或跳过当前问题。
- `POST /api/v1/parse/confirm`：复用既有接口完成最终确认。

## 非目标

- 不接入 Chat Router。
- 不使用 LangGraph `interrupt`。
- 不自动确认档案。
- 不让 LLM 决定提问顺序、修改其他字段或判断岗位资格。
- 不包含语音、图片、专业类别推断和搜索偏好访谈。

