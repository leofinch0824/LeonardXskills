#!/usr/bin/env python3
"""Hard structural gates for learn-loop Markdown artifacts and rendered HTML."""

import argparse
import json
import re
import sys
from pathlib import Path


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

PROFILE_SOURCE_PREFIXES = ("用户回答：", "用户开场已提供：", "未提供")
PROFILE_SOURCE_FIELDS = ("当前水平", "目标深度", "角色 / 使用场景")


def section_content(text, marker):
    lines = text.splitlines()
    heading_candidates = [
        (index, line)
        for index, line in enumerate(lines)
        if marker in line and re.match(r"^#{1,6}\s+", line)
    ]
    candidates = heading_candidates or [
        (index, line) for index, line in enumerate(lines) if marker in line
    ]
    start = candidates[0][0] if candidates else None
    if start is None:
        return ""
    heading_match = re.match(r"^(#+)\s+", lines[start])
    heading_level = len(heading_match.group(1)) if heading_match else 6
    content = []
    for line in lines[start + 1 :]:
        next_heading = re.match(r"^(#+)\s+", line)
        if next_heading and len(next_heading.group(1)) <= heading_level:
            break
        content.append(line)
    return "\n".join(content).strip()


def heading_sections(text, pattern):
    matches = list(re.finditer(pattern, text, re.MULTILINE))
    sections = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(0), text[match.end() : end]))
    return sections


def require_sections(text, labels, violations):
    for label in labels:
        content = section_content(text, label)
        if not content:
            violations.append(f"缺少非空章节：{label}")


def check_placeholder_scope(text, violations):
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("|"):
            if "{{" in line or "}}" in line:
                violations.append(f"标题或表格行残留占位符（第 {line_number} 行）")


