# Learn Loop 格式契约实施评估结果

> 状态：确定性实现与回归门禁已完成；跨模型内容质量压力测试待具备可重复的新上下文模型执行环境后补测。
>
> 评估日期：2026-08-05

## 1. 评估边界

本轮评估回答两个不同问题：

1. 格式、顺序、引用、状态与渐进披露是否已经变成可执行约束；
2. 不同模型在真实新上下文中是否仍能产出充实且稳定的自由文本内容。

第一个问题已有自动化证据。第二个问题需要同一场景多次调用中端/Flash 与强模型；当前仓库和会话没有可控的多模型新上下文执行入口，因此没有把结构夹具或本模型自评冒充为跨模型质量结论。

## 2. 改造前控制样本

控制样本为：

`learning/2026-08-04-215937-emotional-regulation-cognitive-reframing/`

它由 DeepSeek V4 Flash 按旧版 skill 跑完，重新送入新校验器后稳定暴露出以下问题：

- 步骤 1 只有父文件，没有五份可独立验证、可保留完整分析和失败检索的角色文件；
- 多个文件使用“元信息/产物”等旧标题，模板与验证器没有共同的阶段契约；
- 步骤 3 出现标题粘连，并在正文尾部泄漏模型思考结束标记；
- 步骤 5 用自由表格表达一周路径，无法逐条校验行动节点字段；
- 步骤 8 的题型分组与新固定题目记录不一致；
- 步骤 9 预先生成“困惑点”和“最终定义”，替代了真实复述暴露理解缺口的费曼循环；
- 步骤 10 生成 7 道快问快答，而最终规范要求恰好 5 题且每题有答案；
- 多个阶段的“本步提炼”不是恰好 3 条。

这些不是对旧产物做兼容迁移的理由，而是新契约需要在生成前披露、在交付前阻断的控制证据。

## 3. 改造后的确定性证据

| 压力场景 | 自动化证据 | 结果 |
|---|---|---|
| 锚定并行步骤 1，其中一次检索未命中 | `test_anchored_stage1_retains_a_failed_search_record` | 失败检索保留在角色文件中，角色与父汇总仍可通过校验 |
| 五个角色隔离执行、父级只在屏障后读取 | `test_stage1_materializes_five_isolated_role_packets` | 五个任务包只含本角色原始提示词；父上下文不快照空范本 |
| 未锚定步骤 2–3，全体发现为 C | `test_unanchored_no_conflict_stages2_and3_accept_only_c_hypotheses` | 只接受“模型先验·待验证”和“假设简报”，不伪装独立共识 |
| 无真实分歧的主题 | 同上及完整 golden run | 允许带理由的“无”，不要求制造分歧 |
| 步骤 7 两批长输出 | `test_stage7_batch2_requires_batch1_and_reuses_one_stage_record` | 第二批必须等待第一批通过；披露记录只保留一个阶段条目 |
| 非法跳过阶段 | `test_stage_gate_rejects_skipping_the_run_cursor` | 即使手工放入上一步文件，也不能绕过运行游标和披露链 |
| 模式 B 用户尚未回答 | `test_exam_record_accepts_real_pending_transaction_before_answer` | 允许真实 pending 事务，不生成回答、得分或完成记录 |
| 模式 C 用户尚未复述 | `test_feynman_record_accepts_real_pending_invitation_before_restatement` | 邀请先落盘，只有真实逐字复述后才可追加完成轮次 |
| 步骤 4 引用步骤 3 | `test_review_cards_expand_the_referenced_finding` | 静态构建时展开被评发现，而不是在浏览器中读取 Markdown |
| 未锚定 HTML 语义 | `test_unanchored_run_renders_stage3_as_hypothesis_brief` | 地图和阶段标题均渲染为“假设简报” |
| 历史模型标题/表格漂移 | 三个 `deepseek-*` fixture 回归用例 | 返回局部结构化错误，不把漂移静默当作有效记录 |
| 完整运行与重复最终化 | `test_complete_run_finalizes_idempotently` | CLI 连续执行两次；HTML、INDEX、队列和画像事实不重复 |

此外，完整测试覆盖：原始提示词锚点与摘要、阶段/模板可达性、结构化错误对象、A/B/C 与状态枚举、引用路径防穿越、原子状态更新、HTML 离线资源和无脚本回退。

最终验证结果：

- `poetry run python -m unittest discover -s tests -p 'test_learn_loop.py' -v`：71 项通过；
- `poetry run python -m compileall -q skills/learn-loop/scripts tests`：通过；
- `poetry check`：通过；
- `git diff --check`：通过；
- `git diff --exit-code -- skills/learn-loop/reference/original-prompts.md`：通过，原始提示词无改动。

## 4. 信息保留检查

结构设计没有要求角色只返回短结构化片段：

- 每个角色拥有独立正式文件，保留“视角分析”“检索记录”“未决问题”等完整内容；
- 父文件只逐字抽取核心字段用于比较，不删除或改写角色全文；
- HTML 同时展示父汇总，并以可折叠区域保留五份角色详情；
- 只有需要机器判断的字段、枚举、数量、引用和事务状态被固定；解释、分析、理由、例子等仍为自由文本。

因此，当前自动化证据能证明信息通道没有因结构化校验被截断；它不能单独证明每个模型都会写出同等深度的自由文本。

## 5. 尚未完成的跨模型实证

以下结论本轮不作宣称：

- 中端/Flash 模型与强模型的内容深度是否相当；
- 同一措辞敏感场景运行至少 5 次后的结构方差和叙事方差；
- 父模型汇总是否在真实并行生成中始终不改变角色核心主张；
- 更严格格式是否对某一模型造成明显的内容缩水。

补测时应使用第 3 节同一组场景，每个措辞敏感场景至少运行 5 个全新上下文；逐项比较完整角色文件、父汇总逐字字段、自由文本信息密度、失败检索保留率和校验错误，而不是只统计通过率。该补测属于模型适配证据，不阻塞本次确定性契约实现落地。

## 6. 当前结论

新实现已经把旧样本中可观察的格式漂移、状态伪造、引用丢失和阶段越权转化为生成前披露与交付前校验。自动化回归与 CLI golden run 可以作为实现验收证据；跨模型内容质量仍应保持“待实测”，不能从结构测试外推。
