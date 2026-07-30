#!/usr/bin/env python3
"""Bootstrap and check a Paper Trail skill against any target workspace."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MCP = {
    "paper-search": ("paper-search-mcp==0.1.4", "paper-search-mcp"),
    "semantic-scholar": ("s2-mcp-server==1.7.1", "s2-mcp-server"),
    "arxiv": ("arxiv-mcp-server==0.6.2", "arxiv-mcp-server"),
}
REQUIRED_SKILL_FILES = (
    "SKILL.md",
    "agents/openai.yaml",
    "reference/backends.md",
    "reference/extract.md",
    "reference/reframe.md",
    "reference/synthesize.md",
    "reference/triage.md",
    "reference/verify.md",
    "scripts/extract_paper.py",
    "scripts/preflight.py",
    "templates/brief.md",
    "templates/extraction.md",
    "templates/intake.md",
    "templates/landscape.md",
    "templates/ledger.md",
    "templates/pool.md",
    "templates/profile.md",
    "templates/synthesis.md",
    "templates/triage.md",
)
WORKER_ENV = (
    "PAPER_TRAIL_WORKER_BASE_URL",
    "PAPER_TRAIL_WORKER_KEY",
    "PAPER_TRAIL_WORKER_MODEL",
)
INDEX_TEMPLATE = """# Paper Trail Research Index

每次调研完成后追加一行；详细证据保存在对应运行目录。

| 日期 | slug | 痛点 | 核心结论 | T0 论文 |
|---|---|---|---|---|
"""


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace-root",
        default=os.environ.get("PAPER_TRAIL_WORKSPACE_ROOT"),
        help="目标工作区根目录；默认 PAPER_TRAIL_WORKSPACE_ROOT、Git 根目录或当前目录",
    )
    parser.add_argument(
        "--state-dir",
        default=os.environ.get("PAPER_TRAIL_STATE_DIR"),
        help="profile 状态目录；默认 <workspace-root>/.paper-trail",
    )
    parser.add_argument(
        "--research-dir",
        default=os.environ.get("PAPER_TRAIL_RESEARCH_DIR"),
        help="调研产物目录；默认 <workspace-root>/research",
    )
    parser.add_argument(
        "--mcp-config",
        default=None,
        help="可选 MCP 配置；默认 <workspace-root>/.mcp.json",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="在缺失时创建 profile 和 research/INDEX.md，不覆盖已有数据",
    )
    parser.add_argument(
        "--live-mcp",
        action="store_true",
        help="调用 claude mcp list 验证推荐 MCP 是否 Connected",
    )
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    return parser.parse_args()


def resolve_path(raw_value, workspace_root, default_relative):
    path = Path(raw_value).expanduser() if raw_value else workspace_root / default_relative
    if not path.is_absolute():
        path = workspace_root / path
    return path.resolve()


def resolve_workspace_root(raw_value):
    if raw_value:
        return Path(raw_value).expanduser().resolve()

    current_directory = Path.cwd().resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=current_directory,
            text=True,
            capture_output=True,
            timeout=10,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return current_directory

    git_root = result.stdout.strip()
    return Path(git_root).resolve() if git_root else current_directory


def resolve_paths(args):
    workspace_root = resolve_workspace_root(args.workspace_root)
    state_root = resolve_path(args.state_dir, workspace_root, ".paper-trail")
    research_root = resolve_path(args.research_dir, workspace_root, "research")
    mcp_config = resolve_path(args.mcp_config, workspace_root, ".mcp.json")
    return {
        "skill_root": SKILL_ROOT,
        "workspace_root": workspace_root,
        "state_root": state_root,
        "profile_path": state_root / "profile.md",
        "research_root": research_root,
        "index_path": research_root / "INDEX.md",
        "mcp_config": mcp_config,
    }


def bootstrap_runtime(paths):
    created = []
    profile_path = paths["profile_path"]
    index_path = paths["index_path"]
    if not profile_path.exists():
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SKILL_ROOT / "templates/profile.md", profile_path)
        created.append(str(profile_path))
    if not index_path.exists():
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(INDEX_TEMPLATE, encoding="utf-8")
        created.append(str(index_path))
    return created


def check_skill_package(errors):
    missing = [
        relative_path
        for relative_path in REQUIRED_SKILL_FILES
        if not (SKILL_ROOT / relative_path).is_file()
    ]
    if missing:
        errors.append(f"Skill 包不完整: {', '.join(missing)}")
    return not missing


def check_runtime_artifacts(paths, errors):
    missing = [
        str(path)
        for path in (paths["profile_path"], paths["index_path"])
        if not path.is_file()
    ]
    if missing:
        errors.append(f"缺少运行数据: {', '.join(missing)}；使用 --bootstrap 初始化")
    return not missing


def check_mcp_config(mcp_config, warnings):
    if not mcp_config.is_file():
        warnings.append(f"未找到 MCP 配置 {mcp_config}；可使用 user-scope MCP 或 API 降级梯")
        return False
    try:
        config = json.loads(mcp_config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"MCP 配置无法读取: {exc}")
        return False

    servers = config.get("mcpServers", {})
    mismatches = []
    for name, (package, command) in EXPECTED_MCP.items():
        entry = servers.get(name, {})
        expected_args = ["--from", package, command]
        if entry.get("command") != "uvx" or entry.get("args") != expected_args:
            mismatches.append(name)
    if mismatches:
        warnings.append(f"推荐 MCP pin 未匹配: {', '.join(mismatches)}")
    return not mismatches


def check_live_mcp(workspace_root, warnings):
    try:
        result = subprocess.run(
            ["claude", "mcp", "list"],
            cwd=workspace_root,
            text=True,
            capture_output=True,
            timeout=60,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        warnings.append(f"claude mcp list 不可用: {exc}")
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
        warnings.append(f"推荐 MCP 未连接: {', '.join(disconnected)}")
    return not disconnected


def build_report(args):
    paths = resolve_paths(args)
    errors = []
    warnings = []
    created = bootstrap_runtime(paths) if args.bootstrap else []
    checks = {
        "skill_package": check_skill_package(errors),
        "runtime_artifacts": check_runtime_artifacts(paths, errors),
        "mcp_config": check_mcp_config(paths["mcp_config"], warnings),
    }
    if args.live_mcp:
        checks["live_mcp"] = check_live_mcp(paths["workspace_root"], warnings)

    capabilities = {
        "mcp": checks.get("live_mcp", checks["mcp_config"]),
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
        "paths": {name: str(path) for name, path in paths.items()},
        "checks": checks,
        "capabilities": capabilities,
        "created": created,
        "warnings": warnings,
        "errors": errors,
    }


def main():
    args = parse_args()
    report = build_report(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"paper-trail preflight: {report['status']}")
        for name, passed in report["checks"].items():
            print(f"- {name}: {'OK' if passed else 'FAIL'}")
        for name, available in report["capabilities"].items():
            print(f"- {name}: {'available' if available else 'fallback required'}")
        for path in report["created"]:
            print(f"- created: {path}")
        for warning in report["warnings"]:
            print(f"- warning: {warning}")
        for error in report["errors"]:
            print(f"- error: {error}")
    if report["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