def check_table_cells(text, violations):
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip().startswith("|") or re.match(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if any(not cell for cell in cells):
            violations.append(f"表格存在空单元格（第 {line_number} 行）")
        if any(is_sentinel(cell) for cell in cells):
            violations.append(f"表格存在未填占位值（第 {line_number} 行）")


def field_value(text, label):
    pattern = rf"(?m)^\s*(?:[-*]\s*)?(?:\*\*)?{re.escape(label)}(?:\*\*)?\s*[:：]\s*(?:\*\*)?\s*(\S.+?)\s*$"
    match = re.search(pattern, text)
    if not match:
        return ""
    return match.group(1).strip().strip("*")


def field_is_nonempty(text, label):
    return not is_sentinel(field_value(text, label))


def is_sentinel(value):
    normalized = re.sub(r"\s+", "", value).strip("。；;，, ")
    # 用户来源标记本身不是内容：`用户回答：待填写` 仍应视为未填
    normalized = re.sub(r"^(?:用户回答|用户开场已提供)\s*[:：]", "", normalized)
    if normalized in {"", "—", "-", "TBD"}:
        return True
    if normalized.startswith(("待填写", "待检索", "待真实", "待评分")):
        return True
    # 值内任一分段为占位，整个字段视为未填：
    # `查询词：待填写；命中数：3` 不能算检索记录已填
    segments = re.split(r"[；;、]", normalized)
    return any(
        segment.startswith(("待填写", "待检索", "待真实", "待评分"))
        or re.search(r"[:：]待(?:填写|检索|真实|评分)", segment)
        for segment in segments
    )


def require_nonempty_fields(text, labels, violations, context):
    for label in labels:
        if not field_is_nonempty(text, label):
            violations.append(f"{context}缺少非空字段：{label}")


def require_nonempty_alternatives(text, alternatives, violations, context):
    for labels in alternatives:
        if not any(field_is_nonempty(text, label) for label in labels):
            violations.append(f"{context}缺少非空字段：{' / '.join(labels)}")


def check_common(text, violations):
    require_sections(text, ("消费上游", "产物", "本步提炼"), violations)
    takeaways = section_content(text, "本步提炼")
    count = len(re.findall(r"(?m)^\s*[-*]\s+\S", takeaways))
    if not 3 <= count <= 5:
        violations.append(f"本步提炼应有 3–5 条，实际 {count} 条")
    check_placeholder_scope(text, violations)
    check_table_cells(text, violations)
    if re.search(r"(?m)^\s*[-*]\s+待填写", takeaways):
        violations.append("本步提炼仍含待填写占位值")


def check_upstream_files(text, run_dir):
    violations = []
    upstream = section_content(text, "消费上游")
    for reference in re.findall(r"`([^`]+\.md)`", upstream):
        if (
            "/" in reference
            or reference.startswith("<")
            or reference in {"learner-profile.md", "review-queue.md", "INDEX.md"}
        ):
            continue
        if not (run_dir / reference).is_file():
            violations.append(f"消费上游引用的文件不存在：{reference}")
    return violations


def validate_stage_0(text):
    violations = []
    require_sections(text, ("学习画像", "独立性档位", "锚定模式"), violations)
    require_nonempty_fields(
        text,
        ("当前水平", "目标深度", "角色 / 使用场景", "画像句", "独立性档位", "锚定模式"),
        violations,
        "运行状态",
    )
    for label in PROFILE_SOURCE_FIELDS:
        value = field_value(text, label)
        if not value.startswith(PROFILE_SOURCE_PREFIXES):
            violations.append(
                f"运行状态字段缺少来源标记（须以“用户回答：/用户开场已提供：/未提供”开头）：{label}"
            )
    if any(
        field_value(text, label).startswith("未提供")
        for label in PROFILE_SOURCE_FIELDS
    ):
        if "已按默认值执行" not in text and "阻塞说明" not in text:
            violations.append("存在“未提供”画像字段，但缺少“已按默认值执行”或“阻塞说明”声明")
    require_sections(text, ("前置判定",), violations)
    verdict = field_value(text, "判定")
    if not re.match(r"^(适合|调整后适合)", verdict):
        violations.append(
            f"前置判定的判定值须以“适合”或“调整后适合”开头（不适合时不创建运行目录），实际：{verdict or '缺失'}"
        )
    require_nonempty_fields(
        text, ("判定理由", "调整说明", "资料探针"), violations, "前置判定"
    )
    if verdict.startswith("调整后适合"):
        note = field_value(text, "调整说明").strip("。 ")
        if note in {"无", "不适用", "无调整", "无需调整"}:
            violations.append("判定为“调整后适合”时，调整说明不得为“无/不适用”类空泛值")
    if "模式 A" not in text and "模式A" not in text:
        violations.append("运行状态缺少模式 A 记录")
    return violations


def validate_stage_1(text):
    violations = []
    check_common(text, violations)
    names = ("实践者", "学者", "怀疑者", "经济学家", "历史学家")
    sections = []
    for name in names:
        matches = heading_sections(text, rf"^###\s+{name}\s*$")
        if len(matches) != 1:
            violations.append(f"视角“{name}”应恰好出现 1 次，实际 {len(matches)} 次")
        sections.extend(matches)
    if len(sections) != 5:
        violations.append(f"视角总数必须为 5，实际 {len(sections)}")
    for name, (_, content) in zip(names, sections):
        for label in ("核心立场", "最强证据", "独家洞见", "检索记录"):
            if label not in content:
                violations.append(f"视角“{name}”缺少：{label}")
        require_nonempty_fields(
            content,
            ("核心立场", "最强证据", "独家洞见", "检索记录"),
            violations,
            f"视角“{name}”",
        )
        evidence = re.search(r"(?:等级|来源等级)\s*[:：|]\s*[^\n]*\b([ABC])\b", content)
        if not evidence and not re.search(r"[【|]([ABC])[】|]", content):
            violations.append(f"视角“{name}”的证据缺少 A/B/C 等级")
    return violations


def validate_stage_2(text):
    violations = []
    check_common(text, violations)
    conflict_content = section_content(text, "冲突分类")
    require_nonempty_fields(
        conflict_content,
        ("实质分歧", "措辞分歧", "未决"),
        violations,
        "冲突分类",
    )
    for label in ("实质分歧", "措辞分歧", "未决"):
        if label not in text:
            violations.append(f"冲突分类缺少：{label}")
    for label in ("独立共识", "模型先验·待验证"):
        if label not in text:
            violations.append(f"共识分级缺少：{label}")
    for label in ("领域盲区", "未覆盖"):
        if label not in text:
            violations.append(f"盲区判定缺少：{label}")
    return violations


def validate_stage_3(text):
    violations = []
    check_common(text, violations)
    sections = heading_sections(text, r"^###\s+(?:关键发现|发现)\s*[1-5]\s*$")
    if len(sections) != 5:
        violations.append(f"关键发现必须恰好 5 条，实际 {len(sections)} 条")
    for index, (_, content) in enumerate(sections[:3], start=1):
        if "模型先验·待验证" in content:
            violations.append(f"关键发现 {index} 将模型先验·待验证放入前 3 条")
        grade = field_value(content, "来源等级")
        if not re.search(r"[AB]", grade):
            violations.append(
                f"关键发现 {index} 前 3 条必须含 A/B 来源等级，实际：{grade or '缺失'}"
            )
    for index, (_, content) in enumerate(sections, start=1):
        for label in ("来源等级", "支持视角", "反对视角"):
            if label not in content:
                violations.append(f"关键发现 {index} 缺少：{label}")
        require_nonempty_fields(
            content,
            ("发现", "来源等级", "支持视角", "反对视角"),
            violations,
            f"关键发现 {index} ",
        )
    return violations


def validate_stage_4(text):
    violations = []
    check_common(text, violations)
    sections = heading_sections(text, r"^###\s+(?:可靠性发现|发现)\s*[1-5]\s*$")
    if len(sections) != 5:
        violations.append(f"评审发现必须恰好 5 条，实际 {len(sections)} 条")
    for index, (_, content) in enumerate(sections, start=1):
        score = re.search(r"(?:可靠性分数|评分)\s*[:：]\s*\**\s*(10|[1-9])(?:\s|分|/)", content)
        if not score:
            violations.append(f"评审发现 {index} 缺少 1–10 分评分")
        if "推导依据" not in content:
            violations.append(f"评审发现 {index} 缺少来源/分歧推导依据")
        require_nonempty_fields(
            content,
            ("发现", "可靠性分数", "推导依据"),
            violations,
            f"评审发现 {index} ",
        )
    if not section_content(text, "第 6 视角"):
        violations.append("缺少非空的第 6 视角结论")
    return violations


def validate_stage_5(text):
    violations = []
    check_common(text, violations)
    sections = heading_sections(text, r"^###\s+资源\s*[1-5]\s*$")
    if len(sections) != 5:
        violations.append(f"资源必须恰好 5 个，实际 {len(sections)} 个")
    for index, (_, content) in enumerate(sections, start=1):
        for label in ("为什么比同类强", "怎么用", "花多久", "关键点"):
            if label not in content:
                violations.append(f"资源 {index} 缺少：{label}")
        require_nonempty_fields(
            content,
            ("资源名 / 类型", "为什么比同类强", "怎么用", "花多久", "关键点"),
            violations,
            f"资源 {index} ",
        )
        if not re.search(r"https?://\S+", content) and not re.search(r"等级\s*[:：]\s*C", content):
            violations.append(f"资源 {index} 缺少可解析 URL 或 C 级标记")
    path_content = section_content(text, "一周路径")
    if len(re.findall(r"(?m)^\s*(?:\d+[.)、]|[-*])\s+\S", path_content)) < 5:
        violations.append("一周路径至少覆盖 5 个条目")
    return violations


def validate_stage_6(text):
    violations = []
    check_common(text, violations)
    sections = heading_sections(text, r"^###\s+级别\s*[1-5]\b.*$")
    if len(sections) != 5:
        violations.append(f"学习阶梯必须恰好 5 级，实际 {len(sections)} 级")
    labels = ("应该理解", "掌握表现", "重点概念", "里程碑", "动手练习", "常见错误", "自测问题")
    for index, (_, content) in enumerate(sections, start=1):
        for label in labels:
            if label not in content:
                violations.append(f"级别 {index} 缺少：{label}")
        require_nonempty_alternatives(
            content,
            (
                ("应该理解",),
                ("掌握表现",),
                ("重点概念", "重点概念或技能"),
                ("里程碑",),
                ("动手练习", "动手练习或小项目"),
                ("常见错误",),
                ("自测问题",),
            ),
            violations,
            f"级别 {index} ",
        )
    current = section_content(text, "当前级与下一里程碑")
    if not current or is_sentinel(current):
        violations.append("缺少已定位的当前级与下一里程碑")
    return violations


def validate_stage_7(text):
    violations = []
    check_common(text, violations)
    sections = heading_sections(text, r"^###\s+第\s*\d+\s*课\b.*$")
    if not 8 <= len(sections) <= 12:
        violations.append(f"课程数应在 8–12 次之间，实际 {len(sections)} 次")
    labels = ("学习目标", "关键概念", "动手练习", "推荐资源", "预期结果")
    for index, (_, content) in enumerate(sections, start=1):
        for label in labels:
            if label not in content:
                violations.append(f"第 {index} 课缺少：{label}")
        require_nonempty_fields(content, labels, violations, f"第 {index} 课")
        question_content = section_content(content, "复习题")
        count = len(re.findall(r"(?m)^\s*(?:[-*]\s*)?\d+[.)、]\s+\S", question_content))
        if not 3 <= count <= 7:
            violations.append(f"第 {index} 课复习题应有 3–7 道，实际 {count} 道")
    if not section_content(text, "终局小项目"):
        violations.append("缺少非空终局小项目")
    core = section_content(text, "核心 20%")
    if "为什么" not in core:
        violations.append("核心 20% 缺少为什么是核心的解释")
    require_nonempty_fields(
        section_content(text, "终局小项目"),
        ("输入", "动作", "可检查输出", "完成标准"),
        violations,
        "终局小项目",
    )
    return violations


def validate_stage_8(text):
    violations = []
    check_common(text, violations)
    sections = heading_sections(text, r"^###\s+题目\s*\d+\b.*$")
    if len(sections) != 10:
        violations.append(f"题库必须恰好 10 题，实际 {len(sections)} 题")
    expected_ranges = ((1, 3, "初级"), (4, 6, "中级"), (7, 8, "高级"), (9, 10, "专家级"))
    for start, end, difficulty in expected_ranges:
        for number in range(start, end + 1):
            match = re.search(rf"^###\s+题目\s*{number}\b.*$", text, re.MULTILINE)
            if not match:
                continue
            content = text[match.end() :]
            next_heading = re.search(r"^###\s+", content, re.MULTILINE)
            if next_heading:
                content = content[: next_heading.start()]
            if difficulty not in content:
                violations.append(f"题目 {number} 难度应为 {difficulty}")
            if "参考答案" not in content or "评分标准" not in content:
                violations.append(f"题目 {number} 缺少参考答案或评分标准")
            require_nonempty_fields(
                content,
                ("题目", "难度", "参考答案", "评分标准"),
                violations,
                f"题目 {number} ",
            )
    challenges = section_content(text, "终极挑战")
    challenge_count = len(re.findall(r"(?m)^\s*\d+[.)、]\s+\S", challenges))
    if challenge_count != 5:
        violations.append(f"终极挑战必须恰好 5 道，实际 {challenge_count} 道")
    if re.search(r"(?:用户回答|我的答案|逐字引用|答题记录)\s*[:：]", text):
        violations.append("题库混入答题/施考记录")
    return violations


def validate_stage_9(text):
    violations = []
    check_common(text, violations)
    for label in ("第一层", "第二层", "第三层"):
        content = section_content(text, label)
        if not content or is_sentinel(content):
            violations.append(f"费曼讲解缺少非空层级：{label}")
    confusion_count = len(heading_sections(text, r"^###\s+困惑点\s*\d+\b.*$"))
    if not 3 <= confusion_count <= 5:
        violations.append(f"困惑点应有 3–5 个，实际 {confusion_count} 个")
    if re.search(r"(?:用户复述|逐字引用|复述记录)\s*[:：]", text):
        violations.append("费曼 notes 混入复述记录")
    return violations


def find_ancestor_file(run_dir, filename):
    for parent in (run_dir, *run_dir.parents):
        candidates = [parent / filename]
        if filename == "review-queue.md":
            candidates.append(parent / ".learn-loop" / filename)
        for candidate in candidates:
            if candidate.is_file():
                return candidate
    return None


def validate_stage_10(text, run_dir):
    violations = []
    check_common(text, violations)
    for label in ("一句定义", "短条目要点", "真实例子", "易错易混", "上场清单", "快问快答"):
        content = section_content(text, label)
        if not content or is_sentinel(content):
            violations.append(f"速查表缺少非空六件套章节：{label}")
    examples = section_content(text, "真实例子")
    example_count = len(re.findall(r"(?m)^\s*\d+[.)、]\s+\S", examples))
    if not 3 <= example_count <= 5:
        violations.append(f"真实例子应有 3–5 个，实际 {example_count} 个")
    qa_content = section_content(text, "快问快答")
    qa_count = len(re.findall(r"(?m)^\s*\d+[.)、]\s+\S", qa_content))
    if not 3 <= qa_count <= 7:
        violations.append(f"快问快答应有 3–7 道，实际 {qa_count} 道")
    answer_count = len(re.findall(r"(?m)^\s*[-*]\s*答案\s*[:：]", qa_content))
    if answer_count < qa_count:
        violations.append(f"快问快答每道题必须附参考答案（当前 {answer_count}/{qa_count} 题有答案）")
    index_path = find_ancestor_file(run_dir, "INDEX.md")
    queue_path = find_ancestor_file(run_dir, "review-queue.md")
    if not index_path:
        violations.append("找不到已回灌的 INDEX.md")
    elif run_dir.name not in index_path.read_text(encoding="utf-8"):
        violations.append("INDEX.md 没有对应运行目录记录")
    if not queue_path:
        violations.append("找不到已回灌的 review-queue.md")
    else:
        queue_text = queue_path.read_text(encoding="utf-8")
        slug_match = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)$", run_dir.name)
        run_slug = slug_match.group(1) if slug_match else run_dir.name
        if run_dir.name not in queue_text and run_slug not in queue_text:
            violations.append("review-queue.md 没有对应主题或 slug 记录")
    return violations


