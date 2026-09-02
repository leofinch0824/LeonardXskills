# Learn Loop 角色表接缝修复实施记录

**日期：** 2026-09-02　**状态：** 已实施并通过全套测试（83 passed）。

## 背景

提交 `ec9fdbc` 对 `reference/perspectives.md` 做了 markdown 表格对齐重排（单元格空白填充）。`prepare_stage._role_guidance` 用空白敏感正则 `^\| <角色> \|.*\|$` 匹配「视角与渠道」表，重排后正则失配，`prepare_stage.py --stage 1` 抛 `ValueError: 角色纪律中找不到视角`，模式 A 流水线在第一关即崩溃。同时测试套件 8 红（3 个源于该崩溃，5 个因 `tests/fixtures/learn-loop/` 从未入库的 fixture 文件而永远无法运行）。

## 根因（codebase-design 视角）

`reference/` 文档层与 `scripts/` 脚本层之间的「视角与渠道」表是一条**隐式接缝**：其接口本应是语义内容（角色 → 优先渠道、重点追问），但消费方实现伸进了文档的排版实现细节（对齐空白）。仓库中同类接缝（模板上游表 ↔ `EXPECTED_UPSTREAMS`、提示词标题 ↔ `PROMPT_HEADINGS`）都有针对真实文件的契约测试钉住，唯独这条接缝没有任何守卫，于是成为唯一破口。

## 修复内容

1. `scripts/contract_io.py`：新增 `ROLE_NAMES`、`markdown_table_rows()`（跳过分隔行的通用管道表解析）与 `role_channel_table(text)`（「视角与渠道」章节 → `{角色: (优先渠道, 重点追问)}`）。markdown 排版细节收敛在这一个深模块里，对齐空白从此是实现细节。
2. `scripts/prepare_stage.py`：`_role_guidance` 改为 `role_channel_table` 的薄消费者，删除空白敏感正则。
3. `scripts/preflight.py`：新增 `check_role_discipline` 检查并挂入 `checks`。`tests/` 按 AGENTS.md 属本地内容不随包发布，preflight 是发布包内唯一能自证接缝完好的入口：五个角色任一无法解析即 `blocked`（exit 1），在初始化前大声失败而非步骤 1 中途崩溃。
4. `reference/perspectives.md`：在「视角与渠道」表旁显式写明机读契约（第一列精确角色名、三列结构、对齐空白不限），把隐式接口变成显式文档。
5. `tests/test_learn_loop.py`：
   - 5 个死 fixture 测试改为自包含：2 个 ContractIo 测试内联构造文档；3 个校验器漂移测试改为 golden builder 生成合法运行后做单点标题突变（`关键发现 5 → 关键发现：第五项`、`行动节点 5 → 行动节点：第 5 天`、`复述检查点 → 复述检查点 1接纳不等于赞同`），断言原违规码不变。删除从未有过适配器的 `FIXTURES` 文件接缝。
   - 新增接缝测试：`role_channel_table` 对已发布 `perspectives.md` 解析出全部五角色；容忍对齐填充；preflight `role_discipline` 对真实包通过、对缺角色的表报错。

## 验证

- `python3 -m pytest tests/test_learn_loop.py tests/learn_loop_golden.py` → 83 passed（修复前 71 passed / 8 failed）。
- 真实文件冒烟：`build_role_packets` 生成 5 个任务包，实践者包正确注入优先渠道与重点追问；preflight CLI 报告 `role_discipline: OK`。

## 未做（建议后续）

- 「来源 URL 是否真的支持主张」的自动核验（新功能，需单独设计）。
- 轻量运行档、中途改范围协议。
- 其余文档↔脚本耦合点（如 `PROMPT_HEADINGS`、`CONTRACT_PATHS`）已有契约测试覆盖，无需额外加固。
