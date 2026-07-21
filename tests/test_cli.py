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

    def test_23_verify_missing_key_does_not_create_one(self):
        self.invoke(["--key", str(self.key), "create", "--input", str(self.input), "--output", str(self.capsule)])
        missing = self.root / "missing.key"
        code, _, err = self.invoke(["--key", str(missing), "verify", str(self.capsule)])
        self.assertEqual(code, 2)
        self.assertIn("never create keys", err)
        self.assertFalse(missing.exists())

    def test_24_resume_output_is_verified_and_nonempty(self):
        prompt = self.root / "receiver.txt"
        self.invoke(["--key", str(self.key), "create", "--input", str(self.input), "--output", str(self.capsule)])
        code, out, _ = self.invoke(["--key", str(self.key), "resume", str(self.capsule), "--format", "prompt", "--output", str(prompt)])
        self.assertEqual(code, 0)
        self.assertIn("written atomically", out)
        self.assertIn("## Sources and provenance", prompt.read_text(encoding="utf-8"))

    def test_25_failed_resume_does_not_create_output(self):
        prompt = self.root / "receiver.txt"
        wrong = self.root / "wrong.key"
        self.invoke(["--key", str(self.key), "create", "--input", str(self.input), "--output", str(self.capsule)])
        wrong.write_bytes(b"x" * 32)
        code, _, err = self.invoke(["--key", str(wrong), "resume", str(self.capsule), "--output", str(prompt)])
        self.assertEqual(code, 1)
        self.assertIn("Cannot resume", err)
        self.assertFalse(prompt.exists())

    def test_26_sender_prompt_prevents_fake_execution_claims(self):
        for sender, receiver in [
            ("GPT", "Qwen"),
            ("Gemini", "Claude"),
            ("Claude", "Grok"),
            ("Grok", "Kimi"),
            ("Qwen", "ChatGPT"),
            ("Kimi", "Other Research Agent"),
        ]:
            with self.subTest(sender=sender, receiver=receiver):
                code, out, _ = self.invoke(["sender-prompt", "--from", sender, "--to", receiver])
                self.assertEqual(code, 0)
                self.assertIn('"project_goal"', out)
                self.assertIn(f'"handoff_from": "{sender}"', out)
                self.assertIn(f'"handoff_to": "{receiver}"', out)
                self.assertIn("Do not claim to create, save, sign, authenticate, or verify", out)

    def test_27_handoff_creates_verified_receiver_package(self):
        output_dir = self.root / "generated"
        code, out, _ = self.invoke([
            "handoff", "--from", "GPT", "--to", "Qwen", "--input", str(self.input),
            "--key", str(self.key), "--output-dir", str(output_dir),
        ])
        self.assertEqual(code, 0)
        self.assertIn("Handoff ready", out)
        capsule = output_dir / "gpt-to-qwen.capsule.json"
        prompt = output_dir / "gpt-to-qwen.prompt.txt"
        self.assertTrue(capsule.exists())
        self.assertTrue((output_dir / "gpt-to-qwen-input.json").exists())
        self.assertTrue((output_dir / "gpt-to-qwen.verified.json").exists())
        rendered = prompt.read_text(encoding="utf-8")
        self.assertIn("Qwen: continue from this handoff", rendered)
        self.assertIn("## Sources and provenance", rendered)
        self.assertEqual(self.invoke(["--key", str(self.key), "verify", str(capsule)])[0], 0)

    def test_28_handoff_accepts_json_code_fences(self):
        fenced = self.root / "fenced.txt"
        fenced.write_text(
            "I cannot access your local key, but here is the requested JSON:\n\n```json\n"
            + self.input.read_text(encoding="utf-8")
            + "\n```\n\nSave this content locally.\n",
            encoding="utf-8",
        )
        code, _, _ = self.invoke([
            "handoff", "--from", "Gemini", "--to", "Grok", "--input", str(fenced),
            "--key", str(self.key), "--output-dir", str(self.root / "fenced-output"),
        ])
        self.assertEqual(code, 0)

    def test_29_handoff_rejects_object_blocker_before_key_creation(self):
        bad = json.loads(self.input.read_text(encoding="utf-8"))
        bad["blockers"] = [{"description": "waiting", "status": "unconfirmed"}]
        bad_input = self.root / "bad-input.json"
        bad_input.write_text(json.dumps(bad), encoding="utf-8")
        key = self.root / "bad.key"
        output_dir = self.root / "bad-output"
        code, _, err = self.invoke([
            "handoff", "--from", "GPT", "--to", "Qwen", "--input", str(bad_input),
            "--key", str(key), "--output-dir", str(output_dir),
        ])
        self.assertEqual(code, 2)
        self.assertIn("blockers[0]", err)
        self.assertFalse(key.exists())
        self.assertFalse((output_dir / "gpt-to-qwen.prompt.txt").exists())

    def test_30_handoff_refuses_overwrite_without_force(self):
        args = [
            "handoff", "--from", "GPT", "--to", "Qwen", "--input", str(self.input),
            "--key", str(self.key), "--output-dir", str(self.root / "generated"),
        ]
        self.assertEqual(self.invoke(args)[0], 0)
        code, _, err = self.invoke(args)
        self.assertEqual(code, 2)
        self.assertIn("Refusing to overwrite", err)
        self.assertEqual(self.invoke(args + ["--force"])[0], 0)