def validate_exam_record(text):
    violations = []
    sections = heading_sections(text, r"^###\s+第\s*\d+\s*题\b.*$")
    cursor_match = re.search(r"当前游标\s*[:：]\s*(\d+)", text)
    done_match = re.search(r"已完成题数\s*[:：]\s*(\d+)", text)
    if done_match and cursor_match and int(done_match.group(1)) != int(cursor_match.group(1)):
        violations.append("施考记录已完成题数与当前游标不一致")
    if not sections and "未启动" in text and cursor_match and int(cursor_match.group(1)) == 0:
        return violations
    if not cursor_match:
        violations.append("施考记录缺少数字游标")
    elif int(cursor_match.group(1)) != len(sections):
        violations.append(f"游标与记录行数不一致：游标 {cursor_match.group(1)}，记录 {len(sections)}")
    for index, (_, content) in enumerate(sections, start=1):
        for label in ("逐字引用", "得分", "差距"):
            if label not in content:
                violations.append(f"第 {index} 题记录缺少：{label}")
    return violations


def validate_feynman_record(text):
    violations = []
    rounds = heading_sections(text, r"^###\s+第\s*\d+\s*轮\b.*$")
    if not rounds and "未启动" in text:
        return violations
    if not rounds:
        violations.append("费曼记录至少需要一轮闭环")
    for index, (_, content) in enumerate(rounds, start=1):
        if not re.search(r"逐字复述\s*[:：]\s*\S", content):
            violations.append(f"第 {index} 轮缺少非空逐字复述")
    ending = re.search(r"结束状态\s*[:：]\s*(已讲清|仍未通过)", text)
    if not ending:
        violations.append("结束状态必须为“已讲清”或“仍未通过”")
    return violations


