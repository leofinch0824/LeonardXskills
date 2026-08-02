import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = PROJECT_ROOT / "learn-loop"
SCRIPTS = SKILL_ROOT / "scripts"


class LearnLoopPackageContractTest(unittest.TestCase):
    REQUIRED_FILES = (
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
    )

    def test_skill_package_contains_every_planned_artifact(self):
        missing = [
            relative_path
            for relative_path in self.REQUIRED_FILES
            if not (SKILL_ROOT / relative_path).is_file()
        ]
        self.assertEqual([], missing)

    def test_skill_is_portable_and_uses_path_anchors(self):
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SKILL_ROOT.rglob("*")
            if path.is_file() and path.suffix in {".md", ".yaml", ".py", ".html"}
        )
        self.assertNotIn("/Users/pegasus", text)
        self.assertNotIn("/home/", text)
        for anchor in ("<skill-root>", "<workspace-root>", "<learning-root>"):
            self.assertIn(anchor, text)

    def test_original_prompt_anchors_are_preserved(self):
        prompts = (SKILL_ROOT / "reference/original-prompts.md").read_text(
            encoding="utf-8"
        )
        for anchor in (
            "支持者们刻意忽略了哪些证据",
            "其他视角绝不会提的事",
            "讲给只有 60 秒的 CEO 听",
            "不要一次给我所有答案",
        ):
            self.assertIn(anchor, prompts)
        self.assertEqual(10, prompts.count("## 第 "))

    def test_markdown_contracts_are_present(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for term in (
            "parallel",
            "serial-isolated",
            "orchestrated",
            "独立共识",
            "模型先验·待验证",
            "未锚定模式",
            "领域盲区",
            "未覆盖",
            "逐字引用",
        ):
            self.assertIn(term, skill)

        for path in SKILL_ROOT.glob("templates/0[1-9]-*.md"):
            content = path.read_text(encoding="utf-8")
            self.assertIn("消费上游", content, path.name)
            self.assertIn("本步提炼", content, path.name)

    def test_agents_metadata_disables_implicit_invocation(self):
        metadata = (SKILL_ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: false", metadata)

    def test_default_profile_is_neutral(self):
        profile = (SKILL_ROOT / "templates/learner-profile.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("暂无用户确认的长期事实", profile)
        self.assertNotIn("默认用户", profile)


class LearnLoopCliTest(unittest.TestCase):
    def run_cli(self, script, *args, env=None):
        command = [sys.executable, str(SCRIPTS / script), *args]
        return subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            env=env,
        )

    def test_preflight_bootstrap_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = self.run_cli(
                "preflight.py",
                "--workspace-root",
                temp_dir,
                "--bootstrap",
                "--json",
            )
            self.assertEqual(0, first.returncode, first.stderr)
            report = json.loads(first.stdout)
            self.assertEqual(
                (Path(temp_dir) / ".learn-loop" / "learner-profile.md").resolve(),
                Path(report["paths"]["profile_path"]),
            )
            profile_path = Path(report["paths"]["profile_path"])
            profile_path.write_text("# 用户修改\n", encoding="utf-8")

            second = self.run_cli(
                "preflight.py",
                "--workspace-root",
                temp_dir,
                "--bootstrap",
                "--json",
            )
            self.assertEqual(0, second.returncode, second.stderr)
            self.assertEqual("# 用户修改\n", profile_path.read_text(encoding="utf-8"))
            self.assertEqual([], json.loads(second.stdout)["created"])

    def test_review_queue_registers_intervals_and_advances_score(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / ".learn-loop"
            add = self.run_cli(
                "review_queue.py",
                "--state-dir",
                str(state_dir),
                "--add",
                "--topic",
                "测试主题",
                "--slug",
                "test-topic",
                "--date",
                "2026-08-02",
            )
            self.assertEqual(0, add.returncode, add.stderr)
            queue = state_dir / "review-queue.md"
            text = queue.read_text(encoding="utf-8")
            for due in ("2026-08-03", "2026-08-09", "2026-09-01"):
                self.assertIn(due, text)

            due = self.run_cli(
                "review_queue.py",
                "--state-dir",
                str(state_dir),
                "--due",
                "--date",
                "2026-08-03",
                "--json",
            )
            self.assertEqual(0, due.returncode, due.stderr)
            self.assertEqual("test-topic", json.loads(due.stdout)[0]["slug"])

            score = self.run_cli(
                "review_queue.py",
                "--state-dir",
                str(state_dir),
                "--record-score",
                "--slug",
                "test-topic",
                "--score",
                "4",
                "--date",
                "2026-08-02",
            )
            self.assertEqual(0, score.returncode, score.stderr)
            text = queue.read_text(encoding="utf-8")
            self.assertIn("2026-08-03", text)
            self.assertIn("4/10", text)

            second_score = self.run_cli(
                "review_queue.py",
                "--state-dir",
                str(state_dir),
                "--record-score",
                "--slug",
                "test-topic",
                "--score",
                "8",
                "--date",
                "2026-08-03",
            )
            self.assertEqual(0, second_score.returncode, second_score.stderr)
            text = queue.read_text(encoding="utf-8")
            self.assertIn("4/10", text)
            self.assertIn("8/10", text)

    def test_validate_stage_reports_json_violation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            (run_dir / "run-state.md").write_text(
                "# 运行状态\n\n## 学习画像\n\n## 独立性档位\n\n## 锚定模式\n",
                encoding="utf-8",
            )
            result = self.run_cli(
                "validate_stage.py",
                "--run-dir",
                str(run_dir),
                "--stage",
                "0",
                "--json",
            )
            self.assertNotEqual(0, result.returncode)
            report = json.loads(result.stdout)
            self.assertFalse(report["ok"])
            self.assertTrue(report["violations"]["0"])

    def test_all_validator_accepts_a_complete_mode_a_fixture(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            preflight = self.run_cli(
                "preflight.py",
                "--workspace-root",
                str(workspace),
                "--bootstrap",
                "--json",
            )
            self.assertEqual(0, preflight.returncode, preflight.stderr)
            run_dir = workspace / "learning" / "2026-08-02-demo-topic"
            run_dir.mkdir(parents=True)
            for name in (
                "01-perspectives.md",
                "02-conflicts.md",
                "03-brief.md",
                "04-review.md",
                "05-resources.md",
                "06-ladder.md",
                "07-sprint.md",
                "08-exam-bank.md",
                "08-exam-record.md",
                "09-feynman-notes.md",
                "09-feynman-record.md",
                "10-cheatsheet.md",
                "run-state.md",
            ):
                destination = run_dir / name
                shutil.copyfile(SKILL_ROOT / "templates" / name, destination)
                materialized = destination.read_text(encoding="utf-8")
                materialized = materialized.replace("待填写", "已填示例")
                materialized = materialized.replace("待检索时补 URL", "C 级示例资源")
                destination.write_text(materialized, encoding="utf-8")

            queue = self.run_cli(
                "review_queue.py",
                "--state-dir",
                str(workspace / ".learn-loop"),
                "--add",
                "--topic",
                "demo topic",
                "--slug",
                "demo-topic",
                "--date",
                "2026-08-02",
            )
            self.assertEqual(0, queue.returncode, queue.stderr)
            index_path = workspace / "learning" / "INDEX.md"
            index_path.write_text(
                index_path.read_text(encoding="utf-8")
                + f"| 2026-08-02 | demo-topic | demo topic | 未施考 | {run_dir.name} |\n",
                encoding="utf-8",
            )
            html = (SKILL_ROOT / "assets/template.html").read_text(encoding="utf-8")
            html = re.sub(r"\{\{[^}]+\}\}", "内容", html)
            (run_dir / "demo-topic.html").write_text(html, encoding="utf-8")

            result = self.run_cli(
                "validate_stage.py",
                "--run-dir",
                str(run_dir),
                "--all",
                "--json",
            )
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            self.assertTrue(json.loads(result.stdout)["ok"])


class LearnLoopValidatorFixtureTest(unittest.TestCase):
    def validate(self, run_dir, stage):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "validate_stage.py"),
                "--run-dir",
                str(run_dir),
                "--stage",
                str(stage),
                "--json",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
        )
        return result, json.loads(result.stdout)

    def copy_templates(self, run_dir, *names):
        run_dir.mkdir(parents=True, exist_ok=True)
        for name in names:
            shutil.copyfile(SKILL_ROOT / "templates" / name, run_dir / name)

    def test_invalid_perspective_count_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            self.copy_templates(run_dir, "01-perspectives.md")
            path = run_dir / "01-perspectives.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace("### 历史学家", "### 缺失视角"),
                encoding="utf-8",
            )
            result, report = self.validate(run_dir, 1)
            self.assertNotEqual(0, result.returncode)
            self.assertTrue(report["violations"]["1"])

    def test_resource_without_url_or_c_grade_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            self.copy_templates(run_dir, "05-resources.md")
            path = run_dir / "05-resources.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace("等级：C", "等级："),
                encoding="utf-8",
            )
            _, report = self.validate(run_dir, 5)
            self.assertTrue(
                any("URL 或 C 级" in item for item in report["violations"]["5"])
            )

    def test_seven_lessons_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            self.copy_templates(run_dir, "07-sprint.md")
            path = run_dir / "07-sprint.md"
            content = path.read_text(encoding="utf-8")
            content = re.sub(
                r"### 第 [7-9] 课：待填写.*?(?=### 第 10 课：待填写)",
                "",
                content,
                flags=re.DOTALL,
            )
            content = re.sub(r"### 第 10 课：待填写.*?(?=### 终局小项目)", "", content, flags=re.DOTALL)
            path.write_text(content, encoding="utf-8")
            _, report = self.validate(run_dir, 7)
            self.assertTrue(any("课程数" in item for item in report["violations"]["7"]))

    def test_bank_with_answer_record_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            self.copy_templates(run_dir, "08-exam-bank.md")
            path = run_dir / "08-exam-bank.md"
            path.write_text(
                path.read_text(encoding="utf-8") + "\n用户回答：代答内容\n",
                encoding="utf-8",
            )
            _, report = self.validate(run_dir, 8)
            self.assertTrue(any("答题/施考记录" in item for item in report["violations"]["8"]))

    def test_exam_cursor_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            self.copy_templates(run_dir, "08-exam-record.md")
            path = run_dir / "08-exam-record.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "\n### 第 1 题\n\n- 逐字引用：用户原话\n- 得分：8/10\n- 差距：无\n",
                encoding="utf-8",
            )
            _, report = self.validate(run_dir, "exam-record")
            self.assertTrue(any("游标" in item for item in report["violations"]["exam-record"]))


if __name__ == "__main__":
    unittest.main()
