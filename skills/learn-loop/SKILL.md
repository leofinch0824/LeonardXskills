---
name: learn-loop
description: >-
  中文优先的十步学习闭环：用五个隔离视角、来源分级、矛盾图谱、学习阶梯、两小时课程、主动回忆和费曼复述，生成可校验的 Markdown 事实源与离线 HTML。用户说“用十步学习法”“十倍速学 X”“learn-10x-faster”“系统学 X”“用 STORM 学 X”，或要求一套可留存、可复习、可施考的主题学习资料时使用。不要用于单一事实、只做某一步或明确要求其他交付格式的任务。
---

# Learn Loop

默认执行模式 A，依次生成十步材料。只有用户真实说“考我”才进入模式 B，真实说“给我讲 / 我来讲”才进入模式 C。

## 先守住这些边界

1. [`reference/original-prompts.md`](reference/original-prompts.md) 是不可改动的设计意图与溯源原文。阶段上下文必须包含当前步骤的连续原文切片；不要改写、删减或把执行契约反写进原文。
2. `reference/stages/*.md` 是阶段语义权威，`reference/modes/*.md` 是真实互动权威，`templates/*.md` 只定义序列化。验证器不得成为未写明的新规范，也不得自动修复产物。
3. 只读取 `prepare_stage.py` 为当前步骤生成的 context 包。当前步骤未通过前，不读取未来步骤契约、范本或产物；步骤 7/8 按两批披露。
4. 第 1 步的五个角色各自只读自己的任务包、只写自己的 `perspectives/*.md`。父 agent 等五份角色文件分别通过校验后，才写 `01-perspectives.md`；核心字段逐字抽取，完整分析留在角色文件。
5. 来源等级固定为：`A` = 可解析 URL 直接支持主张；`B` = 有 URL 但间接、转述或只支持一部分；`C` = 模型先验或未验证。未实测检索能力时进入`未锚定模式`，不得凭记忆补 URL。
   步骤 2 只有不同来源且至少一条 A/B 的共同结论可标`独立共识`；全 C 只能标`模型先验·待验证`。五份检索完整后才可把候选遗漏标为`领域盲区`，否则标`未覆盖`。
6. 步骤 1–10 的`本步提炼`恰好三条：核心结论、证据/边界/风险、对下一步的影响。普通字段使用`- **字段：** 值`；跨文件引用使用`相对路径#精确标题`。
7. 模式 A 不创建真实回答、得分、逐字复述、考试游标或费曼轮次。模式 B/C 不代答；用户没回答就不增加完成记录和游标。
8. `run-state.md`只保存运行、画像、能力、模式 A 进度和实际披露记录。考试事实只在`08-exam-record.md`，费曼事实只在`09-feynman-record.md`。
9. HTML 是 Markdown 的静态渲染视图，不在浏览器读取 Markdown，不补写事实。长期画像只在用户明确授权且提供确认原话时更新。

## 前置判断

创建任何运行文件前，按 [`reference/pre-check.md`](reference/pre-check.md) 判断`适合 / 调整后适合 / 不适合`。

- `不适合`：不创建运行目录，不执行 preflight，直接给出贴近原意的替代路径。
- `调整后适合`：等用户确认调整、风险和边界后再继续，并在`调整说明`保存用户确认原话。
- 主题资料密度不明时可做 1–2 次资料探针；它不产生 A/B/C 记录。

开场已给出的信息不重复问。进入模式 A 前补齐：当前水平、目标深度、角色 / 使用场景。前三项必须以`用户回答：`、`用户开场已提供：`或`未提供`开头。用户授权“你看着办”时才可采用默认值，并在`默认处理`记录实际默认值；否则阻塞步骤 1。

## 路径与能力实测

将本文件目录记为`<skill-root>`。解析：

- `<workspace-root>`：显式参数 → `LEARN_LOOP_WORKSPACE_ROOT` → Git 根 → 当前目录。
- `<state-root>`：默认`<workspace-root>/.learn-loop`。
- `<learning-root>`：默认`<workspace-root>/learning`。
- `<run-dir>`：`<learning-root>/<YYYY-MM-DD>-<HHMMSS>-<topic-slug>`；若存在则追加`-02`等，不覆盖。

