# learn-loop：把十步学习方法论复刻成可校验的 Agent Skill（定稿 v2）

> 状态：**已实施，本文已按当前实现对齐**（核对日期：2026-08-04）。
> 仓库内 skill 包路径为 `skills/learn-loop/`；README 中不带 `skills/` 的 `learn-loop/` 指安装到 skills 目录后的包根。

> 本文档是可实施的开发方案。v2 合入了三轮评审结论：
> ① 对初版计划的自我复盘（缺 Intake、可移植性矛盾、Goodhart 计数、信任型闸门）；
> ② 与 GitHub 参考实现 `ten-step-learning/` 的对照分析（吸收其开场两问、逐字提示词、逐环消费、每步提炼、题库化、HTML 交付；拒绝其单 agent 模拟五视角、材料化替代真实练习、无校验、无闭环）；
> ③ 架构调整：生成流水线与交互练习解耦为「一条流水线 + 两个练习入口」。

## Context

`docs/reference/用_Claude_Codex_Workbuddy_10倍速学习任何知识.md` 描述了融合 STORM 与检索练习法的十步学习闭环。原文形态是十段可复制的提示词，直接执行有四个问题：

1. **五视角由单个 agent 顺序写出**：后写的视角以先写的为条件，产出被编排的分工而非被发现的分歧，第 2 步矛盾图谱拆到的是修辞不是认知。
2. **"所有视角都同意的大概率是真的"只在独立同意时成立**：五个视角一致却无人拿得出来源，是模型先验在五个出口同时显形——表观置信度最高、可核查性最低。
3. **没有执行规范性约束**：跳步、少视角、考试三题收尾都不会被发现。
4. **交互时序错误**：原文第 8 步开头是"我刚学完"——考试应发生在用户真的花时间学过之后。把交互考试嵌进生成流水线，考出来的是零基础不是理解边界。

产出一个中文优先的 `learn-loop` skill，架构为**一条零打断生成流水线 + 两个用户主动触发的练习入口**：

- **模式 A · 生成流水线**（默认）：开场两问 → 自动跑完十步（第 8/9 步产出题库与费曼讲解材料，即"备课"）→ 交付 markdown 产物集 + 教科书式 HTML 页面及同目录固定资源。
- **模式 B · 施考会话**（用户说"考我"时触发）：读题库逐题施考、对照评分标准打分、逐题落盘、断点续考。
- **模式 C · 费曼会话**（用户说"给我讲/我来讲"时触发）：以模式 B 弱项为输入，跑真实的"教 → 复述 → 定位缺口 → 重教"循环。

三个模式通过 `run-state.md` 共享状态；复习队列到期提醒的正是"该回来考了"。**markdown 产物是唯一事实源，HTML 是渲染视图**——模式 B/C 与复习队列都要回读机器可解析的产物，施考后可重渲染 HTML 更新成绩。

工程骨架沿用 `paper-trail/`（路径锚点、preflight bootstrap、stdlib unittest 锁契约、零第三方依赖），方法论约束自立（视角独立性、检索练习真实发生）。

## 实现对齐摘要

| 计划区块 | 状态 | 当前实现证据 |
|---|:---:|---|
| 前置判断与移交 | [x] | `reference/pre-check.md`、`SKILL.md` 前置判断节、`run-state.md` 四字段和 stage 0 闸门 |
| 十步模式 A 与模式 B/C/复习协议 | [x] | `SKILL.md`、`reference/*.md`、15 份模板；模式 B 的 `当前游标` 与模式 C 的逐字复述边界已落盘 |
| 包契约与可移植路径 | [x] | `skills/learn-loop/` 下的 `agents/`、`assets/`、`reference/`、`scripts/`、`templates/` 全部存在 |
| 时间化运行目录与冲突避免 | [x] | `<YYYY-MM-DD>-<HHMMSS>-<topic-slug>` 规则、冲突追加序号和旧格式兼容已写入 `SKILL.md`，时间化 slug fixture 已覆盖 |
| 机器闸门与 CLI | [x] | `preflight.py`、`validate_stage.py`、`review_queue.py` 及 `tests/test_learn_loop.py` |
| HTML 视图与交互 | [x] | `assets/template.html` 已实现自评、已读、洗牌/弱项筛选、搜索、打印、无 JS 降级和可访问性处理；契约在 `reference/html-guide.md` |
| README 入口与运行说明 | [x] | README 已列出 learn-loop、触发语、preflight、产物目录和仓库结构；安装片段按安装后的包根书写 |

