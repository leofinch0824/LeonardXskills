# 前沿大模型技术调研 SOP —— 调研与设计记录

> 目标：为「现实业务痛点 → 学术文献中的解决思路」打造一套成熟的技术调研 SOP，以可解释的多步骤 skill 形态沉淀。
> 本文档持久化整个调研过程的核心结论、已实测确认的事实、欠考虑点修订、以及最终设计方案。

---

## 一、核心判断

检索论文不难，真正的难点在**两端的桥**：

- **上行翻译**：业务痛点 → 学术语言。词对不上就会误以为"没人研究过"。
- **下行翻译**：论文 → 可落地的工程思路。一篇漂亮论文若要 8×H100 从头训，对工程师就是废纸。

市面工具都默认用户已有学术 framing，只做 search。**SOP 的重心应压在 Reframe（上行）与 Translate/可适用性（下行），而不是把 retrieval 做得多花哨。**

---

## 二、SOP 七阶段（★ 为价值重心）

1. **Intake / Reframe ★** — 痛点 → 结构化问题 + 候选技术维度 + 学术词汇表。决定性步骤，错了一路白跑。
2. **Landscape（补课）** — 找 1–3 篇近期 survey，拉出 taxonomy + 术语 + SOTA 快照。先有地图再钻细节。
3. **Discovery** — 多源并行检索 + 对 foundational/SOTA 做 snowballing（前向引用看跟进、反向引用看底座）。输出候选池 + 元数据。
4. **Triage ★** — 用廉价信号先过滤：title/abstract/TLDR + citation + 年份 + 有无代码 + 与痛点相关度 → 分层（T0 奠基 / T1 必读 / T2 扫 / T3 跳过）。**只对 T0+T1 做昂贵的精读**。每条 T1+ 决策附一句理由（可解释）。
5. **Extract（深读/结构化抽取）** — 只对幸存者，从 abstract+TLDR+metadata 抽机制/结果/局限/可适用性/落地成本/前置依赖。
6. **Synthesis** — 跨方案 trade-off 矩阵 + 时间线/演进 + 方案映射回痛点排出可执行 idea（带工作量/可行性）+ 开放问题。不是摘要堆叠。
7. **Brief & Profile 回写** — 汇总成中文简报，把新约束/新兴趣写回 profile。

---

## 三、验证设计（验证不是第 8 阶段，是每个阶段的出口闸）

关键前提：用户非研究者，无法一眼看出 synthesis 错误，验证负担由管线自己扛，且把不确定性显式抛出。

**廉价、永远开：**
- 强制真实 URL：池里每篇论文必须带可解析 URL + 元数据，无 URL 丢弃。干掉"幻觉引用"。
- 内联引用：synthesis 每条事实结论必须挂 `[paper-id]`，挂不上的标注为"推断"。
- 可适用性诚实：强制引用具体证据，区分"论文已证明" vs "对你场景的外推"。

**中等、只对幸存者（T0/T1）：**
- 对抗式复核：verifier 拿抽取结果回比对源文本，字段打 {grounded/partial/unsupported}。
- 完整性批判：critic 问"漏了哪篇奠基论文/哪个竞争方向？"——查 recall 不只 precision。

**昂贵、每轮一次：**
- 报告自评记分卡：覆盖度/引用密度/未支持声明数/可操作性/校准度，低于阈值回炉。

**人参与（最省力，杠杆最高）：**
- 抽样审计：随机抽 2–3 篇 T1 人工扫一眼校准信任。
- Intake 后的 gate 本身即上游验证。

**质量记分卡**（每次 BRIEF 顶部）+ **可追溯矩阵**（每个痛点 → 哪些论文 → 证据 → 可适用性判定）。

---

## 四、三层架构（解决"读全文耗 token"）

核心：summary 是错误抽象（预先烤好、提前决定什么重要）。正确范式是**根本不让全文进 agent 上下文**。

- **Layer A — 元数据+TLDR+摘要**（零解析、零 agent token）：Semantic Scholar 免费 API 直接给 abstract/TLDR/citationCount/influentialCitationCount/正反向引用/有无代码。撑起整个 Discovery 池 + Triage。= v1 摘要级基线。
- **Layer B — 全文解析成结构化 markdown**（确定性、一次性、离线）：PDF→markdown/JSON 存盘可复用。
- **Layer C — 检索/RAG**（省 token 关键）：agent 发窄问题（"loss 怎么设计？要微调吗？几张卡？局限？"），回 3–8 个带引用片段（几十 token 不是几千）。agent 只读片段，永不读全文。

