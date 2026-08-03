---
name: learn-loop
description: >-
  中文优先的十步学习闭环：从开场学习画像、五个独立视角和来源分级，经过矛盾图谱、课程阶梯、核心练习，生成可校验的 Markdown 事实源与单文件 HTML 教材；再按用户主动触发的“考我”“给我讲/我来讲”执行可续考的检索练习和费曼复述。用户说“用十步学习法”“十倍速学 X”“learn-10x-faster”“系统学 X”“用 STORM 学 X”或要一套可留存、可复习的主题学习资料时使用。不要用于只问一个事实、只要某一步，或明确要 PPT/正式报告等其他交付物的请求。
---

# Learn Loop

把十步学习法执行成一条可追溯、可校验、可复习的学习闭环。默认使用模式 A 生成材料；只有用户明确触发时才进入模式 B 施考或模式 C 费曼会话。

## 不可违反的不变量

1. **保持视角独立性。** 第 1 步首选 `parallel`：5 个 subagent 只收到主题、自己的原文提示词段和 persona 纪律，互不可见输出。没有并行能力时使用 `serial-isolated`；每次写盘前不得读取另外四份。没有 subagent 时才使用 `orchestrated`，并在 `run-state.md` 与第 2 步声明“编排模式·分歧可信度降级”。记录实际档位，不把串行编排伪装成独立发现。
2. **分化取证渠道。** 实践者优先工程博客、issue、事故复盘和从业者论坛；学者优先同行评审论文、综述和会议录；怀疑者优先复现失败、负面结果、撤稿和批评；经济学家优先融资并购、定价、营收和市场报告；历史学家优先行业史、相似先例和失败案例。每个视角落盘查询词、渠道、命中数和是否采信。
3. **标注来源等级。** `A` = 有可解析 URL 且直接支持主张；`B` = 有 URL 但为转述、间接或部分支持；`C` = 模型内生、未验证。检索工具经实测不可用、或本轮未实测声明时，进入“未锚定模式”，第 1–5 步全部标 C，状态和 HTML 顶部都要声明，不能编造链接；未声明 ≠ 不可用，不得把“没人验证过”说成“工具不存在”。
4. **分级共识。** 至少两个视角以不同来源支持同一结论且至少一条为 A/B，才写“独立共识”；全为 C 的一致只能写“模型先验·待验证”，不得进入简报前 3 个关键发现。
5. **依据检索记录判断盲区。** 5 份检索记录完整后，才可称“领域盲区”；否则写“未覆盖”。
6. **隔离真实练习记录。**
   - 6a. 模式 A 只生成题库和讲解材料，不生成答题记录或复述记录（脚本可校验）。
   - 6b. 模式 B/C 不代答、不因用户未答推进游标；答题和复述必须逐字引用用户原话（脚本只能校验字段非空，不能证明是真原话）。
   - 6c. 「逐字引用用户原话」是信任型闸门：人工复核者必须是用户本人或另一名人类，不是执行本 skill 的模型。模型不得代为宣告通过，必须在交付时显式列出自己无法自证的项，交由用户确认。
7. **把原文提示词当法条。** 每步执行指令必须取自 [`reference/original-prompts.md`](reference/original-prompts.md)，只填 `{{主题}}`、`{{角色}}`、`{{水平}}`、`{{目标}}`（`{{水平}}`/`{{目标}}` 由纪律层第 6/7 步消费，不进入原文法条正文），再追加对应纪律附录；不得改写、删减原文要求。
8. **只回灌用户确认的长期事实。** 开场学习画像默认不进 `learner-profile.md`（属本轮一次性场景）；仅当用户明确表示“记住这个”时才回灌，并引用原话和日期。`learner-profile.md` 不记录模型从分数推断的倾向；这类观察只留在本轮产物和复习队列。

## 前置判断：适用性判定

用户给出主题后、执行任何初始化之前，先做适用性判定（细则见 [`reference/pre-check.md`](reference/pre-check.md)）：

- 复用开场已给信息，最多补问 3 个问题；判定只产出三种结论：适合 / 调整后适合 / 不适合。
- 判定为不适合：不创建运行目录、不执行 preflight，直接向用户交付三行结论与贴近原意的替代路径；用户明确坚持时转为「调整后适合」，调整说明中记录原判定与已声明风险。
- 判定移交模式 A 时，把判定、判定理由、调整说明、资料探针写入 `run-state.md` 的「前置判定」节；任何降级（未锚定、orchestrated、范围收窄）必须显式记录，不得隐性降级。
- 前置判断不替代开场画像；画像三问仍在模式 A 中照常执行。

