import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from zeitgeister.cli import main


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.key = self.root / "key"
        self.input = self.root / "input.json"
        self.capsule = self.root / "capsule.json"
        self.input.write_text(json.dumps({"project_goal": "Goal", "project_ethos": "Ethos", "constraints": [], "decisions": [], "blockers": [], "next_steps": [], "provenance": {"example": True}}), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_16_full_cli_flow(self):
        self.assertEqual(self.invoke(["--key", str(self.key), "create", "--input", str(self.input), "--output", str(self.capsule)])[0], 0)
        self.assertEqual(self.invoke(["validate", str(self.capsule)])[0], 0)
        self.assertEqual(self.invoke(["--key", str(self.key), "verify", str(self.capsule)])[0], 0)
        code, out, _ = self.invoke(["--key", str(self.key), "resume", str(self.capsule), "--format", "prompt"])
        self.assertEqual(code, 0)
        self.assertIn("Goal", out)

    def test_17_cli_tamper_returns_one(self):
        self.invoke(["--key", str(self.key), "create", "--input", str(self.input), "--output", str(self.capsule)])
        value = json.loads(self.capsule.read_text(encoding="utf-8"))
        value["project_goal"] = "tampered"
        self.capsule.write_text(json.dumps(value), encoding="utf-8")
        self.assertEqual(self.invoke(["--key", str(self.key), "verify", str(self.capsule)])[0], 1)

    def test_18_cli_update_and_lineage(self):
        successor = self.root / "next.json"
        self.invoke(["--key", str(self.key), "create", "--input", str(self.input), "--output", str(self.capsule)])
        self.assertEqual(self.invoke(["--key", str(self.key), "update", str(self.capsule), "--output", str(successor), "--next-step", "Ship"])[0], 0)
        self.assertEqual(self.invoke(["--key", str(self.key), "verify-lineage", str(self.capsule), str(successor)])[0], 0)
