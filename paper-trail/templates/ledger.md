# Token 台账 — <slug>

有 API usage 时使用实际数据；agent token 只能估算时明确标注“估算”；无法获取时写“不可得”，不得假造精确值。

| 阶段 | 动作 | 模型 | 输入/输出 token(约) | 备注 |
|---|---|---|---|---|
| preflight | | | | |
| intake | | | | |
| landscape | | | | |
| discovery | N 路 subagent | | | |
| triage | | | | |
| extract | worker × N 篇 | <worker 模型> | | 抄 worker stdout |
| verify | 复核 × N + 批判 | | | |
| synthesis+brief | | | | |
| **合计** | | | | |

## 汇总指标

分母为 0 时写 `N/A`。

| 指标 | 值 | 计算方式 |
|---|---|---|
| 总 token | | 各阶段合计 |
| Discovery 候选数 | | 02-pool 去重后候选 |
| T0+T1 篇数 | | 03-triage |
| 完成抽取卡数 | | 04-extractions |
| 每篇抽取卡 token | | extract token / 抽取卡数 |
| 每篇入选论文总 token | | 总 token / (T0+T1) |
| 不可计量阶段 | | 无 usage 数据时列出 |