## 路径与初始化

进入本节前必须已完成前置判断且结论为适合或调整后适合；判定为不适合时不执行本节任何动作。将当前文件所在目录称为 `<skill-root>`。按以下优先级解析目标：显式 `--workspace-root` → `LEARN_LOOP_WORKSPACE_ROOT` → Git 根 → 当前目录，得到 `<workspace-root>`。

- `<state-root>`：`LEARN_LOOP_STATE_DIR`，默认 `<workspace-root>/.learn-loop`。
- `<learning-root>`：`LEARN_LOOP_LEARNING_DIR`，默认 `<workspace-root>/learning`。
- `<profile-path>`：`<state-root>/learner-profile.md`。
- `<queue-path>`：`<state-root>/review-queue.md`。
- `<index-path>`：`<learning-root>/INDEX.md`。
- `<run-dir>`：`<learning-root>/<YYYY-MM-DD>-<slug>`，其中 `<slug>` 为 `<HHMMSS>-<topic-slug>`；例如 `2026-08-03-143052-python-asyncio`。创建前检查目录是否已存在；存在时在 slug 后追加 `-02`、`-03` 等序号，绝不覆盖既有产物。

保持 skill 包只读。首次运行先实测能力再声明：实际试调用一次检索工具成功后传 `--retrieval-verified`；实际试 spawn 一次独立 subagent 成功后传 `--subagents-verified` 与 `--subagent-mode parallel|serial-isolated|orchestrated`。然后执行：

```bash
python3 <skill-root>/scripts/preflight.py --workspace-root <workspace-root> --bootstrap \
  [--retrieval-verified] [--subagents-verified --subagent-mode <档位>] --json
```

`--bootstrap` 只创建缺失的 profile、queue 和 INDEX，不覆盖已有内容。未声明的维度按「未知」处理，未声明 ≠ 不可用；只有 JSON 中能力 `verified` 为真时才采用 `parallel` 或 `anchored`，否则按 `suggested_independence_tier` / `anchoring_mode` 输出执行，并把裁决依据（实测结果或「未声明」）写入 `run-state.md`。不要因为能力缺失而跳过阶段，改为明确降级并标 C。

## 模式 A：生成流水线

开场画像必须在执行第 1 步之前完成，且必须真实问询：

1. 当前水平和目标深度（零基础/有点基础/有经验 × 能聊两句/能上手干活/能和专业人士对谈）。向用户提问并等待回答，不得以默认值或模型假设替代提问。
2. 角色和使用场景。仅当用户在开场消息中已显式陈述时才记录“用户开场已提供：<引用原话>”；模型的推断不算已提供。

三个画像字段的取值必须以 `用户回答：`、`用户开场已提供：`（附原话引用）或 `未提供` 之一开头。用户明确说“你看着办”时记为 `未提供`，采用默认值，并在 `run-state.md` 与 HTML 学习画像处注明“已按默认值执行”；字段缺失且用户未授权默认时，阻塞并向用户追问，不得继续。

把答案凝成一句学习画像写入 `run-state.md`，以本轮开始时间和主题生成 slug，记录档位、锚定模式、模式 A 状态和十步游标。之后按 1→10 顺序执行，严禁跳序。每份阶段文件都要声明“消费上游”、保存完整原始“产物”、并提供 3–5 条“本步提炼”。需要详细规则时按下表读取对应参考文件：

| 步骤 | 必须交付与硬闸门 | 纪律附录 |
|---|---|---|
| 1 | 恰好 5 视角；每个有立场、最强证据、独家洞见、检索记录和 A/B/C 等级 | [`perspectives.md`](reference/perspectives.md) |
| 2 | 分类实质/措辞/未决分歧；分级共识；带依据判断领域盲区或未覆盖 | [`conflict.md`](reference/conflict.md) |
| 3 | CEO 60 秒段；恰好 5 个发现；每个有来源等级、支持/反对视角；前 3 不放模型先验 | [`conflict.md`](reference/conflict.md) |
| 4 | 5 个发现各有 1–10 分和推导依据；回答最弱结论、过重视角和第 6 视角 | [`conflict.md`](reference/conflict.md) |
| 5 | 恰好 5 个资源 × 4 字段；每项有 URL 或 C 级；坑清单和覆盖 5 项的一周路径 | [`curriculum.md`](reference/curriculum.md) |
| 6 | 5 级 × 8 要素全非空；定位当前级和下一里程碑 | [`curriculum.md`](reference/curriculum.md) |
| 7 | 核心 20% 及原因；8–12 课；每课 5 字段和 3–7 题；可验证终局项目 | [`curriculum.md`](reference/curriculum.md) |
| 8 | 10 题（1–3 初、4–6 中、7–8 高、9–10 专家）各有参考答案和评分标准，另 5 道挑战只给题 | [`examination.md`](reference/examination.md) |
| 9 | 12 岁版、3–5 个困惑点、简单准确完整的最终定义；不写复述记录 | [`examination.md`](reference/examination.md) |
| 10 | 一句定义、短条目、3–5 例、易错易混、上场清单、3–7 道快问快答；渲染、索引和复习队列回灌 | [`retention.md`](reference/retention.md)、[`html-guide.md`](reference/html-guide.md) |

