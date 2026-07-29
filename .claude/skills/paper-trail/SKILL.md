---
name: paper-trail
description: 前沿论文调研 SOP:业务痛点 → 学术文献 → 可落地方案简报。遇到技术痛点想查论文时手动触发。
disable-model-invocation: true
---

# Paper Trail — 前沿论文调研 SOP

把业务痛点翻译成学术问题(**上行翻译**),把论文翻译成可落地方案(**下行翻译**)。检索只是中间环节,价值在两座桥。

每次运行产出一条**证据链**:痛点 → 检索池 → 分层决策 → 抽取卡 → 简报,逐环节落盘、可追溯。
每个阶段以**闸门**收尾:过不了闸门就补齐,补齐前不进入下一阶段。

## 不变量(每次运行、每个 subagent 都必须遵守)

1. **论文的存在性只能由 API 决定。** identifier(arXiv ID / S2 paperId / DOI)逐字复制自 live API 响应;模型可以概括标题和摘要,identifier 一律只复制。凭记忆想到的论文,经 API 验证存在后才准进池。
2. 简报里每条事实性结论挂 `[paper-id]`;挂不上的一律标注"推断"。
3. 检索词只含结构性问题词;业务领域词的处理见 [reference/reframe.md](reference/reframe.md)。

## 运行前提(preflight,按序执行)

1. 读当前工作区 `.claude/paper-trail/profile.md`(用户约束+兴趣史)。文件不存在:复制 [templates/profile.md](templates/profile.md) 到该路径,并向用户确认约束值后再继续。
2. 读当前工作区 `research/INDEX.md`(过往调研一行式索引)。有与本次痛点重叠的条目,先读对应简报,复用其术语表和结论,在 `00-intake.md` 注明复用点。INDEX.md 不存在则跳过。
3. 运行 `python3 .claude/skills/paper-trail/scripts/preflight.py --live-mcp`,再按 [reference/backends.md](reference/backends.md) 的 preflight 清单检查后端可用性。把 `ready/degraded/blocked`、本轮可用源和降级项记录到 `02-pool.md`;不可用源也是完整性证明的一部分。

## 七阶段

先建运行目录 `research/<YYYY-MM-DD>-<slug>/`(slug = 痛点的英文短横线概括),按以下映射实例化 [templates/](templates/)：

| 产出 | 模板 |
|---|---|
| `00-intake.md` | `templates/intake.md` |
| `01-landscape.md` | `templates/landscape.md` |
| `02-pool.md` | `templates/pool.md` |
| `03-triage.md` | `templates/triage.md` |
| `04-extractions/<paper-id>.md` | `templates/extraction.md` |
| `05-synthesis.md` | `templates/synthesis.md` |
| `06-brief.md` | `templates/brief.md` |
| `ledger.md` | `templates/ledger.md` |

### 1. Intake / Reframe ★(全程唯一人工交互点)

按 [reference/reframe.md](reference/reframe.md) 把痛点原子化:剥离领域词、映射学术词表、拆出可独立检索的原子问题。产出 `00-intake.md`。
**闸门:向用户展示结构化问题+学术词表+领域词剥离清单,获得确认。** 用户改了哪里,文件里更新哪里。

### 2. Landscape(补课)

用学术词表找 1–3 篇近 24 个月的 survey(含 benchmark/评测方法类),笔记落盘 `01-landscape.md`:taxonomy、术语表、SOTA 快照、候选奠基作列表。
**闸门:taxonomy+术语表落盘;或明确记录"该方向无 survey"及降级策略(用奠基作+近期高引自构地图)。**

### 3. Discovery(建池)

按 [reference/backends.md](reference/backends.md) 的源清单并发检索(每源一路 subagent,批量结果落盘 `.cache/` 后切片读取):paper-search-mcp 多源、s2-mcp recommendations/双向引用图、HF Papers(新论文 buzz)、Papers with Code(has-code 信号)。对 survey 提到的奠基作做一轮 snowballing。产出 `02-pool.md`。
**闸门:每条候选带 API 来源的 identifier+URL+元数据;多源已去重;每个源的查询词和返回数已记录。**

### 4. Triage ★(分层)

按 [reference/triage.md](reference/triage.md) 的年龄分层加权规则打分分层:T0(奠基)≤3 / T1(必读)≤10 / T2(扫读) / T3(跳过)。产出 `03-triage.md`。
**闸门:每条 T0/T1 附一句理由(回答哪个原子问题+凭什么信号晋级);T2/T3 各一行归类;超名额的补晋级理由或降级。**

### 5. Extract(结构化抽取)

对每篇 T0/T1:按 [reference/extract.md](reference/extract.md) 的 Layer B 路由拿正文(arXiv LaTeX 源 > MinerU 子进程 > GROBID),跑离线抽取 worker(`.claude/skills/paper-trail/scripts/extract_paper.py`,不经 agent 上下文;不可用时按该文件的降级梯处理),产出抽取卡 `04-extractions/<paper-id>.md`。可适用性对照 profile 约束打四档:直接可用 / 需微调(算力内)/ API 辅助(脱敏后)/ 不适用。
**闸门:T0/T1 每篇有抽取卡,schema 各字段有值或标"论文未述";四档判定完成。**

### 6. Synthesis(综合)

按 [reference/synthesize.md](reference/synthesize.md) 产出 `05-synthesis.md`:方案×环节 trade-off 矩阵、时间线/演进、痛点映射(每个 Intake 原子问题 → 答案或"未找到")、方案路线 mermaid 流程图(有沉淀价值时)。
**闸门:矩阵覆盖全部 T0/T1;每个 Intake 问题有处置;事实结论全部挂 [paper-id]。**

### 7. 验证、Brief 与回灌

按 [reference/verify.md](reference/verify.md) 跑验证:对抗复核(T0/T1 抽取卡回比对源文本)、完整性批判、记分卡。不及格 → 回炉 ≤1 次 → 仍不及格则带警告交付并在简报顶部标注未过闸章节。
产出 `06-brief.md`(顶部记分卡、附可追溯矩阵、结论→方案路线→证据→风险四层结构)。写 `ledger.md`(分阶段 token 台账)。
回灌:`research/INDEX.md` 追加一行(日期/slug/痛点一句话/核心结论/T0 论文);profile.md 有新增约束或兴趣时增量追加,不覆写。
**闸门:记分卡落盘且处置完成(及格/回炉/带警告交付三态之一);INDEX.md 已追加。空结果按一等结果处理:简报写明"已充分检索"的证据(各源查询词+返回数)。**

## 交付时

向用户提出抽样审计:随机指 2–3 篇 T1,请其花 ~10 分钟核对抽取卡与原文。审计结果回填 06-brief.md 记分卡"校准度"栏。
