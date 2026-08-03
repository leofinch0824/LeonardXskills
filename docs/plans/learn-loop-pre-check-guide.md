# Learn Loop 前置判断指南实施计划

## 背景与目标

`learn-loop` 的 description 层已有粗粒度排除（单事实 / 只要一步 / 要 PPT），但存在中间地带：主题通过了触发词，执行到一半才发现不适合十步闭环（真实意图是决策或产出、范围过大、资料稀缺等），此时已付出开场画像和部分流水线的成本。

目标：在 skill 内增加**前置判断**机制——用户给出主题后、任何初始化之前，先判定适用性；不适合时把用户意图拆解为贴近原意的替代路径。机制为「对话层规程 + run-state 落盘记录 + stage 0 结构闸门」三层，与 skill 既有的「结构闸门强制记录、语义诚实归用户确认」双层模式对齐。

## 现状关键事实

- skill 实际位于 `skills/learn-loop/`，但 `tests/test_learn_loop.py:13` 与 `tests/test_paper_trail.py:14` 的 `SKILL_ROOT` 仍指向仓库根下的旧路径，**当前 31 个 learn-loop 用例全部因路径失败**。这是目录迁移遗留的既有破坏，不修则任何改动都无法验证。
- 前置判断发生在 run-dir 创建之前，因此判定结论只能**随移交带入** `run-state.md`，不能提前落盘。
- 既有 stage 0 闸门（`validate_stage.py:159`）已建立「画像字段来源标记」模式：结构强制 + 信任型内容归人。前置判定闸门复用该模式。

## 可改动范围

| 路径 | 改动 |
|---|---|
| `docs/plans/learn-loop-pre-check-guide.md` | 本计划（新增） |
| `skills/learn-loop/reference/pre-check.md` | 新增，判定细则全文 |
| `skills/learn-loop/SKILL.md` | 新增「前置判断」一节 + 资源导航一行 + 初始化节一句顺序约束 |
| `skills/learn-loop/templates/run-state.md` | 新增「前置判定」节 |
| `skills/learn-loop/scripts/validate_stage.py` | `validate_stage_0` 增加前置判定结构检查 |
| `tests/test_learn_loop.py` | 修 `SKILL_ROOT`；4 处既有 fixture 各加一行合法前置判定；新增反例/正例用例 |
| `tests/test_paper_trail.py` | 仅修 `SKILL_ROOT` 一行（同源既有破坏，不顺便修会让套件保持红色） |

不做：不改 description 前置词、不改 HTML 模板与 html-guide、不回填 `learning/` 既有产物、不新增检索探针脚本、不提交 git。

## 设计决策

1. **位置**：前置判断是 skill 的「门」而非「第 0 步」。SKILL.md 新节置于不变量之后、「路径与初始化」之前；细则入 `reference/pre-check.md`，与既有「SKILL.md 存简明规则、reference 存细则」分层一致。
2. **三值判定**：适合 / 调整后适合 / 不适合。「不适合」不建 run-dir、不跑 preflight，纯对话交付三行结论 + 替代路径；用户明确坚持时转为「调整后适合」，在调整说明中记录原判定与已声明风险（枚举保持二元，记录不造假）。
3. **闸门范围**：stage 0 只强制「判定记录存在且枚举合法、理由非空、调整后适合时调整说明非空」；判定是否真实反映对话属信任型，归入交付前用户确认清单（同 B3 模式）。
4. **不越界**：前置判断不替代开场画像，画像三问仍在模式 A 照常执行；反问最多 3 问，开场已答信息直接采信。
5. **测试纪律**：先写失败用例再实现；既有断言只增不删，4 处 fixture 编辑均为「补一节合法前置判定」的纯追加。

## 实施步骤

1. **修既有破坏** → `tests/test_learn_loop.py:13` 与 `tests/test_paper_trail.py:14` 的 `PROJECT_ROOT / "learn-loop"`（/ `"paper-trail"`）改为 `PROJECT_ROOT / "skills" / "learn-loop"`（/ `"paper-trail"`）。
   验证：`poetry run pytest tests/ -q` 全绿；若有路径以外的真实失败，先报告再决定。
2. **写失败测试** → `test_learn_loop.py`：
   - `REQUIRED_FILES` 增加 `reference/pre-check.md`；
   - `test_markdown_contracts_are_present` 增加 `"前置判断"` 断言；
   - 新增 `test_stage0_rejects_invalid_precheck_verdict`（判定为占位或「不适合」→ FAIL）、`test_stage0_rejects_adjusted_without_note`（调整后适合但调整说明为「无」→ FAIL）、`test_stage0_accepts_valid_precheck`（合法节 → PASS）；
   - 4 处既有 PASS 型 fixture（两个 `--all` 完整 fixture、`test_stage0_accepts_sourced_profile_fields`、`test_stage0_accepts_unprovided_with_fallback`）各补一节合法前置判定。
   验证：新用例 FAIL、既有 FAIL 型用例仍 FAIL（原因不丢）。
3. **模板与闸门** → `templates/run-state.md` 在「学习画像」前插入「前置判定」节（判定 / 判定理由 / 调整说明 / 资料探针 四字段）；`validate_stage_0` 增加：判定须以「适合 / 调整后适合」开头；判定理由非占位；判定为调整后适合时调整说明不得为「无/不适用/占位」；资料探针非占位（「未做」合法）。
   验证：步骤 2 全部用例转 PASS。
4. **细则文档** → 新建 `reference/pre-check.md`：定位与触发时机、正/负向信号表、反问清单（≤3 问 + 你看着办处理）、意图拆解决策树（7 分支）、三行结论交付格式、移交规范、可选资料探针、话术示例、红线（不隐性降级、不硬判适合挽留、用户坚持时的记录方式）。
   验证：`poetry run pytest tests/test_learn_loop.py -q` 全绿（包契约与可移植性用例覆盖新文件）。
5. **SKILL.md 接线** → 不变量后插入「## 前置判断：适用性判定」节（≤8 行，指向 reference）；「路径与初始化」开头加一句「须先完成前置判断并移交」；「资源导航」加一行。
   验证：全量 `poetry run pytest tests/ -q` 全绿；`validate_stage.py --all` 对完整 fixture 仍 PASS。

## 全局验收

- `poetry run pytest tests/ -q` 全绿，无既有断言被删除或放宽。
- 新增闸门正例（合法前置判定通过）与反例（占位判定 / 不适合枚举 / 调整后无说明被拦）各至少一个用例。
- 新文件中无绝对路径（可移植性用例保证）。
- SKILL.md 中前置判断、画像、初始化三者顺序无歧义：前置判断 → preflight/能力实测 → 开场画像 → run-dir → 第 1–10 步。
