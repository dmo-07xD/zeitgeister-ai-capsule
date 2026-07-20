import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from zeitgeister.core import CapsuleError, canonical_json, create_capsule, load_or_create_key, read_capsule, resume_prompt, update_capsule, validate_capsule, verify_capsule, verify_lineage, write_capsule


def content():
    return {
        "project_goal": "Test goal",
        "project_ethos": "Test ethos",
        "constraints": ["standard library"],
        "decisions": [{"decision": "Use a spine", "rationale": "coverage first"}],
        "blockers": ["none"],
        "next_steps": ["test"],
        "provenance": {"source": "unit test"},
    }


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.key = load_or_create_key(self.root / "key")
        self.capsule = create_capsule(content(), self.key)

    def tearDown(self):
        self.temp.cleanup()

    def test_01_canonical_json_is_stable(self):
        self.assertEqual(canonical_json({"b": 2, "a": 1}), b'{"a":1,"b":2}')

    def test_02_create_verifies(self):
        self.assertTrue(verify_capsule(self.capsule, self.key)[0])

    def test_03_tampered_goal_fails(self):
        self.capsule["project_goal"] = "Changed"
        self.assertFalse(verify_capsule(self.capsule, self.key)[0])

    def test_04_wrong_key_fails(self):
        other = load_or_create_key(self.root / "other-key")
        self.assertFalse(verify_capsule(self.capsule, other)[0])

    def test_05_missing_field_is_invalid(self):
        del self.capsule["project_ethos"]
        self.assertTrue(validate_capsule(self.capsule))

    def test_06_decision_requires_rationale(self):
        bad = content()
        bad["decisions"] = [{"decision": "Only half"}]
        with self.assertRaises(CapsuleError):
            create_capsule(bad, self.key)

    def test_07_round_trip_file(self):
        path = self.root / "capsule.json"
        write_capsule(path, self.capsule)
        self.assertEqual(read_capsule(path)["integrity"], self.capsule["integrity"])

    def test_08_invalid_json_message(self):
        path = self.root / "bad.json"
        path.write_text("{broken", encoding="utf-8")
        with self.assertRaisesRegex(CapsuleError, "Invalid JSON"):
            read_capsule(path)

    def test_09_update_links_parent(self):
        updated = update_capsule(self.capsule, self.key, {"next_steps": ["next"], "blockers": [], "decisions": []})
        self.assertEqual(updated["parent_hash"], self.capsule["integrity"]["content_hash"])

    def test_10_update_verifies(self):
        updated = update_capsule(self.capsule, self.key, {"next_steps": ["next"], "blockers": [], "decisions": []})
        self.assertTrue(verify_capsule(updated, self.key)[0])

    def test_11_lineage_verifies(self):
        updated = update_capsule(self.capsule, self.key, {"next_steps": [], "blockers": [], "decisions": []})
        self.assertTrue(verify_lineage([self.capsule, updated], self.key)[0])

    def test_12_lineage_break_fails(self):
        orphan = create_capsule(content(), self.key)
        self.assertFalse(verify_lineage([self.capsule, orphan], self.key)[0])

    def test_13_resume_prompt_is_honest(self):
        prompt = resume_prompt(self.capsule)
        self.assertIn("not encrypted", prompt)
        self.assertIn("Test goal", prompt)

    def test_14_key_permissions_are_owner_only(self):
        path = self.root / "key"
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_15_refuse_update_tampered(self):
        self.capsule["next_steps"].append("malicious")
        with self.assertRaisesRegex(CapsuleError, "Refusing update"):
            update_capsule(self.capsule, self.key, {"next_steps": [], "blockers": [], "decisions": []})
