# Learn Loop 前置判断指南实施计划

> 状态：**已实施，本文已按当前实现对齐**（核对日期：2026-08-04）。
> 实际包根为 `skills/learn-loop/`；README 的仓库内链接和直接运行命令使用该前缀，复制到宿主 skills 目录后再按安装后的包根使用。

## 背景与目标

`learn-loop` 的 description 层已有粗粒度排除（单事实 / 只要一步 / 要 PPT），但存在中间地带：主题通过了触发词，执行到一半才发现不适合十步闭环（真实意图是决策或产出、范围过大、资料稀缺等），此时已付出开场画像和部分流水线的成本。

目标：在 skill 内增加**前置判断**机制——用户给出主题后、任何初始化之前，先判定适用性；不适合时把用户意图拆解为贴近原意的替代路径。机制为「对话层规程 + run-state 落盘记录 + stage 0 结构闸门」三层，与 skill 既有的「结构闸门强制记录、语义诚实归用户确认」双层模式对齐。

## 实现核对结果

- 历史路径问题已修复：`tests/test_learn_loop.py` 与 `tests/test_paper_trail.py` 当前都从 `PROJECT_ROOT / "skills" / ...` 解析包根。
- 前置判断发生在 run-dir 创建之前；当前 `SKILL.md`、`reference/pre-check.md`、`templates/run-state.md` 和 `validate_stage_0` 已共同实现判定记录、移交顺序与结构闸门。
- 当前 learn-loop 测试收集 40 个用例，前置判断相关正反例、跨行 `<noscript>` 回归以及固定资源交付测试均通过；全量套件为 65 个测试、6 个 subtests 全部通过。

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

## 实施步骤与完成状态

以下条目均已在当前源码中落地，`[x]` 表示实现与对应测试存在。

1. [x] **修既有路径问题** → `tests/test_learn_loop.py` 与 `tests/test_paper_trail.py` 均使用 `PROJECT_ROOT / "skills" / ...` 包根。
   验证：路径相关用例通过；完整套件通过。
2. [x] **写失败测试** → `test_learn_loop.py`：
   - `REQUIRED_FILES` 增加 `reference/pre-check.md`；
   - `test_markdown_contracts_are_present` 增加 `"前置判断"` 断言；
   - 新增 `test_stage0_rejects_invalid_precheck_verdict`（判定为占位或「不适合」→ FAIL）、`test_stage0_rejects_adjusted_without_note`（调整后适合但调整说明为「无」→ FAIL）、`test_stage0_accepts_valid_precheck`（合法节 → PASS）；
   - 4 处既有 PASS 型 fixture（两个 `--all` 完整 fixture、`test_stage0_accepts_sourced_profile_fields`、`test_stage0_accepts_unprovided_with_fallback`）各补一节合法前置判定。
   验证：占位/不适合/调整无说明的反例被拦，合法判定正例通过。
3. [x] **模板与闸门** → `templates/run-state.md` 已含「前置判定」四字段；`validate_stage_0` 已检查合法枚举、理由/资料探针非空、调整后适合的具体调整说明，以及画像字段来源标记。
   验证：stage 0 相关正反例通过；不适合不会进入运行目录的规则由 SKILL.md 语义执行。
4. [x] **细则文档** → `reference/pre-check.md` 已覆盖定位与触发时机、正/负向信号、最多 3 问、意图拆解、三行交付、移交、资料探针、话术和红线。
   验证：包契约、可移植性和文档关键词用例通过。
5. [x] **SKILL.md 接线** → 已接入前置判断节、初始化顺序约束和资源导航；前置判断不替代开场画像。
   验证：完整 fixture 的 stage 0 前置判定检查通过；整体测试通过。

## 全局验收

- [x] 新增闸门正例（合法前置判定通过）与反例（占位判定 / 不适合枚举 / 调整后无说明被拦）均有用例。
- [x] 新文件和规则中无绝对路径（可移植性用例覆盖）。
- [x] `SKILL.md` 中前置判断、画像、初始化三者顺序明确：前置判断 → preflight/能力实测 → 开场画像 → run-dir → 第 1–10 步。
- [x] stage 0 对合法前置判定保持通过；跨行 `<noscript>` 回归已修复，完整测试通过。
