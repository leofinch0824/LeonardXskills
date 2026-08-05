#!/usr/bin/env python3
"""Maintain the append-friendly 1/7/30-day review queue for learn-loop."""

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path


HEADER = (
    "| 日期 | slug | 主题 | +1 日到期 | +7 日到期 | +30 日到期 | "
    "下次复习 | 历史得分 | 状态 |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", default=os.environ.get("LEARN_LOOP_STATE_DIR"))
    parser.add_argument("--queue-path", help="直接指定 review-queue.md")
    parser.add_argument("--add", action="store_true", help="登记一轮学习的 1/7/30 天复习日期")
    parser.add_argument("--due", action="store_true", help="列出到期主题")
    parser.add_argument("--record-score", action="store_true", help="记录得分并按分数推进下一间隔")
    parser.add_argument("--topic")
    parser.add_argument("--slug")
    parser.add_argument("--score", type=float)
    parser.add_argument("--date", dest="run_date", default=date.today().isoformat())
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def queue_path(args):
    if args.queue_path:
        return Path(args.queue_path).expanduser().resolve()
    state_root = Path(args.state_dir).expanduser() if args.state_dir else Path.cwd() / ".learn-loop"
    if not state_root.is_absolute():
        state_root = Path.cwd() / state_root
    return (state_root / "review-queue.md").resolve()


def parse_day(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"日期必须为 YYYY-MM-DD: {value}") from exc


def split_row(line):
    if not line.strip().startswith("|"):
        return []
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def load_rows(path):
    if not path.exists():
        return [], []
    lines = path.read_text(encoding="utf-8").splitlines()
    header_index = next(
        (index for index, line in enumerate(lines) if "| slug |" in line),
        None,
    )
    if header_index is None:
        return lines, []
    header = split_row(lines[header_index])
    rows = []
    for index in range(header_index + 2, len(lines)):
        cells = split_row(lines[index])
        if len(cells) == len(header):
            rows.append({"line_index": index, "cells": cells})
    return lines, rows


def ensure_queue(path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Learn Loop 复习队列\n\n" + HEADER, encoding="utf-8")


def append_row(path, cells):
    ensure_queue(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("| " + " | ".join(cells) + " |\n")


def add_review(path, topic, slug, run_day):
    dates = [run_day + timedelta(days=offset) for offset in (1, 7, 30)]
    lines, rows = load_rows(path)
    if rows:
        header_index = next(
            index for index, line in enumerate(lines) if "| slug |" in line
        )
        indices = find_column_indices(split_row(lines[header_index]))
        matches = [
            row for row in rows if row["cells"][indices["slug"]] == slug
        ]
        if matches:
            expected = (run_day.isoformat(), topic)
            actual = (
                matches[0]["cells"][indices["日期"]],
                matches[0]["cells"][indices["主题"]],
            )
            if len(matches) == 1 and actual == expected:
                return {
                    "topic": topic,
                    "slug": slug,
                    "one_day": dates[0].isoformat(),
                    "seven_day": dates[1].isoformat(),
                    "thirty_day": dates[2].isoformat(),
                    "updated": False,
                }
            raise ValueError(f"复习队列中同一运行 ID 存在冲突记录：{slug}")
    append_row(
        path,
        [
            run_day.isoformat(),
            slug,
            topic,
            *(day.isoformat() for day in dates),
            dates[0].isoformat(),
            "—",
            "待复习",
        ],
    )
    return {
        "topic": topic,
        "slug": slug,
        "one_day": dates[0].isoformat(),
        "seven_day": dates[1].isoformat(),
        "thirty_day": dates[2].isoformat(),
        "updated": True,
    }


def find_column_indices(header):
    return {name: index for index, name in enumerate(header)}


def update_score(path, slug, topic, score, score_day):
    lines, rows = load_rows(path)
    if not rows:
        raise ValueError("复习队列为空或表头不完整")
    header_index = next(index for index, line in enumerate(lines) if "| slug |" in line)
    header = split_row(lines[header_index])
    indices = find_column_indices(header)
    if slug and topic:
        candidates = [
            row
            for row in rows
            if row["cells"][indices["slug"]] == slug
            and row["cells"][indices["主题"]] == topic
        ]
    elif slug:
        candidates = [row for row in rows if row["cells"][indices["slug"]] == slug]
    else:
        candidates = [row for row in rows if row["cells"][indices["主题"]] == topic]
    if not candidates:
        raise ValueError("找不到对应 slug 或主题")
    if len(candidates) > 1:
        raise ValueError("slug 或主题对应多条运行记录；请同时提供唯一 slug 和主题")

    row = candidates[0]
    cells = row["cells"]
    history_index = indices["历史得分"]
    old_history = cells[history_index]
    score_entry = f"{score_day.isoformat()}: {score:g}/10"
    cells[history_index] = score_entry if old_history in {"", "—", "-"} else old_history + "; " + score_entry

    interval = 1 if score < 6 else 7 if score < 8 else 30
    next_review = score_day + timedelta(days=interval)
    cells[indices["下次复习"]] = next_review.isoformat()
    cells[indices["状态"]] = "需补强" if score < 6 else "已复习"
    lines[row["line_index"]] = "| " + " | ".join(cells) + " |"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "slug": cells[indices["slug"]],
        "score": score,
        "next_review": next_review.isoformat(),
        "interval_days": interval,
    }


def due_rows(path, today):
    lines, rows = load_rows(path)
    if not rows:
        return []
    header_index = next((index for index, line in enumerate(lines) if "| slug |" in line), None)
    if header_index is None:
        return []
    indices = find_column_indices(split_row(lines[header_index]))
    due = []
    for row in rows:
        cells = row["cells"]
        try:
            due_day = parse_day(cells[indices["下次复习"]])
        except (KeyError, ValueError):
            continue
        if due_day <= today and cells[indices["状态"]] != "已完成":
            due.append(
                {
                    "date": cells[indices["日期"]],
                    "slug": cells[indices["slug"]],
                    "topic": cells[indices["主题"]],
                    "due": cells[indices["下次复习"]],
                    "status": cells[indices["状态"]],
                }
            )
    return due


def main():
    args = parse_args()
    operations = sum((args.add, args.due, args.record_score))
    if operations != 1:
        raise SystemExit("必须且只能选择 --add、--due 或 --record-score 之一")
    try:
        path = queue_path(args)
        if args.add:
            if not args.topic or not args.slug:
                raise ValueError("--add 需要 --topic 和 --slug")
            result = add_review(path, args.topic, args.slug, parse_day(args.run_date))
        elif args.due:
            result = due_rows(path, parse_day(args.run_date))
        else:
            if args.score is None or not 0 <= args.score <= 10:
                raise ValueError("--record-score 需要 0 到 10 的 --score")
            if not args.slug and not args.topic:
                raise ValueError("--record-score 需要 --slug 或 --topic")
            result = update_score(
                path,
                args.slug,
                args.topic,
                args.score,
                parse_day(args.run_date),
            )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.due:
        for row in result:
            print(f"{row['due']}\t{row['slug']}\t{row['topic']}\t{row['status']}")
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
