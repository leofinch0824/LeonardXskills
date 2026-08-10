# 第 1 步角色任务包 · {{ROLE}}

> 这是该角色唯一允许读取的输入包。只写 `{{OUTPUT_PATH}}`，不要读取或修改其他角色文件、`run-state.md` 或父级汇总。

## 主题与运行模式

- **主题：** {{TOPIC}}
- **角色：** {{ROLE}}
- **锚定模式：** {{ANCHORING_MODE}}
- **独立性档位：** {{INDEPENDENCE_TIER}}

## 角色职责与优先渠道

{{PERSONA_GUIDANCE}}

## 原始提示词逐字片段

{{ORIGINAL_PROMPT}}

## 来源分级

{{GRADING_RULES}}

## 输出范本

{{ROLE_TEMPLATE}}

## 完成条件

- 只写 `{{OUTPUT_PATH}}`。
- 保存两个核心立场句、最强证据、独家洞见、完整视角分析、成功与失败检索、未决问题。
- A/B 的每个来源字段只写一个裸 http(s) URL，不加说明；额外来源拆成新的检索记录。C 不补造 URL。
- 写完运行角色文件校验：`{{VALIDATE_COMMAND}}`。
- 只返回文件路径与校验状态。
