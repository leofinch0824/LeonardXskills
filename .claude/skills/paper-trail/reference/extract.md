# Extract — 结构化抽取

只对 T0/T1。目标是几 KB 的抽取卡,不是全文摘要。全文永不进 agent 上下文。

## Layer B 路由(拿正文,按优先级)

1. **arXiv 有 LaTeX 源** → arxiv-mcp 按章节读(最干净,公式保真,零解析错误)
2. **仅 PDF** → MinerU 子进程解析成 markdown(`uvx magic-pdf`,AGPL 只作子进程),落 `.cache/`
3. **MinerU 不可用或 license 敏感** → GROBID(Apache-2.0)
4. 以上皆缺 → abstract+TLDR only,抽取卡标注 `abstract-only`(置信度降档)

## 离线抽取 worker

```bash
python3 .claude/skills/paper-trail/scripts/extract_paper.py \
  --paper <解析后 markdown 或 LaTeX 拼接> \
  --template .claude/skills/paper-trail/templates/extraction.md \
  --profile .claude/paper-trail/profile.md \
  --out 04-extractions/<paper-id>.md
```

worker 用便宜模型一次调用按模板产出抽取卡,不经 agent 上下文,token 用量打印到 stdout(抄进 ledger.md)。若端点不属于 localhost/private IP/`.local`/`.internal`/`PAPER_TRAIL_WORKER_TRUSTED_HOSTS`,必须使用 HTTPS 并在确认 paper 与 profile 均已脱敏后显式加 `--desensitized`。

正文超过 120,000 字符时 worker 会拒绝静默截断。先按章节筛出机制/结果/局限/资源需求后重试；无法可靠筛选时走下述降级梯，并在抽取卡记录覆盖缺口。

**降级梯**:worker 不可用 → 每篇派一个 subagent 抽取(只回抽取卡,markdown 留在磁盘)→ 主 agent 抽取(仅限 T0)。

## 抽取卡 schema

见 [templates/extraction.md](../templates/extraction.md)。固定字段:机制 / 结果(数字+基准)/ 局限(作者自认 + 我方判断)/ 可适用性四档 / 落地成本 / 前置依赖 / schema 外值得注意的点(**逃生口自由字段**——schema 装不下的重要发现放这,是将来升级 schema 的依据)。

## 可适用性四档(对照 profile.md 的硬约束)

| 档 | 含义 |
|---|---|
| 直接可用 | 开源权重 + 推理期方案,4×H20 内可跑 |
| 需微调(算力内) | 全参 ≤~30B 或 LoRA 更大;>70B 全参标"超算力"归不适用 |
| API 辅助(脱敏后) | 混合模式:本地小模型 + API 大模型做蒸馏/数据合成/复杂推理 |
| 不适用 | 闭源-only 且无法脱敏外包,或算力明显超标 |

判定必须引用论文中的具体证据(模型规模、数据、资源需求),并区分**"论文已证明"**与**"对你场景的外推"**——外推的结论在抽取卡上标注。
