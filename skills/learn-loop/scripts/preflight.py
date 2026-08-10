#!/usr/bin/env python3
"""Resolve a learn-loop workspace, bootstrap missing runtime files, and report trial-backed capability verdicts."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SKILL_FILES = (
    "SKILL.md",
    "agents/openai.yaml",
    "assets/template.html",
    "reference/conflict.md",
    "reference/curriculum.md",
    "reference/examination.md",
    "reference/html-guide.md",
    "reference/original-prompts.md",
    "reference/perspectives.md",
    "reference/retention.md",
    "scripts/preflight.py",
    "scripts/contract_io.py",
    "scripts/prepare_stage.py",
    "scripts/render_learning_page.py",
    "scripts/finalize_run.py",
    "scripts/review_queue.py",
    "scripts/validate_stage.py",
    "templates/01-perspectives.md",
    "templates/02-conflicts.md",
    "templates/03-brief.md",
    "templates/04-review.md",
    "templates/05-resources.md",
    "templates/06-ladder.md",
    "templates/07-sprint.md",
    "templates/08-exam-bank.md",
    "templates/08-exam-record.md",
    "templates/09-feynman-notes.md",
    "templates/09-feynman-record.md",
    "templates/10-cheatsheet.md",
    "templates/learner-profile.md",
    "templates/review-queue.md",
    "templates/run-state.md",
    "templates/perspective-role.md",
    "templates/perspective-task.md",
    "reference/stages/00-run-state.md",
    "reference/stages/01-perspectives.md",
    "reference/stages/02-conflicts.md",
    "reference/stages/03-brief.md",
    "reference/stages/04-review.md",
    "reference/stages/05-resources.md",
    "reference/stages/06-ladder.md",
    "reference/stages/07-sprint.md",
    "reference/stages/08-exam-bank.md",
    "reference/stages/09-feynman-notes.md",
    "reference/stages/10-cheatsheet.md",
    "reference/modes/exam-record.md",
    "reference/modes/feynman-record.md",
)

INDEX_TEMPLATE = """# Learn Loop 学习索引

每轮生成流水线完成后追加一行；Markdown 产物保存在对应运行目录，HTML 是渲染视图。