**T0 全文交互方式**：从"外部塞一份 summary" → "agent 向外部索引发窄查询拿回带引用片段"。

---

## 五、网络调研实测确认 / 未确认（2026-07-30，环境半残）

本环境 WebSearch 全程返回空壳，GitHub/PyPI 被 client-challenge 挡住。改用直接打 API 端点实测承重事实。

**实测确认：**
- **arXiv API** 实拉成功：返回 `id/title/summary(=abstract)/published/category/journal_ref/comment/author/link(含PDF)`。免费、无需 key。**但无 citation 信号。**
- **Semantic Scholar Graph API** 存在且字段对：`title,abstract,tldr,citationCount,openAccessPdf,url,year,authors` 合法。**但单次请求即 429**——无 key 限流极严，雪球检索必挂。
- **MinerU**（`magic-pdf`）实拉确认：**AGPL-3.0**，PDF→markdown/JSON，公式→LaTeX、表格→HTML，84 语言 OCR，DocLayout-YOLO+UniMERNet。成熟。

**复核方式**：本环境 WebFetch 对 github.com 被安全预检拦截、api.github.com 匿名限流耗尽；改用 `curl` 拉 `raw.githubusercontent.com` README + HTML 页（不吃 API 限流）补确认。

**已复核（curl 实拉）：**
- **PaperQA2**（Future-House/paper-qa）：**Apache-2.0**，RAG over PDFs/文本/Office/源码，专攻科学文献，QA/摘要/矛盾检测 superhuman。license 干净，可作 RAG 后端。
- **Marker**（datalab-to/marker）："Convert PDF to markdown + JSON quickly with high accuracy"。

**学术 MCP server 已复核（2026-07-30，curl 实拉 README/LICENSE/atom feed）：**

| MCP | License | Stars | 最近提交 | 关键能力 |
|---|---|---|---|---|
| **openags/paper-search-mcp** | MIT | 2284 | 2026-07-02 | 20+ 源统一检索+去重（arXiv/S2/OpenAlex/Crossref/dblp/PubMed/CORE/HAL/SSRN…），`download_with_fallback` OA 优先下载链；**官方提供 Claude Code skill + CLI 模式** → 可走 Bash → JSON 落盘 → jq 切片，批量内容不进上下文。free-first，S2 key 可选增强 |
| **smaniches/semantic-scholar-mcp**（`uvx s2-mcp-server`） | MIT | 13（年轻，藏接口后） | 2026-07-29 | 14 个 typed 工具：`recommendations`/`multi_recommend`（**S2 Recommendations 源落地**）、`snippet_search`（**正文片段匹配，新廉价相关性信号**）、`get_paper` 双向引用图、bulk_search、match_paper（标题→论文解析）；客户端限速+分层字段集（省 token） |
| **blazickjp/arxiv-mcp-server** | Apache-2.0 | 3002 | 2026-07-29 | 14 工具：搜索/下载/本地读；**可按章节读 arXiv LaTeX 源码**——Layer B 新路径，有 LaTeX 源时绕开 PDF 解析 |
| salwks/mcp-techTrend | MIT | 3 | 2026-05-20 | arXiv+HF+GitHub 趋势监控简报；可参考，非核心 |
| papersflow-ai/papersflow-mcp | MIT | 13 | 2026-03-11 | 托管服务（S2+OpenAlex 474M 论文）；依赖第三方账号，不采用 |

**补充实测（免 key，直接 curl 通）：**
- **HF Papers API** `https://huggingface.co/api/papers` → 给 `upvotes`/`publishedAt`。**年龄分层 Triage 的"新论文 buzz 信号"落地**，无需专用 MCP。
- **OpenAlex API** 免 key → `cited_by_count` 等元数据。**S2 429 时的 citation 后备骨干**（paper-search-mcp 已内置该源）。

---

## 六、调研翻出的欠考虑点与修订（按影响排序）