FLASH_BLOCK = re.compile(
    r"<div class=\"flash-answer\".*?</div>", re.DOTALL
)
EVIDENCE_OPEN = re.compile(r"<details[^>]*class=\"[^\"]*evidence[^\"]*\"[^>]*\bopen\b")
# 只匹配「标签＋冒号」的答案正文形式，避免误伤散文里提到的“参考答案”字样
ANSWER_LABELS = ("参考答案", "评分标准")
# 双重转义：花括号先被写成 &#123; 又整体转义一次，页面上会显示成实体码
DOUBLE_ESCAPED = re.compile(r"&amp;#1(?:23|25);")
# 未代入的中文槽位，转义前后两种写法都要抓
PROMPT_SLOTS = ("主题", "角色", "水平", "目标")
EXAM_STATUS_LINE = re.compile(r"交互施考(?:\s*[:：])?\s*(?:未进行|已完成\s*\d+\s*题)")
NOSCRIPT_OPEN_TAG = re.compile(r"<noscript\b[^>]*>", re.IGNORECASE | re.DOTALL)
STYLESHEET_TAG = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
SCRIPT_SOURCE_TAG = re.compile(
    r"<script\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*></script>", re.IGNORECASE
)
ASSET_NAMES = {"template.css", "template.js"}
RUN_ID_ATTR = re.compile(
    r"<body\b[^>]*\bdata-run-id=[\"']([^\"']+)[\"'][^>]*>",
    re.IGNORECASE | re.DOTALL,
)
VIEW_OPEN_TAG = re.compile(
    r"<section\b[^>]*\bclass=[\"'][^\"']*\bview\b[^\"']*[\"'][^>]*>",
    re.IGNORECASE,
)
WORKBENCH_OD_IDS = (
    "learning-directory",
    "learning-workbench",
    "learning-map",
    "chapter-context",
)


