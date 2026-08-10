# Learn Loop 检索介质边界实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task.

**Goal:** 为 Learn Loop 的检索策略补上"不可读介质"（视频、音频、付费墙内容）的行为边界：取证层明确准入线（不进证据链、不评级）、查询层优先可读正文渠道、候选筛选引入可用性双判据；同时澄清步骤 5 中非文本媒体资源的等级语义。纯契约文档改动，不新增枚举、不改校验器。

**Architecture:** 新规则全部落在 `reference/perspectives.md` 的既有「检索操作要求」章节内——该章节由 `prepare_stage.py` 的 `_retrieval_requirements()` 以正则 `(?ms)^## 检索操作要求\s*\n(.*?)(?=^## |\Z)` 整体截取，并注入第 1 步全部角色任务包的 `PERSONA_GUIDANCE`。因此无需改动 `templates/perspective-task.md` 或任何脚本即可让五个隔离角色看到新规则。步骤 5 的语义澄清落在阶段语义权威 `reference/stages/05-resources.md`。

**Tech Stack:** Markdown 契约文档、Python 3.11、unittest。

## 背景与依据

- 设计意图原文（`reference/original-prompts.md` 第 5 步）明确资源"书、视频、课程、社区都行"，但取证层（步骤 1–4）的 A/B 校验链假设来源是可提取正文的网页/PDF，两条轨道的介质差异从未写明。
- 已实测 AnySearch（2026-08-10）：无介质类型过滤参数；`extract` 规格明确仅支持 HTML 页面；`academic.biomedical` 的 `has_pdf` / `open_access` 参数真实生效但为**软过滤**（5 条结果中仍有 2 条非开放获取漏网），`year_from` 同为软性；返回结果自带 `Availability` 行与 `Full Text Links` 的 `(Open access)` / `(Subscription required)` 标注，可作为提取前的零成本判据。
- 结论共识：对正文不可读的介质做评级无业务价值且有伪精度风险；正确形态是准入线（不评级、不进证据链）+ 检索记录留痕（复用现有`未采信`状态，不新增枚举）。

## Global Constraints

- 只修改 `skills/learn-loop/reference/perspectives.md`、`skills/learn-loop/reference/stages/05-resources.md`、`tests/test_learn_loop.py` 和本计划。
- 不修改 `reference/original-prompts.md`（不可改动的溯源原文）。
- 不修改 `scripts/` 下任何脚本、不修改 `templates/` 下任何模板（规则经 `_retrieval_requirements()` 自动注入）。
- 不新增字段名、枚举值或校验规则（遵守"验证器不得成为未写明的新规范"边界）。
- 「检索操作要求」章节内不得新增 `## ` 级标题（会截断注入正则的捕获范围）；段落以普通文本追加。
- 不提交或推送 Git 变更。

---

### Task 1: 注入守卫测试（red）

**Files:**
- Modify: `tests/test_learn_loop.py`

**Interfaces:**
- Consumes: `prepare_stage._retrieval_requirements() -> str`

- [x] 新增测试：导入 `prepare_stage` 模块，断言 `_retrieval_requirements()` 返回文本同时包含新规则锚点关键词`介质不可读`（准入线）与`Subscription required`（候选出局判据），确保两条规则都落在注入范围内、未被章节结构截断。
- [x] 运行该测试，确认其因规则尚不存在而失败。

### Task 2: perspectives.md 补检索介质边界

**Files:**
- Modify: `skills/learn-loop/reference/perspectives.md`

**Interfaces:**
- Produces: 「检索操作要求」章节新增三段规则，经既有机制注入全部角色任务包。

- [x] 在 AnySearch 查询设计段之后追加**渠道可读性优先**段：取证查询优先选择产物为文本的渠道；主题属 AnySearch 垂直域时优先文档类子域（academic、code.doc、legal、health 等）；academic 域尽量带 `has_pdf=true` 或 `open_access=true` 并用 `year_from` 设定年份倾向，但注明二者均为软过滤、不构成保证，候选仍须逐条核对可读性；使用 `social_media` 域时避开 `reddit_media`、`x_media` 等媒体型 `type` 值。
- [x] 在正文提取段（jina-reader / extract 段）之后追加**候选出局双判据**段：候选先按可用性标记、再按 URL 形态筛选；优先核对结果的 `Availability` 行与 `Full Text Links` 的 `(Open access)` / `(Subscription required)` 标注，标注订阅制者不进入正文提取；URL 形态识别为视频/音频/课程平台（watch、video、episode 类路径）的候选同样出局——AnySearch `extract` 仅支持 HTML 页面；两者均记入检索记录，状态`未采信`、理由注明付费墙或介质不可读。
- [x] 追加**准入线与文本替身**段：正文不可读的介质（视频、音频、付费墙后内容）不进入证据链、不承载主张、不参与评级；命中的此类来源仅作为线索记入检索记录。确有价值的候选补一次文本替身查询（官方文档、文字稿/transcript、配套文章）；命中文本替身按既有转述规则定级，找不到即放弃。
- [x] 运行 Task 1 测试确认转绿；重跑全量测试确认无回归。

### Task 3: 步骤 5 资源等级语义澄清

**Files:**
- Modify: `skills/learn-loop/reference/stages/05-resources.md`

**Interfaces:**
- Produces: 阶段契约中资源等级的语义边界说明。

- [x] 在「结构约束」的资源字段规则附近补一条：资源来源等级所支持的主张是"资源存在且简介与描述相符"，不是"其内容已被通读"；视频、课程、书籍等非文本媒体资源的 URL 指向资源介绍页或书目页，定级依据为介绍页正文对资源描述的支持程度。
- [x] 补一条使用要求：非文本媒体资源的`使用方法`必须写清介质形态（读/看/练），已知付费的须注明。
- [x] 不新增字段；`资源类型`、`使用方法`等既有字段含义不变。

### Task 4: 端到端复核

**Files:**
- 无新增修改，仅验证。

- [x] 在临时运行目录实际执行 `prepare_stage.py --stage 1`（或复用测试夹具），抽查一份生成的 `context/roles/*-task.md`，确认三段新规则完整出现在任务包中。
- [x] 运行全量 unittest 与技能包既有快速校验，确认无失败。
- [x] 将本计划各任务复选框勾选状态更新为实际结果。

## 自审

- 需求覆盖：准入线（用户共识点 1）、渠道优先级提示（共识点 2，含 AnySearch 实测修正——软过滤措辞、Availability 判据）、步骤 5 语义（共识点 3）均有对应任务。
- 范围控制：不触碰 original-prompts.md、脚本与模板；不新增枚举；上一轮分析中提及但本轮未达成实施共识的项（"不同来源"独立性定义、preflight 口径、时效性字段）不纳入本计划，仅在背景中留档。
- 时效性说明：`year_from` 经实测为软过滤，故不作为硬性时效闸门写入规则；候选的 `Published` 字段核对留由既有"内容评审"环节承担。
- 无占位符；三个任务间引用的章节名（检索操作要求、结构约束）与现有文档一致。
