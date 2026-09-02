# Learn Loop 执行流程瘦身实施计划

**日期：** 2026-09-02　**状态：** 已实施。前置分析见 `learn-loop-role-table-seam-remediation.md` 与运行瓶颈归因讨论（取证质量 + 流程重量为两大真实痛点）。

## 目标

在**不迁移形态**（仍是 skill）、**不触碰法条层**（`reference/original-prompts.md` 一字不改）的前提下，砍掉执行流程中的仪式性开销，降低修复循环频率。

## 变更一：删除阶段 7/8 双批次披露

两批之间没有任何用户交互、外部输入或改变生成条件的事件，批次闸门是纯仪式。删除后阶段 7/8 与其他阶段同构：一次 prepare、一次全量校验。每个主题净省 4 次脚本往返。

- `scripts/prepare_stage.py`、`scripts/validate_stage.py`：删除 `--batch` 参数及全部分支逻辑。
- `SKILL.md`：删除「步骤 7/8 使用两批」整节及边界 3 中的「按两批披露」。
- `reference/stages/07-sprint.md`、`08-exam-bank.md`、`reference/curriculum.md`、`reference/examination.md`：删除分两批生成的条款。

## 变更二：学科层数量约束放宽为区间

**法条锁定原则**：凡 `original-prompts.md` 原文写明的数量（5 个发现、5 个资源、5 级阶梯、10 次课、每课 5 复习题、10 题 + 5 挑战、5 快问快答、两句核心立场、一段 CEO 总结）是设计意图本身，保留精确校验；只放宽**学科层自设**的两处：

| 约束 | 原 | 新 | 理由 |
|---|---|---|---|
| 本步提炼 | 恰好 3 条 | 2–4 条（建议 3 条） | 学科层自设；模板保留 3 条占位作为提示 |
| 生活例子（步骤 9） | 恰好 2 个 | 1–3 个 | 法条未定数量；模板保留 2 个占位作为提示 |

## 变更三：prepare_stage 瘦身（删 context 打包与披露账本）

诊断结论：父级披露账本是不可执行的自我声明（执行器可读任意文件，校验器无法检测越权读取）；真正可执行的隔离在角色任务包层，**保留**。删减后 `prepare_stage.py` 的职责收敛为四件事：阶段闸门、模板物化（含 stage-3 锚定分支渲染）、角色任务包、游标推进。

- 删除 `build_stage_context` / `_context_path` / `_upstream_snapshot` / `_source_paths_for_stage` / `_record_disclosure` / `_completion_command`；`context/` 目录只保留 `context/roles/`。
- 返回值以 `read`（契约/原文/范本/角色包的相对路径清单）替代 `context`/`disclosed`——保留「指路」价值，去掉「打包复制」成本。上游产物清单本就在各范本的「消费上游」表中，产物自描述。
- `run-state.md` 删除「上下文披露记录」节；`reference/stages/00-run-state.md` 与 `_validate_stage_0` 同步去除披露校验（DUPLICATE/CONTINUITY/PROGRESS 等 5 个违规码退役）。
- `contract_io.py` 删除 `_append_disclosure` / `append_disclosure_items`，`update_run_state` 收敛为纯字段更新。
- 游标推进（当前阶段/已完成阶段/生成状态）保留，幂等：仅当游标从 N-1 前进到 N 时更新。
- `SKILL.md` 边界 3 改述：不读未来步骤契约/范本/产物仍是纪律（由 prepare 闸门 + 规范入口表支撑），但不再声称有披露账本式强制。

## 明确不做

- 法条层数量（5/10/5 等）——设计意图本身，放宽即覆盖法条。
- 模式 B/C 一切完整性不变量（游标、轮次、追加式、总结闸门）——反伪造内核。
- 标题结构、引用解析、上下游一致性校验——HTML 渲染器与交叉引用承重。
- URL 支持性核验脚本、轻量档——属下一步（取证质量轨道）。

## 验证

- 全套 pytest 通过（含改写后的 golden 集成流）。
- CLI 冒烟：临时目录实跑 prepare 阶段 0→2，确认闸门、物化、游标推进与 read 清单。