def check_html_learnability(text, name, violations):
    """答案必须折叠、取证必须收起、提炼不得重复、提示词必须已填且只转义一次。"""
    stripped = FLASH_BLOCK.sub("", text)
    for label in ANSWER_LABELS:
        if re.search(r"%s\s*[:：]" % label, stripped):
            violations.append(f"HTML 答案未折叠（{label} 出现在 flash-answer 之外）：{name}")

    if EVIDENCE_OPEN.search(text):
        violations.append(f"HTML 取证折叠不得默认展开：{name}")

    ids = re.findall(r"\sid=\"([^\"]+)\"", text)
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        violations.append(f"HTML 存在重复 id：{name}（{'、'.join(duplicates[:5])}）")

    takeaway_count = text.count("本步提炼")
    if takeaway_count > 10:
        violations.append(
            f"HTML「本步提炼」渲染 {takeaway_count} 次，超过 10 步各一次：{name}"
        )

    if DOUBLE_ESCAPED.search(text):
        violations.append(
            f"HTML 花括号被双重转义，页面会显示 &#123; 实体码：{name}"
        )

    unfilled = [
        slot
        for slot in PROMPT_SLOTS
        if re.search(r"(?:\{\{|&(?:amp;)?#123;(?:&(?:amp;)?#123;)?)%s" % slot, text)
    ]
    if unfilled:
        violations.append(
            f"HTML 取证提示词未代入槽位：{name}（{'、'.join(unfilled)}）"
        )


