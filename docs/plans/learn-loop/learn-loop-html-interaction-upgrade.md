# Learn Loop HTML 模板与交互改良方案

> 状态：**历史实施记录，已由 [`learn-loop-ui-redesign-plan.md`](learn-loop-ui-redesign-plan.md) 取代**（2026-08-04）。本文保留二态自评与零新增占位符阶段的设计背景，不再描述当前模板；当前实现以 UI 重设计计划和 `skills/learn-loop/reference/html-guide.md` 为准。
> 范围约束：不动 SKILL.md 十步流程、不动任何 Markdown 产物结构、**零新增占位符、零新增渲染义务**。

## 一、背景

`assets/template.html`、`template.css` 与 `template.js` 共同构成十步闭环的固定视图层，`reference/html-guide.md` 是其渲染契约。以下清单记录实施前已验证的不足；本方案的修复已经落在模板、guide、validator 和测试中。

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
| 5 | **禁 JS 时非首页视图全部不可达**：视图切换纯 JS 驱动，无 `<noscript>` 降级 | template.html 无 noscript | 页面健壮性失守 |
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

## 二·一、实施状态（按当前源码核对）

| 条目 | 状态 | 当前实现证据 |
|---|:---:|---|
| P0-1 闪卡自评 | [x] | 模板 JS 向 `.flash-answer` 注入“答对了/答错了”，状态写入按文档隔离的 `localStorage` 键 |
| P0-2 章节进度 | [x] | 模板 JS 注入“标记本章已读”，同步侧栏和学习地图状态 |
| P0-3 洗牌与弱项筛选 | [x] | 每个 deck 有“洗牌重练 / 只看未掌握 / 全部收起”和进度计数，使用 CSS `order` 不改事实源顺序 |
| P1-4 打印/PDF | [x] | `@media print` 与 `beforeprint/afterprint` 展开全部视图和 details |
| P1-5 禁 JS 降级 | [x] | 模板含 `<noscript>` 平铺视图；validator 使用正则识别带空白/属性/换行的合法起始标签 |
| P1-6 页内搜索 | [x] | JS 建立全部视图索引，提供标题、命中片段和跳转闪烁 |
| P1-7 导航滚顶 | [x] | `show()` 调用 `window.scrollTo(0, 0)` |
| P2-8 可访问性导航 | [x] | `aria-current`、目标标题聚焦和 `aria-expanded` 同步 |
| P2-9 移动端抽屉 | [x] | Esc、点击主区关闭及菜单状态同步 |
| P2-10 动效降级 | [x] | `prefers-reduced-motion` 关闭平滑滚动和动画 |
| P2-11 窄屏表格 | [x] | `.prose table` 使用横向滚动容器 |
| P2-12 存储兜底 | [x] | `localStorage` 读写均 try/catch，失败时保留当前页面内存态 |

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

## 四、契约与闸门同步（已完成）

### `reference/html-guide.md`

- 「事实源和模板」节：把"不改 CSS、侧栏结构或 JS"更新为——渲染只替换占位符；**交互层（自评、进度、搜索、打印）由模板 JS 运行时注入，生成物源码不携带交互标记**。
- 新增「交互层与状态边界」节：自评/已读 ≠ 施考记录、不进事实源、不得写入 HTML 源码；洗牌/筛选不改变事实源题库顺序。
- 「答案必须可折叠」节补：自评按钮位于 `.flash-answer` 内（先对照后自评）。
- 「交付前检查」节补：`<noscript>` 降级存在（闸款项）；注明**本版零新增占位符**。
- 增补固定资源维护纪律：`template.js`/`template.css` 内花括号分行书写。

### `scripts/validate_stage.py`

`validate_html` 使用正则识别合法的 `<noscript ...>` 起始标签，并在模板使用外链资源时验证 `template.css`、`template.js` 均为同目录可读取文件。

```python
if not NOSCRIPT_OPEN_TAG.search(text):
    violations.append(f"HTML 缺少 noscript 降级（JS 禁用时全部视图应可读）：{path.name}")
```

不加自评/进度的闸门——它们是运行时注入，源码中不存在，无可查；其边界由文案约定 + 人工复核保障。

### `tests/test_learn_loop.py`（只增不删既有断言）

1. 新增 `test_template_placeholders_are_documented_in_guide`：模板全部 `{{[A-Z0-9_]+}}` ⊆ html-guide.md 文本（防契约漂移）。
2. 新增模板资源契约测试：CSS/JS 独立存在、HTML 各引用一次且不再内嵌大段实现；`render_template.py` 覆盖同目录复制与可选内联。
3. 新增 `test_html_rejects_missing_nojs_fallback`：无 `<noscript>` 的产物被拦。
4. 两个既有 `test_html_*` fixture 的手写 HTML 补 `<noscript></noscript>`（spec 演进的 fixture 适配，断言不动）。
5. 两个 `--all` 完整 fixture 无需改动（产物由模板生成，自动继承 noscript）。

### TDD 顺序（实施记录）

已按“先写失败用例 → 确认跨行起始标签被误报 → 最小化放宽 validator 匹配 → 回归测试”的顺序完成。

## 五、明确不做（及理由）

| 项 | 理由 |
|---|---|
| 暗色模式 | 视觉偏好而非功能改良；现有变量体系已为此留好扩展点，需要时再加 |
| pushState 支持后退键 | `replaceState` 避免历史噪音是合理现状；章节回退由侧栏导航承担 |
| 施考游标/复习到期日渲染进页面 | 需要新增占位符 = 新增渲染义务，超出本次"零渲染义务变更"约束；归下一轮 |
| 多结果高亮/拼音搜索 | 复杂度不成比例，片段预览已解决定位问题 |
| 自评数据统计页 | 视图层不累积分析职能；弱项分析是模式 B 的职责 |

## 六、全局验收（完成项）

- [x] 交互模板、guide、HTML 闸门和回归 fixture 已同步；无新增占位符或 Markdown 渲染义务。
- [x] 产物中无自评/已读状态写入 HTML 源码，运行时状态与模式 B/C 施考记录保持边界。
- [x] 模板占位符集合与 guide 清单一致；固定 CSS/JS 已脱离 HTML 骨架，并由资源契约测试守护。
- [x] 手工验收所需能力已由模板实现：自评刷新保留、打印展开全部视图、禁用 JS 内容可读、搜索可定位未激活视图。
- [x] 40 个 learn-loop 测试用例已收录并通过；全量运行结果为 65 个测试、6 个 subtests 全部通过。