实现状态以当前文件为准；本计划不再把已落地条目标成“待实施”。模式 B/C 的会话动作由执行 skill 的 agent 按协议执行，不是额外的独立 Python 服务。

README 的相对链接、复制命令和快速开始命令按安装后的 skill 包根书写；从本仓库 checkout 直接运行时，应使用 `skills/learn-loop/` 前缀。该路径差异曾在本计划记录；2026-08-05 的知识收尾已将 README 的仓库内链接与命令统一改为 `skills/...`，安装后的包根用法仍保持不变。

> 验证注记（本工作树，2026-08-04）：`poetry run pytest tests/test_learn_loop.py -q` 为 40 个通过，`poetry run pytest tests/ -q` 为 65 个通过、6 个 subtests 通过。新增回归测试覆盖跨行 `<noscript>` 起始标签，以及固定 CSS/JS 的同目录交付和可选内联。

---

## 设计决策（已确认）

| 决策 | 选择 |
|---|---|
| skill 边界 | 单一 skill；模式 A 流水线 + 模式 B/C 练习入口 + 复习模式；run-state 落盘支持断点续跑与单步调用 |
| 提示词保真 | 两层结构：`reference/original-prompts.md` 逐字保存原文十段提示词（只挖占位符），纪律层只追加约束、不改写原文 |
| 规范性检查 | `scripts/validate_stage.py` 硬校验结构 + SKILL.md 语义闸门，互不替代 |
| 视角独立性 | 首选 5 个并行独立 subagent；定义三级降级序列（见不变量 1） |
| 取证方式 | 每个视角走自己的信息渠道；取不到标注来源等级，不阻断 |
| 第 8/9 步 | 流水线内材料化（题库/分层讲解）；真实施考与费曼循环移入模式 B/C，由用户决定何时开始 |
| 交付物 | markdown 产物集（事实源）+ 完整 HTML 页面（教科书式视图，携带同目录固定资源） |
| 跨轮回顾 | `learner-profile.md` + `review-queue.md`（1/7/30 天间隔，预留得分字段供将来自适应） |

**依赖**：全部 stdlib（`argparse`/`json`/`pathlib`/`datetime`/`re`/`html`），无需 `poetry add`。

---

## 一、核心不变量（写入 SKILL.md 顶部）

1. **视角独立性（含降级序列）**：第 1 步五个视角的产出者互不可见彼此输出，主 agent 只分发与收集。执行方式按可用性降级，且必须在 `run-state.md` 记录实际采用的档位：
   - `parallel`（首选）：5 个并行 subagent；
   - `serial-isolated`（次选，宿主无并行能力）：5 次串行独立调用，每个视角写盘前不得读其他四份产物；
   - `orchestrated`（最后手段，宿主无 subagent 能力）：主 agent 顺序写五段，第 2 步矛盾图谱必须标注「编排模式·分歧可信度降级」。
2. **取证渠道分化**：每个视角按自己的渠道优先级取证并落盘检索记录（查询词 / 渠道 / 命中数 / 是否采信）。
3. **来源等级强制标注**（覆盖第 1–5 步的所有主张与资源）：
   - `A` 一手可核查：有可解析 URL 且直接支持该主张；
   - `B` 二手或间接：有 URL 但为转述、或仅部分支持；
   - `C` 模型内生·未验证：无来源。
   检索工具不可用时整轮进入「未锚定模式」：全部记 C，`run-state.md` 标注，第 3/4 步产物与 HTML 顶部声明。
4. **共识必须分级**：≥2 视角一致、各自引用**不同**来源且至少一条 A/B → 「独立共识」；一致但全为 C → 「模型先验·待验证」，禁止进入简报前 3 个关键发现。
5. **盲区需以检索记录为前提**：各视角检索记录已落盘才可判「领域盲区」，否则只能写「未覆盖」。
6. **施考记录只能产生于模式 B/C 的真实会话**：模式 A 流水线不得生成任何答题记录或复述记录；模式 B/C 中模型不得代答、不得因用户未答而推进游标。此为**信任型不变量**（事后不可机器验证），缓解措施：答题与复述必须**逐字引用用户原话**（禁止转述），供人工抽查。
7. **原文提示词是法条**：各步执行指令 = `original-prompts.md` 对应段（填占位符，一字不改）+ 该步纪律附录（只追加约束与产出格式，不覆盖原文要求）。
8. **profile 只记录用户明确确认的长期事实**；从答题表现推断的倾向只写入本轮产物与复习队列，不回灌 profile。

