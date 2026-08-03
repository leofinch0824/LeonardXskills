# Learn Loop HTML 模板与交互改良方案

> 状态：**仅方案，未实施**。本文档自包含，执行者可据此直接动手。
> 范围约束：不动 SKILL.md 十步流程、不动任何 Markdown 产物结构、**零新增占位符、零新增渲染义务**。

## 一、背景

`assets/template.html` 是十步闭环的唯一视图层，`reference/html-guide.md` 是其渲染契约。现状已做到：阅读序≠生成序、双层信息架构、答案折叠、施考状态行、结构闸门。但与 skill 理念（检索练习、主动回忆、可留存可复习）对照，仍存在一批已验证的不足。

## 二、已验证的不足清单（源码实证，非推测）

### P0 · 理念差距（功能改良核心）

| # | 不足 | 证据 | 违背的理念 |
|---|---|---|---|
| 1 | 闪卡展开答案后**无自评机制**，回忆→对照→自评的检索练习闭环断在最后一环 | `.flash` 仅原生 `<details>` | 检索练习（模式 B 的视图层预习形态） |
| 2 | 学习地图是**纯导航**，无"学到哪/掌握多少"的记录 | `.step-map` 仅 `<a>` | 可复习、弱项定位 |
| 3 | 题库顺序固定、无洗牌/筛选，重复自测时产生顺序记忆 | `{{STEP_8_CARDS}}` 静态渲染 | 测试效应（变式与随机化） |

### P1 · 真实缺陷（内容不可达）

| # | 不足 | 证据 | 后果 |
|---|---|---|---|
| 4 | **打印/PDF 只输出当前页**：`.view{display:none}` 不打印，未 `open` 的 `<details>` 内容 UA 不渲染 | 现有 CSS + UA 行为 | "可留存"教材无法完整导出 |
| 5 | **禁 JS 时非首页视图全部不可达**：视图切换纯 JS 驱动，无 `<noscript>` 降级 | template.html 无 noscript | 单文件健壮性失守 |
| 6 | **Cmd-F 搜不到未激活视图**：`display:none` 不参与浏览器页内查找 | 同上 | "可复习"资料无法检索定位 |
| 7 | **切换视图不滚顶**：`show()` 无 `scrollTo`，从长页底部切走后停在新页中段 | 现有 JS | 导航体验断裂 |

### P2 · 健壮性与可访问性

| # | 不足 | 备注 |
|---|---|---|
| 8 | 无 `aria-current`、切视图后焦点滞留侧栏 | 读屏/键盘用户迷失 |
| 9 | 移动端抽屉无 Esc/外点关闭、`aria-expanded` 缺失 | `.menu` 仅 toggle class |
| 10 | 无 `prefers-reduced-motion` 兜底（`scroll-behavior:smooth`） | 前庭障碍用户 |
| 11 | `.prose` 内表格窄屏溢出 | 产物表格多，移动端必现 |
| 12 | 隐私模式/file:// 下 localStorage 可能抛异常 | 新交互的存储需 try/catch + 内存兜底 |

## 三、改良设计

### 总原则

1. **零新增占位符**：自评按钮、工具条、已读 toggle 全部由模板 JS **运行时注入 DOM**。生成物源码与既有闸门检查面（占位符残留、状态行、flash-answer、id 重复等）完全不变，渲染者义务不变。
2. **状态边界（对齐不变量 6 的精神）**：自评/已读是本机浏览器状态，存 localStorage（键格式 `learn-loop:<document.title>`，按教材隔离；无存储权限时退化为内存态）。UI 文案固定为「自评仅存本机浏览器，与施考成绩无关」——**不得**把自评标记渲染成施考成绩，施考状态行仍以 `08-exam-record.md` 的 `当前游标` 为唯一依据。
3. **先对照后自评**：自评按钮注入 `.flash-answer` 内部末尾，流程上强制先展开答案再标记。
4. **书写纪律（模板维护者）**：`<script>`/`<style>` 内每个 `}` 单独成行，禁止连续 `}}`/`{{`——产物闸门的占位符残留检查是文本级的，连续花括号会误报。

### 3.1 闪卡检索练习闭环（P0-1/3）

- `{{STEP_8_CARDS}}` 与 `{{STEP_10_QUIZ}}` 各包一层 `<div class="deck">`（CSS `display:flex;flex-direction:column`，洗牌用 `order` 实现，不动 DOM 顺序语义）。
- JS 向每个 ≥1 张 `.flash` 的 `.deck` 前注入工具条：
  `[洗牌重练] [只看未掌握] [全部收起]　已掌握 X/N`
- JS 向每张卡的 `.flash-answer` 末尾注入：
  `自评（仅存本机浏览器）：[答对了] [答错了]`
- 卡片身份：对 summary 文本做 djb2 hash 作为存储键（洗牌后身份不变）；状态写到卡片 `data-self="known|unknown"`，CSS 给边框色与 summary 角标（✓/✗）。
- 「只看未掌握」：`.deck.only-weak .flash[data-self="known"]{display:none}`。
- 进度计数实时更新；快问快答卡组与题库卡组各自独立统计。

### 3.2 章节进度（P0-2）