第 8/9 步是备考/备教材料，不是实际练习。模式 A 完成后按 [`html-guide.md`](reference/html-guide.md) 将全部 Markdown 片段填入 [`assets/template.html`](assets/template.html) 副本，输出 `<run-dir>/<主题>-十步学习.html`。HTML 是视图，不得成为事实源；不得残留 `{{`。页面要显示施考状态行：未施考时为“交互施考未进行，对我说‘考我’即可开始”，用户练习后按 `08-exam-record.md` 的 `当前游标` 重渲染为“交互施考已完成 N 题”；并在 `<index-path>` 追加一行、用 `review_queue.py --add` 登记 1/7/30 天复习。

## 模式 B：施考会话

用户说“考我 <主题>”时，定位对应 `<run-dir>`，读取 `08-exam-bank.md` 和 `run-state.md`，从 `08-exam-record.md` 的 `当前游标` 继续，一次只问一题。用户回答后才写入四件套：逐字引用原话、0–10 分、答对处、确切差距与简语重讲；弱答先追问，强答提高难度。立即落盘并推进 `当前游标`，不能替用户回答或预先写记录。10 题完成后写总分、强弱领域、复习计划和 5 道挑战；低于 6 分的弱项写入状态供模式 C，并执行：

```bash
python3 <skill-root>/scripts/review_queue.py --state-dir <state-root> --record-score --slug <slug> --score <0-10>
```

中断后只信 `08-exam-record.md` 的 `当前游标`，不根据聊天记忆补题。

## 模式 C：费曼会话与复习

用户说“给我讲 <主题>”或“我来讲 <主题>”时，优先读取模式 B 的弱项；尚未施考则使用第 3 步核心概念。以 `09-feynman-notes.md` 为底稿执行“教 → 用户复述 → 定位含糊/跳步 → 只重教缺口 → 再复述”，直到“已讲清”或显式记录“仍未通过”。每轮将用户复述逐字写入 `09-feynman-record.md`，用户讲清前不进入新内容。

复习时执行 `review_queue.py --due`，对到期主题按模式 B 重考，优先历史弱项和终极挑战，得分后推进下一间隔；不要覆盖历史得分。

## 机器闸门与交付前检查

运行：

```bash
python3 <skill-root>/scripts/validate_stage.py --run-dir <run-dir> --all --json
```

脚本负责数量、必填章节、表格非空、上游文件存在、游标一致、HTML 占位符和回灌记录等结构检查；它不判断分歧是否实质、来源是否真的支持结论、评分推导是否合理或引用是否真为用户原话。交付前分两栏确认：

- 脚本已验证：10 个阶段按序、来源等级结构完整、HTML 可打开且无外部依赖、模式 A 没有答题/复述记录、INDEX/queue 已追加。
- 需用户确认（模型不得代为宣告通过）：分歧是否实质、来源是否真的支持结论、评分推导是否合理、逐字引用是否真为用户原话、profile 回灌是否经用户明确确认。

## 资源导航

- 前置判断细则（适用性信号、反问清单、意图拆解）：[`reference/pre-check.md`](reference/pre-check.md)
- 原文十段提示词：[`reference/original-prompts.md`](reference/original-prompts.md)
- 五视角与独立性：[`reference/perspectives.md`](reference/perspectives.md)
- 冲突、共识与可靠性：[`reference/conflict.md`](reference/conflict.md)
- 资源、阶梯和课程：[`reference/curriculum.md`](reference/curriculum.md)
- 题库、施考和费曼：[`reference/examination.md`](reference/examination.md)
- 速查表、回灌和复习：[`reference/retention.md`](reference/retention.md)
- HTML 占位符和渲染：[`reference/html-guide.md`](reference/html-guide.md)
