# 后端 — 工具、命令与降级梯

先使用 `SKILL.md` 解析出的锚点运行：

```bash
python3 "<skill-root>/scripts/preflight.py" \
  --workspace-root "<workspace-root>" \
  --bootstrap \
  --live-mcp
```

输出 `ready` 表示运行数据、MCP 与可选凭据齐备；`degraded` 表示工作区可运行但部分能力需走本页降级梯；`blocked` 表示 Skill 包或运行数据不完整，修复前不开始调研。项目 `.mcp.json` 是可选配置，user-scope MCP 或免 key API 同样合法。

未显式传 `--workspace-root` 时，preflight 会从当前目录寻找 Git 根；找不到 Git 根才使用当前目录。`--bootstrap` 只补齐缺失的 profile 和索引，不覆盖已有项目数据。

Preflight 的 `details.worker_endpoint` 会在不发起抽取调用的情况下报告数据边界。它与 Extract 共用 `scripts/worker_boundary.py`：

| classification | Worker 能力 | 数据边界 |
|---|---|---|
| `unconfigured` | false | 走 Extract 降级梯 |
| `invalid` | false | 修正 URL 或走降级梯 |
| `trusted-local` | true | 允许 HTTP/HTTPS，不要求`--desensitized` |
| `external-https` | true | 抽取时必须显式传`--desensitized` |
| `external-http-blocked` | false | 始终拒绝，走降级梯 |

配置只完成一部分时，`missing_variables` 列出缺失的环境变量。报告不得输出 worker key。Worker 不可用只导致`degraded`，因为 Extract 有合法降级梯。

## Preflight 清单(按序检查,结果记入 02-pool.md 检索记录)

| 后端 | 检查命令 | 角色 |
|---|---|---|
| paper-search-mcp | MCP 工具可用；项目或 user scope 均可 | 多源并发检索主力(20+ 源) |
| s2-mcp | MCP 工具列表有 `semantic_scholar_*` | S2 recommendations / 双向引用图 / snippet_search |
| arxiv-mcp-server | MCP 工具列表有 arxiv 系工具 | LaTeX 按章节读、下载 |
| S2 API key | env `SEMANTIC_SCHOLAR_API_KEY` 已设 | 无 key 时 S2 系限速极严(单次即 429 实测) |
| curl 兜底 | `curl -sI https://arxiv.org` 通 | 所有 MCP 缺失时的最后通道 |

## 源清单与用法

- **paper-search-mcp**:arXiv/S2/OpenAlex/Crossref/dblp/PubMed/CORE/HAL/SSRN 等 20+ 源并发+去重,`download_with_fallback` OA 优先下载链。批量结果**先落盘 `<run-dir>/.cache/` 再 jq 切片**,不整体进上下文。可选 env 增强:`PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY`、`PAPER_SEARCH_MCP_UNPAYWALL_EMAIL` 等。推荐版本由 `preflight.py` 维护；目标工作区可用 project scope 或 user scope。
- **s2-mcp**:`semantic_scholar_recommendations`(seed → 近期相关工作,**补课场景核心源**)、`get_paper` 双向引用(snowballing)、`snippet_search`(正文片段匹配,供 Triage)、`bulk_search`、`match_paper`(标题→论文解析)。
- **HF Papers API**(免 key):`curl "https://huggingface.co/api/papers"` → `upvotes`+`publishedAt`,**新论文 buzz 信号**。
- **OpenAlex API**(免 key):`https://api.openalex.org/works?search=...&select=id,title,cited_by_count` → **S2 429 时的 citation 后备**。
- **Papers with Code**:has-code 信号,一等源;有 API 给代码链接+leaderboard。
- **arXiv API**(免 key,无 citation 信号):字段 `id/title/summary(=abstract)/published/category/journal_ref/comment/author/link(含PDF)`。

## 调用纪律

- S2 系调用间隔 ≥1s;429 时指数退避 2s/4s/8s,连挂 3 次标记该源本轮不可用并记入检索记录。
- 所有批量 API 响应落盘 `<run-dir>/.cache/` 后再切片读取。
- 每个 Discovery 查询记录词来源，只能是`Intake`、`Landscape`、`Snowballing`或`补检`；查询使用 Intake 已确认词与 Landscape 衍生词的并集。
- **License 边界**:MinerU(AGPL-3.0)只作外部子进程/CLI 调用(`uvx magic-pdf`),不作库 import;需要 license 无暇时换 GROBID(Apache-2.0)。paper-search-mcp、s2-mcp 为 MIT,arxiv-mcp-server 为 Apache-2.0。

## 降级梯

- paper-search-mcp 缺 → curl arXiv API + OpenAlex 手工多源
- s2-mcp 缺 → curl S2 Graph API(严守限速退避)
- arxiv-mcp 缺 → arXiv 下 e-print 源码包自解 LaTeX,或走 MinerU
- 全部 MCP 缺 → curl 直连(arXiv/OpenAlex/HF Papers 均免 key 实测通),本轮池规模收缩并在检索记录注明

## 抽取 worker 配置(`<skill-root>/scripts/extract_paper.py`)

三个环境变量(缺一 worker 即不可用,走 extract.md 降级梯):
- `PAPER_TRAIL_WORKER_BASE_URL`:OpenAI 兼容端点(如 relay 的 /v1 路径)
- `PAPER_TRAIL_WORKER_KEY`:该端点 key
- `PAPER_TRAIL_WORKER_MODEL`:最便宜档模型名
- `PAPER_TRAIL_WORKER_TRUSTED_HOSTS`(可选):逗号分隔的可信内网主机名；localhost/private IP/`.local`/`.internal` 默认可信

Preflight 自测:`python3 "<skill-root>/scripts/extract_paper.py" --selftest`(一次极小调用,验证端点可用)。自测也会拒绝无效 URL 和外部 HTTP，避免在明文传输中暴露 key。实际抽取发送 paper+profile；外部端点必须为 HTTPS，且只在两者已脱敏时显式传 `--desensitized`。