---

## 二、路径契约

沿用 paper-trail 四锚点（复用 `paper-trail/scripts/preflight.py:100` `resolve_workspace_root`、`:93` `resolve_path`，改前缀）：

- `<skill-root>`：`SKILL.md` 所在目录
- `<workspace-root>`：显式参数 → `LEARN_LOOP_WORKSPACE_ROOT` → Git 根 → 当前目录
- `<state-root>`：`LEARN_LOOP_STATE_DIR`，默认 `<workspace-root>/.learn-loop`
- `<learning-root>`：`LEARN_LOOP_LEARNING_DIR`，默认 `<workspace-root>/learning`

派生：`<profile-path> = <state-root>/learner-profile.md`、`<queue-path> = <state-root>/review-queue.md`、`<index-path> = <learning-root>/INDEX.md`、`<run-dir> = <learning-root>/<YYYY-MM-DD>-<slug>`；当前 `<slug>` 为 `<HHMMSS>-<topic-slug>`，创建前检查冲突并在必要时追加 `-02`、`-03`，不覆盖既有产物。

skill 包只读；`--bootstrap` 是唯一写操作，只创建缺失文件，不覆盖。

---

## 三、文件树

```text
skills/learn-loop/
├── SKILL.md                      # 8 条不变量 + 路径契约 + preflight + 模式A十步闸门 + 模式B/C协议入口 + 交付
├── agents/openai.yaml            # 仓库惯例：display_name / allow_implicit_invocation: false
├── assets/
│   ├── template.html             # 轻量页面骨架：侧边栏(总览+十步+收尾)、三栏语义、翻卡题库、{{...}}占位
│   ├── template.css              # 固定视觉样式
│   └── template.js               # 固定交互逻辑
├── reference/
│   ├── pre-check.md              # 前置适用性判断与意图拆解纪律
│   ├── original-prompts.md       # 【法条层】原文十段提示词逐字保真，只挖 {{主题}}/{{角色}}/{{水平}}/{{目标}} 占位
│   ├── perspectives.md           # 【纪律层】第1步：五视角渠道优先级、三档独立性降级、A/B/C 定义、检索记录表规格
│   ├── conflict.md               # 【纪律层】第2-4步：实质/措辞/未决分歧分类、共识分级、盲区判定、可靠性打分推导规则
│   ├── curriculum.md             # 【纪律层】第5-7步：资源 URL 要求、阶梯规格、课程计数区间、消费上游要求
│   ├── examination.md            # 【纪律层】第8-9步：题库规格(题+参考答案+评分标准)、模式B施考协议(逐题落盘/游标/续考)、模式C费曼循环协议
│   ├── retention.md              # 【纪律层】第10步：速查表六件套、INDEX/queue/profile 回灌边界、复习模式协议
│   └── html-guide.md             # 模板占位符总清单、组件片段写法、渲染与重渲染(施考后更新成绩)规则
├── templates/                    # 每轮实例化到 <run-dir>
│   ├── 01-perspectives.md  02-conflicts.md   03-brief.md      04-review.md
│   ├── 05-resources.md     06-ladder.md      07-sprint.md
│   ├── 08-exam-bank.md           # 模式A产物：10题分级+参考答案+评分标准+5道终极挑战
│   ├── 08-exam-record.md         # 模式B产物：逐题施考记录(逐字引用用户回答)+游标
│   ├── 09-feynman-notes.md       # 模式A产物：分层费曼讲解材料(12岁版/预判困惑点/最终定义)
│   ├── 09-feynman-record.md      # 模式C产物：逐轮复述循环记录(逐字引用)+结束状态
│   ├── 10-cheatsheet.md
│   ├── run-state.md              # 前置判定 + 学习画像(两问答案) + 十步进度 + 独立性档位 + 锚定模式 + 练习状态 + 考试游标
│   ├── learner-profile.md        # 中性占位，无个人化默认值
│   └── review-queue.md           # 到期日 + 历次得分字段(预留自适应)
└── scripts/
    ├── preflight.py              # 路径解析 + bootstrap + 包完整性 + 检索/subagent 能力探测(写入建议档位)
    ├── validate_stage.py         # 结构硬校验：--run-dir <dir> --stage {0..10,exam-record,feynman-record,html} / --all，--json
    └── review_queue.py           # --add(登记1/7/30) / --due(到期查询) / --record-score(回写得分并推进间隔)
```