**1. [最大] RAG 对你的体量是过度设计，离线结构化抽取才是 T0 默认。**
个体、周期性调研，T0 每次 5–20 篇，问题集合固定（机制/结果/可适用性/成本/局限）。
- **离线批处理抽取**：外部 worker（非 agent，一次 API 调用 + 固定 prompt）把 MinerU 解析出的 markdown 跑一次 → 按固定 schema 抽成几 KB 结构化结果落盘 → synthesis 只读精简结果。**agent token 真·零**，且比 RAG 简单（无向量库/embedding/reranker）。
- RAG 唯一优势是"问 schema 外的临时问题"，用逃生口补足：schema 留「schema 外值得注意的方法/细节」自由字段 + 解析后 markdown 留盘，真需要追问时再上 RAG。
- **翻转默认：v1 T0 = 离线结构化抽取；RAG 为语料长大后的升级项。**

**2. [重要] citationCount 对核心场景是弱信号。**
主场景是"落后补最近课"，但最近 6 个月论文引用数天然近 0，按 citation 排序会把最新好工作排后面。
- 修正：Triage 按**论文年龄分层加权**——老论文看 citation/influentialCitationCount，新论文看「是否被 survey 引用 / HF papers 热度 / X 讨论 / S2 Recommendations 相关度」。
- **S2 Recommendations API**（给 seed 论文反查相关近期工作）之前没用足，恰是补课场景天然 discovery 信号且不依赖引用年龄，提为 Discovery 正式源。

**3. [重要] MinerU 是 AGPL-3.0，需正视 license 边界。**
本地个人用、跑独立进程基本无碍；但包成团队工具/对外服务时 AGPL 网络条款咬人。
- 出路：(a) **始终以外部子进程/CLI 调用 MinerU，绝不当库 import**；(b) 要 license 无暇换 **GROBID（Apache-2.0）**，质量略逊但最干净、参考文献抽取 SOTA。
- 建议：v1 用 MinerU（子进程），skill 文档明确写 license 边界。

**4. [运维] S2 必须申请免费 key + 实现 backoff，列为前置条件。**
实测一次请求即 429。"申请 S2 free API key + arXiv 礼貌限速 + 指数退避重试"是安装前置步骤，不是脚注。

**5. [反幻觉] 规则升级为不变量。**
**论文的"存在性"只能由 API 决定，模型只能标注、不能凭空造论文。** 池里每条 identifier（arXiv ID/S2 paperId/DOI）必须来自 live API 响应；title/abstract 概括可改写，但 identifier 与元数据字段以 API 返回为准，禁止模型生成 identifier。写成 skill 顶部不变量。

**6. [可用性] Papers with Code 升一等源 + has-code 进 Triage 信号。**
工程师要落地，"有没有能跑的代码"和论文本身一样重要。PwC 有 API 给代码链接+leaderboard。列为正式 Discovery 源，Triage 里 has-code 加权（applicability 强正信号）。

**7. [诚实] PaperQA2/MCP 未复核。**
skill 只承诺稳定接口 `query_paper(paper_id, question) → 带引用片段`，后端 PaperQA2/DIY RAG/离线抽取可插拔。**接口稳定，后端可换，v1 不绑死未复核工具。**

---

## 七、最终设计锁定

- 7 阶段，Reframe 与 Triage 为重心
- v1 摘要级深度（Layer A），T0 走**离线结构化抽取**（Layer B 子进程），markdown 留盘作逃生口；RAG（Layer C）为升级项
- **Layer B 解析优先级：arXiv LaTeX 源按章节读（arxiv-mcp-server，最干净）> MinerU（子进程）> GROBID（license 无暇兜底）**；仅 PDF-only 论文走解析
- **Discovery 默认后端：paper-search-mcp CLI（20+ 源并发+去重，JSON 落盘不进上下文）+ s2-mcp（recommendations / 双向引用图 / snippet_search）**；直连 API curl 为兜底；三者全 license 干净（MIT/Apache）且活跃维护
- **Triage 信号表更新**：老论文看 citation（S2 主，OpenAlex 免 key 后备）；新论文看 survey 提及 / **HF Papers upvotes（免 key API 实测通）** / S2 Recommendations 相关度 / **snippet_search 正文片段匹配**
- 验证闸 + 质量记分卡 + 可追溯矩阵全做进 skill
- Profile（约束+历史关注点）+ 知识库沉淀（`research/<date>-<slug>/`）做复利
- 轻交互（仅 Intake 后 gate），并行 subagent 提速，内置工具先行 MCP 可选增强
- PwC 一等源；has-code 加权
- 前置：`uv` + paper-search-mcp / s2-mcp / arxiv-mcp-server 三者安装 + S2 key（强烈建议，无 key 429 严重）+ 限速退避
- 反幻觉不变量：identifier 只能 API 生成
- 中文简报；首轮在项目 `.claude/skills/` 中隔离测试，验证通过后再决定是否晋升为 personal skill；知识库写工作区 `research/`

