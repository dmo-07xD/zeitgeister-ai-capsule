#!/usr/bin/env python3
"""A guided, non-sensitive demonstration of a Zeitgeister handoff."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from zeitgeister.cli import main as cli


def stage(title: str, guided: bool) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
    if guided:
        try:
            input("Press Enter to continue… ")
        except EOFError:
            print("(No interactive input available; continuing.)")


def run(args: list[str]) -> None:
    shown = list(args)
    if "--key" in shown:
        shown[shown.index("--key") + 1] = "[local key]"
    print("$ python3 -m zeitgeister", " ".join(shown))
    result = cli(args)
    if result:
        raise SystemExit(f"Demo command unexpectedly failed with exit code {result}.")


def main() -> int:
    options = argparse.ArgumentParser(description="Zeitgeister MVP demo")
    options.add_argument("--guided", action="store_true", help="Pause between each demonstration stage.")
    guided = options.parse_args().guided
    with tempfile.TemporaryDirectory(prefix="zeitgeister-demo-") as directory:
        workspace = Path(directory)
        key = workspace / "local-demo.key"  # temporary; never printed or committed
        source = workspace / "dataset-handoff-input.json"
        original = workspace / "capsule-01.json"
        tampered = workspace / "capsule-tampered.json"
        successor = workspace / "capsule-02.json"
        source.write_text(json.dumps({
            "project_goal": "Build a reproducible country-quarter panel for a fictional Political Economy study.",
            "project_ethos": "Keep source lineage visible, distinguish observations from plans, and never invent evidence.",
            "constraints": ["Use public, non-sensitive sample data only", "Keep raw inputs immutable", "Do not merge before a country-quarter spine is reviewed"],
            "decisions": [{"decision": "Start with a country-quarter spine", "rationale": "It makes coverage gaps and country coding explicit before measure merges."}],
            "blockers": ["The fictional policy-rate coding convention still needs supervisor approval."],
            "next_steps": ["Review the spine with the research team", "Document source-specific transformations"],
            "provenance": {"authoring_context": "Fictional demo; no real respondents or confidential data", "sources": ["Illustrative country and quarter labels"], "tool": "Zeitgeister AI Capsule MVP"}
        }, indent=2), encoding="utf-8")
        common = ["--key", str(key)]
        stage("1. Create: capture a portable project handoff", guided)
        run(common + ["create", "--input", str(source), "--output", str(original)])
        stage("2. Validate and verify: check shape, content hash, and local authentication", guided)
        run(["validate", str(original)])
        run(common + ["verify", str(original)])
        stage("3. Tampering: changing content makes verification fail", guided)
        changed = json.loads(original.read_text(encoding="utf-8"))
        changed["next_steps"].append("Quietly substitute an unreviewed source")
        tampered.write_text(json.dumps(changed), encoding="utf-8")
        print("$ python3 -m zeitgeister --key [local key] verify", tampered)
        result = cli(common + ["verify", str(tampered)])
        print("Expected failed verification." if result else "Unexpected verification success!")
        stage("4. Resume: turn the authenticated handoff into an agent-ready prompt", guided)
        run(common + ["resume", str(original), "--format", "prompt"])
        stage("5. Update: append a decision and link the successor to its verified parent", guided)
        run(common + ["update", str(original), "--output", str(successor), "--decision", "Document every transformation | Reproducibility requires auditable changes.", "--next-step", "Begin the approved fictional acquisition plan"])
        stage("6. Verify lineage: confirm the two authenticated capsules link in order", guided)
        run(common + ["verify-lineage", str(original), str(successor)])
        print("\nDemo complete. The temporary local signing key was never displayed or written to this repository.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
