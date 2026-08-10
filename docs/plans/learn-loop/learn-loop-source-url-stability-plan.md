# Learn Loop 来源 URL 稳定化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task.

**Goal:** 让 Learn Loop 的 `来源 URL` 字段只接受单一裸 HTTP(S) URL，并保证最终 HTML 将合法来源稳定渲染为链接。

**Architecture:** 在共享契约层提供唯一的 URL 规范化函数，阶段校验器与 Markdown 渲染器共同调用它。角色任务包明确单 URL 形态；HTML 校验器补充最后一道“来源 URL 必须是锚点”的输出闸门。

**Tech Stack:** Python 3.11、标准库 `urllib.parse`、markdown-it-py、unittest。

## Global Constraints

- 只修改 `skills/learn-loop/`、`tests/test_learn_loop.py` 和本计划。
- 不修改已有 `learning/` 产物，不改变非 `来源 URL` 字段的链接行为。
- 不增加依赖，不提交或推送 Git 变更。

---

### Task 1: 锁定单 URL 契约

**Files:**
- Modify: `tests/test_learn_loop.py`
- Modify: `skills/learn-loop/scripts/contract_io.py`
- Modify: `skills/learn-loop/scripts/validate_stage.py`
- Modify: `skills/learn-loop/reference/stages/01-perspectives.md`
- Modify: `skills/learn-loop/reference/perspectives.md`
- Modify: `skills/learn-loop/templates/perspective-role.md`
- Modify: `skills/learn-loop/templates/perspective-task.md`

**Interfaces:**
- Produces: `canonical_http_url(value: str) -> str | None`

- [x] 添加阶段 1 集成测试：复合的“主 URL + 佐证 URL”字段必须产生 `SOURCE_URL` 违规。
- [x] 运行该测试，确认它因当前宽松校验而失败。
- [x] 实现 `canonical_http_url`，允许单一 `http/https` URL 和字段末尾可选中文句号，拒绝内部空白、拼接来源与说明性中文标点。
- [x] 让第 1 步角色校验调用共享函数，并在角色契约与任务范本中写明额外来源必须拆成独立检索记录。
- [x] 重跑测试确认通过。

### Task 2: 稳定渲染并补充 HTML 闸门

**Files:**
- Modify: `tests/test_learn_loop.py`
- Modify: `skills/learn-loop/scripts/render_learning_page.py`
- Modify: `skills/learn-loop/scripts/validate_stage.py`

**Interfaces:**
- Consumes: `canonical_http_url(value: str) -> str | None`
- Produces: 合法来源字段的单一 `<a href>`；非法复合字段拒绝渲染。

- [x] 添加渲染测试：带查询参数和尾随空白的单 URL 生成正确锚点，复合 URL 被拒绝。
- [x] 添加 HTML 集成测试：存在裸 `来源 URL` 的最终页面必须触发 `HTML_CONTRACT`。
- [x] 运行新增测试，确认它们对现有实现报出预期失败。
- [x] 让 `_linkify_source_urls` 捕获完整字段值并调用共享契约；让 HTML 校验器检查五视角来源行锚点。
- [x] 运行新增测试、Learn Loop 可运行 unittest、技能包快速校验和目标产物复现检查。

## 自审

- 需求覆盖：输入契约、阶段校验、渲染和最终 HTML 闸门均有对应任务。
- 范围控制：不启用全局 linkify，不改 CSS，不重写现有学习产物。
- 无占位符；函数名和测试边界在两项任务间一致。