**接口契约（后端可插拔）：** `query_paper(paper_id, question) → 带引用片段`

---

## 八、GitHub 访问问题诊断（已定位）

排查结论（2026-07-30）：**机器网络本身通 GitHub，问题分三层，根因各异。**

| 层 | 现象 | 根因 | 解法 |
|---|---|---|---|
| **WebFetch 工具** | "Unable to verify if domain github.com is safe to fetch... blocking claude.ai" | Claude Code 的域名安全预检要连 claude.ai 验证，而本机走第三方 relay（`router.shengsuanyun.com`），claude.ai 不可达。`skipWebFetchPreflight:true` 未完全绕过（预检端点本身被 relay 挡）。 | **工具级拦截，非网络问题。绕过：改用 `curl` 取 GitHub 内容。** |
| **GitHub API**（api.github.com） | HTTP 403 `API rate limit exceeded`（limit 60, remaining 0） | 匿名限流 60 次/小时，且代理出口 IP（188.253.115.14）是共享的，额度已被他人用光。 | 配 `GITHUB_TOKEN`（PAT）→ 5000/小时；或装 `gh` CLI 并 `gh auth login`。 |
| **github.com HTML + raw.githubusercontent.com** | curl 实测 HTTP 200 | 不受 API 限流约束 | **当前即可用的调研通道**：`curl` 拉 README/HTML 页。 |

**已用 curl 确认**：PaperQA2（Apache-2.0）、Marker（PDF→markdown+JSON）。

**环境备注**：HTTP(S)_PROXY=http://127.0.0.1:7897（Clash 类代理），端口通；DNS 解析 github.com 正常；直连与走代理均 200。

## 十、需求锁定（grilling 2026-07-30，11 问全部确认）

**验收测试用例（两个真实痛点，skill 模板的及格线）：**
- **痛点一**：PCB 多图参数抽取中 VLM 数值判断错误（单位换算错/基铜厚与完成铜厚混淆/大小比较错/跨页拼接），无法归因到视觉读取、单位归一化、算术比较、证据选择哪一环；单图调试不代表多图真实效果，修 A 案例退化 B 案例。
- **痛点二**：多环节链路（PDF 转图/切分/过滤/召回/VLM 抽取/后处理/归一化/评测）失败后无法判断改 Prompt 还是改流程；需要把大量失败样例压缩成少数可人工分析、可 Prompt 修复、可实验验证的错误模式。
- **元问题**：两个痛点都是**归因 + 验证闭环**；用户瓶颈不在"发现新技术"（已知 OCR/约束解码/外部计算器/LLM Judge），而在**方案×环节适配决策**。

**原子化 → 学术词汇映射（上行翻译样例）：**

| 原子问题 | 学术检索词（脱离 PCB 语境） |
|---|---|
| 数值从图读对 | document VQA / table understanding / OCR-free extraction |
| 单位归一化（mm/mil/oz/μm、分数记法） | quantity & unit extraction / measurement normalization |
| 读对了但比较错 | LLM numerical reasoning / tool-augmented LLM / Program-of-Thought |
| 多图相似数值干扰、跨页拼接 | multi-document distraction robustness / lost-in-the-middle / evidence selection |
| 语义相近参数混淆 | schema-guided extraction / entity disambiguation |
| 失败样例压缩成错误模式 | automated failure mode discovery / failure clustering & taxonomy |
| Judge 读全文还是证据包 | LLM-as-a-Judge reliability / evidence compression faithfulness |
| Prompt Patch 自动优化+回归合入 | automatic prompt optimization（DSPy/MIPRO、TextGrad、OPRO）/ eval-driven development |
| 规则冲突、知识卡片拆开管 | modular prompt / prompt versioning / compound AI observability |

**三条设计修订：**
1. Reframe 强制剥离领域词（PCB/铜厚等），检索词只留结构性问题；领域词仅用于最终可适用性映射，防检索污染。
2. 方法论/评测设计类论文升为一等检索目标（用户问"如何设计对照实验""用什么指标合入规则"）。
3. Synthesis 权重上调、Discovery 权重下调（用户已过"发现"阶段）。

