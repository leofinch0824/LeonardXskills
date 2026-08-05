#!/usr/bin/env python3
"""Finalize a validated Learn Loop run and register its retention metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import preflight
import review_queue
import validate_stage
from contract_io import atomic_write, parse_document, update_run_state
from render_learning_page import render_learning_page


def _serialize(violations) -> list[dict]:
    return [item.to_dict() for item in violations]


def _state_fields(run_dir: Path) -> dict[str, str]:
    document = parse_document(
        (run_dir / "run-state.md").read_text(encoding="utf-8")
    )
    fields = {}
    for section in document.sections:
        fields.update(section.fields)
    return fields


def _validate_stages(run_dir: Path) -> dict[str, list[dict]]:
    failures = {}
    for stage in map(str, range(11)):
        violations = validate_stage.validate_one(stage, run_dir)
        if violations:
            failures[stage] = _serialize(violations)
    for optional in ("exam-record", "feynman-record"):
        if (run_dir / validate_stage.STAGE_FILES[optional]).is_file():
            violations = validate_stage.validate_one(optional, run_dir)
            if violations:
                failures[optional] = _serialize(violations)
    return failures


def _index_row(run_day: date, run_id: str, topic: str, status: str, run_dir: Path) -> str:
    return (
        f"| {run_day.isoformat()} | {run_id} | {topic} | {status} | "
        f"{run_dir.name} |"
    )


def _inspect_index(
    path: Path, run_day: date, run_id: str, topic: str, status: str, run_dir: Path
) -> tuple[str, bool]:
    expected = _index_row(run_day, run_id, topic, status, run_dir)
    if not path.exists():
        return preflight.INDEX_TEMPLATE.rstrip() + "\n" + expected + "\n", True
    text = path.read_text(encoding="utf-8")
    matches = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 5 and cells[1] == run_id:
            matches.append(line.strip())
    if not matches:
        return text.rstrip() + "\n" + expected + "\n", True
    if matches == [expected]:
        return text, False
    raise ValueError(f"INDEX.md 中同一运行 ID 存在冲突记录：{run_id}")


def _inspect_queue(path: Path, run_day: date, run_id: str, topic: str) -> None:
    if not path.exists():
        return
    lines, rows = review_queue.load_rows(path)
    if not rows:
        return
    header_index = next(index for index, line in enumerate(lines) if "| slug |" in line)
    indices = review_queue.find_column_indices(
        review_queue.split_row(lines[header_index])
    )
    matches = [row for row in rows if row["cells"][indices["slug"]] == run_id]
    if not matches:
        return
    actual = {
        (row["cells"][indices["日期"]], row["cells"][indices["主题"]])
        for row in matches
    }
    if len(matches) != 1 or actual != {(run_day.isoformat(), topic)}:
        raise ValueError(f"review-queue.md 中同一运行 ID 存在冲突记录：{run_id}")


def _profile_update(
    path: Path,
    run_day: date,
    fact: str | None,
    quote: str | None,
) -> tuple[str | None, bool]:
    if bool(fact) != bool(quote):
        raise ValueError("长期画像更新必须同时提供 profile_fact 和 profile_quote")
    if not fact:
        return None, False
    text = (
        path.read_text(encoding="utf-8")
        if path.exists()
        else (SKILL_ROOT / "templates" / "learner-profile.md").read_text(
            encoding="utf-8"
        )
    )
    safe_fact = fact.replace("|", "／").strip()
    safe_quote = quote.replace("|", "／").strip()
    row = (
        f"| {run_day.isoformat()} | {safe_fact} | — | {safe_fact} | "
        f"{safe_quote} |"
    )
    if row in text:
        return text, False
    if "暂无用户确认的长期事实。" in text:
        text = text.replace(
            "暂无用户确认的长期事实。",
            f"- {safe_fact}（用户依据：{safe_quote}）",
            1,
        )
    else:
        marker = "## 增量更新记录"
        before, after = text.split(marker, 1)
        text = before.rstrip() + f"\n- {safe_fact}（用户依据：{safe_quote}）\n\n" + marker + after
    return text.rstrip() + "\n" + row + "\n", True


def _exercise_status(run_dir: Path) -> str:
    path = run_dir / "08-exam-record.md"
    if not path.exists():
        return "未施考"
    fields = _state_fields_from(path)
    return f"已完成 {fields.get('当前游标', '0')} 题"


def _state_fields_from(path: Path) -> dict[str, str]:
    document = parse_document(path.read_text(encoding="utf-8"))
    values = {}
    for section in document.sections:
        values.update(section.fields)
    return values


def finalize_run(
    run_dir: Path,
    state_root: Path,
    learning_root: Path,
    inline: bool = False,
    profile_fact: str | None = None,
    profile_quote: str | None = None,
) -> dict:
    """Validate, render, register metadata, and atomically close Mode A."""
    run_dir = Path(run_dir).expanduser().resolve()
    state_root = Path(state_root).expanduser().resolve()
    learning_root = Path(learning_root).expanduser().resolve()
    result = {
        "ok": False,
        "html": None,
        "index_updated": False,
        "queue_updated": False,
        "profile_updated": False,
        "state": "进行中",
        "violations": {},
    }
    try:
        if not run_dir.is_relative_to(learning_root):
            raise ValueError("运行目录必须位于 learning_root 内")
        if bool(profile_fact) != bool(profile_quote):
            raise ValueError("长期画像更新必须同时提供事实和用户确认原话")
        failures = _validate_stages(run_dir)
        if failures:
            result["violations"] = failures
            return result
        state = _state_fields(run_dir)
        run_id = state["运行 ID"].strip()
        if not re.fullmatch(r"[\w.\-\u4e00-\u9fff]+", run_id):
            raise ValueError(f"运行 ID 不能安全用于文件名：{run_id}")
        topic = state["主题"].strip()
        created = datetime.fromisoformat(state["创建时间"])
        run_day = created.date()
        status = _exercise_status(run_dir)
        index_path = learning_root / "INDEX.md"
        queue_path = state_root / "review-queue.md"
        profile_path = state_root / "learner-profile.md"
        index_text, index_updated = _inspect_index(
            index_path, run_day, run_id, topic, status, run_dir
        )
        _inspect_queue(queue_path, run_day, run_id, topic)
        profile_text, profile_updated = _profile_update(
            profile_path, run_day, profile_fact, profile_quote
        )

        output = run_dir / f"{run_id}-十步学习.html"
        render_learning_page(run_dir, output, inline=inline)

        if index_updated:
            atomic_write(index_path, index_text)
        queue_result = review_queue.add_review(queue_path, topic, run_id, run_day)
        if profile_updated and profile_text is not None:
            atomic_write(profile_path, profile_text)

        state_path = run_dir / "run-state.md"
        original_state = state_path.read_text(encoding="utf-8")
        update_run_state(
            state_path,
            {
                "当前阶段": "完成",
                "已完成阶段": "0–10",
                "生成状态": "已完成",
            },
        )
        final_failures = {
            stage: _serialize(items)
            for stage, items in validate_stage.validate_all(run_dir).items()
            if items
        }
        if final_failures:
            atomic_write(state_path, original_state)
            result["violations"] = final_failures
            return result
        result.update(
            {
                "ok": True,
                "html": str(output),
                "index_updated": index_updated,
                "queue_updated": queue_result["updated"],
                "profile_updated": profile_updated,
                "state": "已完成",
            }
        )
        return result
    except (KeyError, OSError, ValueError) as error:
        result["violations"] = {"finalize": [str(error)]}
        return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--state-root", required=True)
    parser.add_argument("--learning-root", required=True)
    parser.add_argument("--inline", action="store_true")
    parser.add_argument("--profile-fact")
    parser.add_argument("--profile-quote")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = finalize_run(
        Path(args.run_dir),
        Path(args.state_root),
        Path(args.learning_root),
        inline=args.inline,
        profile_fact=args.profile_fact,
        profile_quote=args.profile_quote,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Learn Loop 最终化完成" if report["ok"] else "Learn Loop 最终化失败")
        if report["html"]:
            print(report["html"])
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
