import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = PROJECT_ROOT / "paper-trail"
WORKER = SKILL_ROOT / "scripts" / "extract_paper.py"


class PaperTrailPackageContractTest(unittest.TestCase):
    def test_skill_package_contains_every_bundled_artifact(self):
        expected_files = [
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
        ]

        missing = [
            relative_path
            for relative_path in expected_files
            if not (SKILL_ROOT / relative_path).is_file()
        ]

        self.assertEqual([], missing)

    def test_skill_contract_has_no_installation_specific_paths(self):
        skill_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SKILL_ROOT.rglob("*")
            if path.is_file() and path.suffix in {".md", ".yaml", ".py"}
        )

        self.assertNotIn("/home/", skill_text)
        self.assertNotIn(".claude/skills/paper-trail", skill_text)
        self.assertNotIn(".claude/paper-trail", skill_text)
        self.assertNotIn("~/.claude/skills/paper-trail", skill_text)
        self.assertNotIn("~/.claude/paper-trail/profile.md", skill_text)
        self.assertNotIn("triage-log.md", skill_text)
        self.assertIn("<skill-root>", skill_text)
        self.assertIn("<workspace-root>", skill_text)
        self.assertIn("<research-root>", skill_text)


class WorkerHandler(BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        self.__class__.requests.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "body": body,
            }
        )
        user_content = body["messages"][1]["content"]
        content = "正常" if user_content == "回复两个字:正常" else "# 抽取卡\n\n已完成\n"
        response = json.dumps(
            {
                "choices": [{"message": {"content": content}}],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 3,
                    "total_tokens": 15,
                },
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, *_args):
        pass


class ExtractPaperCliTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WorkerHandler.requests = []
        cls.server = HTTPServer(("127.0.0.1", 0), WorkerHandler)
        cls.server_thread = threading.Thread(
            target=cls.server.serve_forever,
            daemon=True,
        )
        cls.server_thread.start()
        cls.worker_env = os.environ | {
            "PAPER_TRAIL_WORKER_BASE_URL": (
                f"http://127.0.0.1:{cls.server.server_port}/v1"
            ),
            "PAPER_TRAIL_WORKER_KEY": "test-key",
            "PAPER_TRAIL_WORKER_MODEL": "test-model",
        }

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=2)

    def test_selftest_calls_openai_compatible_endpoint(self):
        result = subprocess.run(
            ["python3", str(WORKER), "--selftest"],
            env=self.worker_env,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("selftest OK: model=test-model", result.stdout)
        request = WorkerHandler.requests[-1]
        self.assertEqual("/v1/chat/completions", request["path"])
        self.assertEqual("Bearer test-key", request["authorization"])
        self.assertEqual("test-model", request["body"]["model"])

    def test_extract_writes_card_and_reports_usage(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paper = root / "paper.md"
            template = root / "template.md"
            profile = root / "profile.md"
            output = root / "output.md"
            paper.write_text("论文正文证据", encoding="utf-8")
            template.write_text("# 模板字段", encoding="utf-8")
            profile.write_text("算力:4×H20", encoding="utf-8")

            result = subprocess.run(
                [
                    "python3",
                    str(WORKER),
                    "--paper",
                    str(paper),
                    "--template",
                    str(template),
                    "--profile",
                    str(profile),
                    "--out",
                    str(output),
                ],
                env=self.worker_env,
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertEqual("# 抽取卡\n\n已完成\n", output.read_text(encoding="utf-8"))
            self.assertIn('"total_tokens": 15', result.stdout)
            user_message = WorkerHandler.requests[-1]["body"]["messages"][1]["content"]
            self.assertIn("论文正文证据", user_message)
            self.assertIn("算力:4×H20", user_message)

    def test_extract_rejects_oversized_paper_instead_of_silently_truncating(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paper = root / "paper.md"
            template = root / "template.md"
            profile = root / "profile.md"
            output = root / "output.md"
            paper.write_text("证" * 120_001, encoding="utf-8")
            template.write_text("# 模板字段", encoding="utf-8")
            profile.write_text("算力:4×H20", encoding="utf-8")

            result = subprocess.run(
                [
                    "python3",
                    str(WORKER),
                    "--paper",
                    str(paper),
                    "--template",
                    str(template),
                    "--profile",
                    str(profile),
                    "--out",
                    str(output),
                ],
                env=self.worker_env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("正文超过 120000 字符", result.stderr)
            self.assertFalse(output.exists())

    def test_extract_requires_confirmation_for_external_worker(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paper = root / "paper.md"
            template = root / "template.md"
            profile = root / "profile.md"
            output = root / "output.md"
            paper.write_text("论文正文证据", encoding="utf-8")
            template.write_text("# 模板字段", encoding="utf-8")
            profile.write_text("算力:4×H20", encoding="utf-8")
            external_env = self.worker_env | {
                "PAPER_TRAIL_WORKER_BASE_URL": "https://example.invalid/v1",
            }

            result = subprocess.run(
                [
                    "python3",
                    str(WORKER),
                    "--paper",
                    str(paper),
                    "--template",
                    str(template),
                    "--profile",
                    str(profile),
                    "--out",
                    str(output),
                ],
                env=external_env,
                text=True,
                capture_output=True,
                timeout=5,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("外部 worker 端点需要 --desensitized", result.stderr)
            self.assertFalse(output.exists())

    def test_extract_rejects_external_http_even_after_desensitization(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paper = root / "paper.md"
            template = root / "template.md"
            profile = root / "profile.md"
            output = root / "output.md"
            paper.write_text("论文正文证据", encoding="utf-8")
            template.write_text("# 模板字段", encoding="utf-8")
            profile.write_text("算力:4×H20", encoding="utf-8")
            external_env = self.worker_env | {
                "PAPER_TRAIL_WORKER_BASE_URL": "http://example.invalid/v1",
            }

            result = subprocess.run(
                [
                    "python3",
                    str(WORKER),
                    "--paper",
                    str(paper),
                    "--template",
                    str(template),
                    "--profile",
                    str(profile),
                    "--out",
                    str(output),
                    "--desensitized",
                ],
                env=external_env,
                text=True,
                capture_output=True,
                timeout=5,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("外部 worker 端点只允许 HTTPS", result.stderr)
            self.assertFalse(output.exists())


class PortablePreflightCliTest(unittest.TestCase):
    def test_preflight_blocks_an_incomplete_skill_copy(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            relocated_skill = root / "paper-trail"
            workspace = root / "target-workspace"
            shutil.copytree(SKILL_ROOT, relocated_skill)
            workspace.mkdir()
            (relocated_skill / "reference/verify.md").unlink()

            result = subprocess.run(
                [
                    "python3",
                    str(relocated_skill / "scripts/preflight.py"),
                    "--workspace-root",
                    str(workspace),
                    "--bootstrap",
                    "--json",
                ],
                cwd=workspace,
                text=True,
                capture_output=True,
            )
            report = json.loads(result.stdout)

            self.assertEqual(1, result.returncode)
            self.assertEqual("blocked", report["status"])
            self.assertFalse(report["checks"]["skill_package"])
            self.assertIn("reference/verify.md", "\n".join(report["errors"]))

    def test_preflight_falls_back_to_git_root_from_skill_directory(self):
        env = os.environ.copy()
        env.pop("PAPER_TRAIL_WORKSPACE_ROOT", None)

        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory) / "target-workspace"
            relocated_skill = workspace / "tools" / "paper-trail"
            workspace.mkdir()
            shutil.copytree(SKILL_ROOT, relocated_skill)
            subprocess.run(
                ["git", "init", "--quiet"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=True,
            )

            result = subprocess.run(
                [
                    "python3",
                    "scripts/preflight.py",
                    "--bootstrap",
                    "--json",
                ],
                cwd=relocated_skill,
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            report = json.loads(result.stdout)

            self.assertEqual(
                str(workspace.resolve()),
                report["paths"]["workspace_root"],
            )
            self.assertTrue((workspace / ".paper-trail/profile.md").is_file())
            self.assertTrue((workspace / "research/INDEX.md").is_file())
            self.assertFalse((relocated_skill / ".paper-trail").exists())
            self.assertFalse((relocated_skill / "research").exists())

    def test_relocated_skill_bootstraps_an_empty_workspace(self):
        env = os.environ.copy()
        for name in (
            "SEMANTIC_SCHOLAR_API_KEY",
            "PAPER_TRAIL_WORKER_BASE_URL",
            "PAPER_TRAIL_WORKER_KEY",
            "PAPER_TRAIL_WORKER_MODEL",
        ):
            env.pop(name, None)

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            relocated_skill = root / "custom-skill-location" / "paper-trail"
            workspace = root / "empty-target-workspace"
            shutil.copytree(SKILL_ROOT, relocated_skill)
            workspace.mkdir()
            preflight = relocated_skill / "scripts" / "preflight.py"

            result = subprocess.run(
                [
                    "python3",
                    str(preflight),
                    "--workspace-root",
                    str(workspace),
                    "--bootstrap",
                    "--json",
                ],
                cwd=workspace,
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            report = json.loads(result.stdout)

            self.assertEqual("degraded", report["status"])
            self.assertEqual([], report["errors"])
            self.assertTrue(report["checks"]["skill_package"])
            self.assertTrue(report["checks"]["runtime_artifacts"])
            self.assertFalse(report["checks"]["mcp_config"])
            self.assertFalse(report["capabilities"]["s2_api_key"])
            self.assertFalse(report["capabilities"]["worker"])
            self.assertEqual(
                str(relocated_skill.resolve()),
                report["paths"]["skill_root"],
            )
            self.assertEqual(
                str(workspace.resolve()),
                report["paths"]["workspace_root"],
            )
            self.assertTrue((workspace / ".paper-trail/profile.md").is_file())
            self.assertTrue((workspace / "research/INDEX.md").is_file())
            self.assertEqual(
                (relocated_skill / "templates/profile.md").read_text(
                    encoding="utf-8"
                ),
                (workspace / ".paper-trail/profile.md").read_text(
                    encoding="utf-8"
                ),
            )

            custom_profile = "# Existing project profile\n"
            (workspace / ".paper-trail/profile.md").write_text(
                custom_profile,
                encoding="utf-8",
            )
            second_result = subprocess.run(
                [
                    "python3",
                    str(preflight),
                    "--workspace-root",
                    str(workspace),
                    "--bootstrap",
                    "--json",
                ],
                cwd=workspace,
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            second_report = json.loads(second_result.stdout)

            self.assertEqual([], second_report["created"])
            self.assertEqual(
                custom_profile,
                (workspace / ".paper-trail/profile.md").read_text(
                    encoding="utf-8"
                ),
            )

            alternate_workspace = root / "alternate-workspace"
            alternate_workspace.mkdir()
            alternate_state = root / "portable-state"
            alternate_research = root / "portable-research"
            alternate_env = env | {
                "PAPER_TRAIL_STATE_DIR": str(alternate_state),
                "PAPER_TRAIL_RESEARCH_DIR": str(alternate_research),
            }
            alternate_result = subprocess.run(
                [
                    "python3",
                    str(preflight),
                    "--workspace-root",
                    str(alternate_workspace),
                    "--bootstrap",
                    "--json",
                ],
                cwd=alternate_workspace,
                env=alternate_env,
                text=True,
                capture_output=True,
                check=True,
            )
            alternate_report = json.loads(alternate_result.stdout)

            self.assertEqual(
                str(alternate_state),
                alternate_report["paths"]["state_root"],
            )
            self.assertEqual(
                str(alternate_research),
                alternate_report["paths"]["research_root"],
            )
            self.assertTrue((alternate_state / "profile.md").is_file())
            self.assertTrue((alternate_research / "INDEX.md").is_file())


if __name__ == "__main__":
    unittest.main()