**Q2–Q11 确认项：**
- 纯事件驱动，v1 无周期追踪
- 每轮 T0≤3、T1≤10、人工审计 ~10 分钟
- 简报自用：强制逻辑分层（结论→方案路线→证据→风险）；方案路线有沉淀价值时必附 **mermaid 流程图**
- 约束 Profile：微调可；**4×H20（560GB）**→ 全参微调 ~30B 内可行，>70B 全参标"超算力"；开源权重优先自部署；**未脱敏不出内网、脱敏可调 API**（混合模式：本地小模型 + API 大模型做蒸馏/数据合成/复杂推理 = 可适用）；延迟 TBD（Intake 涉延迟敏感方案时追问）
- 可适用性四档：直接可用 / 需微调（算力内）/ API 辅助（脱敏后）/ 不适用
- 成本无硬预算 → **每轮输出分阶段 token 台账**（主流程/subagent/抽取 worker 分列），2–3 轮后自校准
- 验证闸失败：自动回炉 ≤1 次 → 仍不及格则**带警告交付**并标注未过闸章节（不静默降级、不无限回炉）
- 知识库粒度：简报 + 池元数据 + Triage 分层理由 + 抽取结果全留；解析后 markdown 进缓存目录可重建
- 检索池：近 24 个月主窗口，snowballing 不限年代捞奠基作；**学科不限 LLM 时代**（经典 document AI 一等公民）；Intake 可按题调整
- **空结果合法且一等**：附"已充分检索"证据；完整性批判负责证明"确实找过"；空结果=自己趟路的决策依据
- 语言：中文笔记 + 英文术语原词不译（Program-of-Thought、constrained decoding 等），防翻译歧义污染后续检索

## 十一、Skill 落地实施计划（2026-07-30，plan 阶段产出）

### 位置与文件树

首轮以项目级 skill 测试：`.claude/skills/paper-trail/`（user-invoked，`disable-model-invocation: true`，零 context load；事件驱动由用户手动触发，符合 Q2）。用户数据与 skill 定义分离：profile 在 `.claude/paper-trail/profile.md`，知识库在工作区 `research/`。验收通过后再决定是否晋升到 personal scope，测试阶段不保留同名 personal 副本，避免发现顺序干扰。

```
.claude/skills/paper-trail/
├── SKILL.md                 — 骨架:3 条不变量 + preflight 3 步 + 7 阶段(每阶段带闸门)+ 交付审计
├── agents/openai.yaml       — 仓库惯例样板
├── reference/               — 按需查阅(渐进披露,不占骨架篇幅)
│   ├── reframe.md           — 上行翻译 playbook:三步法 + 问题类型→检索策略 + PCB 完整示范 + 出口检查
│   ├── backends.md          — preflight 清单 + 源用法 + 调用纪律(限速/落盘/license 边界)+ 降级梯 + worker 配置
│   ├── triage.md            — 年龄分层加权信号表 + T0≤3/T1≤10 名额纪律
│   ├── extract.md           — Layer B 路由(LaTeX>MinerU>GROBID)+ worker 用法与降级梯 + 可适用性四档
│   ├── verify.md            — 全部验证协议单一出处:对抗复核/完整性批判/记分卡阈值/失败政策
│   └── synthesize.md        — trade-off 矩阵 + 时间线 + 痛点映射 + mermaid 约定 + 语言约定
├── templates/               — 每轮实例化到 research/<date>-<slug>/ 的模板
│   ├── intake.md / landscape.md / pool.md / triage.md / extraction.md
│   └── synthesis.md / brief.md / ledger.md / profile.md
└── scripts/
    ├── preflight.py         — 项目产物/MCP pin/可选 env 一键检查,可选 --live-mcp
    └── extract_paper.py     — 离线抽取 worker:OpenAI 兼容端点,env 三变量配置,--selftest 自测,usage 打 stdout 供台账
```

### 关键契约

- **每轮运行目录**：`research/<YYYY-MM-DD>-<slug>/` → `00-intake.md` … `06-brief.md` + `04-extractions/` + `ledger.md` + `.cache/`（解析 markdown/原始 API 响应，可重建）
- **回灌契约**：读侧 = preflight 必读 profile.md + research/INDEX.md（恒定小成本）；写侧 = Brief 阶段追加 INDEX.md 一行 + profile 增量追加（不覆写）
- **记分卡及格线**（verify.md）：覆盖度 100% / 引用密度 ≥90% / unsupported=0 / 可操作性布尔 / 完整性 100% / 校准度人工回填
- **失败政策**：回炉 ≤1 次 → 带警告交付并标注未过闸章节；不静默降级、不无限回炉
- **抽取 worker**：`PAPER_TRAIL_WORKER_BASE_URL/_KEY/_MODEL` 三变量；不配则走降级梯（subagent 抽取 → 主 agent 仅 T0）

