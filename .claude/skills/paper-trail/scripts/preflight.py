#!/usr/bin/env python3
"""Check project-local Paper Trail artifacts, MCP pins, and optional capabilities."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
EXPECTED_MCP = {
    "paper-search": ("paper-search-mcp==0.1.4", "paper-search-mcp"),
    "semantic-scholar": ("s2-mcp-server==1.7.1", "s2-mcp-server"),
    "arxiv": ("arxiv-mcp-server==0.6.2", "arxiv-mcp-server"),
}
REQUIRED_ARTIFACTS = (
    ".claude/paper-trail/profile.md",
    ".claude/skills/paper-trail/SKILL.md",
    "research/INDEX.md",
    ".mcp.json",
)
WORKER_ENV = (
    "PAPER_TRAIL_WORKER_BASE_URL",
    "PAPER_TRAIL_WORKER_KEY",
    "PAPER_TRAIL_WORKER_MODEL",
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live-mcp",
        action="store_true",
        help="调用 claude mcp list 验证三个 pinned MCP 均为 Connected",
    )
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    return parser.parse_args()


def check_artifacts(errors):
    missing = [
        relative_path
        for relative_path in REQUIRED_ARTIFACTS
        if not (PROJECT_ROOT / relative_path).is_file()
    ]
    if missing:
        errors.append(f"缺少项目产物: {', '.join(missing)}")
    return not missing


def check_mcp_pins(errors):
    try:
        config = json.loads((PROJECT_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f".mcp.json 无法读取: {exc}")
        return False

    servers = config.get("mcpServers", {})
    mismatches = []
    for name, (package, command) in EXPECTED_MCP.items():
        entry = servers.get(name, {})
        expected_args = ["--from", package, command]
        if entry.get("command") != "uvx" or entry.get("args") != expected_args:
            mismatches.append(name)
    if mismatches:
        errors.append(f"MCP pin 不匹配: {', '.join(mismatches)}")
    return not mismatches


def check_live_mcp(errors):
    try:
        result = subprocess.run(
            ["claude", "mcp", "list"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=60,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append(f"claude mcp list 失败: {exc}")
        return False

    disconnected = [
        name
        for name in EXPECTED_MCP
        if not any(
            line.startswith(f"{name}:") and "Connected" in line
            for line in result.stdout.splitlines()
        )
    ]
    if disconnected:
        errors.append(f"MCP 未连接: {', '.join(disconnected)}")
    return not disconnected


def build_report(live_mcp):
    errors = []
    checks = {
        "project_artifacts": check_artifacts(errors),
        "mcp_pins": check_mcp_pins(errors),
    }
    if live_mcp:
        checks["live_mcp"] = check_live_mcp(errors)

    capabilities = {
        "s2_api_key": bool(os.environ.get("SEMANTIC_SCHOLAR_API_KEY")),
        "worker": all(os.environ.get(name) for name in WORKER_ENV),
    }
    if errors:
        status = "blocked"
    elif all(capabilities.values()):
        status = "ready"
    else:
        status = "degraded"
    return {
        "status": status,
        "checks": checks,
        "capabilities": capabilities,
        "errors": errors,
    }


def main():
    args = parse_args()
    report = build_report(args.live_mcp)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"paper-trail preflight: {report['status']}")
        for name, passed in report["checks"].items():
            print(f"- {name}: {'OK' if passed else 'FAIL'}")
        for name, available in report["capabilities"].items():
            print(f"- {name}: {'available' if available else 'fallback required'}")
        for error in report["errors"]:
            print(f"- error: {error}")
    if report["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
