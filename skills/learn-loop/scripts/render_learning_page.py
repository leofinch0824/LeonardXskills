#!/usr/bin/env python3
"""Build the offline Learn Loop HTML view from validated Markdown facts."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from markdown_it import MarkdownIt


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import render_template
import validate_stage
from contract_io import MarkdownDocument, Section, parse_document, parse_upstream_table, resolve_reference
from prepare_stage import extract_original_prompt


STAGE_FILES = {
    stage: validate_stage.STAGE_FILES[str(stage)] for stage in range(1, 11)
}
STAGE_TITLES = {
    1: "五视角独立取证",
    2: "矛盾图谱",
    3: "综合简报",
    4: "同行评审",
    5: "资源筛选",
    6: "学习阶梯",
    7: "两小时核心 20%",
    8: "主动回忆题库",
    9: "费曼备教材料",
    10: "五分钟速查表",
}
STAGE_PURPOSES = {
    1: "先保留五个隔离视角的完整取证，再比较它们。",
    2: "分清真实冲突、共识与尚待验证的盲区。",
    3: "把证据压缩为可靠性有序、可行动的结论。",
    4: "逐项复查关键发现的可靠性与缺失信息。",
    5: "只留下会实际使用的资源和一周行动路径。",
    6: "定位当前能力级别和下一项可观察里程碑。",
    7: "用十课覆盖最高杠杆的概念、练习和项目。",
    8: "用主动回忆题库暴露理解边界。",
    9: "准备简单讲解，让真实复述决定需要重教什么。",
    10: "在上场前五分钟快速恢复关键定义、场景与检查项。",
}
ROLES = ("实践者", "学者", "怀疑者", "经济学家", "历史学家")


MARKDOWN = MarkdownIt(
    "commonmark",
    {"html": False, "linkify": False, "typographer": False},
).enable("table")


def _linkify_source_urls(text: str) -> str:
    expression = re.compile(
        r"(?m)(- \*\*来源 URL：\*\*\s*)(https?://[^\s。]+)(。?)$"
    )

    def replacement(match: re.Match) -> str:
        url = match.group(2)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"拒绝渲染不安全来源 URL：{url}")
        return f"{match.group(1)}[{url}]({url}){match.group(3)}"

    return expression.sub(replacement, text)


def render_markdown(text: str) -> str:
    """Render deterministic CommonMark with raw HTML disabled."""
    html = MARKDOWN.render(_linkify_source_urls(text))

    def wrap_table(match: re.Match) -> str:
        return f'<div class="table-wrap">{match.group(0)}</div>'

    return re.sub(r"<table>.*?</table>", wrap_table, html, flags=re.S)


def _document(run_dir: Path, stage: int) -> MarkdownDocument:
    path = run_dir / STAGE_FILES[stage]
    return parse_document(path.read_text(encoding="utf-8"))


def _section(document: MarkdownDocument, title: str, level: int) -> Section:
    matches = document.find(title, level)
    if len(matches) != 1:
        raise ValueError(f"章节必须恰好匹配一次：{title}（实际 {len(matches)}）")
    return matches[0]


def _strip_source_prefix(value: str) -> str:
    for prefix in ("用户回答：", "用户开场已提供："):
        if value.startswith(prefix):
            return value[len(prefix) :].strip()
    return value.strip().strip("。")


def _prompt_values(state: dict[str, str]) -> dict[str, str]:
    fallback = _strip_source_prefix(state.get("默认处理", ""))
    values = {
        "主题": state.get("主题", ""),
        "角色": _strip_source_prefix(state.get("角色 / 使用场景", "")),
        "水平": _strip_source_prefix(state.get("当前水平", "")),
        "目标": _strip_source_prefix(state.get("目标深度", "")),
    }
    return {
        key: (fallback if value == "未提供" else value) for key, value in values.items()
    }


def _filled_prompt(stage: int, state: dict[str, str]) -> str:
    source = (SKILL_ROOT / "reference" / "original-prompts.md").read_text(
        encoding="utf-8"
    )
    prompt = extract_original_prompt(stage, source)
    for key, value in _prompt_values(state).items():
        prompt = prompt.replace("{{" + key + "}}", value)
    return prompt


def _input_block(stage: int, document: MarkdownDocument, state: dict[str, str]) -> str:
    prompt = html.escape(_filled_prompt(stage, state), quote=True)
    upstreams = parse_upstream_table(document)
    labels = "、".join(f"<code>{html.escape(path)}</code>" for path in upstreams)
    return (
        '<pre class="text"><code>'
        + prompt
        + "</code></pre>"
        + f"<p><strong>本步实际消费：</strong>{labels}</p>"
    )


def _takeaways(document: MarkdownDocument) -> str:
    return render_markdown(_section(document, "本步提炼", 2).body)


def _output_body(document: MarkdownDocument, stage: int) -> str:
    body = _section(document, "产物", 2).body
    if stage == 10:
        body = re.sub(r"(?ms)^### 快问快答\s*$.*\Z", "", body).rstrip()
    return body


def _role_details(run_dir: Path) -> str:
    fragments = []
    for role in ROLES:
        relative = validate_stage.ROLE_FILES[role]
        document = parse_document((run_dir / relative).read_text(encoding="utf-8"))
        start = _section(document, "核心立场", 2).start_line - 1
        detail_markdown = "\n".join(document.text.splitlines()[start:])
        fragments.append(
            '<details class="panel role-detail">'
            f"<summary>{html.escape(role)}完整取证</summary>"
            f'<div class="panel-body">{render_markdown(detail_markdown)}</div>'
            "</details>"
        )
    return "".join(fragments)


def _perspective_output(run_dir: Path, document: MarkdownDocument) -> str:
    output = render_markdown(_output_body(document, 1))
    for role in ROLES:
        output = output.replace(
            f"<h3>{role}</h3>",
            f'<h3 id="persona-{role}" data-od-id="persona-{role}">{role}</h3>',
        )
    return output + _role_details(run_dir)


def expand_review_cards(run_dir: Path) -> str:
    """Render each Step 4 review together with its referenced Step 3 finding."""
    review_document = parse_document(
        (run_dir / "04-review.md").read_text(encoding="utf-8")
    )
    fragments = []
    reviews = validate_stage._records(review_document, 3, "发现评审")
    for review in reviews:
        reference = review.fields.get("发现引用", "")
        finding = resolve_reference(run_dir, reference)
        fragments.append(
            '<article class="review-card">'
            f"<h3>{html.escape(review.title)}</h3>"
            "<h4>被评发现</h4>"
            f"{render_markdown(finding.body)}"
            "<h4>评审结论</h4>"
            f"{render_markdown(review.body)}"
            "</article>"
        )
    reviewed_end = reviews[-1].end_line if reviews else 0
    remaining = "\n".join(review_document.text.splitlines()[reviewed_end:])
    if remaining.strip():
        fragments.append(render_markdown(remaining))
    return "".join(fragments)


def _exam_cards(document: MarkdownDocument) -> str:
    coverage = _section(document, "覆盖计划", 3)
    cards = [render_markdown(f"### 覆盖计划\n\n{coverage.body}")]
    for index in range(1, 11):
        question = _section(document, f"题目 {index}", 3)
        fields = question.fields
        answer = (
            f"**参考答案：** {fields['参考答案']}\n\n"
            f"**满分标准：** {fields['满分标准']}\n\n"
            f"**及格标准：** {fields['及格标准']}\n\n"
            f"**常见薄弱点：** {fields['常见薄弱点']}"
        )
        cards.append(
            '<details class="flash" '
            f'data-od-id="exam-question-{index}">'
            "<summary>"
            f'<span class="level">{html.escape(fields["难度"])}</span>'
            f'{html.escape(fields["题干"])}</summary>'
            f'<div class="flash-answer">{render_markdown(answer)}</div>'
            "</details>"
        )
    challenge = _section(document, "终极挑战", 3)
    cards.append(render_markdown(f"### 终极挑战\n\n{challenge.body}"))
    return "".join(cards)


def _quiz_cards(document: MarkdownDocument) -> str:
    section = _section(document, "快问快答", 3)
    lines = section.body.splitlines()
    cards = []
    current_question = None
    for line in lines:
        question = re.match(r"^\s*(\d+)[.)、]\s+(\S.*)$", line)
        if question:
            current_question = (int(question.group(1)), question.group(2))
            continue
        answer = re.match(r"^\s+-\s+\*\*答案：\*\*\s*(\S.*)$", line)
        if answer and current_question:
            index, question_text = current_question
            cards.append(
                '<details class="flash" '
                f'data-od-id="quick-question-{index}">'
                f"<summary>{html.escape(question_text)}</summary>"
                '<div class="flash-answer">'
                + render_markdown(f"**答案：** {answer.group(1)}")
                + "</div></details>"
            )
            current_question = None
    if len(cards) != 5:
        raise ValueError(f"快问快答渲染必须得到 5 张卡片，实际 {len(cards)}")
    return "".join(cards)


def _visualization(stage: int, document: MarkdownDocument) -> str:
    if stage == 1:
        cards = [
            f'<a class="persona" href="#persona-{role}" '
            f'data-od-id="persona-card-{role}">'
            f'<span class="persona__role">{role}</span></a>'
            for role in ROLES
        ]
        return '<div class="persona-grid">' + "".join(cards) + "</div>"
    if stage == 6:
        levels = validate_stage._records(document, 3, "级别")
        return '<div class="ladder">' + "".join(
            '<div class="rung" '
            f'data-od-id="ladder-level-{index}"><strong>{html.escape(level.fields["级别名称"])}</strong>'
            f'<span>{html.escape(level.fields["掌握表现"])}</span></div>'
            for index, level in enumerate(levels, start=1)
        ) + "</div>"
    return ""


def _mode_status(run_dir: Path) -> tuple[str, str]:
    exam_path = run_dir / "08-exam-record.md"
    if exam_path.is_file():
        exam = parse_document(exam_path.read_text(encoding="utf-8"))
        cursor = _section(exam, "会话状态", 2).fields["当前游标"]
        exam_status = f"交互施考已完成 {html.escape(cursor)} 题，对我说“考我”继续。"
    else:
        exam_status = "交互施考未进行，对我说“考我”即可开始。"
    feynman_path = run_dir / "09-feynman-record.md"
    if feynman_path.is_file():
        feynman = parse_document(feynman_path.read_text(encoding="utf-8"))
        state = _section(feynman, "会话状态", 2).fields
        feynman_status = (
            f"交互费曼会话{html.escape(state['结束状态'])}，"
            f"已完成 {html.escape(state['已完成轮次'])} 轮。"
        )
    else:
        feynman_status = "交互费曼会话未进行，对我说“给我讲”或“我来讲”即可开始。"
    return exam_status, feynman_status


def build_view_model(run_dir: Path) -> dict[str, str]:
    """Build template values only from run-state and Stage 1–10 facts."""
    run_dir = Path(run_dir).expanduser().resolve()
    state_document = parse_document(
        (run_dir / "run-state.md").read_text(encoding="utf-8")
    )
    state = {}
    for section in state_document.sections:
        state.update(section.fields)
    topic = state["主题"]
    target = _strip_source_prefix(state["目标深度"])
    role = _strip_source_prefix(state["角色 / 使用场景"])
    documents = {stage: _document(run_dir, stage) for stage in range(1, 11)}
    stage_titles = dict(STAGE_TITLES)
    if state["锚定模式"] == "未锚定模式":
        stage_titles[3] = "假设简报"
    model = {
        "RUN_ID": state["运行 ID"],
        "TOPIC": topic,
        "TOPIC_SUB": f"{target} · {role}",
        "METHOD_INTRO": (
            f"面向“{role}”场景，以“{target}”为目标；"
            f"本轮来源模式为 {state['锚定模式']}。"
        ),
        "CLOSING_INTRO": "十步材料已经从独立取证推进到主动回忆与一页压缩。",
        "CLOSING_DELIVERABLES": render_markdown(
            "- Markdown 文件保存事实源\n- HTML 保存离线阅读视图\n- 模式 B/C 只记录真实互动"
        ),
        "LOOP_DIAGRAM": "",
    }
    map_items = []
    for stage in range(1, 11):
        map_items.append(
            f'<a class="step-card" href="#view-{stage}" data-od-id="map-step-{stage}">'
            f'<span class="step-number">{stage:02d}</span>'
            f"<strong>{html.escape(stage_titles[stage])}</strong></a>"
        )
    model["STEP_MAP"] = "".join(map_items)
    for stage, document in documents.items():
        model[f"STEP_{stage}_TITLE"] = stage_titles[stage]
        model[f"STEP_{stage}_PURPOSE"] = STAGE_PURPOSES[stage]
        model[f"STEP_{stage}_INPUT"] = _input_block(stage, document, state)
        model[f"STEP_{stage}_TAKEAWAYS"] = _takeaways(document)
        model[f"STEP_{stage}_VIZ"] = _visualization(stage, document)
        if stage not in {8}:
            if stage == 1:
                output = _perspective_output(run_dir, document)
            elif stage == 4:
                output = expand_review_cards(run_dir)
            else:
                output = render_markdown(_output_body(document, stage))
            model[f"STEP_{stage}_OUTPUT"] = output
    model["STEP_8_CARDS"] = _exam_cards(documents[8])
    model["STEP_10_QUIZ"] = _quiz_cards(documents[10])
    model["EXAM_STATUS"], model["FEYNMAN_STATUS"] = _mode_status(run_dir)
    return model


def _render_template_values(values: dict[str, str]) -> str:
    template = (SKILL_ROOT / "assets" / "template.html").read_text(
        encoding="utf-8"
    )
    rendered = template
    html_keys = {
        "STEP_MAP",
        "CLOSING_DELIVERABLES",
        "LOOP_DIAGRAM",
        *(f"STEP_{stage}_{suffix}" for stage in range(1, 11) for suffix in ("INPUT", "OUTPUT", "TAKEAWAYS", "VIZ")),
        "STEP_8_CARDS",
        "STEP_10_QUIZ",
    }
    for key, value in values.items():
        safe = value if key in html_keys else html.escape(value, quote=True)
        rendered = rendered.replace("{{" + key + "}}", safe)
    unresolved = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", rendered)))
    if unresolved:
        raise ValueError("HTML 模板仍有未填槽位：" + "、".join(unresolved))
    return rendered


def _validate_markdown_run(run_dir: Path) -> None:
    failures = {}
    for stage in map(str, range(11)):
        violations = validate_stage.validate_one(stage, run_dir)
        if violations:
            failures[stage] = [item.to_dict() for item in violations]
    for optional in ("exam-record", "feynman-record"):
        if (run_dir / validate_stage.STAGE_FILES[optional]).is_file():
            violations = validate_stage.validate_one(optional, run_dir)
            if violations:
                failures[optional] = [item.to_dict() for item in violations]
    if failures:
        raise ValueError(
            "Markdown 阶段尚未通过校验："
            + json.dumps(failures, ensure_ascii=False)
        )


def render_learning_page(
    run_dir: Path, output: Path, inline: bool = False
) -> Path:
    """Validate facts, render the fixed template, package assets, then validate HTML."""
    run_dir = Path(run_dir).expanduser().resolve()
    output = Path(output).expanduser().resolve()
    _validate_markdown_run(run_dir)
    html_text = _render_template_values(build_view_model(run_dir))
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent, prefix=".learn-loop-render-", suffix=".html"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(html_text)
        render_template.render(Path(temporary_name), output, inline)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    violations = validate_stage.validate_html(output.parent)
    if violations:
        raise ValueError(
            "HTML 校验失败："
            + json.dumps([item.to_dict() for item in violations], ensure_ascii=False)
        )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--inline", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        output = render_learning_page(
            Path(args.run_dir), Path(args.output), inline=args.inline
        )
    except (OSError, KeyError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