| 日期 | slug | 主题 | 练习状态 | 运行目录 |
|---|---|---|---|---|
"""


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace-root",
        default=os.environ.get("LEARN_LOOP_WORKSPACE_ROOT"),
        help="目标工作区；默认 LEARN_LOOP_WORKSPACE_ROOT、Git 根目录或当前目录",
    )
    parser.add_argument(
        "--state-dir",
        default=os.environ.get("LEARN_LOOP_STATE_DIR"),
        help="状态目录；默认 <workspace-root>/.learn-loop",
    )
    parser.add_argument(
        "--learning-dir",
        default=os.environ.get("LEARN_LOOP_LEARNING_DIR"),
        help="学习产物目录；默认 <workspace-root>/learning",
    )
    parser.add_argument(
        "--subagent-mode",
        choices=("parallel", "serial-isolated", "orchestrated"),
        help="本轮实际采用的独立性档位；未声明时按 orchestrated 处理",
    )
    parser.add_argument(
        "--retrieval-verified",
        action="store_true",
        help="声明已实际试调用一次检索工具并成功读取至少一个候选正文（先实测，再声明）",
    )
    parser.add_argument(
        "--subagents-verified",
        action="store_true",
        help="声明已实际试 spawn 一次独立 subagent 并成功（先实测，再声明）",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="只创建缺失的 profile、queue 和 INDEX，不覆盖已有文件",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser.parse_args()


def resolve_workspace_root(raw_value=None):
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


def resolve_path(raw_value, workspace_root, default_relative):
    path = Path(raw_value).expanduser() if raw_value else workspace_root / default_relative
    if not path.is_absolute():
        path = workspace_root / path
    return path.resolve()


def resolve_paths(args):
    workspace_root = resolve_workspace_root(args.workspace_root)
    state_root = resolve_path(args.state_dir, workspace_root, ".learn-loop")
    learning_root = resolve_path(args.learning_dir, workspace_root, "learning")
    return {
        "skill_root": SKILL_ROOT,
        "workspace_root": workspace_root,
        "state_root": state_root,
        "profile_path": state_root / "learner-profile.md",
        "queue_path": state_root / "review-queue.md",
        "learning_root": learning_root,
        "index_path": learning_root / "INDEX.md",
    }


def bootstrap_runtime(paths):
    created = []
    paths["state_root"].mkdir(parents=True, exist_ok=True)
    paths["learning_root"].mkdir(parents=True, exist_ok=True)

    copies = (
        ("profile_path", "templates/learner-profile.md"),
        ("queue_path", "templates/review-queue.md"),
    )
    for path_key, template_name in copies:
        destination = paths[path_key]
        if not destination.exists():
            shutil.copyfile(SKILL_ROOT / template_name, destination)
            created.append(str(destination))

    index_path = paths["index_path"]
    if not index_path.exists():
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
        errors.append("Skill 包不完整: " + ", ".join(missing))
    return not missing


def check_runtime_artifacts(paths, errors):
    missing = [
        str(paths[key])
        for key in ("profile_path", "queue_path", "index_path")
        if not paths[key].is_file()
    ]
    if missing:
        errors.append("缺少运行数据；使用 --bootstrap 初始化: " + ", ".join(missing))
    return not missing


def inspect_capabilities(args, warnings):
    retrieval_verified = args.retrieval_verified
    if not retrieval_verified:
        warnings.append(
            "检索能力未声明已验证；未声明 ≠ 不可用。请先实际试调用一次检索工具并成功读取"
            "至少一个候选正文，再以 --retrieval-verified 据实声明；未实测前按未锚定模式处理并将来源标 C"
        )

    declared_mode = args.subagent_mode or "orchestrated"
    subagents_verified = args.subagents_verified
    effective_mode = declared_mode if subagents_verified else "orchestrated"
    if not subagents_verified:
        warnings.append(
            "subagent 能力未声明已验证；未声明 ≠ 不可用。请先实际试 spawn 一次独立 subagent，"
            "再以 --subagents-verified 据实声明；未实测前记录 orchestrated 档位"
        )
    elif declared_mode == "orchestrated":
        warnings.append(
            "已声明 subagent 可用但档位为 orchestrated；如需 parallel/serial-isolated 请显式声明档位"
        )

    return {
        "retrieval": {
            "declared": retrieval_verified,
            "verified": retrieval_verified,
            "available": retrieval_verified,
            "source": "CLI --retrieval-verified" if retrieval_verified else "未声明",
        },
        "subagents": {
            "declared": args.subagent_mode is not None,
            "verified": subagents_verified,
            "available": subagents_verified and effective_mode != "orchestrated",
            "declared_mode": declared_mode,
        },
        "suggested_independence_tier": effective_mode,
        "anchoring_mode": "anchored" if retrieval_verified else "未锚定模式",
    }


def build_report(args):
    paths = resolve_paths(args)
    errors = []
    warnings = []
    created = bootstrap_runtime(paths) if args.bootstrap else []
    checks = {
        "skill_package": check_skill_package(errors),
        "runtime_artifacts": check_runtime_artifacts(paths, errors),
    }
    capabilities = inspect_capabilities(args, warnings)
    if errors:
        status = "blocked"
    elif capabilities["retrieval"]["verified"] and (
        capabilities["subagents"]["declared_mode"] == "orchestrated"
        or capabilities["subagents"]["verified"]
    ):
        status = "ready"
    elif (
        capabilities["retrieval"]["verified"]
        or capabilities["subagents"]["verified"]
        or capabilities["subagents"]["declared"]
    ):
        status = "degraded"
    else:
        status = "unknown"
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
        print(f"learn-loop preflight: {report['status']}")
        for name, passed in report["checks"].items():
            print(f"- {name}: {'OK' if passed else 'FAIL'}")
        print("- independence tier: " + report["capabilities"]["suggested_independence_tier"])
        print("- anchoring mode: " + report["capabilities"]["anchoring_mode"])
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
