# 后端 — 工具、命令与降级梯

先从工作区根目录运行：

```bash
python3 .claude/skills/paper-trail/scripts/preflight.py --live-mcp
```

输出 `ready` 表示项目产物、MCP 与可选凭据齐备；`degraded` 表示项目可运行但 S2 key 或 worker 未配置，必须使用本页降级梯；`blocked` 表示项目产物或 pinned MCP 契约损坏，修复前不开始调研。

## Preflight 清单(按序检查,结果记入 02-pool.md 检索记录)

| 后端 | 检查命令 | 角色 |
|---|---|---|
| paper-search-mcp | 项目 `.mcp.json` 中的 pinned MCP 工具可用 | 多源并发检索主力(20+ 源) |
| s2-mcp | MCP 工具列表有 `semantic_scholar_*` | S2 recommendations / 双向引用图 / snippet_search |
| arxiv-mcp-server | MCP 工具列表有 arxiv 系工具 | LaTeX 按章节读、下载 |
| S2 API key | env `SEMANTIC_SCHOLAR_API_KEY` 已设 | 无 key 时 S2 系限速极严(单次即 429 实测) |
| curl 兜底 | `curl -sI https://arxiv.org` 通 | 所有 MCP 缺失时的最后通道 |

## 源清单与用法

- **paper-search-mcp**:arXiv/S2/OpenAlex/Crossref/dblp/PubMed/CORE/HAL/SSRN 等 20+ 源并发+去重,`download_with_fallback` OA 优先下载链。批量结果**先落盘 `.cache/` 再 jq 切片**,不整体进上下文。可选 env 增强:`PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY`、`PAPER_SEARCH_MCP_UNPAYWALL_EMAIL` 等。测试期版本由项目 `.mcp.json` 固定；升级时逐项验活后再改 pin。
- **s2-mcp**:`semantic_scholar_recommendations`(seed → 近期相关工作,**补课场景核心源**)、`get_paper` 双向引用(snowballing)、`snippet_search`(正文片段匹配,供 Triage)、`bulk_search`、`match_paper`(标题→论文解析)。
- **HF Papers API**(免 key):`curl "https://huggingface.co/api/papers"` → `upvotes`+`publishedAt`,**新论文 buzz 信号**。
- **OpenAlex API**(免 key):`https://api.openalex.org/works?search=...&select=id,title,cited_by_count` → **S2 429 时的 citation 后备**。
- **Papers with Code**:has-code 信号,一等源;有 API 给代码链接+leaderboard。
- **arXiv API**(免 key,无 citation 信号):字段 `id/title/summary(=abstract)/published/category/journal_ref/comment/author/link(含PDF)`。

## 调用纪律

- S2 系调用间隔 ≥1s;429 时指数退避 2s/4s/8s,连挂 3 次标记该源本轮不可用并记入检索记录。
- 所有批量 API 响应落盘 `.cache/` 后再切片读取。
- **License 边界**:MinerU(AGPL-3.0)只作外部子进程/CLI 调用(`uvx magic-pdf`),不作库 import;需要 license 无暇时换 GROBID(Apache-2.0)。paper-search-mcp、s2-mcp 为 MIT,arxiv-mcp-server 为 Apache-2.0。

## 降级梯

- paper-search-mcp 缺 → curl arXiv API + OpenAlex 手工多源
- s2-mcp 缺 → curl S2 Graph API(严守限速退避)
- arxiv-mcp 缺 → arXiv 下 e-print 源码包自解 LaTeX,或走 MinerU
- 全部 MCP 缺 → curl 直连(arXiv/OpenAlex/HF Papers 均免 key 实测通),本轮池规模收缩并在检索记录注明

## 抽取 worker 配置(`.claude/skills/paper-trail/scripts/extract_paper.py`)

三个环境变量(缺一 worker 即不可用,走 extract.md 降级梯):
- `PAPER_TRAIL_WORKER_BASE_URL`:OpenAI 兼容端点(如 relay 的 /v1 路径)
- `PAPER_TRAIL_WORKER_KEY`:该端点 key
- `PAPER_TRAIL_WORKER_MODEL`:最便宜档模型名
- `PAPER_TRAIL_WORKER_TRUSTED_HOSTS`(可选):逗号分隔的可信内网主机名；localhost/private IP/`.local`/`.internal` 默认可信

Preflight 自测:`python3 .claude/skills/paper-trail/scripts/extract_paper.py --selftest`(一次极小调用,验证端点可用)。实际抽取发送 paper+profile；外部端点必须为 HTTPS，且只在两者已脱敏时显式传 `--desensitized`。