每份 `0N-*.md` 模板统一含三个骨架区：**「消费上游」**（声明本步吃了哪些上游产物文件）、**「产物」**（本步原始产出）、**「本步提炼」**（3–5 条给人看的 takeaway）。

---

## 四、模式 A · 生成流水线（SKILL.md 主体）

### 前置判断（已实现）

用户给出主题后先执行 `reference/pre-check.md` 规定的适用性判定，再决定是否初始化。判定记录随移交写入 `run-state.md` 的「前置判定」节；结论为「不适合」时不创建 run-dir、不执行 preflight。此门不替代模式 A 的开场画像三问。

### 第 0 步 · 开场两问（唯一一次计划内打断）

1. 当前水平 + 目标深度（零基础/有点基础/有经验 × 能聊两句/能上手干活/能和专业人士对谈，默认后者）；
2. 角色 / 使用场景（用户开场已给则不问）。

答案凝成一句「学习画像」写入 `run-state.md`，作为后续 `{{角色}}`/`{{水平}}`/`{{目标}}` 占位来源；slug 由主题生成。**闸门**：两问有答案（或记录"用户开场已提供"）；画像已落盘。

### 第 1 步 · 五视角（独立取证）

按不变量 1 选定并记录独立性档位。每个视角只拿到「主题 + 原文该视角段 + 自己的 persona 纪律」。渠道分化：

| 视角 | 渠道优先级 |
|---|---|
| 实践者 | 工程博客、issue tracker、事故复盘、从业者论坛 |
| 学者 | 同行评审论文、综述、会议录 |
| 怀疑者 | 复现失败报告、负面结果、撤稿与批评、对立立场长文 |
| 经济学家 | 融资与并购、定价与营收、市场规模报告 |
| 历史学家 | 相似先例的回顾性记述、行业史、失败案例分析 |

每视角产出：核心立场（两句）、最强证据（带 A/B/C）、独家洞见、检索记录表。
**闸门**：恰好 5 视角各自完整；每视角有检索记录；证据均有等级；独立性档位已记录且执行与之相符。

### 第 2 步 · 矛盾图谱

由只读五份原始产物的执行者完成。冲突先分类：**实质分歧**（双方各有 A/B 级来源且结论不兼容）→ 进图谱；**措辞分歧** → 剔除；**未决**（至少一方无来源）→ 单列待验证。产出：冲突项、关键裁决问题、共识分级表（独立共识/模型先验·待验证）、盲区（领域盲区/未覆盖）。
**闸门**：冲突已分类且实质分歧双方均引来源；共识已分级；盲区判定附检索记录依据；`orchestrated` 档位时已标注降级声明。

### 第 3 步 · 综合简报

按原文提示词（60 秒 CEO 段、5 关键发现按可靠性排序、隐藏关联、以{{角色}}的行动建议、前沿问题）。
**闸门**：每个发现挂来源等级与支持/反对视角；「模型先验·待验证」不出现在前 3 发现。

### 第 4 步 · 同行评审自检

可靠性 1–10 分**由来源等级与分歧类型推导**（规则在 `conflict.md`），另答：最没把握结论、过重视角、第 6 视角要不要加、教授评分。
**闸门**：5 发现逐个打分且附推导依据；第 6 视角问题有明确结论与理由。

### 第 5 步 · 资源筛选

恰好 5 个资源（原文如此，属法条）×4 字段 + 被高估的坑 + 一周路径。**每个资源必须有可解析 URL，或显式标 C 级**。
**闸门**:5 资源字段齐且有 URL 或 C 标；坑清单非空或明确"无"；一周路径覆盖 5 资源。

### 第 6 步 · 学习阶梯

5 级 × 8 字段（原文明确规格，精确校验）。结合 {{水平}} 在「本步提炼」指出用户当前所在级与下一里程碑。
**闸门**：5×8 全非空；已定位用户当前级。

### 第 7 步 · 2 小时核心 20%

先甄别核心 20% 并说明为何核心；课程计划 **8–12 次课**（原文提示词要求 10，校验器收区间防凑数），每课 5 字段 + **3–7 道**复习题；终局小项目。
**闸门**：核心 20% 有"为什么"；课数与题数在区间内；终局项目可验证。

### 第 8 步 · 题库（备考材料）

产出 `08-exam-bank.md`：恰好 10 题分级（1–3 初/4–6 中/7–8 高/9–10 专家）+ 每题参考答案 + 评分标准（满分/及格/常见薄弱点）+ 5 道终极挑战（只给题）。**流水线内不施考、不生成任何答题记录。**
**闸门**：10 题 + 5 挑战齐；每题有参考答案与评分标准；难度分档与题号匹配；无答题记录。