- JS 向每个 `.view` 的 `.step-head` 注入 `.read-toggle` 按钮（文案：`标记本章已读` / `✓ 本章已读`）。
- 已读视图在侧栏 nav 对应链接显示圆点（`a.read .num::after`），学习地图页同步可见。
- 存储键 `read:<view-id>`，与自评共用同一 localStorage 命名空间。

### 3.3 打印导出（P1-4）

- `@media print`：`.view{display:block!important}`、`.rail,.menu,.search{display:none!important}`、`.main{margin:0}`。
- `beforeprint`：暂存当前视图，给所有视图加 `active`、给所有未开 `<details>` 补 `open` 并标记 `data-print-open`；`afterprint` 恢复。
- CSS 保底 + JS 增强 details，双保险。

### 3.4 禁 JS 降级（P1-5）

`</head>` 前加一行：

```html
<noscript><style>.view{display:block}.rail{position:static;width:auto}.main{margin-left:0}.menu,.search{display:none}</style></noscript>
```

平铺全部视图，导航失效但内容全可读。

### 3.5 页内搜索（P1-6）

- rail 内 brand 区下方加 `<input type="search">` + 结果容器。
- 输入 ≥2 字符：遍历各视图缓存的 `textContent`，大小写不敏感匹配，结果项显示「视图标题 + 命中片段 ±30 字」；点击跳转到该视图并加一次性 `.hit-flash` 闪烁动画。
- 不做多结果高亮、不做拼音/模糊匹配（80/20 止步）。

### 3.6 导航与可访问性修复（P1-7、P2-8/9/10/11）

- `show()` 补 `window.scrollTo(0,0)`、`aria-current="page"` 的 set/remove、焦点落到目标视图标题（`tabindex=-1` + `focus({preventScroll:true})`）。
- Esc 关闭移动端抽屉、点击主区关闭、`aria-expanded`/`aria-controls` 同步。
- `@media (prefers-reduced-motion: reduce)`：关平滑滚动与动画。
- `.prose table{display:block;overflow-x:auto}` 防窄屏溢出。

## 四、契约与闸门同步

### `reference/html-guide.md`

- 「事实源和模板」节：把"不改 CSS、侧栏结构或 JS"更新为——渲染只替换占位符；**交互层（自评、进度、搜索、打印）由模板 JS 运行时注入，生成物源码不携带交互标记**。
- 新增「交互层与状态边界」节：自评/已读 ≠ 施考记录、不进事实源、不得写入 HTML 源码；洗牌/筛选不改变事实源题库顺序。
- 「答案必须可折叠」节补：自评按钮位于 `.flash-answer` 内（先对照后自评）。
- 「交付前检查」节补：`<noscript>` 降级存在（闸款项）；注明**本版零新增占位符**。
- 增补模板维护纪律：script/style 内花括号分行书写。

### `scripts/validate_stage.py`

`validate_html` 只加一条结构检查：

```python
if "<noscript>" not in text:
    violations.append(f"HTML 缺少 noscript 降级（JS 禁用时全部视图应可读）：{path.name}")
```

不加自评/进度的闸门——它们是运行时注入，源码中不存在，无可查；其边界由文案约定 + 人工复核保障。

### `tests/test_learn_loop.py`（只增不删既有断言）

1. 新增 `test_template_placeholders_are_documented_in_guide`：模板全部 `{{[A-Z0-9_]+}}` ⊆ html-guide.md 文本（防契约漂移）。
2. 新增 `test_template_script_and_style_avoid_double_braces`：模板 script/style 块内无连续 `{{`/`}}`（守护书写纪律）。
3. 新增 `test_html_rejects_missing_nojs_fallback`：无 `<noscript>` 的产物被拦。
4. 两个既有 `test_html_*` fixture 的手写 HTML 补 `<noscript></noscript>`（spec 演进的 fixture 适配，断言不动）。
5. 两个 `--all` 完整 fixture 无需改动（产物由模板生成，自动继承 noscript）。

### TDD 顺序

先写 1–3 失败用例 → 实现闸门与模板 → 全绿 → 同步 guide。每组改完跑 `poetry run pytest tests/ -q`。

## 五、明确不做（及理由）

| 项 | 理由 |
|---|---|
| 暗色模式 | 视觉偏好而非功能改良；现有变量体系已为此留好扩展点，需要时再加 |
| pushState 支持后退键 | `replaceState` 避免历史噪音是合理现状；章节回退由侧栏导航承担 |
| 施考游标/复习到期日渲染进页面 | 需要新增占位符 = 新增渲染义务，超出本次"零渲染义务变更"约束；归下一轮 |
| 多结果高亮/拼音搜索 | 复杂度不成比例，片段预览已解决定位问题 |
| 自评数据统计页 | 视图层不累积分析职能；弱项分析是模式 B 的职责 |

## 六、全局验收

- `poetry run pytest tests/ -q` 全绿，无既有断言被删或放宽。
- 产物中无自评/已读状态被写入 HTML 源码（运行时状态）。
- 模板占位符集合与 guide 清单一致（新测试守护）。
- 模板 script/style 无连续花括号（新测试守护）。
- 手工冒烟：渲染产物在浏览器中验证——自评刷新后保留、打印预览含全部 12 个视图、禁用 JS 内容全可读、搜索可定位未激活视图内容。