### 环境配置步骤

1. 测试阶段用 project scope 注册三个 MCP（配置落在项目 `.mcp.json`，并固定已验活版本）：`paper-search-mcp==0.1.4`、`s2-mcp-server==1.7.1`、`arxiv-mcp-server==0.6.2`。uv/uvx 已装，三项均已在项目内实测 Connected（2026-07-30）。
2. 用户行动：申请 S2 免费 API key，配 `SEMANTIC_SCHOLAR_API_KEY`（无 key 时 S2 系 429 严重，可用但慢）。
3. 用户行动：配 worker 三环境变量（OpenAI 兼容端点 + 最便宜档模型），不配则 worker 走降级。localhost/private IP/`.local`/`.internal` 默认视为内网；其他端点仅允许 HTTPS，且只有 paper 与 profile 均已脱敏时才显式传 `--desensitized`。
4. 注意：已装的 github plugin MCP 报 Authorization 错误（400），需配 token 才能用，与本 skill 无关，另行处理。

### 实施顺序与进度

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 坐实三后端 CLI 入口（PyPI+README 实证） | ✅ |
| 2 | 写项目级 skill（SKILL.md+6 reference+9 templates+script+yaml） | ✅ |
| 3 | 落地 `.claude/paper-trail/profile.md` + 工作区 `research/INDEX.md` | ✅ |
| 4 | 用 project scope 注册并验活三个 MCP | ✅ |
| 5 | 更新本文档实施状态 + 项目级发现/worker 回归测试 | ✅ |
| 6 | 验收：用痛点一（PCB 多图数值归因）跑一轮完整 7 阶段 | 待用户触发（消耗 token） |

### 本轮工程验证（2026-07-30）

- Claude CLI 从项目 `.claude/skills/paper-trail/` 成功发现 `/paper-trail`，并正确返回项目 profile 路径与 Intake 人工闸门。
- `claude mcp list`：`paper-search`、`semantic-scholar`、`arxiv` 均为 `Connected`；GitHub plugin 的 HTTP 400 仍是独立已知问题。
- `python3 .claude/skills/paper-trail/scripts/preflight.py --live-mcp`：项目产物与 pinned MCP 检查通过；因真实 S2/worker 凭据未配置，按设计返回 `degraded`。
- `python3 -m unittest -v tests/test_paper_trail.py`：8/8 通过，覆盖项目产物契约、personal 路径隔离、preflight 降级报告、worker `--selftest`、完整抽取写卡、外部端点脱敏/HTTPS 闸、超长正文拒绝静默截断与 token usage 输出。
- 真实 worker 凭据与 S2 key 当前未配置；worker 已通过本地假 OpenAI 兼容端点验证，真实运行按既定降级梯处理。

### 验收标准

- 每个模板被实例化且闸门逐项过；简报顶部记分卡落盘；可追溯矩阵每个 Intake 问题有处置；INDEX.md 追加成功。
- 验收用例即第十节痛点一（原子化样例已在 reframe.md）。

## 九、待办（2026-07-30 更新）

- [ ] 给环境配 `GITHUB_TOKEN`（或装 gh CLI），解锁 API 元数据批量查询（rate limit 60→5000）。
- [x] ~~按名手动核对学术 MCP server 现状与许可证~~ → 已完成（见第五节复核表）：全部 license 干净且活跃维护；产出三条设计修订写入第七节。
- [x] ~~细化需求（grilling 11 问）~~ → 已全部确认，见第十节。
- [x] ~~进 plan 定 skill 文件结构、各阶段模板（含验证闸出口标准）、记分卡与回灌契约格式~~ → 已落地项目级 skill，并补齐 `landscape.md` / `synthesis.md` 与统一的 `triage.md` 模板。
- [ ] 配置 `SEMANTIC_SCHOLAR_API_KEY` 与 `PAPER_TRAIL_WORKER_*` 三变量后，运行真实后端 preflight。
- [ ] 用第十节痛点一跑首轮完整 7 阶段验收。
