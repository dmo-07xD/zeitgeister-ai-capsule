"""Command-line interface for Zeitgeister AI Capsule."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .core import CapsuleError, create_capsule, load_or_create_key, read_capsule, resume_prompt, update_capsule, validate_capsule, verify_capsule, verify_lineage, write_capsule


def _data(path: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CapsuleError(f"Input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CapsuleError(f"Invalid input JSON in {path}: line {exc.lineno}, column {exc.colno}.") from exc
    if not isinstance(value, dict):
        raise CapsuleError("Create input must be a JSON object.")
    return value


def _decision(value: str) -> dict[str, str]:
    if "|" not in value:
        raise argparse.ArgumentTypeError("Decision must be 'decision | rationale'.")
    decision, rationale = (part.strip() for part in value.split("|", 1))
    if not decision or not rationale:
        raise argparse.ArgumentTypeError("Decision and rationale must both be non-empty.")
    return {"decision": decision, "rationale": rationale}


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(prog="zeitgeister", description="Portable, locally authenticated AI-agent handoffs.")
    command.add_argument("--key", help="Local signing-key path (default: platform state directory).")
    sub = command.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create", help="Create and locally authenticate a capsule.")
    create.add_argument("--input", required=True, help="JSON content matching schema/zeitgeister-capsule.schema.json.")
    create.add_argument("--output", required=True)
    validate = sub.add_parser("validate", help="Check JSON structure, without authenticating it.")
    validate.add_argument("capsule")
    verify = sub.add_parser("verify", help="Check structure, SHA-256, and local HMAC authentication.")
    verify.add_argument("capsule")
    resume = sub.add_parser("resume", help="Render an authenticated capsule for an agent handoff.")
    resume.add_argument("capsule")
    resume.add_argument("--format", choices=("prompt", "json"), default="prompt")
    update = sub.add_parser("update", help="Append updates and create a linked successor capsule.")
    update.add_argument("capsule")
    update.add_argument("--output", required=True)
    update.add_argument("--next-step", action="append", default=[])
    update.add_argument("--blocker", action="append", default=[])
    update.add_argument("--decision", action="append", type=_decision, default=[])
    lineage = sub.add_parser("verify-lineage", help="Verify capsule authentication and parent-hash sequence.")
    lineage.add_argument("capsules", nargs="+")
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        key = load_or_create_key(args.key) if args.command in {"create", "verify", "resume", "update", "verify-lineage"} else None
        if args.command == "create":
            write_capsule(args.output, create_capsule(_data(args.input), key))
            print(f"Created locally authenticated capsule: {args.output}")
        elif args.command == "validate":
            errors = validate_capsule(read_capsule(args.capsule))
            if errors:
                print("Validation failed: " + " ".join(errors), file=sys.stderr)
                return 1
            print("Valid capsule structure.")
        elif args.command == "verify":
            ok, message = verify_capsule(read_capsule(args.capsule), key)
            print(message, file=sys.stdout if ok else sys.stderr)
            return 0 if ok else 1
        elif args.command == "resume":
            capsule = read_capsule(args.capsule)
            ok, message = verify_capsule(capsule, key)
            if not ok:
                print("Cannot resume. " + message, file=sys.stderr)
                return 1
            print(resume_prompt(capsule) if args.format == "prompt" else json.dumps(capsule, indent=2, sort_keys=True))
        elif args.command == "update":
            successor = update_capsule(read_capsule(args.capsule), key, {"next_steps": args.next_step, "blockers": args.blocker, "decisions": args.decision})
            write_capsule(args.output, successor)
            print(f"Created linked successor capsule: {args.output}")
        elif args.command == "verify-lineage":
            ok, message = verify_lineage([read_capsule(path) for path in args.capsules], key)
            print(message, file=sys.stdout if ok else sys.stderr)
            return 0 if ok else 1
    except CapsuleError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