def check_html_assets(path, text, violations):
    """模板采用外链固定资源时，二者必须是同目录的本地文件。"""
    references = []
    for tag in STYLESHEET_TAG.findall(text):
        if re.search(r"\brel=[\"']stylesheet[\"']", tag, re.IGNORECASE):
            match = re.search(r"\bhref=[\"']([^\"']+)[\"']", tag, re.IGNORECASE)
            if match:
                references.append(match.group(1))
    references.extend(SCRIPT_SOURCE_TAG.findall(text))
    if not references:
        return
    if set(references) != ASSET_NAMES or len(references) != len(ASSET_NAMES):
        violations.append(f"HTML 固定资源引用必须各为一次 template.css 和 template.js：{path.name}")
        return
    for reference in references:
        asset = Path(reference)
        if asset.name != reference or not (path.parent / asset).is_file():
            violations.append(f"HTML 固定资源必须位于同目录且可读取：{reference}（{path.name}）")


def check_html_workbench_contract(text, name, violations):
    """固定工作台模板必须携带稳定状态键和可检查的区域标识。"""
    template_based = bool(
        re.search(r"href=[\"']template\.css[\"']", text, re.IGNORECASE)
        or 'data-learn-loop="template.css"' in text
    )
    if not template_based:
        return

    run_id = RUN_ID_ATTR.search(text)
    if not run_id or not run_id.group(1).strip():
        violations.append(f"HTML 工作台缺少非空 data-run-id：{name}")

    od_ids = re.findall(r"\bdata-od-id=[\"']([^\"']+)[\"']", text)
    duplicates = sorted({value for value in od_ids if od_ids.count(value) > 1})
    if duplicates:
        violations.append(
            f"HTML 存在重复 data-od-id：{name}（{'、'.join(duplicates[:5])}）"
        )
    for required in WORKBENCH_OD_IDS:
        if required not in od_ids:
            violations.append(f"HTML 工作台缺少关键区域 data-od-id={required}：{name}")

    for tag in VIEW_OPEN_TAG.findall(text):
        view_id = re.search(r"\bid=[\"']([^\"']+)[\"']", tag)
        if not re.search(r"\bdata-od-id=[\"'][^\"']+[\"']", tag):
            label = view_id.group(1) if view_id else "未知视图"
            violations.append(f"HTML 视图缺少 data-od-id：{name}（{label}）")
        if not re.search(r"\bdata-module=[\"'][^\"']+[\"']", tag):
            label = view_id.group(1) if view_id else "未知视图"
            violations.append(f"HTML 视图缺少 data-module：{name}（{label}）")

    for view_id, command in (("view-8", "考我"), ("view-9", "给我讲")):
        if f'id="{view_id}"' in text and f'data-workflow-command="{command}"' not in text:
            violations.append(f"HTML {view_id} 缺少对话交接命令“{command}”：{name}")