实际成功检索、且至少一个候选的正文实际读取成功后才传`--retrieval-verified`；实际成功创建隔离 subagent 后才传`--subagents-verified`。执行：

```bash
python3 <skill-root>/scripts/preflight.py \
  --workspace-root <workspace-root> --bootstrap \
  [--retrieval-verified] \
  [--subagents-verified --subagent-mode parallel|serial-isolated|orchestrated] \
  --json
```

`parallel`与`serial-isolated`使用相同隔离任务包，只改变调度；`orchestrated`仍保留五份角色文件，但步骤 2 明示分歧可信度降级。未声明能力表示未知，不表示工具不存在。

## 模式 A：逐阶段执行

### 初始化阶段 0

```bash
python3 <skill-root>/scripts/prepare_stage.py \
  --run-dir <run-dir> --stage 0 --json
```

只填写生成的`run-state.md`。记录当前原始提示词 SHA-256、前置判定、画像来源、实际能力依据、独立性档位和锚定模式。然后运行：

```bash
python3 <skill-root>/scripts/validate_stage.py \
  --run-dir <run-dir> --stage 0 --json
```

### 步骤 1：角色隔离与父级屏障

```bash
python3 <skill-root>/scripts/prepare_stage.py \
  --run-dir <run-dir> --stage 1 --json
```

按照`run-state.md`的档位调度五个角色。每个角色只收到`context/roles/<role>-task.md`；任务包含自己的原文 persona、优先渠道、来源规则、完整输出范本、唯一输出路径和校验命令。角色完成后分别执行：

```bash
python3 <skill-root>/scripts/validate_stage.py \
  --run-dir <run-dir> --role <实践者|学者|怀疑者|经济学家|历史学家> --json
```

五份都通过后，父 agent 读取五份完整角色文件，填写`01-perspectives.md`并验证阶段 1。不要让角色并发写父级汇总或`run-state.md`。

### 步骤 2–10：统一阶段协议

对步骤`N`严格重复：

```bash
python3 <skill-root>/scripts/prepare_stage.py \
  --run-dir <run-dir> --stage <N> --json
```

只读取返回的当前 context，填写已物化的当前输出；不要覆盖已有的非空产物。完成后：

```bash
python3 <skill-root>/scripts/validate_stage.py \
  --run-dir <run-dir> --stage <N> --json
```

验证失败只修当前产物或它明确指出的上游，不跳过阶段。脚本检查结构、数量、枚举、引用和事实源边界；父 agent 仍需评审证据是否真的支持主张、分歧分类、评分理由和教学质量。

步骤 7/8 使用两批：

```bash
python3 <skill-root>/scripts/prepare_stage.py --run-dir <run-dir> --stage <7|8> --batch 1 --json
python3 <skill-root>/scripts/validate_stage.py --run-dir <run-dir> --stage <7|8> --batch 1 --json
python3 <skill-root>/scripts/prepare_stage.py --run-dir <run-dir> --stage <7|8> --batch 2 --json
python3 <skill-root>/scripts/validate_stage.py --run-dir <run-dir> --stage <7|8> --batch 2 --json
```

批次 2 只有在批次 1 通过后才生成；两批写同一阶段文件，并在同一披露记录追加第二个 context 路径。

### 当前步骤的规范入口

只在准备对应步骤后读取相应文件：

