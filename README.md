# LeonardX Skills

中文优先的 Agent Skill 实践仓库 · Maintained by **[LeonardX](https://github.com/leofinch0824)**

<br clear="left">

把工作与学习中反复出现的方法沉淀为可复用、可验证、可移植的 Agent Skill。所有 skill 采用标准 `SKILL.md` 结构，强调明确的阶段契约、可追溯产物和自动化验证。

![platform](https://img.shields.io/badge/Codex-supported-2ea44f?style=flat-square)
![skills](https://img.shields.io/badge/skills-1-informational?style=flat-square)
![lang](https://img.shields.io/badge/%E4%B8%AD%E6%96%87%E4%BC%98%E5%85%88-blue?style=flat-square)
![standard](https://img.shields.io/badge/Agent_Skills-compatible-8957e5?style=flat-square)
![license](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)

---

## 内容一览

| skill | 用途 | 状态 |
|---|---|:---:|
| [**paper-trail**](#paper-trail) | 将业务或技术痛点翻译成学术问题，系统调研前沿论文，并产出带证据链、可追溯、可落地的方案简报 | 可用 |

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

详细流程见 [`paper-trail/SKILL.md`](./paper-trail/SKILL.md)，后端和降级策略见 [`reference/backends.md`](./paper-trail/reference/backends.md)。

---

## 安装

<a id="安装"></a>

**方式一 · 复制到 Codex skills 目录**

```bash
git clone https://github.com/leofinch0824/LeonardXskills.git
mkdir -p ~/.codex/skills
cp -R LeonardXskills/paper-trail ~/.codex/skills/
```

重新打开 Codex 会话后，通过 `$paper-trail` 显式调用。

**方式二 · 在仓库中直接使用**

让 Agent 读取当前仓库的 `paper-trail/SKILL.md`，并明确要求按照该流程执行。此方式适合开发、调试和修改 skill。

> `paper-trail` 默认保持 skill 包只读；Profile 写入目标工作区的 `.paper-trail/`，调研产物写入目标工作区的 `research/`。

---

## 快速开始

<a id="快速开始"></a>

### 1. 运行自动化测试

```bash
python3 -m unittest discover -s tests -v
```

### 2. 初始化测试工作区

```bash
python3 paper-trail/scripts/preflight.py \
  --workspace-root /absolute/path/to/test-workspace \
  --bootstrap \
  --json
```

未配置可选后端时，报告为 `degraded` 是预期行为；只有 skill 包或运行数据不完整才会进入 `blocked`。

### 3. 按需填写 Profile

Preflight 首次运行会创建 `.paper-trail/profile.md`。只需补齐本轮方案判断真正依赖的字段：微调能力、算力预算、权重要求、数据出域规则、延迟要求和 License 限制。

### 4. 可选能力

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
├── paper-trail/
│   ├── SKILL.md                 # 主流程、不变量与阶段闸门
│   ├── agents/openai.yaml       # Codex 展示与调用元数据
│   ├── reference/               # Reframe、后端、分层、抽取、综合与验证协议
│   ├── scripts/
│   │   ├── preflight.py         # 路径解析、bootstrap 与能力检查
│   │   ├── worker_boundary.py   # Worker 端点与数据边界分类
│   │   └── extract_paper.py     # OpenAI-compatible 结构化抽取 Worker
│   └── templates/               # 每轮调研的标准化 Markdown 产物
├── tests/test_paper_trail.py     # 包契约、CLI、安全边界与工作流测试
├── docs/                         # 设计说明与优化计划
└── README.md
```

新增或修改 skill 后，至少运行：

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile paper-trail/scripts/*.py
```

---

## License

- **paper-trail** — [MIT License](./LICENSE)，可在保留版权与许可声明的前提下使用、修改与分发。

问题与建议欢迎通过 [Issue](https://github.com/leofinch0824/LeonardXskills/issues) 反馈。
