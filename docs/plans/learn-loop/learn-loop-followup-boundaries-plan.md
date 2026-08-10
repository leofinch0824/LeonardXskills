# Learn Loop 遗留边界实施计划（独立性 / preflight 口径 / 时效性）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task.

**Goal:** 落实检索策略讨论中的三项遗留边界：①「不同来源」独立性采用触发式规则（仅在标`独立共识`、打 9–10 分时执行排查）；② `--retrieval-verified` 口径改为端到端（检索成功且至少一个候选正文读取成功）；③ 时效性以软纪律落地（复用既有自由字段，不新增 schema 字段）。

**Architecture:** 三项均为契约文档级改动。独立性规则与时效性扣分理由落在第 2–4 步纪律权威 `reference/conflict.md`；时效性候选核对句落在 `reference/perspectives.md`「检索操作要求」（经 `prepare_stage._retrieval_requirements()` 自动注入角色任务包）；preflight 口径改动落在 `SKILL.md` 判据句与 `preflight.py` 的旗标说明文案（仅文档字符串，无行为变更），并在 `reference/stages/00-run-state.md` 要求`检索验证依据`注明端到端实测。

**Tech Stack:** Markdown 契约文档、Python 3.11、unittest。

## 背景与共识

- 独立性（2026-08-11 确认）：真正的独立性是证据生成意义上的——转述同一原始出处的多条候选是一条证据的多个回声；逐条谱系溯源成本过高，故只在共识/高分两个"升格时刻"触发排查。
- preflight 口径（2026-08-11 确认）：管线真正依赖的是"检索+读取"组合能力；失败应在步骤 1 之前暴露，而不是五个角色跑完后才整体降级。单旗标重定义，不拆双旗标。
- 时效性（2026-08-11 确认）：必填日期字段会诱发编造（许多页面无明确日期），与"不给不可读介质评级"同构——不强制标注模型拿不到的事实。改为软纪律：候选筛选核对发布时间、第 4 步把证据过旧列为合法扣分理由。
- `tests/test_learn_loop.py` 仅在 1002 行使用过 `--retrieval-verified` 旗标，无测试断言 preflight 文案措辞，脚本说明文字可安全更新。

## Global Constraints

- 只修改本计划列出的文件：`skills/learn-loop/reference/conflict.md`、`skills/learn-loop/reference/perspectives.md`、`skills/learn-loop/SKILL.md`、`skills/learn-loop/scripts/preflight.py`（仅 docstring/help/警告文案）、`skills/learn-loop/reference/stages/00-run-state.md`、`tests/test_learn_loop.py` 和本计划。
- 不修改 `reference/original-prompts.md`、templates、验证器；不新增字段名或枚举值。
- `perspectives.md`「检索操作要求」章节内不新增 `## ` 级标题（保护注入正则捕获范围）。
- 不提交或推送 Git 变更。

---

### Task 1: 时效性注入守卫（red → 与 Task 3 一并转绿）

**Files:**
- Modify: `tests/test_learn_loop.py`

**Interfaces:**
- Consumes: 既有 `test_stage1_role_packets_carry_media_boundary_rules` 注入守卫测试。

- [x] 在该测试的锚点词列表中追加`发布时间`，确保时效性核对句落在注入范围内。
- [x] 运行该测试，确认因规则尚不存在而失败。

### Task 2: conflict.md 独立性触发式规则与时效性扣分理由

**Files:**
- Modify: `skills/learn-loop/reference/conflict.md`

**Interfaces:**
- Produces: 「共识与盲区」节的独立性排查规则；「第 4 步可靠性推导」的 9–10 分独立性引用与过旧扣分理由。

- [x] 在「共识与盲区」`独立共识`规则之后追加独立性判定段：独立性在证据生成意义上判定；仅在标`独立共识`或对发现打 9–10 分时执行三条排查——同一母站/出版方视为同一来源；引用同一原始出处（同一研究、公告、新闻稿）的多条候选视为同一谱系、只算一条；带转载/摘编标记（"转自"、canonical 指向、标题正文雷同）视为同一来源。同一视频的页面与其文字稿/transcript 亦属同一谱系。
- [x] 在第 4 步评分规则中：9–10 档的"两条不同的一手 A 来源"后注明须按上述独立性判定核算；区间调整理由中补入"证据发布时间显著旧于主张所涉现状"为合法扣分理由。
- [x] 不改其他档位分数定义与既有措辞。

### Task 3: perspectives.md 时效性候选核对句

**Files:**
- Modify: `skills/learn-loop/reference/perspectives.md`

**Interfaces:**
- Produces: 「候选出局双判据」段内的时效核对句，经既有注入机制进入角色任务包。

- [x] 在「候选出局双判据」段末追加一句：对时效敏感的主张，候选筛选时同时核对发布时间（academic 域结果带 `Published` 字段，网页提取正文常含日期）；显著过旧的在`取舍理由`注明，或出局换更新的候选。
- [x] 运行 Task 1 测试确认转绿。

### Task 4: preflight 端到端口径

**Files:**
- Modify: `skills/learn-loop/SKILL.md`
- Modify: `skills/learn-loop/scripts/preflight.py`（仅文案）
- Modify: `skills/learn-loop/reference/stages/00-run-state.md`

**Interfaces:**
- Produces: `--retrieval-verified` 的端到端判据在三处口径一致。

- [x] SKILL.md「路径与能力实测」节：将"实际成功检索后才传`--retrieval-verified`"改为"实际成功检索、且至少一个候选的正文实际读取成功后才传`--retrieval-verified`"。
- [x] preflight.py：更新 `--retrieval-verified` 的 help 文案与未声明时的警告文案，与端到端判据一致（只改字符串，不改逻辑）。
- [x] 00-run-state.md「结构约束」：`检索验证依据`须注明端到端实测内容（检索与正文读取各一次）。
- [x] 运行全量测试确认无回归。

### Task 5: 端到端复核

**Files:**
- 无新增修改，仅验证。

- [x] 重跑全量 unittest（存量 13 个 fixture 缺失错误除外，须与改动前数量一致）。
- [x] 抽查一份实际生成的 `context/roles/*-task.md`，确认时效核对句出现。
- [x] 将本计划各任务复选框更新为实际结果。

## 自审

- 需求覆盖：三个已确认方向（触发式独立性、端到端单旗标、软纪律时效性）各有对应任务；独立性规则的两个触发点（共识、9–10 分）在 Task 2 中都被写到。
- 范围控制：不新增字段/枚举/验证规则；preflight.py 只动文案不动逻辑；上上轮已实施的介质边界不重复触碰。
- 一致性：SKILL.md、preflight.py 文案、00-run-state.md 三处旗标语义由 Task 4 统一改齐，避免口径漂移。
- 无占位符；引用的章节名（共识与盲区、第 4 步可靠性推导、候选出局双判据、结构约束）与现有文档一致。
