#!/usr/bin/env python3
"""Audit that A/B source URLs in role files are alive and plausibly support their claims.

A 级要求抓取成功且主张关键词与正文重合达标；B 级只要求链接存活。
报告写入 context/source-audit.md；未决发现非零时退出码为 1。
"""

from __future__ import annotations

import argparse
import html as html_module
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from contract_io import atomic_write, normalize_value, parse_document


ROLE_FILES = {
    "实践者": "practitioner.md",
    "学者": "scholar.md",
    "怀疑者": "skeptic.md",
    "经济学家": "economist.md",
    "历史学家": "historian.md",
}
MAX_BYTES = 2 * 1024 * 1024
MAX_KEYWORDS = 24
DEFAULT_MIN_OVERLAP = 0.3
USER_AGENT = "Mozilla/5.0 (compatible; learn-loop-source-audit/1.0)"
CJK_STOPCHARS = set("的了是在和与及或对为有无不分将被把其该此等往往从很也又都就还会再只可我能你他它们上下中内外前后自己什么怎么这样那么因为所以但如果而且虽然")
# 最小近似表：仅覆盖常见多级后缀，不追求完整 public suffix 列表。
MULTI_LABEL_SUFFIXES = {
    "co.uk", "org.uk", "ac.uk", "gov.uk",
    "com.cn", "org.cn", "net.cn", "gov.cn",
    "com.au", "com.br", "co.jp", "com.sg",
    "github.io", "gitlab.io", "readthedocs.io", "substack.com",
}


def registrable_domain(url: str) -> str:
    host = re.sub(r"^https?://", "", url.strip()).split("/", 1)[0]
    host = host.split("@")[-1].split(":")[0].lower().rstrip(".")
    if not host:
        return ""
    labels = host.split(".")
    if all(label.isdigit() for label in labels):
        return host  # IP 地址整体视为一个来源
    if len(labels) <= 2:
        return host
    if ".".join(labels[-2:]) in MULTI_LABEL_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def claim_keywords(claim: str) -> list[str]:
    keywords: list[str] = []
    for run in re.findall(r"[\u4e00-\u9fff]+|[A-Za-z][A-Za-z0-9_+.#/-]*|\d+", claim):
        if re.match(r"[\u4e00-\u9fff]", run):
            for index in range(len(run) - 1):
                bigram = run[index : index + 2]
                if not (set(bigram) & CJK_STOPCHARS):
                    keywords.append(bigram)
        elif len(run) >= 2:
            keywords.append(run.lower())
    unique: list[str] = []
    for keyword in keywords:
        if keyword not in unique:
            unique.append(keyword)
    return unique[:MAX_KEYWORDS]


def html_to_text(payload: bytes, content_type: str) -> str:
    charset = "utf-8"
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    if match:
        charset = match.group(1)
    try:
        text = payload.decode(charset, errors="replace")
    except LookupError:
        text = payload.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1\s*>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html_module.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch(url: str, timeout: int) -> tuple[str, str]:
    """Return (status, detail)；status ∈ fetched / dead / unverified / pdf。"""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            payload = response.read(MAX_BYTES)
    except urllib.error.HTTPError as error:
        if error.code in {404, 410}:
            return "dead", f"HTTP {error.code}"
        return "unverified", f"HTTP {error.code}"
    except urllib.error.URLError as error:
        reason = getattr(error, "reason", error)
        if isinstance(reason, OSError) and reason.errno in {8, -2, 61, -3, 111, 113}:
            return "dead", f"无法解析或拒绝连接：{reason}"
        return "unverified", f"{type(reason).__name__}"
    except (TimeoutError, OSError, ValueError) as error:
        return "unverified", type(error).__name__
    if "pdf" in content_type.lower():
        return "pdf", "PDF 未经脚本抽取"
    return "fetched", html_to_text(payload, content_type)


def collect_evidence(run_dir: Path) -> tuple[list[dict], dict[str, list[str]]]:
    evidence: list[dict] = []
    cited: dict[str, list[str]] = {}
    for role, filename in ROLE_FILES.items():
        path = run_dir / "perspectives" / filename
        if not path.is_file():
            continue
        document = parse_document(path.read_text(encoding="utf-8"))
        matches = document.find("最强证据", 2)
        if matches:
            fields = matches[0].fields
            evidence.append(
                {
                    "role": role,
                    "claim": normalize_value(fields.get("证据主张", "")),
                    "url": normalize_value(fields.get("来源 URL", "")).strip("`"),
                    "grade": normalize_value(fields.get("来源等级", "")).strip("。"),
                }
            )
            url = evidence[-1]["url"]
            if url.startswith(("http://", "https://")):
                cited.setdefault(url, []).append(f"{role}·最强证据")
        for record in document.sections:
            if record.level != 3 or not re.fullmatch(r"检索 \d+", record.title):
                continue
            status = normalize_value(record.fields.get("结果状态", "")).strip("。")
            url = normalize_value(record.fields.get("来源 URL", "")).strip("`")
            if status == "采信" and url.startswith(("http://", "https://")):
                cited.setdefault(url, []).append(f"{role}·检索")
    return evidence, cited


