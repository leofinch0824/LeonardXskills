# Learn Loop 模板资源拆分设计

> 状态：**已实施，本文已按当前实现对齐**（核对日期：2026-08-04）。

## 目标

降低 agent 读取 `skills/learn-loop/assets/template.html` 时的上下文消耗：模板仅保留页面结构、内容槽位与固定资源引用；将固定 CSS 和 JavaScript 拆至独立文件。用户打开生成结果时仍获得一个完整、可交互的学习页面，但不强制交付物必须是单个 HTML 文件。

## 复核结论（2026-08-04）

本设计与需求一致：agent 只需读取轻量的 HTML 骨架并替换内容槽位；固定样式和交互逻辑由相邻资源文件加载；学习者只需打开 HTML 页面即可获得完整体验。这里的“单文件感知”指一个可直接打开的页面，而不是要求交付目录中只能存在一个物理文件。

实施前的差异如下，现已全部处理：

- `assets/template.html` 曾内嵌全部 CSS 和 JS，模板约 1,200 行，固定实现代码占主要篇幅。
- `SKILL.md`、`reference/html-guide.md` 与根 `README.md` 曾写有“单文件”或“无外部依赖”的严格要求。
- `validate_stage.py` 曾只验证 HTML 的学习内容契约，不验证相对 CSS/JS 是否随 HTML 一同交付；测试 fixture 也只写入 HTML。

现已拆出 `assets/template.css`、`assets/template.js`，添加 `scripts/render_template.py`，并同步更新三份文档、资源校验和 fixture。模板现为 308 行，仅保留 HTML 骨架、内容槽位、资源引用与最小无 JS 兜底。

## 约束

- 保留现有 HTML 占位符集合和替换语义，不新增内容填充责任。
- 保留现有页面行为：导航、闪卡自评、已读状态、洗牌/弱项筛选、搜索、打印、无 JavaScript 降级和可访问性处理。
- CSS/JS 是 skill 的固定资产；agent 不修改它们，只填 `template.html` 中明确的 `{{...}}` 内容槽位。
- 默认交付可由一个 HTML 文件及同目录的固定 `template.css`、`template.js` 构成；浏览者感知为一个完整页面，不出现额外操作步骤或外部网络依赖。
- 如需便携的单 HTML 文件，可提供可选内联渲染；这不是日常生成的前提。
- 不改变 Markdown 事实源、阶段闸门或模式 A/B/C 协议。

## 方案

### 文件职责

| 文件 | 职责 |
|---|---|
| `assets/template.html` | 页面骨架、内容区、占位符、`template.css`/`template.js` 的相对引用，以及最小无 JS 兜底结构 |
| `assets/template.css` | 全部固定 CSS：布局、响应式、打印、动画、闪卡和无障碍视觉样式 |
| `assets/template.js` | 全部固定 JS：视图切换、状态存储、闪卡工具条、章节已读、搜索和打印生命周期 |
| `scripts/render_template.py` | 可选工具：将相对资源引用内联为独立 HTML，并验证引用路径与占位符安全 |
| `reference/html-guide.md` | 说明 agent 只替换内容槽位；说明默认同目录资源交付和可选内联方式 |
| `SKILL.md`、根 `README.md` | 将“严格单文件、无外部依赖”改为“完整单页体验、仅携带同目录本地资源” |

### 资源装配

模板直接使用浏览器可识别的相对资源引用：

```html
<link rel="stylesheet" href="template.css" />
<script src="template.js"></script>
```

因此在 `assets/` 中打开模板即可预览；生成页面时将两个固定资源复制到 HTML 所在目录即可正常浏览。资源必须来自 skill 包内，且不引用 CDN、网络地址或 skill 包外路径。可选渲染工具仅用于需要单个可迁移 HTML 的场景；它不改变默认的同目录资源交付方式。

### Agent 可见边界

模板按“内容填充区”组织，并在每个区域保留注释标题：

- 页面标题和总览：`TOPIC`、`METHOD_INTRO`、`STEP_MAP`
- 十步标题/目的/提炼/可视化/正文/取证：`STEP_N_*`
- 题库和快问快答：`STEP_8_CARDS`、`STEP_10_QUIZ`
- 收尾：`CLOSING_*`、`LOOP_DIAGRAM`

固定资源不出现在这些填充区中。占位符集合继续由测试从模板和 guide 交叉核对。

## 验证策略

1. 模板契约测试确认 CSS/JS 资源文件存在、相对引用各出现一次，模板主体不含大段内联 `<style>`/`<script>`。
2. 可选渲染工具测试确认 CSS/JS 可正确内联、资源越界路径被拒绝、占位符原样保留。
3. HTML 闸门新增资源契约：相对 `template.css`、`template.js` 必须存在于 HTML 同目录，且不得指向网络或目录外路径；fixture 使用默认的同目录资源交付方式。
4. 继续确认状态行、无 JS 降级、答案折叠、取证折叠和无残留占位符。
5. 全量 `poetry run pytest tests/ -q` 和 `python3 -m py_compile skills/learn-loop/scripts/*.py` 必须通过。

> 验证结果：`poetry run pytest tests/test_learn_loop.py -q` 为 40 个通过、6 个 subtests 通过；`poetry run pytest tests/ -q` 为 65 个通过、6 个 subtests 通过；Python 编译与 `git diff --check` 均通过。

## 不在本次范围

- 不重写页面视觉设计或交互行为。
- 不把 Markdown 事实源改为 HTML/JS 数据源。
- 不引入第三方前端构建依赖；可选渲染工具仅使用 Python 标准库。
