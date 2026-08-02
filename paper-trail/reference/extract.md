# Extract — 结构化抽取

只对 T0/T1。目标是几 KB 的抽取卡,不是全文摘要。全文永不进 agent 上下文。

## Layer B 路由(拿正文,按优先级)

1. **arXiv 有 LaTeX 源** → arxiv-mcp 按章节读(最干净,公式保真,零解析错误)
2. **仅 PDF** → MinerU 子进程解析成 markdown(`uvx magic-pdf`,AGPL 只作子进程),落 `<run-dir>/.cache/`
3. **MinerU 不可用或 license 敏感** → GROBID(Apache-2.0)
4. 以上皆缺 → abstract+TLDR only,抽取卡标注 `abstract-only`(置信度降档)

## 离线抽取 worker

```bash
python3 "<skill-root>/scripts/extract_paper.py" \
  --paper "<run-dir>/.cache/<paper-id>.md" \
  --template "<skill-root>/templates/extraction.md" \
  --profile "<profile-path>" \
  --out "<run-dir>/04-extractions/<paper-id>.md"
```

worker 用便宜模型一次调用按模板产出抽取卡,不经 agent 上下文,token 用量打印到 stdout(抄进 ledger.md)。若端点不属于 localhost/private IP/`.local`/`.internal`/`PAPER_TRAIL_WORKER_TRUSTED_HOSTS`,必须使用 HTTPS 并在确认 paper 与 profile 均已脱敏后显式加 `--desensitized`。

正文超过 120,000 字符时 worker 会拒绝静默截断。先按章节筛出机制/结果/局限/资源需求后重试；无法可靠筛选时走下述降级梯，并在抽取卡记录覆盖缺口。

**降级梯**:worker 不可用 → 每篇派一个 subagent 抽取(只回抽取卡,markdown 留在磁盘)→ 主 agent 抽取(仅限 T0)。

## 抽取卡 schema

见 [templates/extraction.md](../templates/extraction.md)。固定字段:机制 / 结果(数字+基准)/ 局限(作者自认 + 我方判断)/ 可适用性四档 / 落地成本 / 前置依赖 / schema 外值得注意的点(**逃生口自由字段**——schema 装不下的重要发现放这,是将来升级 schema 的依据)。

## 可适用性四档（对照 Profile 的硬约束）

| 档 | 含义 |
|---|---|
| 直接可用 | 满足 Profile 中的部署、权重、数据和资源约束 |
| 需微调(算力内) | 论文所需训练资源在 Profile 上限内 |
| API 辅助(脱敏后) | Profile 明确允许数据出域，并满足脱敏要求 |
| 不适用 | 与 Profile 中任一硬约束明确冲突 |

Profile 中与判定相关的约束为 `TBD` 时，不得自行假设满足。抽取卡先使用临时状态**待确认**，指出缺失字段，并在 `06-brief.md` 的开放问题中列出。Stage 5 闸门前必须依据用户已经确认的 Profile 将其解析为四档之一；否则按未过闸项处理。

判定必须引用论文中的具体证据（模型规模、数据、资源需求），并区分**“论文已证明”**与**“对该场景的外推”**；外推结论在抽取卡上标注。