| 步骤 | 最终契约                                                      | 内容判断补充                                   |
| ---- | ------------------------------------------------------------- | ---------------------------------------------- |
| 0    | [`00-run-state.md`](reference/stages/00-run-state.md)         | [`pre-check.md`](reference/pre-check.md)       |
| 1    | [`01-perspectives.md`](reference/stages/01-perspectives.md)   | [`perspectives.md`](reference/perspectives.md) |
| 2    | [`02-conflicts.md`](reference/stages/02-conflicts.md)         | [`conflict.md`](reference/conflict.md)         |
| 3    | [`03-brief.md`](reference/stages/03-brief.md)                 | [`conflict.md`](reference/conflict.md)         |
| 4    | [`04-review.md`](reference/stages/04-review.md)               | [`conflict.md`](reference/conflict.md)         |
| 5    | [`05-resources.md`](reference/stages/05-resources.md)         | [`curriculum.md`](reference/curriculum.md)     |
| 6    | [`06-ladder.md`](reference/stages/06-ladder.md)               | [`curriculum.md`](reference/curriculum.md)     |
| 7    | [`07-sprint.md`](reference/stages/07-sprint.md)               | [`curriculum.md`](reference/curriculum.md)     |
| 8    | [`08-exam-bank.md`](reference/stages/08-exam-bank.md)         | [`examination.md`](reference/examination.md)   |
| 9    | [`09-feynman-notes.md`](reference/stages/09-feynman-notes.md) | [`examination.md`](reference/examination.md)   |
| 10   | [`10-cheatsheet.md`](reference/stages/10-cheatsheet.md)       | [`retention.md`](reference/retention.md)       |

### 最终化

步骤 10 通过后，不手工拼 HTML、INDEX 或复习队列。执行：

```bash
python3 <skill-root>/scripts/finalize_run.py \
  --run-dir <run-dir> --state-root <state-root> \
  --learning-root <learning-root> --json
```

需要物理单文件 HTML 时加`--inline`。仅当用户明确要求记住长期事实时，同时传`--profile-fact`和`--profile-quote`。最终化顺序为：全阶段验证 → 静态渲染 → HTML 验证 → 幂等登记 INDEX / review queue → 可选 profile → 将模式 A 标为完成。任一步失败都不得宣告完成。

## 模式 B：真实施考

用户首次说“考我 <主题>”时才从`templates/08-exam-record.md`创建`08-exam-record.md`，并遵守 [`reference/modes/exam-record.md`](reference/modes/exam-record.md)：

1. 在发送前先写`待回答`的实际题目；当前游标是已完成基础题数 0–10。
2. 一次只发一个基础题、追问或挑战；用户未回答，不创建完成事务。
3. 收到回答后追加完整事务，保存用户回答逐字引用、得分、答对处、确切差距和简语重讲。
4. 追问与挑战不增加基础题游标；记录只追加。
5. 每次写入后运行`validate_stage.py --stage exam-record --json`。十道基础题完成后才写最终总结。

复习得分用`review_queue.py --record-score`追加历史，不覆盖旧分数。

## 模式 C：真实费曼循环

用户首次说“给我讲 <主题>”或“我来讲 <主题>”时才从`templates/09-feynman-record.md`创建记录，并遵守 [`reference/modes/feynman-record.md`](reference/modes/feynman-record.md)：

1. 用步骤 9 的简单讲解和开放式检查点发出教学与复述邀请。
2. 用户复述后，依据真实措辞找含糊、跳步和错误；只重教这些缺口。
3. 追加完整轮次后再增加轮次计数，再邀请复述。
4. 用户讲清前不切换概念；`已讲清`必须引用最后一轮用户逐字复述，用户停止可记`仍未通过`。
5. 每次写入后运行`validate_stage.py --stage feynman-record --json`。

步骤 9 的备教材料不是用户最终定义。费曼通过的终点是用户能用简单、准确、完整的话真实复述；步骤 10 的一句定义只是以后快速恢复记忆的压缩提示。

## 交付边界

脚本能确认：结构、数量、枚举、引用、上下游、无模拟互动、HTML 离线资源、INDEX / queue 幂等性。执行模型不能自证以下事项，交付时明确请用户复核：

- 来源是否真的支持对应主张；
- 分歧、共识和盲区的语义判断是否合理；
- 评分和教学内容是否有质量；
- 模式 B/C 的逐字内容是否真是用户原话；
- 长期 profile 是否得到用户明确授权。