def audit(run_dir: Path, timeout: int, min_overlap: float) -> dict:
    run_dir = run_dir.expanduser().resolve()
    evidence, cited = collect_evidence(run_dir)
    audited = [item for item in evidence if item["grade"] in {"A", "B"} and item["url"].startswith(("http://", "https://"))]

    results = []
    for item in audited:
        status, detail = fetch(item["url"], timeout)
        keywords = claim_keywords(item["claim"]) if item["grade"] == "A" else []
        matched = [k for k in keywords if k in detail] if status == "fetched" and keywords else []
        overlap = round(len(matched) / len(keywords), 2) if keywords and status == "fetched" else None
        missed = [k for k in keywords if k not in matched] if keywords else []
        if status == "dead":
            verdict, finding = "链接失效", True
        elif status == "pdf":
            verdict, finding = "未核验：PDF 未经脚本抽取", False
        elif item["grade"] == "A":
            if status == "fetched" and overlap is not None and overlap >= min_overlap:
                verdict, finding = "通过", False
            elif status == "fetched":
                verdict, finding = "建议降级", True
            else:
                verdict, finding = f"未核验：{detail}", False
        elif status == "fetched":
            verdict, finding = "通过", False
        else:
            verdict, finding = f"未核验：{detail}", False
        results.append(
            {
                **item,
                "status": status,
                "verdict": verdict,
                "finding": finding,
                "overlap": overlap,
                "matched": len(matched),
                "keywords": len(keywords),
                "missed": missed[:8],
            }
        )

    # 网络全不可用启发式：一个都没抓成功时无法区分死链与断网，全部按未核验处理。
    fetched_any = any(result["status"] == "fetched" for result in results)
    network_down = bool(results) and not fetched_any
    if network_down:
        for result in results:
            if result["verdict"] == "链接失效":
                result["verdict"], result["finding"] = "未核验：网络不可用", False

    domain_map: dict[str, set[str]] = {}
    for url in cited:
        domain = registrable_domain(url)
        if domain:
            domain_map.setdefault(domain, set()).update(cited[url])
    shared_domains = {
        domain: sorted(roles) for domain, roles in domain_map.items() if len(roles) > 1
    }

    findings = sum(1 for result in results if result["finding"])
    unverified = sum(1 for result in results if result["verdict"].startswith("未核验"))
    return {
        "results": results,
        "findings": findings,
        "unverified": unverified,
        "audited": len(results),
        "network_down": network_down,
        "shared_domains": shared_domains,
        "cited_total": len(cited),
    }


def render_report(report: dict, run_dir: Path) -> str:
    lines = [
        "# 来源支持性审计",
        "",
        f"- **审计时间：** {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- **核验 URL 数：** {report['audited']}",
        f"- **未决发现：** {report['findings']}",
        f"- **未核验：** {report['unverified']}",
        f"- **网络可用性：** {'全部失败，死链按未核验处理' if report['network_down'] else '至少一个 URL 抓取成功'}",
        "",
    ]
    if report["results"]:
        lines.append("## URL 审计")
        lines.append("")
        for index, result in enumerate(report["results"], start=1):
            overlap = (
                f"{result['overlap']:.2f}（命中 {result['matched']}/{result['keywords']}）"
                if result["overlap"] is not None
                else "不适用"
            )
            lines.extend(
                [
                    f"### 审计 {index}",
                    "",
                    f"- **角色：** {result['role']}",
                    f"- **来源 URL：** {result['url']}",
                    f"- **来源等级：** {result['grade']}",
                    f"- **状态：** {result['verdict']}",
                    f"- **重合度：** {overlap}",
                ]
            )
            if result["missed"]:
                lines.append(f"- **未命中关键词：** {'、'.join(result['missed'])}")
            lines.append("")
    lines.extend(["## 跨角色来源独立性", ""])
    if report["shared_domains"]:
        lines.append("- **提示：** 下列母站被多个角色引用；按纪律同一母站视为同一来源，标`独立共识`前须核对谱系：")
        for domain, roles in report["shared_domains"].items():
            lines.append(f"  - `{domain}`：{'、'.join(roles)}")
    else:
        lines.append("- **提示：** 未发现跨角色共用母站。")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--min-overlap", type=float, default=DEFAULT_MIN_OVERLAP)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    try:
        report = audit(run_dir, args.timeout, args.min_overlap)
        report_path = run_dir / "context" / "source-audit.md"
        atomic_write(report_path, render_report(report, run_dir))
    except (OSError, ValueError) as error:
        if args.json:
            print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        else:
            print(f"审计失败：{error}")
        return 2

    summary = {
        "ok": report["findings"] == 0,
        "audited": report["audited"],
        "findings": report["findings"],
        "unverified": report["unverified"],
        "network_down": report["network_down"],
        "shared_domains": report["shared_domains"],
        "report": str(run_dir / "context" / "source-audit.md"),
        "results": [
            {
                key: result[key]
                for key in ("role", "url", "grade", "verdict", "overlap", "finding")
            }
            for result in report["results"]
        ],
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("来源审计完成" if summary["ok"] else f"来源审计有 {report['findings']} 个未决发现")
        for result in report["results"]:
            mark = "×" if result["finding"] else "✓"
            print(f"- {mark} [{result['grade']}] {result['url']} → {result['verdict']}")
        print(f"- 报告：{summary['report']}")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
