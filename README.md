# LeonardX Skills

中文优先的 Agent Skill 实践仓库 · Maintained by **[LeonardX](https://github.com/leofinch0824)**

<br clear="left">

把工作与学习中反复出现的方法沉淀为可复用、可验证、可移植的 Agent Skill。所有 skill 采用标准 `SKILL.md` 结构，强调明确的阶段契约、可追溯产物和自动化验证。

![platform](https://img.shields.io/badge/Codex-supported-2ea44f?style=flat-square)
![skills](https://img.shields.io/badge/skills-3-informational?style=flat-square)
![lang](https://img.shields.io/badge/%E4%B8%AD%E6%96%87%E4%BC%98%E5%85%88-blue?style=flat-square)
![standard](https://img.shields.io/badge/Agent_Skills-compatible-8957e5?style=flat-square)
![license](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)

---

## 内容一览

| skill | 用途 | 状态 |
|---|---|:---:|
| [**paper-trail**](#paper-trail) | 将业务或技术痛点翻译成学术问题，系统调研前沿论文，并产出带证据链、可追溯、可落地的方案简报 | 可用 |
| [**paper-reading-assistant**](#paper-reading-assistant) | 以 Three-Pass 方法协作阅读单篇论文，判断相关性、证据质量、复现价值与下一步投入 | 可用 |
| [**learn-loop**](#learn-loop) | 将“十倍速学习”方法固化为有来源分级、阶段闸门、题库施考、费曼复述和复习队列的中文学习闭环 | 可用 |

安装方式见「[安装](#安装)」，实际运行方式见「[快速开始](#快速开始)」。

---

## paper-trail

<a id="paper-trail"></a>

`paper-trail` 是一套前沿论文调研 SOP。它不把检索结果简单堆成摘要，而是完成两次关键翻译：先把**业务痛点上行翻译成可检索的学术问题**，再把**论文证据下行翻译成满足现实约束的方案路线**。

### 核心理念：两座桥 + 一条证据链

每轮调研沿固定的七阶段流程推进。前一阶段的产物是后一阶段的输入，每个阶段都以闸门收尾；闸门未通过时先补齐证据，不静默跳过。

```
① Intake / Reframe → ② Landscape → ③ Discovery → ④ Triage
        → ⑤ Extract → ⑥ Synthesis → ⑦ Verify / Brief / 回灌
```

| 阶段 | 核心动作 | 主要产物 |
|:-:|---|---|
| 1 | 将痛点拆成可独立检索的原子问题，剥离业务领域词，并由用户确认范围 | `00-intake.md` |
| 2 | 用 Survey / Benchmark 建立 taxonomy、术语表与 SOTA 快照 | `01-landscape.md` |
| 3 | 多源检索、引用图 Snowballing、API identifier 校验与候选去重 | `02-pool.md` |
| 4 | 按相关度、年代、引用、代码和正文信号分为 T0–T3，并检查论文池充分性 | `03-triage.md` |
| 5 | 从正文逐字段抽取机制、结果、局限、资源需求和可适用性 | `04-extractions/` |
| 6 | 形成 Trade-off 矩阵、演进时间线、痛点映射和推荐路线 | `05-synthesis.md` |
| 7 | 对抗复核、完整性批判、质量记分、成本汇总与知识回灌 | `06-brief.md`、`ledger.md` |

### 关键设计

- **Intake 是冻结的范围合同**：用户确认后，Landscape 可以补充同义词与 taxonomy 节点，但不能静默改写原子问题；语义或边界发生变化时必须重新打开 Intake。
- **论文存在性只由实时 API 决定**：arXiv ID、Semantic Scholar paperId 和 DOI 必须逐字复制自 API 响应，不能依赖模型记忆补论文。
- **薄结果也是一等结果**：T0 + T1 少于 5 篇、原子问题覆盖不足或关键后端缺失时，只执行一次有界补检；仍然过薄则以 `accepted-thin` 携带完整检索证据交付。
- **适用性只引用当前 Profile**：部署、权重、数据出域、资源和 License 约束为 `TBD` 时先标记“待确认”，不允许模型替用户假设。
- **Worker 数据边界前置可见**：Preflight 与 Extract 共用端点分类，明确区分可信本地、外部 HTTPS、被阻止的外部 HTTP 和无效配置，报告不会输出 worker key。
- **质量与成本分开**：覆盖度、引用密度和证据支持度决定质量；token、单位抽取成本只用于跨轮比较，不参与质量及格判定。

### 触发方式

明确调用 `$paper-trail`，并提供一个真实技术痛点：

```text
使用 $paper-trail 调研：
我们的 RAG 系统在长文档、多跳问题中经常遗漏跨章节证据，
请调研 evidence selection、long-context retrieval 和 multi-hop RAG，
给出有论文证据、符合当前算力与数据边界的改进路线。
```

也可以从更模糊的业务问题开始：

```text
用 $paper-trail 查一下这个技术痛点有没有新的论文方案
把这个工程问题翻译成学术问题并做一份可落地调研
不要只列论文，给我证据链、取舍和实施顺序
```

**适用场景**：需要从论文证据形成工程决策；需要回答“有什么方案、证据多强、是否适合当前约束”；需要保存可复查、可增量更新的调研资产。

**不适用**：只查一个已知事实；只需要几篇论文标题；不需要证据链的一次性头脑风暴。

详细流程见 [`skills/paper-trail/SKILL.md`](./skills/paper-trail/SKILL.md)，后端和降级策略见 [`skills/paper-trail/reference/backends.md`](./skills/paper-trail/reference/backends.md)。

---

## paper-reading-assistant

<a id="paper-reading-assistant"></a>

`paper-reading-assistant` 是一套面向**单篇论文**的协作式渐进阅读协议。它以 Keshav 的 Three-Pass 方法为骨架，把用户要做的决定、论文的外部状态、主张与证据、复现缺口和下一步投入组织成可暂停、可复核的阅读过程。它不做多篇论文批量筛选，也不把一篇论文压缩成缺乏证据边界的一段通用摘要。

### 核心理念：渐进深度 + 人在回路

每次阅读先澄清目的与熟悉程度，再按需从 Pass 1、Pass 2 或 Pass 3 开始；每一遍都在交付显式判断后停下，不静默升级到下一遍。

```
开场两问 → Pass 1 筛选 → ⛔ 检查点
                         → Pass 2 理解 → ⛔ 用户授权
                                           → Pass 3 深入 / 复现
```

| 阶段 | 核心动作 | 主要产物 |
|:-:|---|---|
| 0 | 澄清阅读目的与子领域熟悉度；若只需事实、引用或两行要点则直接回答 | 对话中的阅读目标与深度边界 |
| 1 | 扫读论文结构，回答 Keshav 的 Five Cs，并核验发表、评审与引用状态 | 论文筛选报告 |
| 2 | 细读核心方法与结果，建立理解图谱、主张—证据对照和可迁移零件 | `.paper-reading/<slug>/pass2-understanding.md` |
| 3 | 在用户授权后反向工程、检查假设、规划复现或批判性复核 | `.paper-reading/<slug>/pass3-deep-dive.md` |

### 关键设计

- **单篇约束**：一次只读一篇论文；收到多篇时先列清单并请用户选择，不默默取第一篇。
- **证据纪律**：维护来源台账，并将实质性陈述明确标为 `Observation`、`Author claim` 或 `Inference`；证据不可得时不补写数据、baseline、实现细节或引用。
- **外部状态先核验**：发表状态、公开评审记录和引用情况只报告实际检索结果；检索不可用时明确标记未核实，不凭记忆重构。
- **红旗上浮**：会改变判断的证据问题在当前遍次报告顶部单独列出，不埋在表格的注意事项中。
- **用户判断不代做**：问题重要性、当前最强 baseline 和收益是否有实践意义等判断，交还给用户在「需要你判断」下决定。
- **深度闸门**：Pass 1 后停止一次；Pass 3 只能在相关性与证据支持继续投入、且用户明确授权后开始。

### 触发方式

明确调用 `$paper-reading-assistant`，并提供一篇论文的链接、PDF 或可访问材料：

```text
使用 $paper-reading-assistant 阅读这篇论文：
<论文链接或 PDF>
我想判断它是否值得复现；我对这个子领域有工作基础。
```

**适用场景**：判断论文是否值得投入时间、理解核心方法和证据、准备复现或严谨评审；需要将阅读过程保留为可继续的研究资产。

**不适用**：批量文献筛选、只查一个事实或引用格式、只需要两行摘要。

详细流程见 [`skills/paper-reading-assistant/SKILL.md`](./skills/paper-reading-assistant/SKILL.md)，Pass 3 反向工程和批判性复核见 [`skills/paper-reading-assistant/references/deep-dive.md`](./skills/paper-reading-assistant/references/deep-dive.md)，Three-Pass 保真度审计见 [`skills/paper-reading-assistant/references/THREE_PASS_FIDELITY_AUDIT.md`](./skills/paper-reading-assistant/references/THREE_PASS_FIDELITY_AUDIT.md)。

---

## learn-loop

<a id="learn-loop"></a>

`learn-loop` 是中文优先的十步学习闭环。它把五视角 STORM、来源等级、矛盾图谱、学习阶梯、主动回忆和费曼复述组织成一条可校验流水线：模式 A 生成 Markdown 事实源和完整学习页面（HTML 与同目录固定资源），用户之后说“考我”进入可续考的模式 B，说“给我讲/我来讲”进入真实的模式 C。用户说“十倍速学 X”或 `learn-10x-faster` 时也应触发它。

```text
开场两问 → 5 个独立视角 → 冲突/共识 → 简报 → 评审
→ 资源/阶梯/课程 → 题库与费曼材料 → 速查表/HTML/复习队列
```

```bash
poetry run python skills/learn-loop/scripts/preflight.py \
  --workspace-root /absolute/path/to/test-workspace \
  --bootstrap --json
```

详细规则见 [`skills/learn-loop/SKILL.md`](./skills/learn-loop/SKILL.md)。运行产物默认写入目标工作区的 `.learn-loop/` 与 `learning/`；skill 包本身保持只读。`docs/reference/ten-step-learning/` 仍作为早期一次性 HTML 实现保留，`learn-loop` 是带校验与真实练习入口的版本。

Learn Loop 的阶段契约、实现计划和当前评估见 [`docs/plans/learn-loop/learn-loop-format-contract-gap-analysis.md`](./docs/plans/learn-loop/learn-loop-format-contract-gap-analysis.md)、[`docs/plans/learn-loop/learn-loop-format-contract-remediation-plan.md`](./docs/plans/learn-loop/learn-loop-format-contract-remediation-plan.md) 和 [`docs/plans/learn-loop/learn-loop-format-contract-eval-results.md`](./docs/plans/learn-loop/learn-loop-format-contract-eval-results.md)。

---

## 安装

<a id="安装"></a>

**方式一 · 复制到 Codex skills 目录**

```bash
git clone https://github.com/leofinch0824/LeonardXskills.git
mkdir -p ~/.codex/skills
cp -R LeonardXskills/skills/paper-trail ~/.codex/skills/
cp -R LeonardXskills/skills/paper-reading-assistant ~/.codex/skills/
cp -R LeonardXskills/skills/learn-loop ~/.codex/skills/
```

重新打开 Codex 会话后，通过 `$paper-trail`、`$paper-reading-assistant` 或 `$learn-loop` 显式调用。

**方式二 · 在仓库中直接使用**

让 Agent 读取当前仓库的 `skills/paper-trail/SKILL.md`，并明确要求按照该流程执行。此方式适合开发、调试和修改 skill。

> `paper-trail` 默认保持 skill 包只读；Profile 写入目标工作区的 `.paper-trail/`，调研产物写入目标工作区的 `research/`。

对单篇论文阅读任务，让 Agent 读取当前仓库的 `skills/paper-reading-assistant/SKILL.md`，并明确要求按照该流程执行；从 Pass 2 起，它会把阅读产物写入目标工作区的 `.paper-reading/<slug>/`，且不会自行进入 Pass 3。

对学习任务，让 Agent 读取 `skills/learn-loop/SKILL.md`；它会把运行状态写入目标工作区的 `.learn-loop/`，把 Markdown 事实源与 HTML 视图写入 `learning/`。

---

## 快速开始

<a id="快速开始"></a>

### 1. 运行自动化测试

```bash
poetry install
poetry run python -m unittest discover -s tests -v
```

### 2. 初始化测试工作区

```bash
poetry run python skills/paper-trail/scripts/preflight.py \
  --workspace-root /absolute/path/to/test-workspace \
  --bootstrap \
  --json
```

未配置可选后端时，报告为 `degraded` 是预期行为；只有 skill 包或运行数据不完整才会进入 `blocked`。

### 3. 阅读一篇论文

把论文的链接、PDF 或可访问材料交给 Agent，明确调用 `$paper-reading-assistant`。它会先询问阅读要支持的决定和你的熟悉程度，再按目标进入对应的 Pass；每一遍结束后都会给出是否继续的判断。若只需一个事实、引用格式或两行要点，则不启动完整阅读协议。

### 4. 按需填写 Profile

Preflight 首次运行会创建 `.paper-trail/profile.md`。只需补齐本轮方案判断真正依赖的字段：微调能力、算力预算、权重要求、数据出域规则、延迟要求和 License 限制。

### 5. 可选能力

| 能力 | 配置 | 未配置时 |
|---|---|---|
| Semantic Scholar | `SEMANTIC_SCHOLAR_API_KEY` | 使用免 key 来源或降低 S2 调用频率 |
| 抽取 Worker | `PAPER_TRAIL_WORKER_BASE_URL`、`PAPER_TRAIL_WORKER_KEY`、`PAPER_TRAIL_WORKER_MODEL` | 按 Extract 降级梯使用 subagent / 主 agent |
| 自定义可信内网主机 | `PAPER_TRAIL_WORKER_TRUSTED_HOSTS` | 仅自动信任 localhost、私网 IP、`.local`、`.internal` |
| 运行目录 | `PAPER_TRAIL_STATE_DIR`、`PAPER_TRAIL_RESEARCH_DIR` | 使用 `<workspace-root>/.paper-trail` 与 `<workspace-root>/research` |

外部 Worker 必须使用 HTTPS；发送论文与 Profile 前还要完成脱敏，并在实际抽取时显式传入 `--desensitized`。

---

## 仓库结构

```text
LeonardXskills/
├── skills/paper-trail/
│   ├── SKILL.md                 # 主流程、不变量与阶段闸门
│   ├── agents/openai.yaml       # Codex 展示与调用元数据
│   ├── reference/               # Reframe、后端、分层、抽取、综合与验证协议
│   ├── scripts/
│   │   ├── preflight.py         # 路径解析、bootstrap 与能力检查
│   │   ├── worker_boundary.py   # Worker 端点与数据边界分类
│   │   └── extract_paper.py     # OpenAI-compatible 结构化抽取 Worker
│   └── templates/               # 每轮调研的标准化 Markdown 产物
├── skills/paper-reading-assistant/
│   ├── SKILL.md                 # 单篇论文的 Three-Pass 协作阅读协议
│   └── references/              # Pass 3 指南、中文说明与保真度审计
├── skills/learn-loop/
│   ├── SKILL.md                 # 十步流程、不变量、模式 A/B/C 与闸门
│   ├── reference/               # 法条提示词、纪律附录与 HTML 指南
│   ├── scripts/                 # preflight、结构校验和复习队列 CLI
│   ├── templates/               # 十步、练习记录和运行状态模板
│   └── assets/                  # 轻量 HTML 骨架及同目录 CSS/JS 固定资源
├── tests/test_paper_trail.py     # 包契约、CLI、安全边界与工作流测试
├── tests/test_learn_loop.py      # learn-loop 包契约与 CLI 测试
├── docs/                         # 设计说明与优化计划
└── README.md
```

新增或修改 skill 后，至少运行：

```bash
poetry run python -m unittest discover -s tests -v
poetry run python -m py_compile skills/paper-trail/scripts/*.py
poetry run python -m py_compile skills/learn-loop/scripts/*.py
```

---

## License

- **paper-trail**、**paper-reading-assistant**、**learn-loop** — [MIT License](./LICENSE)，可在保留版权与许可声明的前提下使用、修改与分发。

问题与建议欢迎通过 [Issue](https://github.com/leofinch0824/LeonardXskills/issues) 反馈。
