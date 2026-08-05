#!/usr/bin/env python3
"""Validate Learn Loop stage artifacts against the canonical contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from contract_io import (
    ContractViolation,
    MarkdownDocument,
    Section,
    exact_sections,
    is_sentinel,
    normalize_value,
    parse_document,
    parse_upstream_table,
    resolve_reference,
)


STAGE_FILES = {
    "0": "run-state.md",
    "1": "01-perspectives.md",
    "2": "02-conflicts.md",
    "3": "03-brief.md",
    "4": "04-review.md",
    "5": "05-resources.md",
    "6": "06-ladder.md",
    "7": "07-sprint.md",
    "8": "08-exam-bank.md",
    "9": "09-feynman-notes.md",
    "10": "10-cheatsheet.md",
    "exam-record": "08-exam-record.md",
    "feynman-record": "09-feynman-record.md",
}
EXPECTED_UPSTREAMS = {
    "0": (),
    "1": (
        "run-state.md",
        "perspectives/practitioner.md",
        "perspectives/scholar.md",
        "perspectives/skeptic.md",
        "perspectives/economist.md",
        "perspectives/historian.md",
    ),
    "2": (
        "run-state.md",
        "01-perspectives.md",
        "perspectives/practitioner.md",
        "perspectives/scholar.md",
        "perspectives/skeptic.md",
        "perspectives/economist.md",
        "perspectives/historian.md",
    ),
    "3": ("run-state.md", "01-perspectives.md", "02-conflicts.md"),
    "4": ("run-state.md", "02-conflicts.md", "03-brief.md"),
    "5": ("run-state.md", "03-brief.md", "04-review.md"),
    "6": ("run-state.md", "03-brief.md"),
    "7": ("run-state.md", "03-brief.md", "05-resources.md", "06-ladder.md"),
    "8": ("run-state.md", "03-brief.md", "06-ladder.md", "07-sprint.md"),
    "9": ("run-state.md", "03-brief.md", "06-ladder.md"),
    "10": (
        "run-state.md",
        "01-perspectives.md",
        "02-conflicts.md",
        "03-brief.md",
        "04-review.md",
        "05-resources.md",
        "06-ladder.md",
        "07-sprint.md",
        "08-exam-bank.md",
        "09-feynman-notes.md",
    ),
    "exam-record": ("run-state.md", "08-exam-bank.md"),
    "feynman-record": ("run-state.md", "03-brief.md", "09-feynman-notes.md"),
    "role": ("run-state.md",),
}
ROLES = ("实践者", "学者", "怀疑者", "经济学家", "历史学家")
ROLE_FILES = {
    "实践者": "perspectives/practitioner.md",
    "学者": "perspectives/scholar.md",
    "怀疑者": "perspectives/skeptic.md",
    "经济学家": "perspectives/economist.md",
    "历史学家": "perspectives/historian.md",
}
GRADE_VALUES = {"A", "B", "C"}
CONTRACT_PATHS = {
    "0": "reference/stages/00-run-state.md",
    **{
        str(stage): f"reference/stages/{STAGE_FILES[str(stage)]}"
        for stage in range(1, 11)
    },
    "exam-record": "reference/modes/exam-record.md",
    "feynman-record": "reference/modes/feynman-record.md",
    "role": "reference/stages/01-perspectives.md",
}
PROMPT_HEADINGS = {
    1: "第 1 步 · 五视角 STORM",
    2: "第 2 步 · 矛盾图谱",
    3: "第 3 步 · 综合简报",
    4: "第 4 步 · 同行评审自检",
    5: "第 5 步 · 资源筛选",
    6: "第 6 步 · 学习阶梯",
    7: "第 7 步 · 2 小时啃下核心 20%",
    8: "第 8 步 · 考到我崩溃",
    9: "第 9 步 · 费曼循环",
    10: "第 10 步 · 一页速查表",
}


def _violation(
    file: str,
    code: str,
    message: str,
    *,
    record: str | None = None,
    field: str | None = None,
    expected: str = "满足阶段契约",
    actual: str = "不满足",
) -> ContractViolation:
    return ContractViolation(code, file, record, field, expected, actual, message)


def _add(
    violations: list[ContractViolation],
    file: str,
    code: str,
    message: str,
    **details,
) -> None:
    violations.append(_violation(file, code, message, **details))


def _read_document(
    path: Path, violations: list[ContractViolation]
) -> MarkdownDocument | None:
    if not path.is_file():
        _add(
            violations,
            path.name,
            "MISSING_FILE",
            f"缺少文件：{path.name}",
            expected="文件存在",
            actual="不存在",
        )
        return None
    try:
        return parse_document(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        _add(
            violations,
            path.name,
            "MARKDOWN_PARSE",
            f"受控 Markdown 无法解析：{error}",
            expected="唯一字段和合法 UTF-8",
            actual=str(error),
        )
        return None


def _one_section(
    document: MarkdownDocument,
    file: str,
    title: str,
    level: int,
    violations: list[ContractViolation],
) -> Section | None:
    matches = document.find(title, level)
    if len(matches) != 1:
        _add(
            violations,
            file,
            "SECTION_COUNT",
            f"章节“{title}”必须恰好出现一次，实际 {len(matches)} 次",
            record=title,
            expected="1",
            actual=str(len(matches)),
        )
        return None
    return matches[0]


def _records(
    document: MarkdownDocument, level: int, prefix: str
) -> list[Section]:
    return exact_sections(document, level, rf"{re.escape(prefix)} [1-9]\d*")


def _check_exact_titles(
    document: MarkdownDocument,
    level: int,
    expected: list[str],
    file: str,
    violations: list[ContractViolation],
) -> None:
    actual = [section.title for section in document.sections if section.level == level]
    if actual != expected:
        _add(
            violations,
            file,
            "HEADING_SEQUENCE",
            f"{level} 级标题必须与阶段契约完全一致且顺序固定",
            expected="、".join(expected),
            actual="、".join(actual),
        )


def _expect_numbered_records(
    records: list[Section],
    file: str,
    prefix: str,
    expected: int | tuple[int, int],
    violations: list[ContractViolation],
) -> bool:
    low, high = (expected, expected) if isinstance(expected, int) else expected
    count = len(records)
    if not low <= count <= high:
        wording = str(low) if low == high else f"{low}–{high}"
        _add(
            violations,
            file,
            "RECORD_COUNT",
            f"{prefix}数量必须为 {wording}，实际 {count}",
            record=prefix,
            expected=wording,
            actual=str(count),
        )
        return False
    expected_titles = [f"{prefix} {index}" for index in range(1, count + 1)]
    actual_titles = [record.title for record in records]
    if actual_titles != expected_titles:
        _add(
            violations,
            file,
            "RECORD_ORDER",
            f"{prefix}必须从 1 连续编号",
            record=prefix,
            expected="、".join(expected_titles),
            actual="、".join(actual_titles),
        )
        return False
    return True


def _check_fields(
    section: Section,
    file: str,
    required: tuple[str, ...],
    violations: list[ContractViolation],
    *,
    allow_sentinel: set[str] | None = None,
    exact: bool = True,
) -> None:
    allow_sentinel = allow_sentinel or set()
    labels = set(section.fields)
    required_set = set(required)
    for field in required:
        if field not in labels:
            _add(
                violations,
                file,
                "MISSING_FIELD",
                f"{section.title}缺少字段：{field}",
                record=section.title,
                field=field,
                expected="字段存在且非空",
                actual="缺失",
            )
        elif field not in allow_sentinel and is_sentinel(section.fields[field]):
            _add(
                violations,
                file,
                "SENTINEL_VALUE",
                f"{section.title}字段仍为空或包含占位值：{field}",
                record=section.title,
                field=field,
                expected="真实非占位内容",
                actual=section.fields[field],
            )
    if exact:
        for field in sorted(labels - required_set):
            _add(
                violations,
                file,
                "UNEXPECTED_FIELD",
                f"{section.title}包含契约未定义字段：{field}",
                record=section.title,
                field=field,
                expected="仅包含规范字段",
                actual=field,
            )


def _is_reasoned_none(text: str) -> bool:
    value = normalize_value(text).lstrip("- ")
    return bool(re.fullmatch(r"无[：:].+", value)) and not is_sentinel(value)


def _check_free_text(
    section: Section | None,
    file: str,
    violations: list[ContractViolation],
) -> None:
    if section is not None and is_sentinel(section.body):
        _add(
            violations,
            file,
            "SENTINEL_VALUE",
            f"章节“{section.title}”必须有真实内容",
            record=section.title,
            expected="非占位内容",
            actual=section.body,
        )


def _check_enum(
    section: Section,
    field: str,
    allowed: set[str],
    file: str,
    violations: list[ContractViolation],
) -> None:
    value = normalize_value(section.fields.get(field, "")).strip("。")
    if value not in allowed:
        _add(
            violations,
            file,
            "ENUM_VALUE",
            f"{section.title}字段“{field}”枚举非法：{value}",
            record=section.title,
            field=field,
            expected=" / ".join(sorted(allowed)),
            actual=value,
        )


def _valid_url(value: str) -> bool:
    parsed = urlparse(value.strip().strip("`"))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _check_grade_and_url(
    section: Section,
    file: str,
    violations: list[ContractViolation],
    *,
    grade_field: str = "来源等级",
    url_field: str = "来源 URL",
) -> None:
    grade = normalize_value(section.fields.get(grade_field, "")).strip("。")
    url = normalize_value(section.fields.get(url_field, "")).strip("。")
    if grade not in GRADE_VALUES:
        _check_enum(section, grade_field, GRADE_VALUES, file, violations)
    elif grade in {"A", "B"} and not _valid_url(url):
        _add(
            violations,
            file,
            "SOURCE_URL",
            f"{section.title}的 {grade} 级来源必须有可解析 URL",
            record=section.title,
            field=url_field,
            expected="http(s) URL",
            actual=url,
        )
    elif grade == "C" and url != "无":
        _add(
            violations,
            file,
            "SOURCE_URL",
            f"{section.title}的 C 级来源 URL 必须写“无”",
            record=section.title,
            field=url_field,
            expected="无",
            actual=url,
        )


def _reference_values(value: str) -> list[str]:
    backticked = re.findall(r"`([^`]+\.md#[^`]+)`", value)
    if backticked:
        return backticked
    stripped = value.strip().strip("`")
    return [stripped] if ".md#" in stripped else []


def _check_references(
    section: Section,
    field: str,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
) -> None:
    value = section.fields.get(field, "")
    references = _reference_values(value)
    if not references:
        _add(
            violations,
            file,
            "REFERENCE_FORMAT",
            f"{section.title}字段“{field}”必须包含“相对路径#精确标题”引用",
            record=section.title,
            field=field,
            expected="relative.md#精确标题",
            actual=value,
        )
        return
    for reference in references:
        try:
            resolve_reference(run_dir, reference)
        except ValueError as error:
            _add(
                violations,
                file,
                "REFERENCE_INVALID",
                f"{section.title}引用不可解析：{error}",
                record=section.title,
                field=field,
                expected="运行目录内唯一精确标题",
                actual=reference,
            )


def _check_upstreams(
    stage: str,
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
) -> None:
    try:
        actual = parse_upstream_table(document)
    except ValueError as error:
        _add(
            violations,
            file,
            "UPSTREAM_TABLE",
            str(error),
            record="消费上游",
            expected="规范 Markdown 表格",
            actual=str(error),
        )
        return
    expected = EXPECTED_UPSTREAMS[stage]
    if stage == "feynman-record" and actual == (*expected, "08-exam-record.md"):
        expected = actual
    if actual != expected:
        _add(
            violations,
            file,
            "UPSTREAM_MISMATCH",
            "消费上游必须与阶段契约完全一致且顺序固定",
            record="消费上游",
            expected="、".join(expected) or "无",
            actual="、".join(actual) or "无",
        )
    for relative in actual:
        if stage == "feynman-record" and relative == "08-exam-record.md":
            continue
        if not (run_dir / relative).is_file():
            _add(
                violations,
                file,
                "UPSTREAM_MISSING",
                f"消费上游不存在：{relative}",
                record="消费上游",
                expected="文件存在",
                actual=relative,
            )


def _check_execution(
    stage: str,
    document: MarkdownDocument,
    file: str,
    violations: list[ContractViolation],
) -> None:
    execution = _one_section(document, file, "执行契约", 2, violations)
    if execution is None:
        return
    if stage in {"exam-record", "feynman-record"}:
        fields = ("模式契约",)
        contract_field = "模式契约"
    elif stage == "role":
        fields = ("阶段契约", "角色")
        contract_field = "阶段契约"
    else:
        fields = ("阶段契约", "原始提示词")
        contract_field = "阶段契约"
    _check_fields(execution, file, fields, violations)
    actual = execution.fields.get(contract_field, "").strip().strip("`")
    expected = CONTRACT_PATHS[stage]
    if actual != expected:
        _add(
            violations,
            file,
            "CONTRACT_REFERENCE",
            "执行契约必须引用当前规范文件",
            record="执行契约",
            field=contract_field,
            expected=expected,
            actual=actual,
        )
    if stage.isdigit() and int(stage) in PROMPT_HEADINGS:
        expected_prompt = (
            "reference/original-prompts.md#" + PROMPT_HEADINGS[int(stage)]
        )
        actual_prompt = execution.fields.get("原始提示词", "").strip().strip("`")
        if actual_prompt != expected_prompt:
            _add(
                violations,
                file,
                "PROMPT_REFERENCE",
                "执行契约必须引用当前步骤的原始提示词精确标题",
                record="执行契约",
                field="原始提示词",
                expected=expected_prompt,
                actual=actual_prompt,
            )


def _check_common(
    stage: str,
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
    *,
    check_takeaways: bool = True,
) -> None:
    _check_execution(stage, document, file, violations)
    _one_section(document, file, "消费上游", 2, violations)
    _one_section(document, file, "产物", 2, violations)
    takeaways = _one_section(document, file, "本步提炼", 2, violations)
    _check_upstreams(stage, document, run_dir, file, violations)
    if "{{" in document.text or "}}" in document.text:
        _add(
            violations,
            file,
            "UNRESOLVED_SLOT",
            "产物残留未解析模板占位符",
            expected="无 {{...}}",
            actual="存在占位符",
        )
    if check_takeaways and takeaways is not None:
        items = [
            match.group(1).strip()
            for match in re.finditer(r"(?m)^-\s+(\S.*)$", takeaways.body)
        ]
        if len(items) != 3:
            _add(
                violations,
                file,
                "TAKEAWAY_COUNT",
                f"本步提炼必须恰好 3 条，实际 {len(items)} 条",
                record="本步提炼",
                expected="3",
                actual=str(len(items)),
            )
        for index, value in enumerate(items, start=1):
            if is_sentinel(value):
                _add(
                    violations,
                    file,
                    "SENTINEL_VALUE",
                    f"本步提炼第 {index} 条仍为占位值",
                    record="本步提炼",
                    field=str(index),
                    expected="真实提炼",
                    actual=value,
                )


def _state_value(run_dir: Path, label: str) -> str:
    path = run_dir / "run-state.md"
    if not path.is_file():
        return ""
    try:
        document = parse_document(path.read_text(encoding="utf-8"))
    except ValueError:
        return ""
    for section in document.sections:
        if label in section.fields:
            return normalize_value(section.fields[label]).strip("。")
    return ""


def _iso_with_timezone(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _validate_stage_0(
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
) -> None:
    _check_execution("0", document, file, violations)
    sections = {
        title: _one_section(document, file, title, 2, violations)
        for title in (
            "消费上游",
            "运行标识",
            "前置判定",
            "学习画像",
            "能力与降级",
            "模式 A 进度",
            "上下文披露记录",
        )
    }
    _check_upstreams("0", document, run_dir, file, violations)
    specifications = {
        "运行标识": (
            "运行 ID",
            "创建时间",
            "主题",
            "运行目录",
            "原始提示词文件",
            "原始提示词 SHA-256",
        ),
        "前置判定": ("判定", "判定理由", "调整说明", "资料探针"),
        "学习画像": (
            "当前水平",
            "目标深度",
            "角色 / 使用场景",
            "画像句",
            "默认处理",
        ),
        "能力与降级": (
            "独立性档位",
            "子 agent 验证依据",
            "锚定模式",
            "检索验证依据",
            "降级声明",
        ),
        "模式 A 进度": ("当前阶段", "已完成阶段", "生成状态"),
    }
    for title, fields in specifications.items():
        if sections[title] is not None:
            _check_fields(sections[title], file, fields, violations)

    identity = sections["运行标识"]
    if identity is not None:
        created = identity.fields.get("创建时间", "")
        if not _iso_with_timezone(created):
            _add(
                violations,
                file,
                "TIMESTAMP",
                "创建时间必须为带时区 ISO 8601",
                record="运行标识",
                field="创建时间",
                expected="带时区 ISO 8601",
                actual=created,
            )
        directory = identity.fields.get("运行目录", "")
        if directory and Path(directory).expanduser().resolve() != run_dir:
            _add(
                violations,
                file,
                "RUN_DIRECTORY",
                "运行目录字段必须指向当前运行目录",
                record="运行标识",
                field="运行目录",
                expected=str(run_dir),
                actual=directory,
            )
        source = identity.fields.get("原始提示词文件", "").strip("`")
        if source != "reference/original-prompts.md":
            _add(
                violations,
                file,
                "PROMPT_SOURCE",
                "原始提示词文件必须使用规范逻辑路径",
                record="运行标识",
                field="原始提示词文件",
                expected="reference/original-prompts.md",
                actual=source,
            )
        digest = identity.fields.get("原始提示词 SHA-256", "")
        current_digest = hashlib.sha256(
            (SKILL_ROOT / "reference" / "original-prompts.md").read_bytes()
        ).hexdigest()
        if digest != current_digest:
            _add(
                violations,
                file,
                "PROMPT_DIGEST",
                "原始提示词摘要与当前法条层不一致",
                record="运行标识",
                field="原始提示词 SHA-256",
                expected=current_digest,
                actual=digest,
            )

    precheck = sections["前置判定"]
    if precheck is not None:
        _check_enum(precheck, "判定", {"适合", "调整后适合"}, file, violations)
        verdict = normalize_value(precheck.fields.get("判定", "")).strip("。")
        note = normalize_value(precheck.fields.get("调整说明", "")).strip("。")
        if verdict == "适合" and note != "无需调整":
            _add(
                violations,
                file,
                "PRECHECK_NOTE",
                "判定为适合时，调整说明必须写“无需调整”",
                record="前置判定",
                field="调整说明",
                expected="无需调整",
                actual=note,
            )
        if verdict == "调整后适合" and note in {"", "无", "不适用", "无需调整"}:
            _add(
                violations,
                file,
                "PRECHECK_NOTE",
                "调整后适合必须记录调整、风险和用户确认原话",
                record="前置判定",
                field="调整说明",
                expected="调整、风险、用户确认原话",
                actual=note,
            )
        probe = normalize_value(precheck.fields.get("资料探针", "")).strip("。")
        if probe != "未做" and not probe.startswith("已做："):
            _add(
                violations,
                file,
                "PROBE_VALUE",
                "资料探针只能写“未做”或“已做：<结论>”",
                record="前置判定",
                field="资料探针",
                expected="未做 / 已做：<结论>",
                actual=probe,
            )

    profile = sections["学习画像"]
    if profile is not None:
        source_fields = ("当前水平", "目标深度", "角色 / 使用场景")
        missing = False
        for label in source_fields:
            value = normalize_value(profile.fields.get(label, ""))
            if not value.startswith(("用户回答：", "用户开场已提供：", "未提供")):
                _add(
                    violations,
                    file,
                    "PROFILE_SOURCE",
                    f"学习画像字段缺少来源标记：{label}",
                    record="学习画像",
                    field=label,
                    expected="用户回答： / 用户开场已提供： / 未提供",
                    actual=value,
                )
            missing = missing or value.startswith("未提供")
        default = normalize_value(profile.fields.get("默认处理", "")).strip("。")
        if missing and not default.startswith("已按默认值执行："):
            _add(
                violations,
                file,
                "PROFILE_DEFAULT",
                "存在未提供字段时，必须记录用户授权的默认处理",
                record="学习画像",
                field="默认处理",
                expected="已按默认值执行：<实际默认值>",
                actual=default,
            )
        if not missing and default != "无需默认值":
            _add(
                violations,
                file,
                "PROFILE_DEFAULT",
                "画像无缺失时默认处理必须写“无需默认值”",
                record="学习画像",
                field="默认处理",
                expected="无需默认值",
                actual=default,
            )

    capability = sections["能力与降级"]
    if capability is not None:
        _check_enum(
            capability,
            "独立性档位",
            {"parallel", "serial-isolated", "orchestrated"},
            file,
            violations,
        )
        _check_enum(
            capability,
            "锚定模式",
            {"anchored", "未锚定模式"},
            file,
            violations,
        )

    progress = sections["模式 A 进度"]
    if progress is not None:
        current = normalize_value(progress.fields.get("当前阶段", "")).strip("。")
        if current != "完成" and not re.fullmatch(r"(?:[0-9]|10)", current):
            _add(
                violations,
                file,
                "STAGE_CURSOR",
                "当前阶段只能是 0–10 或完成",
                record="模式 A 进度",
                field="当前阶段",
                expected="0–10 / 完成",
                actual=current,
            )
        completed = normalize_value(progress.fields.get("已完成阶段", "")).strip("。")
        if completed != "无" and not re.fullmatch(r"0(?:–|-)(?:[0-9]|10)", completed):
            _add(
                violations,
                file,
                "COMPLETED_RANGE",
                "已完成阶段必须是从 0 开始的连续区间",
                record="模式 A 进度",
                field="已完成阶段",
                expected="无 / 0–N",
                actual=completed,
            )
        _check_enum(progress, "生成状态", {"进行中", "已完成"}, file, violations)
        expected_completed = None
        if current == "0":
            expected_completed = "无"
        elif current.isdigit():
            expected_completed = f"0–{int(current) - 1}"
        elif current == "完成":
            expected_completed = "0–10"
        if expected_completed is not None and completed.replace("-", "–") != expected_completed:
            _add(
                violations,
                file,
                "PROGRESS_CONSISTENCY",
                "已完成阶段必须与当前阶段形成连续边界",
                record="模式 A 进度",
                field="已完成阶段",
                expected=expected_completed,
                actual=completed,
            )
        status = normalize_value(progress.fields.get("生成状态", "")).strip("。")
        if (current == "完成") != (status == "已完成"):
            _add(
                violations,
                file,
                "PROGRESS_CONSISTENCY",
                "只有当前阶段为完成时，生成状态才能为已完成",
                record="模式 A 进度",
                field="生成状态",
                expected="完成 ↔ 已完成",
                actual=f"{current} / {status}",
            )

    disclosure = sections["上下文披露记录"]
    if disclosure is not None:
        disclosure_records = exact_sections(
            document, 3, r"阶段 (?:0|[1-9]\d*)"
        )
        titles = [record.title for record in disclosure_records]
        if len(titles) != len(set(titles)):
            _add(
                violations,
                file,
                "DISCLOSURE_DUPLICATE",
                "同一阶段只能有一条上下文披露记录",
                record="上下文披露记录",
                expected="每阶段唯一",
                actual="、".join(titles),
            )
        numbers = [int(record.title.removeprefix("阶段 ")) for record in disclosure_records]
        if numbers and numbers != list(range(0, max(numbers) + 1)):
            _add(
                violations,
                file,
                "DISCLOSURE_CONTINUITY",
                "上下文披露记录必须从阶段 0 连续追加",
                record="上下文披露记录",
                expected=f"0–{max(numbers)}",
                actual="、".join(map(str, numbers)),
            )
        for record in disclosure_records:
            _check_fields(record, file, ("准备时间", "披露清单"), violations)
            if not _iso_with_timezone(record.fields.get("准备时间", "")):
                _add(
                    violations,
                    file,
                    "TIMESTAMP",
                    f"{record.title}准备时间必须为带时区 ISO 8601",
                    record=record.title,
                    field="准备时间",
                    expected="带时区 ISO 8601",
                    actual=record.fields.get("准备时间", ""),
                )
        current = normalize_value(
            sections["模式 A 进度"].fields.get("当前阶段", "")
        ).strip("。") if sections["模式 A 进度"] else ""
        if current.isdigit() and numbers != list(range(0, int(current) + 1)):
            _add(
                violations,
                file,
                "DISCLOSURE_PROGRESS",
                "已准备阶段必须与模式 A 当前阶段一致",
                record="上下文披露记录",
                expected=f"0–{current}",
                actual="、".join(map(str, numbers)) or "无",
            )
        if current == "完成" and numbers != list(range(0, 11)):
            _add(
                violations,
                file,
                "DISCLOSURE_PROGRESS",
                "完成状态必须保留阶段 0–10 的披露记录",
                record="上下文披露记录",
                expected="0–10",
                actual="、".join(map(str, numbers)) or "无",
            )
    for forbidden in ("当前考试游标", "弱项", "施考状态", "费曼状态", "已完成题数"):
        if forbidden in document.text:
            _add(
                violations,
                file,
                "STATE_AUTHORITY",
                f"run-state.md 不得保存交互事实：{forbidden}",
                field=forbidden,
                expected="由模式 B/C 记录保存",
                actual="出现在 run-state.md",
            )


def _numbered_items(text: str) -> list[str]:
    return [
        match.group(1).strip()
        for match in re.finditer(r"(?m)^\s*\d+[.)、]\s+(\S.*)$", text)
    ]


def _validate_role_file(
    role: str,
    run_dir: Path,
    violations: list[ContractViolation],
) -> dict[str, str] | None:
    relative = ROLE_FILES[role]
    path = run_dir / relative
    document = _read_document(path, violations)
    if document is None:
        return None
    _check_execution("role", document, relative, violations)
    _check_upstreams("role", document, run_dir, relative, violations)
    stance = _one_section(document, relative, "核心立场", 2, violations)
    evidence = _one_section(document, relative, "最强证据", 2, violations)
    insight = _one_section(document, relative, "独家洞见", 2, violations)
    analysis = _one_section(document, relative, "视角分析", 2, violations)
    retrieval = _one_section(document, relative, "检索记录", 2, violations)
    unresolved = _one_section(document, relative, "未决问题", 2, violations)
    if stance is not None:
        items = _numbered_items(stance.body)
        if len(items) != 2 or any(is_sentinel(item) for item in items):
            _add(
                violations,
                relative,
                "STANCE_COUNT",
                f"{role}核心立场必须恰好两个真实编号句",
                record="核心立场",
                expected="2",
                actual=str(len(items)),
            )
    if evidence is not None:
        fields = ("证据主张", "来源 URL", "来源等级", "支持说明", "未锚定原因")
        _check_fields(evidence, relative, fields, violations)
        _check_grade_and_url(evidence, relative, violations)
        grade = normalize_value(evidence.fields.get("来源等级", "")).strip("。")
        reason = normalize_value(evidence.fields.get("未锚定原因", "")).strip("。")
        if grade in {"A", "B"} and not reason.startswith("不适用："):
            _add(
                violations,
                relative,
                "UNANCHORED_REASON",
                "A/B 级证据的未锚定原因应写“不适用：<理由>”",
                record="最强证据",
                field="未锚定原因",
                expected="不适用：已有可解析 URL",
                actual=reason,
            )
        if grade == "C" and not reason.startswith("未锚定："):
            _add(
                violations,
                relative,
                "UNANCHORED_REASON",
                "C 级证据必须说明未锚定原因",
                record="最强证据",
                field="未锚定原因",
                expected="未锚定：<原因>",
                actual=reason,
            )
        mode = _state_value(run_dir, "锚定模式")
        if mode == "未锚定模式" and grade != "C":
            _add(
                violations,
                relative,
                "ANCHORING_GRADE",
                "未锚定模式下角色证据必须统一为 C",
                record="最强证据",
                field="来源等级",
                expected="C",
                actual=grade,
            )
    if insight is not None:
        _check_fields(
            insight,
            relative,
            ("洞见内容", "为何属于该视角", "适用边界"),
            violations,
        )
    _check_free_text(analysis, relative, violations)
    search_records = _records(document, 3, "检索")
    _expect_numbered_records(search_records, relative, "检索", (1, 99), violations)
    for record in search_records:
        _check_fields(
            record,
            relative,
            ("查询词", "检索渠道", "结果状态", "来源 URL", "取舍理由"),
            violations,
        )
        _check_enum(
            record,
            "结果状态",
            {"采信", "未采信", "未命中", "检索不可用"},
            relative,
            violations,
        )
        status = normalize_value(record.fields.get("结果状态", "")).strip("。")
        url = normalize_value(record.fields.get("来源 URL", "")).strip("。")
        if status in {"采信", "未采信"} and not _valid_url(url):
            _add(
                violations,
                relative,
                "SEARCH_URL",
                f"{record.title}状态为{status}时必须有可解析 URL",
                record=record.title,
                field="来源 URL",
                expected="http(s) URL",
                actual=url,
            )
        if status in {"未命中", "检索不可用"} and url != "无":
            _add(
                violations,
                relative,
                "SEARCH_URL",
                f"{record.title}状态为{status}时来源 URL 必须写“无”",
                record=record.title,
                field="来源 URL",
                expected="无",
                actual=url,
            )
    if unresolved is not None:
        unresolved_items = _numbered_items(unresolved.body)
        if _is_reasoned_none(unresolved.body):
            unresolved_items = [unresolved.body]
        if not 1 <= len(unresolved_items) <= 3 or any(
            is_sentinel(item) for item in unresolved_items
        ):
            _add(
                violations,
                relative,
                "UNRESOLVED_COUNT",
                "未决问题必须为 1–3 项，或带理由的无",
                record="未决问题",
                expected="1–3 / 无：理由",
                actual=str(len(unresolved_items)),
            )
    if not all((stance, evidence, insight, unresolved)):
        return None
    return {
        "核心立场": normalize_value(stance.body),
        "证据主张": normalize_value(evidence.fields.get("证据主张", "")),
        "来源 URL": normalize_value(evidence.fields.get("来源 URL", "")),
        "来源等级": normalize_value(evidence.fields.get("来源等级", "")),
        "支持说明": normalize_value(evidence.fields.get("支持说明", "")),
        "未锚定原因": normalize_value(evidence.fields.get("未锚定原因", "")),
        "独家洞见": normalize_value(insight.fields.get("洞见内容", "")),
        "为何属于该视角": normalize_value(insight.fields.get("为何属于该视角", "")),
        "适用边界": normalize_value(insight.fields.get("适用边界", "")),
        "未决问题": normalize_value(unresolved.body),
    }


def _validate_stage_1(
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
) -> None:
    _check_common("1", document, run_dir, file, violations)
    _check_exact_titles(document, 3, list(ROLES), file, violations)
    parent_records = [
        section
        for section in document.sections
        if section.level == 3 and section.title in ROLES
    ]
    actual_roles = [section.title for section in parent_records]
    if actual_roles != list(ROLES):
        _add(
            violations,
            file,
            "ROLE_ORDER",
            "父级汇总必须恰好按固定顺序包含五个角色",
            record="产物",
            expected="、".join(ROLES),
            actual="、".join(actual_roles),
        )
    parent_by_role = {section.title: section for section in parent_records}
    parent_fields = (
        "角色文件",
        "核心立场",
        "证据主张",
        "来源 URL",
        "来源等级",
        "支持说明",
        "未锚定原因",
        "独家洞见",
        "为何属于该视角",
        "适用边界",
        "未决问题",
    )
    for role in ROLES:
        source = _validate_role_file(role, run_dir, violations)
        parent = parent_by_role.get(role)
        if parent is None:
            continue
        _check_fields(parent, file, parent_fields, violations)
        expected_path = ROLE_FILES[role]
        actual_path = parent.fields.get("角色文件", "").strip().strip("`")
        if actual_path != expected_path:
            _add(
                violations,
                file,
                "ROLE_PATH",
                f"{role}角色文件引用错误",
                record=role,
                field="角色文件",
                expected=expected_path,
                actual=actual_path,
            )
        if source is None:
            continue
        for label, expected_value in source.items():
            actual_value = normalize_value(parent.fields.get(label, ""))
            if actual_value != expected_value:
                _add(
                    violations,
                    file,
                    "SOURCE_MISMATCH",
                    f"{role}汇总字段未逐字抽取角色文件：{label}",
                    record=role,
                    field=label,
                    expected=expected_value,
                    actual=actual_value,
                )


def _view_names(value: str) -> set[str]:
    return {role for role in ROLES if role in value}


def _validate_stage_2(
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
) -> None:
    _check_common("2", document, run_dir, file, violations)
    disagreements = _records(document, 3, "分歧")
    disagreement_container = _one_section(document, file, "分歧记录", 3, [])
    if not disagreements and (
        disagreement_container is None or not _is_reasoned_none(disagreement_container.body)
    ):
        _add(
            violations,
            file,
            "EMPTY_SET_REASON",
            "没有分歧记录时必须在“分歧记录”写带理由的无",
            record="分歧记录",
            expected="无：<可核查理由>",
            actual=disagreement_container.body if disagreement_container else "缺失",
        )
    _expect_numbered_records(disagreements, file, "分歧", (0, 99), violations)
    for record in disagreements:
        _check_fields(
            record,
            file,
            (
                "涉及视角",
                "立场 A",
                "立场 B",
                "依据引用",
                "分类",
                "分类理由",
                "需要的验证",
            ),
            violations,
        )
        _check_enum(record, "分类", {"实质分歧", "措辞分歧", "未决"}, file, violations)
        _check_references(record, "依据引用", run_dir, file, violations)

    comparison = _one_section(document, file, "证据强弱比较", 3, violations)
    if comparison is not None:
        _check_fields(
            comparison,
            file,
            (
                "比较范围",
                "最强视角",
                "最强证据引用",
                "最强理由",
                "最弱视角",
                "最弱证据引用",
                "最弱理由",
                "比较限制",
            ),
            violations,
        )
        _check_references(comparison, "最强证据引用", run_dir, file, violations)
        _check_references(comparison, "最弱证据引用", run_dir, file, violations)
        if _state_value(run_dir, "锚定模式") == "未锚定模式":
            limit = comparison.fields.get("比较限制", "")
            if "相对完整度" not in limit or "事实可靠性" not in limit:
                _add(
                    violations,
                    file,
                    "UNANCHORED_COMPARISON",
                    "未锚定模式须声明强弱仅代表相对完整度而非事实可靠性",
                    record="证据强弱比较",
                    field="比较限制",
                    expected="相对完整度；不表示事实可靠性",
                    actual=limit,
                )

    adjudication = _one_section(document, file, "关键裁决问题", 3, violations)
    actionable = any(
        normalize_value(record.fields.get("分类", "")).strip("。")
        in {"实质分歧", "未决"}
        for record in disagreements
    )
    if adjudication is not None:
        if actionable:
            _check_fields(
                adjudication,
                file,
                (
                    "问题",
                    "对应分歧引用",
                    "为何能化解",
                    "所需证据",
                    "判定方式",
                    "不同答案的影响",
                ),
                violations,
            )
        elif not _is_reasoned_none(adjudication.body):
            _add(
                violations,
                file,
                "ADJUDICATION_CONDITION",
                "没有实质或未决分歧时，裁决问题必须写带理由的无",
                record="关键裁决问题",
                expected="无：<理由>",
                actual=adjudication.body,
            )

    consensus_fields = (
        "结论",
        "支持视角",
        "未支持或反对视角",
        "证据引用",
        "综合来源等级",
        "来源独立性说明",
        "分级",
        "成立边界",
    )
    conclusions: set[str] = set()
    for group, low, high in (("全体一致", 5, 5), ("局部一致", 2, 4)):
        container = _one_section(document, file, group, 3, violations)
        if container is None:
            continue
        records = [
            record
            for record in exact_sections(document, 4, r"一致结论 [1-9]\d*")
            if container.start_line < record.start_line <= container.end_line
        ]
        if not records and not _is_reasoned_none(container.body):
            _add(
                violations,
                file,
                "EMPTY_SET_REASON",
                f"{group}为空时必须给出可核查理由",
                record=group,
                expected="无：<理由>",
                actual=container.body,
            )
        for record in records:
            _check_fields(record, file, consensus_fields, violations)
            support_count = len(_view_names(record.fields.get("支持视角", "")))
            if not low <= support_count <= high:
                _add(
                    violations,
                    file,
                    "CONSENSUS_SUPPORT",
                    f"{group}支持视角数量必须为 {low}–{high}，实际 {support_count}",
                    record=record.title,
                    field="支持视角",
                    expected=f"{low}–{high}",
                    actual=str(support_count),
                )
            _check_enum(record, "综合来源等级", GRADE_VALUES, file, violations)
            _check_enum(
                record,
                "分级",
                {"独立共识", "模型先验·待验证"},
                file,
                violations,
            )
            grade = normalize_value(
                record.fields.get("综合来源等级", "")
            ).strip("。")
            classification = normalize_value(record.fields.get("分级", "")).strip("。")
            if classification == "独立共识" and grade not in {"A", "B"}:
                _add(
                    violations,
                    file,
                    "CONSENSUS_GRADE",
                    "独立共识必须至少由 A/B 综合来源支撑",
                    record=record.title,
                    field="综合来源等级",
                    expected="A / B",
                    actual=grade,
                )
            if (
                _state_value(run_dir, "锚定模式") == "未锚定模式"
                and classification != "模型先验·待验证"
            ):
                _add(
                    violations,
                    file,
                    "CONSENSUS_GRADE",
                    "未锚定模式的一致结论只能标为模型先验·待验证",
                    record=record.title,
                    field="分级",
                    expected="模型先验·待验证",
                    actual=classification,
                )
            _check_references(record, "证据引用", run_dir, file, violations)
            conclusion = normalize_value(record.fields.get("结论", ""))
            if conclusion in conclusions:
                _add(
                    violations,
                    file,
                    "CONSENSUS_DUPLICATE",
                    "同一结论不得同时归入全体一致和局部一致",
                    record=record.title,
                    field="结论",
                    expected="结论唯一归类",
                    actual=conclusion,
                )
            conclusions.add(conclusion)

    blind = _one_section(document, file, "盲区判定", 3, violations)
    if blind is not None:
        candidates = [
            record
            for record in exact_sections(document, 4, r"盲区候选(?: 1)?")
            if blind.start_line < record.start_line <= blind.end_line
        ]
        if len(candidates) > 1:
            _add(
                violations,
                file,
                "RECORD_COUNT",
                "盲区判定最多保留一个最高影响候选",
                record="盲区判定",
                expected="0–1",
                actual=str(len(candidates)),
            )
        if not candidates and not _is_reasoned_none(blind.body):
            _add(
                violations,
                file,
                "EMPTY_SET_REASON",
                "盲区候选为空时必须给出可核查理由",
                record="盲区判定",
                expected="无：<理由>",
                actual=blind.body,
            )
        for candidate in candidates:
            _check_fields(
                candidate,
                file,
                (
                    "候选遗漏",
                    "判定",
                    "未提及依据",
                    "检索完整性依据",
                    "为什么重要",
                    "下一步验证",
                    "表述边界",
                ),
                violations,
            )
            _check_enum(candidate, "判定", {"领域盲区", "未覆盖"}, file, violations)


def _validate_stage_3(
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
) -> None:
    _check_common("3", document, run_dir, file, violations)
    _check_exact_titles(
        document,
        3,
        [
            "60 秒 CEO 总结",
            *(f"关键发现 {index}" for index in range(1, 6)),
            "隐藏关联",
            "行动建议",
            "前沿问题",
        ],
        file,
        violations,
    )
    mode = _state_value(run_dir, "锚定模式")
    expected_title = "第 3 步 · 假设简报" if mode == "未锚定模式" else "第 3 步 · 综合简报"
    h1 = [section.title for section in document.sections if section.level == 1]
    if h1 != [expected_title]:
        _add(
            violations,
            file,
            "BRIEF_MODE",
            "简报标题必须与锚定模式一致",
            expected=expected_title,
            actual="、".join(h1),
        )
    summary = _one_section(document, file, "60 秒 CEO 总结", 3, violations)
    _check_free_text(summary, file, violations)
    if summary is not None:
        paragraphs = [part for part in re.split(r"\n\s*\n", summary.body) if part.strip()]
        if len(paragraphs) != 1:
            _add(
                violations,
                file,
                "CEO_PARAGRAPH",
                "60 秒 CEO 总结必须是一个连续段落",
                record="60 秒 CEO 总结",
                expected="1 个段落",
                actual=str(len(paragraphs)),
            )
    findings = _records(document, 3, "关键发现")
    _expect_numbered_records(findings, file, "关键发现", 5, violations)
    for index, finding in enumerate(findings, start=1):
        _check_fields(
            finding,
            file,
            ("发现", "证据引用", "综合等级", "支持视角", "反对视角"),
            violations,
        )
        _check_enum(finding, "综合等级", GRADE_VALUES, file, violations)
        _check_references(finding, "证据引用", run_dir, file, violations)
        grade = normalize_value(finding.fields.get("综合等级", "")).strip("。")
        if mode == "anchored" and index <= 3 and grade not in {"A", "B"}:
            _add(
                violations,
                file,
                "FINDING_GRADE",
                f"anchored 模式关键发现 {index} 必须为 A/B",
                record=finding.title,
                field="综合等级",
                expected="A / B",
                actual=grade,
            )
        if mode == "未锚定模式" and grade != "C":
            _add(
                violations,
                file,
                "FINDING_GRADE",
                "未锚定模式五个关键发现必须统一为 C",
                record=finding.title,
                field="综合等级",
                expected="C",
                actual=grade,
            )
    for title in ("隐藏关联", "行动建议", "前沿问题"):
        _check_free_text(_one_section(document, file, title, 3, violations), file, violations)


def _validate_stage_4(
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
) -> None:
    _check_common("4", document, run_dir, file, violations)
    _check_exact_titles(
        document,
        3,
        [
            *(f"发现评审 {index}" for index in range(1, 6)),
            "最没把握的结论",
            "过重视角",
            "第 6 视角",
            "教授评分",
        ],
        file,
        violations,
    )
    reviews = _records(document, 3, "发现评审")
    _expect_numbered_records(reviews, file, "发现评审", 5, violations)
    for index, review in enumerate(reviews, start=1):
        _check_fields(
            review,
            file,
            ("发现引用", "可靠性分数", "推导依据", "所需验证信息"),
            violations,
        )
        expected_reference = f"03-brief.md#关键发现 {index}"
        actual = review.fields.get("发现引用", "").strip().strip("`")
        if actual != expected_reference:
            _add(
                violations,
                file,
                "REVIEW_REFERENCE",
                f"发现评审 {index} 必须引用对应关键发现",
                record=review.title,
                field="发现引用",
                expected=expected_reference,
                actual=actual,
            )
        _check_references(review, "发现引用", run_dir, file, violations)
        score = normalize_value(review.fields.get("可靠性分数", "")).strip("。")
        if not score.isdigit() or not 1 <= int(score) <= 10:
            _add(
                violations,
                file,
                "SCORE_RANGE",
                f"{review.title}可靠性分数必须为 1–10",
                record=review.title,
                field="可靠性分数",
                expected="1–10",
                actual=score,
            )
    sections = {
        "最没把握的结论": ("发现引用", "原因", "验证信息"),
        "过重视角": ("视角", "影响"),
        "第 6 视角": ("候选视角", "会改变的发现引用", "改变原因"),
        "教授评分": ("模拟评分", "主要修改意见"),
    }
    for title, fields in sections.items():
        section = _one_section(document, file, title, 3, violations)
        if section is not None:
            _check_fields(section, file, fields, violations)
    professor = document.find("教授评分", 3)
    if professor:
        score = normalize_value(professor[0].fields.get("模拟评分", "")).strip("。")
        if not score.isdigit() or not 1 <= int(score) <= 10:
            _add(
                violations,
                file,
                "SCORE_RANGE",
                "教授模拟评分必须为 1–10",
                record="教授评分",
                field="模拟评分",
                expected="1–10",
                actual=score,
            )
        note = professor[0].fields.get("主要修改意见", "")
        if "模拟" not in note:
            _add(
                violations,
                file,
                "SIMULATION_LABEL",
                "教授评分必须明确声明为模拟同行评审",
                record="教授评分",
                field="主要修改意见",
                expected="包含“模拟”",
                actual=note,
            )


def _validate_stage_5(
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
) -> None:
    _check_common("5", document, run_dir, file, violations)
    _check_exact_titles(
        document,
        3,
        [*(f"资源 {index}" for index in range(1, 6)), "被高估的坑", "一周路径"],
        file,
        violations,
    )
    resources = _records(document, 3, "资源")
    _expect_numbered_records(resources, file, "资源", 5, violations)
    for resource in resources:
        _check_fields(
            resource,
            file,
            (
                "资源名称",
                "资源类型",
                "来源 URL",
                "来源等级",
                "为什么比同类强",
                "画像适配理由",
                "使用方法",
                "预计耗时",
                "关键收获",
            ),
            violations,
        )
        _check_grade_and_url(resource, file, violations)
        grade = normalize_value(resource.fields.get("来源等级", "")).strip("。")
        if _state_value(run_dir, "锚定模式") == "未锚定模式" and grade != "C":
            _add(
                violations,
                file,
                "ANCHORING_GRADE",
                "未锚定模式下步骤 5 的资源必须统一标 C",
                record=resource.title,
                field="来源等级",
                expected="C",
                actual=grade,
            )
        if (
            grade == "C"
            and "未锚定" not in resource.fields.get("为什么比同类强", "")
        ):
            _add(
                violations,
                file,
                "UNANCHORED_COMPARISON",
                "C 级资源比较必须声明未锚定边界",
                record=resource.title,
                field="为什么比同类强",
                expected="包含“未锚定”",
                actual=resource.fields.get("为什么比同类强", ""),
            )
    pit_container = _one_section(document, file, "被高估的坑", 3, violations)
    pits = _records(document, 4, "坑点")
    _expect_numbered_records(pits, file, "坑点", (0, 3), violations)
    if not pits and pit_container is not None and not _is_reasoned_none(pit_container.body):
        _add(
            violations,
            file,
            "EMPTY_SET_REASON",
            "没有坑点时必须使用规范带理由空声明",
            record="被高估的坑",
            expected="无：<理由>",
            actual=pit_container.body,
        )
    for pit in pits:
        _check_fields(
            pit,
            file,
            ("对象或做法", "风险原因", "适用边界", "依据引用", "替代做法"),
            violations,
        )
        _check_references(pit, "依据引用", run_dir, file, violations)
    nodes = _records(document, 4, "行动节点")
    _expect_numbered_records(nodes, file, "行动节点", (5, 7), violations)
    coverage: set[int] = set()
    for node in nodes:
        _check_fields(
            node,
            file,
            ("时间", "资源引用", "具体动作", "完成证据"),
            violations,
        )
        time = node.fields.get("时间", "")
        if not re.search(r"第\s*[1-7](?:\s*[–-]\s*[1-7])?\s*天", time):
            _add(
                violations,
                file,
                "PATH_TIME",
                f"{node.title}时间必须落在第 1–7 天",
                record=node.title,
                field="时间",
                expected="第 1–7 天",
                actual=time,
            )
        coverage.update(int(value) for value in re.findall(r"资源\s*([1-5])", node.fields.get("资源引用", "")))
    if coverage != {1, 2, 3, 4, 5}:
        _add(
            violations,
            file,
            "RESOURCE_COVERAGE",
            "一周路径必须覆盖资源 1–5",
            record="一周路径",
            field="资源引用",
            expected="1,2,3,4,5",
            actual=",".join(map(str, sorted(coverage))),
        )


def _validate_stage_6(
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
) -> None:
    _check_common("6", document, run_dir, file, violations)
    _check_exact_titles(
        document,
        3,
        [*(f"级别 {index}" for index in range(1, 6)), "当前级与下一里程碑"],
        file,
        violations,
    )
    levels = _records(document, 3, "级别")
    _expect_numbered_records(levels, file, "级别", 5, violations)
    names = ("完全初学者", "基本理解", "实际使用者", "问题解决者", "自信的实践者")
    fields = (
        "级别名称",
        "应该理解",
        "掌握表现",
        "重点概念或技能",
        "里程碑",
        "动手练习或小型项目",
        "常见错误",
        "自测问题",
    )
    for index, level in enumerate(levels):
        _check_fields(level, file, fields, violations)
        actual = normalize_value(level.fields.get("级别名称", ""))
        if index < len(names) and actual != names[index]:
            _add(
                violations,
                file,
                "LEVEL_NAME",
                f"{level.title}名称必须使用固定阶梯",
                record=level.title,
                field="级别名称",
                expected=names[index],
                actual=actual,
            )
    current = _one_section(document, file, "当前级与下一里程碑", 3, violations)
    if current is not None:
        _check_fields(current, file, ("当前级别", "判断依据", "下一里程碑"), violations)


def _lesson_questions(section: Section) -> list[str]:
    match = re.search(r"(?ms)^#### 复习题\s*$\n(?P<body>.*)$", section.body)
    return _numbered_items(match.group("body")) if match else []


def _validate_stage_7(
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
    batch: int | None,
) -> None:
    _check_common(
        "7", document, run_dir, file, violations, check_takeaways=batch != 1
    )
    _check_exact_titles(
        document,
        3,
        ["核心 20%", *(f"第 {index} 课" for index in range(1, 11)), "终局小项目"],
        file,
        violations,
    )
    core = _one_section(document, file, "核心 20%", 3, violations)
    _check_free_text(core, file, violations)
    lessons = [section for section in document.sections if section.level == 3 and re.fullmatch(r"第 (?:[1-9]|10) 课", section.title)]
    if len(lessons) != 10:
        _add(
            violations,
            file,
            "LESSON_COUNT",
            f"课程数必须恰好为 10，实际 {len(lessons)}",
            record="十课计划",
            expected="10",
            actual=str(len(lessons)),
        )
    selected = lessons[:5] if batch == 1 else lessons
    for lesson in selected:
        _check_fields(
            lesson,
            file,
            ("课程名称", "学习目标", "关键概念", "动手练习", "推荐资源", "预期结果"),
            violations,
        )
        questions = _lesson_questions(lesson)
        if len(questions) != 5 or any(is_sentinel(question) for question in questions):
            _add(
                violations,
                file,
                "REVIEW_QUESTION_COUNT",
                f"{lesson.title}必须恰好有 5 道真实复习题",
                record=lesson.title,
                expected="5",
                actual=str(len(questions)),
            )
    if batch != 1:
        project = _one_section(document, file, "终局小项目", 3, violations)
        if project is not None:
            _check_fields(project, file, ("输入", "动作", "可检查输出", "完成标准"), violations)


def _table_rows(section: Section) -> list[list[str]]:
    rows = []
    for line in section.body.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells and not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                rows.append(cells)
    return rows


def _validate_stage_8(
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
    batch: int | None,
) -> None:
    _check_common(
        "8", document, run_dir, file, violations, check_takeaways=batch != 1
    )
    _check_exact_titles(
        document,
        3,
        ["覆盖计划", *(f"题目 {index}" for index in range(1, 11)), "终极挑战"],
        file,
        violations,
    )
    interaction_free = document.text.replace(
        "> 这是模式 A 备考材料，不填写用户回答、逐字引用、得分或答题记录。",
        "",
    )
    for forbidden in ("用户回答", "逐字引用", "得分", "答题记录", "施考记录"):
        if forbidden in interaction_free:
            _add(
                violations,
                file,
                "INTERACTION_LEAK",
                f"模式 A 题库不得包含真实答题/施考记录：{forbidden}",
                field=forbidden,
                expected="仅备考材料",
                actual="出现交互字段",
            )
    coverage = _one_section(document, file, "覆盖计划", 3, violations)
    expected_difficulty = {
        1: "初级", 2: "初级", 3: "初级", 4: "中级", 5: "中级", 6: "中级",
        7: "高级", 8: "高级", 9: "专家级", 10: "专家级",
    }
    if coverage is not None:
        rows = _table_rows(coverage)
        data = rows[1:] if rows and rows[0] == ["题号", "概念", "认知动作", "难度"] else []
        if len(data) != 10:
            _add(
                violations,
                file,
                "COVERAGE_COUNT",
                f"覆盖计划必须恰好 10 行，实际 {len(data)}",
                record="覆盖计划",
                expected="10",
                actual=str(len(data)),
            )
        selected_rows = data[:5] if batch == 1 else data
        for index, row in enumerate(selected_rows, start=1):
            if len(row) != 4 or row[0] != str(index) or row[-1] != expected_difficulty[index]:
                _add(
                    violations,
                    file,
                    "COVERAGE_ROW",
                    f"覆盖计划第 {index} 行题号或难度不符合映射",
                    record="覆盖计划",
                    expected=f"{index} / {expected_difficulty[index]}",
                    actual=" / ".join(row),
                )
            if len(row) == 4 and any(is_sentinel(value) for value in row[1:3]):
                _add(
                    violations,
                    file,
                    "SENTINEL_VALUE",
                    f"覆盖计划第 {index} 行仍有占位值",
                    record="覆盖计划",
                    expected="真实概念和认知动作",
                    actual=" / ".join(row),
                )
    questions = [section for section in document.sections if section.level == 3 and re.fullmatch(r"题目 (?:[1-9]|10)", section.title)]
    if len(questions) != 10:
        _add(
            violations,
            file,
            "QUESTION_COUNT",
            f"基础题必须恰好 10 道，实际 {len(questions)}",
            record="题库",
            expected="10",
            actual=str(len(questions)),
        )
    selected_questions = questions[:5] if batch == 1 else questions
    for index, question in enumerate(selected_questions, start=1):
        _check_fields(
            question,
            file,
            ("题干", "难度", "参考答案", "满分标准", "及格标准", "常见薄弱点"),
            violations,
        )
        actual = normalize_value(question.fields.get("难度", "")).strip("。")
        if actual != expected_difficulty[index]:
            _add(
                violations,
                file,
                "DIFFICULTY_MAP",
                f"题目 {index} 难度不符合固定映射",
                record=question.title,
                field="难度",
                expected=expected_difficulty[index],
                actual=actual,
            )
    if batch != 1:
        challenge = _one_section(document, file, "终极挑战", 3, violations)
        if challenge is not None:
            items = _numbered_items(challenge.body)
            if len(items) != 5 or any(is_sentinel(item) for item in items):
                _add(
                    violations,
                    file,
                    "CHALLENGE_COUNT",
                    f"终极挑战必须恰好 5 道无答案题，实际 {len(items)}",
                    record="终极挑战",
                    expected="5",
                    actual=str(len(items)),
                )
            if "答案" in challenge.body or "评分标准" in challenge.body:
                _add(
                    violations,
                    file,
                    "CHALLENGE_ANSWER",
                    "终极挑战禁止附答案或评分标准",
                    record="终极挑战",
                    expected="只含题干",
                    actual="含答案或评分标准",
                )
            extra = re.sub(
                r"(?m)^\s*\d+[.)、]\s+\S.*$", "", challenge.body
            ).strip()
            if extra:
                _add(
                    violations,
                    file,
                    "CHALLENGE_EXTRA",
                    "终极挑战章节只能包含五道编号题干",
                    record="终极挑战",
                    expected="仅五道题干",
                    actual=extra,
                )


def _validate_stage_9(
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
) -> None:
    _check_common("9", document, run_dir, file, violations)
    _check_exact_titles(
        document,
        3,
        ["12 岁版讲解", "复述检查点"],
        file,
        violations,
    )
    _check_exact_titles(
        document,
        4,
        [
            "生活例子 1",
            "生活例子 2",
            *(f"复述检查点 {index}" for index in range(1, len(_records(document, 4, "复述检查点")) + 1)),
        ],
        file,
        violations,
    )
    explanation = _one_section(document, file, "12 岁版讲解", 3, violations)
    _check_free_text(explanation, file, violations)
    examples = _records(document, 4, "生活例子")
    _expect_numbered_records(examples, file, "生活例子", 2, violations)
    for example in examples:
        _check_fields(example, file, ("场景", "对应关系", "例子边界"), violations)
    checkpoints = _records(document, 4, "复述检查点")
    _expect_numbered_records(checkpoints, file, "复述检查点", (3, 5), violations)
    for checkpoint in checkpoints:
        _check_fields(
            checkpoint,
            file,
            ("必须讲清", "可接受的简化", "错误或跳步信号", "对应重讲"),
            violations,
        )
    for forbidden in ("最终定义", "预判困惑点", "用户原话", "复述轮次", "得分"):
        if forbidden in document.text:
            _add(
                violations,
                file,
                "FEYNMAN_PREJUDGMENT",
                f"费曼备教材料不得生成：{forbidden}",
                field=forbidden,
                expected="留待真实复述循环",
                actual="出现在步骤 9",
            )


def _validate_stage_10(
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
) -> None:
    _check_common("10", document, run_dir, file, violations)
    canonical = (
        "一句大白话定义",
        "核心要点",
        "实际应用场景",
        "易错与易混",
        "上场前检查清单",
        "快问快答",
    )
    _check_exact_titles(document, 3, list(canonical), file, violations)
    sections = {
        title: _one_section(document, file, title, 3, violations) for title in canonical
    }
    for section in sections.values():
        _check_free_text(section, file, violations)
    scenes = _numbered_items(sections["实际应用场景"].body) if sections["实际应用场景"] else []
    if not 3 <= len(scenes) <= 5 or any(is_sentinel(scene) for scene in scenes):
        _add(
            violations,
            file,
            "SCENE_COUNT",
            f"实际应用场景必须为 3–5 个真实情境，实际 {len(scenes)}",
            record="实际应用场景",
            expected="3–5",
            actual=str(len(scenes)),
        )
    qa = sections["快问快答"]
    questions = _numbered_items(qa.body) if qa else []
    answers = re.findall(r"(?m)^\s+-\s+\*\*答案：\*\*\s*(\S.*)$", qa.body if qa else "")
    if len(questions) != 5 or len(answers) != 5 or any(is_sentinel(answer) for answer in answers):
        _add(
            violations,
            file,
            "QA_COUNT",
            f"快问快答必须恰好 5 题且每题一个答案，实际 {len(questions)} 题/{len(answers)} 答案",
            record="快问快答",
            expected="5 题 / 5 答案",
            actual=f"{len(questions)} / {len(answers)}",
        )


def _validate_exam_record(
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
) -> None:
    _check_execution("exam-record", document, file, violations)
    _check_upstreams("exam-record", document, run_dir, file, violations)
    state = _one_section(document, file, "会话状态", 2, violations)
    pending = _one_section(document, file, "待回答", 2, violations)
    completed = _one_section(document, file, "完成记录", 2, violations)
    summary = _one_section(document, file, "最终总结", 2, violations)
    if state is not None:
        _check_fields(state, file, ("当前游标", "待回答项", "结束状态"), violations)
        cursor_text = normalize_value(state.fields.get("当前游标", "")).strip("。")
        cursor = int(cursor_text) if cursor_text.isdigit() else -1
        if not 0 <= cursor <= 10:
            _add(
                violations,
                file,
                "EXAM_CURSOR",
                "当前游标必须为完成的基础题数 0–10",
                record="会话状态",
                field="当前游标",
                expected="0–10",
                actual=cursor_text,
            )
        _check_enum(state, "结束状态", {"进行中", "已完成"}, file, violations)
    else:
        cursor = -1
    if pending is not None:
        _check_fields(pending, file, ("所属题号", "类型", "实际提问"), violations)
        _check_enum(pending, "类型", {"基础题", "追问", "挑战"}, file, violations)
    transactions = [
        section
        for section in document.sections
        if section.level == 3
        and re.fullmatch(r"(?:基础题|追问|挑战) [1-9]\d*(?:\.[1-9]\d*)?", section.title)
    ]
    base_count = sum(section.title.startswith("基础题 ") for section in transactions)
    if cursor != -1 and cursor != base_count:
        _add(
            violations,
            file,
            "EXAM_CURSOR",
            "当前游标必须等于已完成基础题事务数；追问和挑战不增加游标",
            record="会话状态",
            field="当前游标",
            expected=str(base_count),
            actual=str(cursor),
        )
    for transaction in transactions:
        _check_fields(
            transaction,
            file,
            ("难度", "实际提问", "用户回答逐字引用", "得分", "答对处", "确切差距", "简语重讲"),
            violations,
        )
    if completed is not None and not transactions and not _is_reasoned_none(completed.body):
        _add(
            violations,
            file,
            "EMPTY_SET_REASON",
            "尚无完成记录时必须使用带理由空声明",
            record="完成记录",
            expected="无：<理由>",
            actual=completed.body,
        )
    if summary is not None:
        if cursor == 10 and _is_reasoned_none(summary.body):
            _add(
                violations,
                file,
                "EXAM_SUMMARY",
                "十道基础题完成后必须生成最终总结",
                record="最终总结",
                expected="真实总结",
                actual=summary.body,
            )
        if 0 <= cursor < 10 and not _is_reasoned_none(summary.body):
            _add(
                violations,
                file,
                "EXAM_SUMMARY",
                "十道基础题完成前不得生成最终总结",
                record="最终总结",
                expected="无：<理由>",
                actual=summary.body,
            )


def _validate_feynman_record(
    document: MarkdownDocument,
    run_dir: Path,
    file: str,
    violations: list[ContractViolation],
) -> None:
    _check_execution("feynman-record", document, file, violations)
    _check_upstreams("feynman-record", document, run_dir, file, violations)
    state = _one_section(document, file, "会话状态", 2, violations)
    pending = _one_section(document, file, "待回答", 2, violations)
    completed = _one_section(document, file, "完成轮次", 2, violations)
    ending = _one_section(document, file, "结束依据", 2, violations)
    if state is not None:
        _check_fields(state, file, ("当前概念", "已完成轮次", "待回答项", "结束状态"), violations)
        count_text = normalize_value(state.fields.get("已完成轮次", "")).strip("。")
        count = int(count_text) if count_text.isdigit() else -1
        _check_enum(state, "结束状态", {"进行中", "已讲清", "仍未通过"}, file, violations)
    else:
        count = -1
    if pending is not None:
        _check_fields(pending, file, ("本轮教学", "复述邀请"), violations)
    rounds = [
        section
        for section in document.sections
        if section.level == 3 and re.fullmatch(r"第 [1-9]\d* 轮", section.title)
    ]
    if count != -1 and count != len(rounds):
        _add(
            violations,
            file,
            "FEYNMAN_ROUND_COUNT",
            "已完成轮次必须与完成记录一致",
            record="会话状态",
            field="已完成轮次",
            expected=str(len(rounds)),
            actual=str(count),
        )
    for round_record in rounds:
        _check_fields(
            round_record,
            file,
            ("本轮教学", "复述邀请", "用户逐字复述", "含糊或跳步处", "只重教缺口", "下一步"),
            violations,
        )
    if completed is not None and not rounds and not _is_reasoned_none(completed.body):
        _add(
            violations,
            file,
            "EMPTY_SET_REASON",
            "尚无完成轮次时必须使用带理由空声明",
            record="完成轮次",
            expected="无：<理由>",
            actual=completed.body,
        )
    status = normalize_value(state.fields.get("结束状态", "")).strip("。") if state else ""
    if ending is not None and status == "进行中" and not _is_reasoned_none(ending.body):
        _add(
            violations,
            file,
            "FEYNMAN_ENDING",
            "进行中会话的结束依据必须明确为空",
            record="结束依据",
            expected="无：<理由>",
            actual=ending.body,
        )
    if status == "已讲清":
        if not rounds or "用户逐字复述" not in ending.body:
            _add(
                violations,
                file,
                "FEYNMAN_ENDING",
                "已讲清必须在结束依据引用最后一轮用户逐字复述",
                record="结束依据",
                expected="引用最后一轮用户逐字复述",
                actual=ending.body if ending else "缺失",
            )


def _html_violation(file: str, message: str) -> ContractViolation:
    return _violation(file, "HTML_CONTRACT", message)


def validate_html(run_dir: Path) -> list[ContractViolation]:
    paths = sorted(run_dir.glob("*.html"))
    if not paths:
        return [_html_violation("*.html", "运行目录缺少 HTML 视图")]
    violations: list[ContractViolation] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        name = path.name
        if "{{" in text or "}}" in text:
            violations.append(_html_violation(name, f"HTML 残留占位符：{name}"))
        if not re.search(r"<noscript\b[^>]*>", text, re.IGNORECASE | re.DOTALL):
            violations.append(_html_violation(name, f"HTML 缺少 noscript 降级：{name}"))
        if not re.search(r"交互施考(?:\s*[:：])?\s*(?:未进行|已完成\s*\d+\s*题)", text):
            violations.append(_html_violation(name, f"HTML 缺少施考状态行：{name}"))
        references = re.findall(
            r"(?:href|src)=[\"'](template\.(?:css|js))[\"']", text, re.IGNORECASE
        )
        if references:
            if references != ["template.css", "template.js"]:
                violations.append(
                    _html_violation(name, f"HTML 固定资源引用必须各为一次 template.css 和 template.js：{name}")
                )
            for reference in set(references):
                if not (run_dir / reference).is_file():
                    violations.append(
                        _html_violation(name, f"HTML 固定资源必须位于同目录且可读取：{reference}（{name}）")
                    )
        template_based = (
            "template.css" in references
            or 'data-learn-loop="template.css"' in text
            or 'data-od-id="learning-workbench"' in text
        )
        if template_based:
            run_id = re.search(r"<body\b[^>]*\bdata-run-id=[\"']([^\"']+)[\"']", text, re.I | re.S)
            if not run_id or not run_id.group(1).strip():
                violations.append(_html_violation(name, f"HTML 工作台缺少非空 data-run-id：{name}"))
            od_ids = re.findall(r"\bdata-od-id=[\"']([^\"']+)[\"']", text)
            for required in (
                "learning-directory",
                "learning-workbench",
                "learning-map",
                "chapter-context",
            ):
                if required not in od_ids:
                    violations.append(_html_violation(name, f"HTML 工作台缺少关键区域 data-od-id={required}：{name}"))
            duplicates = sorted({value for value in od_ids if od_ids.count(value) > 1})
            if duplicates:
                violations.append(_html_violation(name, f"HTML 存在重复 data-od-id：{name}"))
            views = re.findall(
                r"<section\b[^>]*\bclass=[\"'][^\"']*\bview\b[^\"']*[\"'][^>]*>",
                text,
                re.IGNORECASE,
            )
            for view in views:
                view_id = re.search(r"\bid=[\"']([^\"']+)[\"']", view)
                label = view_id.group(1) if view_id else "未知视图"
                if not re.search(r"\bdata-od-id=[\"'][^\"']+[\"']", view):
                    violations.append(
                        _html_violation(name, f"HTML 视图缺少 data-od-id：{name}（{label}）")
                    )
                if not re.search(r"\bdata-module=[\"'][^\"']+[\"']", view):
                    violations.append(
                        _html_violation(name, f"HTML 视图缺少 data-module：{name}（{label}）")
                    )
            for view_id, command in (("view-8", "考我"), ("view-9", "给我讲")):
                if f'id="{view_id}"' in text and f'data-workflow-command="{command}"' not in text:
                    violations.append(
                        _html_violation(name, f"HTML {view_id} 缺少对话交接命令“{command}”：{name}")
                    )
        title = re.findall(
            r"<h1\b[^>]*data-od-id=[\"']topic-title[\"'][^>]*>(.*?)</h1>",
            text,
            re.I | re.S,
        )
        if len(title) > 1:
            violations.append(_html_violation(name, f"HTML 总览主标题必须恰好有一个 topic-title h1：{name}"))
        if title and not re.search(r"<span\b[^>]*class=[\"'][^\"']*\bh1-sub\b[^\"']*[\"'][^>]*>\s*\S", title[0], re.I | re.S):
            violations.append(_html_violation(name, f"HTML 总览主标题缺少非空 h1-sub 副标题：{name}"))
        ids = re.findall(r"\sid=[\"']([^\"']+)[\"']", text)
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        if duplicates:
            violations.append(_html_violation(name, f"HTML 存在重复 id：{name}"))
        if re.search(r"<details[^>]*class=[\"'][^\"']*evidence[^\"']*[\"'][^>]*\bopen\b", text, re.S):
            violations.append(_html_violation(name, f"HTML 取证折叠不得默认展开：{name}"))
        stripped = re.sub(r"<div class=[\"']flash-answer[\"'].*?</div>", "", text, flags=re.S)
        if re.search(r"(?:参考答案|评分标准)\s*[:：]", stripped):
            violations.append(_html_violation(name, f"HTML 答案未折叠：{name}"))
        if text.count("本步提炼") > 10:
            violations.append(_html_violation(name, f"HTML「本步提炼」渲染次数超过 10：{name}"))
    return violations


VALIDATORS = {
    "0": _validate_stage_0,
    "1": _validate_stage_1,
    "2": _validate_stage_2,
    "3": _validate_stage_3,
    "4": _validate_stage_4,
    "5": _validate_stage_5,
    "6": _validate_stage_6,
    "9": _validate_stage_9,
    "10": _validate_stage_10,
    "exam-record": _validate_exam_record,
    "feynman-record": _validate_feynman_record,
}


def validate_one(
    stage: str, run_dir: Path, batch: int | None = None
) -> list[ContractViolation]:
    run_dir = Path(run_dir).expanduser().resolve()
    if stage == "html":
        return validate_html(run_dir)
    if stage not in STAGE_FILES:
        raise ValueError(f"未知阶段：{stage}")
    if batch is not None and (stage not in {"7", "8"} or batch not in {1, 2}):
        raise ValueError("只有阶段 7/8 接受 batch=1|2")
    file = STAGE_FILES[stage]
    violations: list[ContractViolation] = []
    document = _read_document(run_dir / file, violations)
    if document is None:
        return violations
    if stage == "7":
        _validate_stage_7(document, run_dir, file, violations, batch)
    elif stage == "8":
        _validate_stage_8(document, run_dir, file, violations, batch)
    else:
        VALIDATORS[stage](document, run_dir, file, violations)
    return violations


def validate_role(role: str, run_dir: Path) -> list[ContractViolation]:
    if role not in ROLES:
        raise ValueError(f"未知角色：{role}")
    violations: list[ContractViolation] = []
    _validate_role_file(role, Path(run_dir).expanduser().resolve(), violations)
    return violations


def validate_all(run_dir: Path, include_html: bool = True) -> dict[str, list[ContractViolation]]:
    stages = [*map(str, range(11))]
    if include_html:
        stages.append("html")
    for optional in ("exam-record", "feynman-record"):
        if (Path(run_dir) / STAGE_FILES[optional]).is_file():
            stages.append(optional)
    return {stage: validate_one(stage, run_dir) for stage in stages}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument(
        "--stage",
        choices=[*map(str, range(11)), "exam-record", "feynman-record", "html"],
    )
    parser.add_argument("--role", choices=ROLES)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--batch", type=int, choices=(1, 2))
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if sum((bool(args.stage), bool(args.role), args.all)) != 1:
        print("必须且只能选择 --stage、--role 或 --all", file=sys.stderr)
        return 2
    if args.batch is not None and args.stage not in {"7", "8"}:
        print("--batch 仅适用于阶段 7/8", file=sys.stderr)
        return 2
    run_dir = Path(args.run_dir).expanduser().resolve()
    if args.all:
        raw = validate_all(run_dir)
        stages = list(raw)
    elif args.role:
        key = f"role:{args.role}"
        stages = [key]
        raw = {key: validate_role(args.role, run_dir)}
    else:
        stages = [args.stage]
        raw = {args.stage: validate_one(args.stage, run_dir, args.batch)}
    violations = {
        stage: [item.to_dict() for item in items]
        for stage, items in raw.items()
        if items
    }
    report = {
        "ok": not violations,
        "run_dir": str(run_dir),
        "stages": stages,
        "violations": violations,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("learn-loop validation: " + ("OK" if report["ok"] else "FAIL"))
        for stage in stages:
            items = violations.get(stage, [])
            if not items:
                print(f"- stage {stage}: OK")
            else:
                print(f"- stage {stage}:")
                for item in items:
                    print(f"  - [{item['code']}] {item['message']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
