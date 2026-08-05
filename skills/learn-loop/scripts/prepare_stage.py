#!/usr/bin/env python3
"""Prepare one Learn Loop stage without disclosing future-stage context."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from contract_io import (
    ContractViolation,
    append_disclosure_items,
    atomic_write,
    is_sentinel,
    read_run_state,
    update_run_state,
)


STAGE_FILES = {
    0: "run-state.md",
    1: "01-perspectives.md",
    2: "02-conflicts.md",
    3: "03-brief.md",
    4: "04-review.md",
    5: "05-resources.md",
    6: "06-ladder.md",
    7: "07-sprint.md",
    8: "08-exam-bank.md",
    9: "09-feynman-notes.md",
    10: "10-cheatsheet.md",
}
CONTRACT_FILES = {
    stage: ("00-run-state.md" if stage == 0 else filename)
    for stage, filename in STAGE_FILES.items()
}
ROLE_FILES = {
    "实践者": "practitioner.md",
    "学者": "scholar.md",
    "怀疑者": "skeptic.md",
    "经济学家": "economist.md",
    "历史学家": "historian.md",
}
ROLE_NUMBERS = {role: index for index, role in enumerate(ROLE_FILES, start=1)}
PROMPTS_PATH = SKILL_ROOT / "reference" / "original-prompts.md"


def extract_original_prompt(stage: int, prompts_text: str) -> str:
    """Return the exact, contiguous source slice for one original prompt."""
    if stage not in range(1, 11):
        raise ValueError(f"原始提示词阶段必须为 1–10，实际 {stage}")
    start = re.search(rf"(?m)^## 第 {stage} 步(?:\s|·).*$", prompts_text)
    if start is None:
        raise ValueError(f"找不到第 {stage} 步原始提示词")
    following = re.search(r"(?m)^## 第 \d+ 步(?:\s|·).*$", prompts_text[start.end() :])
    end = start.end() + following.start() if following else len(prompts_text)
    return prompts_text[start.start() : end].rstrip() + "\n"


def extract_role_prompt(stage_excerpt: str, role: str) -> str:
    """Return only the assigned persona block from the Step 1 source slice."""
    if role not in ROLE_NUMBERS:
        raise ValueError(f"未知视角：{role}")
    number = ROLE_NUMBERS[role]
    start = re.search(rf"(?m)^{number}\. {re.escape(role)}：.*$", stage_excerpt)
    if start is None:
        raise ValueError(f"原始提示词中找不到角色：{role}")
    following = re.search(
        r"(?m)^(?:[1-5]\. (?:实践者|学者|怀疑者|经济学家|历史学家)：|每个视角请给我：)",
        stage_excerpt[start.end() :],
    )
    end = start.end() + following.start() if following else len(stage_excerpt)
    return stage_excerpt[start.start() : end].rstrip() + "\n"


def _render(template: str, replacements: dict[str, str]) -> str:
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    unresolved = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", rendered)))
    if unresolved:
        raise ValueError("任务包仍有未解析占位符：" + "、".join(unresolved))
    return rendered.rstrip() + "\n"


def _role_guidance(role: str) -> str:
    discipline = (SKILL_ROOT / "reference" / "perspectives.md").read_text(
        encoding="utf-8"
    )
    row = re.search(rf"(?m)^\| {re.escape(role)} \|.*\|$", discipline)
    if row is None:
        raise ValueError(f"角色纪律中找不到视角：{role}")
    cells = [cell.strip() for cell in row.group(0).strip("|").split("|")]
    return (
        f"- **优先渠道：** {cells[1]}\n"
        f"- **重点追问：** {cells[2]}\n"
        "- **隔离边界：** 不读取其他角色产物；失败检索同样保留。"
    )


def _grading_rules() -> str:
    return (
        "- `A`：有可解析 URL，且来源直接支持对应主张。\n"
        "- `B`：有可解析 URL，但属于转述、间接或部分支持。\n"
        "- `C`：模型内生或尚未验证；来源 URL 写“无”，并填写未锚定原因。\n"
        "- 检索不可用或本轮未实测时不得凭记忆补造 URL。"
    )


def _materialize_stage_template(stage: int, state: dict[str, str]) -> str:
    text = (SKILL_ROOT / "templates" / STAGE_FILES[stage]).read_text(
        encoding="utf-8"
    )
    if stage != 3:
        return text
    mode = state.get("锚定模式", "")
    if mode == "anchored":
        kind = "综合简报"
        notice = "本轮已锚定来源；前三个关键发现必须使用 A/B 级来源。"
    elif mode == "未锚定模式":
        kind = "假设简报"
        notice = "模型先验·待验证：本轮未锚定，五个关键发现统一标 C，不补造 URL。"
    else:
        raise ValueError(f"锚定模式必须为 anchored / 未锚定模式，实际：{mode}")
    return _render(text, {"BRIEF_KIND": kind, "ANCHORING_NOTICE": notice})


def _write_once(path: Path, text: str) -> bool:
    """Write missing content; accept identical reruns and reject overwrites."""
    normalized = text.rstrip() + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != normalized:
            raise ValueError(f"拒绝覆盖已有且内容不同的文件：{path}")
        return False
    atomic_write(path, normalized)
    return True


def _read_state_if_available(run_dir: Path) -> dict[str, str]:
    state_path = run_dir / "run-state.md"
    return read_run_state(state_path) if state_path.is_file() else {}


def _source_paths_for_stage(stage: int) -> list[str]:
    contract = SKILL_ROOT / "reference" / "stages" / CONTRACT_FILES[stage]
    if not contract.is_file():
        raise ValueError(f"阶段契约不存在：{contract}")
    sources = [
        str(contract.relative_to(SKILL_ROOT)),
        f"templates/{STAGE_FILES[stage]}",
    ]
    if stage:
        sources.insert(0, "reference/original-prompts.md")
    return sources


def _contract_path(stage: int) -> Path:
    return SKILL_ROOT / "reference" / "stages" / CONTRACT_FILES[stage]


def _upstream_paths(stage: int, template_text: str) -> list[str]:
    if stage == 0:
        return []
    match = re.search(
        r"(?ms)^## 消费上游\s*$\n(?P<body>.*?)(?=^##\s|\Z)", template_text
    )
    if match is None:
        raise ValueError("输出范本缺少消费上游章节")
    paths = []
    for reference in re.findall(r"`([^`]+\.md)`", match.group("body")):
        if reference not in paths:
            paths.append(reference)
    return paths


def _context_path(run_dir: Path, stage: int, batch: int | None) -> Path:
    suffix = f"-batch-{batch}" if batch is not None else ""
    return run_dir / "context" / f"stage-{stage:02d}{suffix}.md"


def _upstream_snapshot(relative: str, path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if relative == "run-state.md":
        text = text.split("\n## 模式 A 进度\n", 1)[0]
    return text.rstrip()


def _completion_command(run_dir: Path, stage: int, batch: int | None) -> str:
    batch_arg = f" --batch {batch}" if batch is not None else ""
    return (
        "python3 <skill-root>/scripts/validate_stage.py"
        f" --run-dir {run_dir} --stage {stage}{batch_arg} --json"
    )


def build_stage_context(
    run_dir: Path, stage: int, batch: int | None = None
) -> tuple[Path, list[str]]:
    """Build a self-contained parent packet for only the requested stage."""
    state = _read_state_if_available(run_dir)
    template_text = _materialize_stage_template(stage, state)
    contract_path = _contract_path(stage)
    contract_text = contract_path.read_text(encoding="utf-8")
    disclosed = _source_paths_for_stage(stage)

    sections = [
        f"# 第 {stage} 步执行上下文" + (f" · 批次 {batch}" if batch else ""),
        "",
    ]
    if stage:
        original = extract_original_prompt(
            stage, PROMPTS_PATH.read_text(encoding="utf-8")
        )
        sections.extend(
            [
                "## 原始提示词逐字片段",
                "",
                f"> 来源：`{PROMPTS_PATH.relative_to(SKILL_ROOT)}`；以下是连续原文切片。",
                "",
                original.rstrip(),
                "",
            ]
        )
    sections.extend(
        [
            "## 当前阶段契约",
            "",
            f"> 来源：`{contract_path.relative_to(SKILL_ROOT)}`",
            "",
            contract_text.rstrip(),
            "",
            "## 当前输出范本",
            "",
            f"> 来源：`templates/{STAGE_FILES[stage]}`",
            "",
            template_text.rstrip(),
            "",
            "## 允许消费的上游快照",
            "",
        ]
    )
    upstreams = _upstream_paths(stage, template_text)
    if not upstreams:
        sections.extend(["无运行目录上游。", ""])
    for relative in upstreams:
        path = run_dir / relative
        if not path.is_file():
            raise ValueError(f"允许消费的上游不存在：{relative}")
        if stage == 1 and relative.startswith("perspectives/"):
            sections.extend(
                [
                    f"### `{relative}`",
                    "",
                    "父级屏障后读取该路径的实际正式角色文件；准备阶段不快照空范本。",
                    "",
                ]
            )
            disclosed.append(relative)
            continue
        sections.extend([f"### `{relative}`", "", _upstream_snapshot(relative, path), ""])
        disclosed.append(relative)
    sections.extend(
        [
            "## 交付边界",
            "",
            f"- **唯一阶段输出：** `{STAGE_FILES[stage]}`",
            f"- **完成校验：** `{_completion_command(run_dir, stage, batch)}`",
        ]
    )
    if stage == 1:
        expected = "、".join(f"`perspectives/{name}`" for name in ROLE_FILES.values())
        sections.extend(
            [
                f"- **父级屏障：** {expected} 必须逐份通过角色校验后，才可汇总。",
                "- **汇总规则：** 核心字段逐字抽取；完整角色分析保留在角色文件中。",
            ]
        )
    context_path = _context_path(run_dir, stage, batch)
    _write_once(context_path, "\n".join(sections))
    return context_path, disclosed


def build_role_packets(run_dir: Path, state: dict[str, str]) -> list[Path]:
    """Create retained role outputs and five isolated Step 1 task packets."""
    source = PROMPTS_PATH.read_text(encoding="utf-8")
    stage_excerpt = extract_original_prompt(1, source)
    role_template = (SKILL_ROOT / "templates" / "perspective-role.md").read_text(
        encoding="utf-8"
    )
    task_template = (SKILL_ROOT / "templates" / "perspective-task.md").read_text(
        encoding="utf-8"
    )
    packets = []
    for role, filename in ROLE_FILES.items():
        output_relative = f"perspectives/{filename}"
        output_path = run_dir / output_relative
        output_text = _render(role_template, {"ROLE": role})
        if not output_path.exists():
            atomic_write(output_path, output_text)

        packet_text = _render(
            task_template,
            {
                "ROLE": role,
                "OUTPUT_PATH": output_relative,
                "TOPIC": state.get("主题", ""),
                "ANCHORING_MODE": state.get("锚定模式", ""),
                "INDEPENDENCE_TIER": state.get("独立性档位", ""),
                "PERSONA_GUIDANCE": _role_guidance(role),
                "ORIGINAL_PROMPT": extract_role_prompt(stage_excerpt, role).rstrip(),
                "GRADING_RULES": _grading_rules(),
                "ROLE_TEMPLATE": output_text.rstrip(),
                "VALIDATE_COMMAND": (
                    f"python3 {SKILL_ROOT / 'scripts' / 'validate_stage.py'} "
                    f"--run-dir {run_dir} --role {role} --json"
                ),
            },
        )
        packet_path = run_dir / "context" / "roles" / f"{Path(filename).stem}-task.md"
        _write_once(packet_path, packet_text)
        packets.append(packet_path)
    return packets


def _prior_stage_violations(run_dir: Path, stage: int) -> list:
    if stage == 0:
        return []
    import validate_stage

    return validate_stage.validate_one(str(stage - 1), run_dir)


def _state_gate_violations(
    run_dir: Path, stage: int, batch: int | None
) -> list[ContractViolation]:
    state_path = run_dir / "run-state.md"
    if not state_path.is_file():
        return [] if stage == 0 else [
            ContractViolation(
                code="STAGE_GATE",
                file="run-state.md",
                record="模式 A 进度",
                field="当前阶段",
                expected="0",
                actual="文件不存在",
                message="阶段 0 尚未准备，不能进入后续阶段",
            )
        ]
    state = read_run_state(state_path)
    actual = state.get("当前阶段", "").strip().strip("。")
    if stage == 0:
        allowed = {"0"}
    elif batch == 2:
        allowed = {str(stage)}
    else:
        allowed = {str(stage - 1), str(stage)}
    if actual in allowed:
        return []
    return [
        ContractViolation(
            code="STAGE_GATE",
            file="run-state.md",
            record="模式 A 进度",
            field="当前阶段",
            expected=" / ".join(sorted(allowed, key=int)),
            actual=actual or "缺失",
            message=(
                f"当前游标为 {actual or '缺失'}，不能准备阶段 {stage}"
                + (f" 批次 {batch}" if batch else "")
            ),
        )
    ]


def _run_state_contract_violations(run_dir: Path, stage: int) -> list:
    if stage <= 1:
        return []
    import validate_stage

    return validate_stage.validate_one("0", run_dir)


def _batch_gate_violations(
    run_dir: Path, stage: int, batch: int | None
) -> list:
    if stage not in {7, 8} or batch != 2:
        return []
    import validate_stage

    return validate_stage.validate_one(str(stage), run_dir, batch=1)


def _initialize_known_state(run_dir: Path) -> None:
    path = run_dir / "run-state.md"
    state = read_run_state(path)
    digest = hashlib.sha256(PROMPTS_PATH.read_bytes()).hexdigest()
    candidates = {
        "运行 ID": run_dir.name,
        "创建时间": datetime.now().astimezone().isoformat(timespec="seconds"),
        "运行目录": str(run_dir.resolve()),
        "原始提示词 SHA-256": digest,
    }
    updates = {
        label: value
        for label, value in candidates.items()
        if label in state and is_sentinel(state[label])
    }
    if updates:
        update_run_state(path, updates)


def _record_disclosure(
    run_dir: Path, stage: int, disclosed: list[str], context_path: Path
) -> None:
    state_path = run_dir / "run-state.md"
    state_text = state_path.read_text(encoding="utf-8")
    heading = f"### 阶段 {stage}"
    if heading in state_text:
        append_disclosure_items(
            state_path,
            stage,
            [*disclosed, str(context_path.relative_to(run_dir))],
        )
        return
    completed = "无" if stage == 0 else f"0–{stage - 1}"
    update_run_state(
        state_path,
        {
            "当前阶段": str(stage),
            "已完成阶段": completed,
            "生成状态": "进行中",
        },
        {
            "stage": stage,
            "prepared_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "items": [*disclosed, str(context_path.relative_to(run_dir))],
        },
    )


def prepare_stage(run_dir: Path, stage: int, batch: int | None = None) -> dict:
    """Gate and prepare one stage. Existing populated outputs are never overwritten."""
    run_dir = Path(run_dir).expanduser().resolve()
    if stage not in STAGE_FILES:
        raise ValueError(f"阶段必须为 0–10，实际 {stage}")
    if batch is not None and (stage not in {7, 8} or batch not in {1, 2}):
        raise ValueError("只有阶段 7/8 接受 --batch 1|2")
    if stage in {7, 8} and batch is None:
        raise ValueError("阶段 7/8 必须显式指定 --batch 1|2")

    run_dir.mkdir(parents=True, exist_ok=True)
    violations = _state_gate_violations(run_dir, stage, batch)
    violations.extend(_run_state_contract_violations(run_dir, stage))
    violations.extend(_prior_stage_violations(run_dir, stage))
    violations.extend(_batch_gate_violations(run_dir, stage, batch))
    if violations:
        return {
            "ok": False,
            "stage": stage,
            "batch": batch,
            "output": str(run_dir / STAGE_FILES[stage]),
            "context": None,
            "disclosed": [],
            "violations": [
                item.to_dict() if hasattr(item, "to_dict") else str(item)
                for item in violations
            ],
        }

    output_path = run_dir / STAGE_FILES[stage]
    if stage == 0:
        if not output_path.exists():
            atomic_write(
                output_path,
                (SKILL_ROOT / "templates" / STAGE_FILES[stage]).read_text(
                    encoding="utf-8"
                ),
            )
        _initialize_known_state(run_dir)
    elif not output_path.exists():
        atomic_write(output_path, _materialize_stage_template(stage, read_run_state(run_dir / "run-state.md")))

    role_packets = []
    if stage == 1:
        role_packets = build_role_packets(
            run_dir, read_run_state(run_dir / "run-state.md")
        )
    context_path, disclosed = build_stage_context(run_dir, stage, batch)
    if role_packets:
        disclosed.extend(str(path.relative_to(run_dir)) for path in role_packets)
    _record_disclosure(run_dir, stage, disclosed, context_path)
    return {
        "ok": True,
        "stage": stage,
        "batch": batch,
        "output": str(output_path),
        "context": str(context_path),
        "disclosed": disclosed,
        "violations": [],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--stage", required=True, type=int, choices=range(0, 11))
    parser.add_argument("--batch", type=int, choices=(1, 2))
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = prepare_stage(Path(args.run_dir), args.stage, args.batch)
    except (OSError, ValueError) as error:
        report = {
            "ok": False,
            "stage": args.stage,
            "batch": args.batch,
            "output": None,
            "context": None,
            "disclosed": [],
            "violations": [str(error)],
        }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("准备完成" if report["ok"] else "准备失败")
        for violation in report["violations"]:
            print(f"- {violation}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