### 第 9 步 · 费曼讲解材料（备教材料）

产出 `09-feynman-notes.md`：对核心概念的三层讲解（12 岁版大白话+生活例子 / 预判 3–5 个易含糊点并逐个讲平 / 一句简单准确完整的最终定义）。
**闸门**：三层齐；困惑点 3–5 个；无复述记录。

### 第 10 步 · 速查表 + 渲染 + 回灌

速查表六件套（一句定义、短条目要点、3–5 例、易错易混、上场清单、**3–7 道**快问快答）。
渲染：按 `html-guide.md` 将全部产物填入 `assets/template.html` 副本，写出 `<run-dir>/<主题>-十步学习.html`；第 8/9 步区块展示题库与讲解材料，并附状态行「交互施考未进行，对我说"考我"即可开始」。
回灌：`<index-path>` 追加一行（日期/slug/主题/练习状态）；`<queue-path>` 登记 1/7/30 到期日；profile 仅写用户明确确认的长期事实。
**闸门**：六件套齐；HTML 无残留 `{{`；INDEX 与 queue 已追加；profile 更新有用户依据。

---

## 五、模式 B / C / 复习（SKILL.md 独立章节，协议在 `examination.md` / `retention.md`）

**模式 B · 施考**（触发语如"考我 <主题>"）：读 `08-exam-bank.md` 与 `run-state.md` 游标，从下一题继续。一次一题；用户答后四件套反馈（对照评分标准打 0–10、答对处、确切差距、简语重讲）；答弱先追问、答好加难。每题立即写 `08-exam-record.md`（**逐字引用用户回答**）并推进游标——续考唯一依据。10 题完成后：最终得分、最强/最弱领域、复习计划、5 挑战题移交用户；弱项（<6 分）写入 run-state 供模式 C；调 `review_queue.py --record-score`。

**模式 C · 费曼**（触发语如"给我讲 X / 我来讲 X"）：输入为模式 B 弱项（未施考则用步 3 核心概念），以 `09-feynman-notes.md` 为底稿跑真实循环：教 → 用户复述（逐字记录）→ 只重教含糊/跳步处 → 再复述，直到「已讲清」或显式记录「仍未通过」。用户讲清前不进新内容。逐轮写 `09-feynman-record.md`。

**复习模式**：`review_queue.py --due` 列出到期主题；复习 = 对该主题历史弱项重新施考（走模式 B 协议，题目优先从弱项相关题与终极挑战中取），结果回写队列并推进到下一间隔。

---

## 六、`scripts/validate_stage.py` 硬校验清单

纯 stdlib，`--run-dir <dir> --stage <s> / --all`，`--json`，非零退出码=未过。通用检查：必填章节存在；表格单元格非空；**占位符检查限定在表格单元格与标题行内**（避免误伤正文合法尖括号）；`0N-*.md` 的「消费上游」引用的文件确实存在于 run-dir、「本步提炼」3–5 条。

计数分两类：**结构承重 → 精确**；**教学任意 → 区间**。

| stage | 硬约束 |
|---|---|
| 0 | run-state 含前置判定四字段、学习画像来源标记、独立性档位、锚定模式和模式 A 状态 |
| 1 | 恰好 5 视角；每视角含 立场/最强证据/独家洞见/检索记录 四段；证据行均有 A\|B\|C |
| 2 | 每条冲突标 实质/措辞/未决；共识行标 独立共识\|模型先验·待验证；盲区标 领域盲区\|未覆盖 |
| 3 | 恰好 5 个关键发现，各有来源等级与支持/反对视角 |
| 4 | 5 发现各有 1–10 分 + 推导依据行；第 6 视角段非空 |
| 5 | 恰好 5 资源 × 4 字段；每资源 URL 非空或标 C；一周路径 ≥5 条目 |
| 6 | 5 级 × 8 字段全非空 |
| 7 | 课程数 ∈ [8,12] 且每课 5 字段；每课复习题 ∈ [3,7]；终局项目段非空 |
| 8 | 题库恰好 10 题 + 5 挑战；每题有参考答案与评分标准；分档与题号匹配；**bank 中无答题记录** |
| 9 | notes 三层齐；困惑点 ∈ [3,5]；**notes 中无复述记录** |
| 10 | 六件套齐且快问快答带答案；快问快答 ∈ [3,7]；INDEX 与 queue 已追加对应行 |
| exam-record | 记录行数与游标一致；每行含 逐字引用/得分/差距；分档与题号匹配 |
| feynman-record | 每弱项 ≥1 轮闭环；每轮含逐字复述；结束状态 ∈ {已讲清, 仍未通过} |
| html | 文件存在；无残留 `{{`；含 `<noscript>` 降级、答案折叠、取证默认收起和两种合法施考状态行 |