def validate_html(run_dir):
    html_files = sorted(run_dir.glob("*.html"))
    if not html_files:
        return ["运行目录缺少 HTML 视图"]
    violations = []
    for path in html_files:
        text = path.read_text(encoding="utf-8")
        if "{{" in text or "}}" in text:
            violations.append(f"HTML 残留占位符：{path.name}")
        if not NOSCRIPT_OPEN_TAG.search(text):
            violations.append(
                f"HTML 缺少 noscript 降级（JS 禁用时全部视图应可读）：{path.name}"
            )
        if not EXAM_STATUS_LINE.search(text):
            violations.append(
                f"HTML 缺少施考状态行（须为“交互施考未进行”或“交互施考已完成 N 题”）：{path.name}"
            )
        check_html_assets(path, text, violations)
        check_html_workbench_contract(text, path.name, violations)
        check_html_learnability(text, path.name, violations)
    return violations


def validate_one(stage, run_dir):
    if stage == "html":
        return validate_html(run_dir)
    path = run_dir / STAGE_FILES[stage]
    if not path.is_file():
        return [f"缺少文件：{path.name}"]
    text = path.read_text(encoding="utf-8")
    validators = {
        "0": validate_stage_0,
        "1": validate_stage_1,
        "2": validate_stage_2,
        "3": validate_stage_3,
        "4": validate_stage_4,
        "5": validate_stage_5,
        "6": validate_stage_6,
        "7": validate_stage_7,
        "8": validate_stage_8,
        "9": validate_stage_9,
        "10": validate_stage_10,
        "exam-record": validate_exam_record,
        "feynman-record": validate_feynman_record,
    }
    if stage == "10":
        result = validators[stage](text, run_dir)
    else:
        result = validators[stage](text)
    if stage in {str(number) for number in range(1, 11)} or stage in {"exam-record", "feynman-record"}:
        result.extend(check_upstream_files(text, run_dir))
    return result


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--stage", choices=[*map(str, range(11)), "exam-record", "feynman-record", "html"])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if bool(args.stage) == args.all:
        print("必须且只能选择 --stage 或 --all", file=sys.stderr)
        return 2
    run_dir = Path(args.run_dir).expanduser().resolve()
    stages = [args.stage] if args.stage else [*map(str, range(11)), "html"]
    if args.all:
        for optional in ("exam-record", "feynman-record"):
            if (run_dir / STAGE_FILES[optional]).is_file():
                stages.append(optional)
    violations = {stage: validate_one(stage, run_dir) for stage in stages}
    violations = {stage: items for stage, items in violations.items() if items}
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
            stage_violations = violations.get(stage, [])
            print(f"- stage {stage}: " + ("OK" if not stage_violations else "; ".join(stage_violations)))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
