import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = PROJECT_ROOT / ".claude" / "skills" / "paper-trail"
WORKER = SKILL_ROOT / "scripts" / "extract_paper.py"


class PaperTrailProjectContractTest(unittest.TestCase):
    def test_project_skill_has_every_runtime_artifact(self):
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
        self.assertTrue((PROJECT_ROOT / ".claude/paper-trail/profile.md").is_file())
        self.assertTrue((PROJECT_ROOT / "research/INDEX.md").is_file())

    def test_skill_contract_uses_only_project_local_paths(self):
        skill_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SKILL_ROOT.rglob("*")
            if path.is_file() and path.suffix in {".md", ".yaml", ".py"}
        )

        self.assertNotIn("~/.claude/skills/paper-trail", skill_text)
        self.assertNotIn("~/.claude/paper-trail/profile.md", skill_text)
        self.assertNotIn("triage-log.md", skill_text)
        self.assertNotIn("python3 scripts/extract_paper.py", skill_text)
        self.assertIn(".claude/paper-trail/profile.md", skill_text)
        self.assertIn(
            "python3 .claude/skills/paper-trail/scripts/extract_paper.py",
            skill_text,
        )


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


class ProjectPreflightCliTest(unittest.TestCase):
    def test_preflight_reports_pinned_mcp_and_optional_env_degradation(self):
        preflight = SKILL_ROOT / "scripts" / "preflight.py"
        env = os.environ.copy()
        for name in (
            "SEMANTIC_SCHOLAR_API_KEY",
            "PAPER_TRAIL_WORKER_BASE_URL",
            "PAPER_TRAIL_WORKER_KEY",
            "PAPER_TRAIL_WORKER_MODEL",
        ):
            env.pop(name, None)

        result = subprocess.run(
            ["python3", str(preflight), "--json"],
            cwd=PROJECT_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        report = json.loads(result.stdout)

        self.assertEqual("degraded", report["status"])
        self.assertEqual([], report["errors"])
        self.assertTrue(report["checks"]["project_artifacts"])
        self.assertTrue(report["checks"]["mcp_pins"])
        self.assertFalse(report["capabilities"]["s2_api_key"])
        self.assertFalse(report["capabilities"]["worker"])


if __name__ == "__main__":
    unittest.main()