语义判断（分歧是否实质、打分推导是否成立、引用是否真是用户原话）留给 SKILL.md 闸门与人工抽查，脚本不做。

---

## 七、测试（`tests/test_learn_loop.py`）

沿用 `tests/test_paper_trail.py` 写法（stdlib unittest、Path 常量、tempfile、零依赖）：

1. **包契约**：REQUIRED_SKILL_FILES 齐（含 `assets/template.html`、`reference/original-prompts.md`）；无安装机绝对路径；含 `<skill-root>`/`<workspace-root>`/`<learning-root>` 占位（对应 `tests/test_paper_trail.py:63`）。
2. **法条保真**：`original-prompts.md` 包含原文十段的关键句（每段抽 1–2 句锚定，如"支持者们刻意忽略了哪些证据"、"其他视角绝不会提的事"、"讲给只有 60 秒的 CEO 听"、"不要一次给我所有答案"），防止转述漂移。
3. **markdown 契约**：SKILL.md 含 8 条不变量关键词（`parallel`/`serial-isolated`/`orchestrated`、`独立共识`、`模型先验·待验证`、`未锚定模式`、`领域盲区`、`未覆盖`、`逐字引用`）；各模板含「消费上游」「本步提炼」及本步必填章节。
4. **profile 可移植性**：默认 learner-profile 中性占位（对应 `:80` 的写法）。
5. **validate_stage 单测**：每个 stage 一份合规 + 一份违规 fixture（4 视角、证据缺级、资源缺 URL、7 次课、bank 混入答题记录、游标不一致、快问快答 2 条等），断言退出码与 JSON violation。
6. **review_queue 单测**：--add 产出 1/7/30 到期日；--due 只列到期；--record-score 回写得分并推进间隔；不覆盖历史行。
7. **preflight CLI**：空工作区 bootstrap 创建 profile/queue/INDEX；二次运行不覆盖；--json 报告路径、检索/subagent 能力与建议档位；Git 根回退。

验证命令（仓库源码路径）：

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile skills/learn-loop/scripts/*.py
python3 skills/learn-loop/scripts/preflight.py --workspace-root /tmp/ll-test --bootstrap --json
python3 skills/learn-loop/scripts/validate_stage.py --run-dir <run-dir> --all --json
```

端到端验收：真实主题跑完模式 A（应零打断），打开 HTML 核对侧边栏/三栏/翻卡/施考状态行；再发起模式 B 答 2–3 题后中断会话，重进验证续考游标；`--all` 全过；INDEX/queue 已登记。

---

## 八、实施顺序与完成状态

以下条目均已在当前源码中落地；`[x]` 表示实现存在，验证命令的现状见文档顶部的验证注记。

1. [x] `tests/test_learn_loop.py`：包契约、法条保真、Markdown 契约、前置判断和 HTML 闸门测试
2. [x] `reference/original-prompts.md`：十段提示词逐字保存并只保留约定槽位
3. [x] `SKILL.md` 与 `agents/openai.yaml`：不变量、前置判断、路径契约、模式 A/B/C/复习入口
4. [x] 纪律层 reference：`pre-check.md`、`perspectives.md`、`conflict.md`、`curriculum.md`、`examination.md`、`retention.md`、`html-guide.md`
5. [x] 15 份 templates：十步产物、exam-record/feynman-record、run-state、learner-profile、review-queue
6. [x] `scripts/preflight.py`：路径解析、bootstrap、包完整性和显式能力验证声明
7. [x] `scripts/validate_stage.py` 与 `scripts/review_queue.py`：阶段结构闸门、回灌检查和 1/7/30 日队列操作
8. [x] `assets/template.html`、`template.css`、`template.js`、`render_template.py` 与 `reference/html-guide.md`：轻量页面骨架、同目录资源交付、可选内联、取证折叠、答案折叠、交互层和无 JS 降级
9. [x] 全量测试用例与 CLI fixture：40 个 learn-loop 用例全部通过；全量套件 65 个测试与 6 个 subtests 全部通过
10. [x] `README.md`：learn-loop 入口、触发语、preflight、产物目录和仓库结构说明已存在
