#!/usr/bin/env python3
"""Shared controlled-Markdown parsing, references, and atomic state writes for Learn Loop."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlparse


HEADING = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>\S.*?)\s*$")
FIELD = re.compile(
    r"^-\s+\*\*(?P<label>[^*：:]+)[：:]\*\*\s*(?P<value>.*)$"
)
TABLE_SEPARATOR = re.compile(r"^:?-{3,}:?$")
STATE_SECTIONS = (
    "运行标识",
    "前置判定",
    "学习画像",
    "能力与降级",
    "模式 A 进度",
)
ROLE_NAMES = ("实践者", "学者", "怀疑者", "经济学家", "历史学家")
SENTINEL_TERMS = (
    "待填写",
    "待抽取",
    "待核查",
    "待在发",
    "已填示例",
)
SOURCE_URL_PROSE_MARKS = frozenset("：；，、（）【】《》“”‘’")


@dataclass(frozen=True)
class ContractViolation:
    code: str
    file: str
    record: str | None
    field: str | None
    expected: str
    actual: str
    message: str

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass
class Section:
    level: int
    title: str
    body: str
    fields: dict[str, str] = field(default_factory=dict)
    start_line: int = 0
    end_line: int = 0


@dataclass
class MarkdownDocument:
    text: str
    sections: list[Section]

    def find(self, title: str, level: int | None = None) -> list[Section]:
        return [
            section
            for section in self.sections
            if section.title == title and (level is None or section.level == level)
        ]


def parse_fields(lines: list[str]) -> dict[str, str]:
    fields = {}
    current_label = None
    current_lines = []

    def finish():
        nonlocal current_label, current_lines
        if current_label is None:
            return
        if current_label in fields:
            raise ValueError(f"重复字段：{current_label}")
        fields[current_label] = "\n".join(current_lines).strip()
        current_label = None
        current_lines = []

    for line in lines:
        match = FIELD.match(line)
        if match:
            finish()
            current_label = match.group("label").strip()
            current_lines = [match.group("value").strip()]
            continue
        if current_label is not None and line[:1].isspace() and line.strip():
            current_lines.append(line.strip())
            continue
        if current_label is not None and not line.strip():
            continue
        finish()
    finish()
    return fields


def parse_document(text: str) -> MarkdownDocument:
    lines = text.splitlines()
    headings = []
    for index, line in enumerate(lines):
        match = HEADING.match(line)
        if match:
            headings.append(
                (index, len(match.group("marks")), match.group("title").strip())
            )

    sections = []
    for position, (start, level, title) in enumerate(headings):
        end = len(lines)
        for candidate_start, candidate_level, _ in headings[position + 1 :]:
            if candidate_level <= level:
                end = candidate_start
                break
        body_lines = lines[start + 1 : end]
        direct_body_lines = []
        for line in body_lines:
            nested = HEADING.match(line)
            if nested and len(nested.group("marks")) > level:
                break
            direct_body_lines.append(line)
        sections.append(
            Section(
                level=level,
                title=title,
                body="\n".join(body_lines).strip(),
                fields=parse_fields(direct_body_lines),
                start_line=start + 1,
                end_line=end,
            )
        )
    return MarkdownDocument(text=text, sections=sections)


def exact_sections(
    document: MarkdownDocument, level: int, pattern: str
) -> list[Section]:
    expression = re.compile(pattern)
    return [
        section
        for section in document.sections
        if section.level == level and expression.fullmatch(section.title)
    ]


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def markdown_table_rows(text: str) -> list[list[str]]:
    """Split pipe-table lines into stripped cells; separator rows are skipped."""
    rows = []
    for line in text.splitlines():
        cells = _split_table_row(line)
        if not cells or all(TABLE_SEPARATOR.fullmatch(cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def role_channel_table(text: str) -> dict[str, tuple[str, str]]:
    """Map each statute role to (优先渠道, 重点追问) in perspectives.md.

    Cell alignment padding is an implementation detail of the document and
    must stay irrelevant to this parse.
    """
    section = re.search(r"(?ms)^## 视角与渠道\s*$\n(.*?)(?=^## |\Z)", text)
    if section is None:
        raise ValueError("perspectives.md 缺少「视角与渠道」章节")
    table: dict[str, tuple[str, str]] = {}
    for cells in markdown_table_rows(section.group(1)):
        if len(cells) >= 3 and cells[0] in ROLE_NAMES:
            table[cells[0]] = (cells[1], cells[2])
    return table


def parse_upstream_table(document: MarkdownDocument) -> tuple[str, ...]:
    matches = document.find("消费上游", level=2)
    if len(matches) != 1:
        raise ValueError("消费上游章节必须恰好一个")
    rows = [_split_table_row(line) for line in matches[0].body.splitlines()]
    rows = [row for row in rows if row]
    if len(rows) < 2 or not rows[0] or rows[0][0] != "文件":
        raise ValueError("消费上游必须使用以“文件”为第一列的 Markdown 表格")
    paths = []
    for row in rows[1:]:
        if not row or all(TABLE_SEPARATOR.fullmatch(cell) for cell in row):
            continue
        value = row[0].strip().strip("`")
        if value and value != "无":
            paths.append(value)
    return tuple(paths)


def normalize_value(value: str) -> str:
    return "\n".join(line.strip() for line in value.strip().splitlines()).strip()


def canonical_http_url(value: str) -> str | None:
    """Return one bare HTTP(S) URL, excluding prose and compound values."""
    candidate = value.strip()
    if candidate.endswith("。"):
        candidate = candidate[:-1].rstrip()
    if (
        not candidate
        or any(character.isspace() for character in candidate)
        or any(mark in candidate for mark in SOURCE_URL_PROSE_MARKS)
    ):
        return None
    try:
        parsed = urlparse(candidate)
        hostname = parsed.hostname
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not hostname:
        return None
    return candidate


def is_sentinel(value: str) -> bool:
    normalized = normalize_value(value)
    return (
        not normalized
        or any(term in normalized for term in SENTINEL_TERMS)
        or bool(re.search(r"\{\{[^{}]+\}\}", normalized))
    )


def resolve_reference(run_dir: Path, reference: str) -> Section:
    raw = reference.strip().strip("`")
    if "#" not in raw:
        raise ValueError(f"引用必须使用“相对路径#精确标题”：{reference}")
    relative_text, title = raw.split("#", 1)
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts or not title.strip():
        raise ValueError(f"引用不得越出运行目录：{reference}")

    root = run_dir.expanduser().resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"引用不得越出运行目录：{reference}")
    if path.suffix.lower() != ".md" or not path.is_file():
        raise ValueError(f"引用文件不存在或不是 Markdown：{reference}")

    document = parse_document(path.read_text(encoding="utf-8"))
    matches = document.find(title.strip())
    if len(matches) != 1:
        raise ValueError(
            f"引用标题必须恰好匹配一次：{reference}（实际 {len(matches)}）"
        )
    return matches[0]


def read_run_state(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ValueError(f"运行状态不存在：{path}")
    document = parse_document(path.read_text(encoding="utf-8"))
    values = {}
    for section_name in STATE_SECTIONS:
        matches = document.find(section_name, level=2)
        if len(matches) != 1:
            raise ValueError(f"运行状态章节必须恰好一个：{section_name}")
        for label, value in matches[0].fields.items():
            if label in values:
                raise ValueError(f"运行状态字段重复：{label}")
            values[label] = value
    return values


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _replace_unique_field(text: str, label: str, value: str) -> str:
    expression = re.compile(
        rf"(?m)^(?P<prefix>\s*-\s+\*\*{re.escape(label)}[：:]\*\*\s*).*$"
    )
    matches = list(expression.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"待更新字段必须恰好一个：{label}（实际 {len(matches)}）")
    return expression.sub(lambda match: match.group("prefix") + value, text, count=1)


def update_run_state(path: Path, updates: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for label, value in updates.items():
        text = _replace_unique_field(text, label, value)
    atomic_write(path, text.rstrip() + "\n")
