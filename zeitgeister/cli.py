"""Command-line interface for Zeitgeister AI Capsule."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from .core import CapsuleError, atomic_write_text, create_capsule, load_existing_key, load_or_create_key, normalize_input_content, read_capsule, resume_prompt, update_capsule, validate_capsule, verify_capsule, verify_lineage, write_capsule


def _strip_json_fence(value: str) -> str:
    stripped = value.strip()
    fenced = re.findall(r"```(?:json)?[ \t]*\r?\n(.*?)\r?\n```", stripped, flags=re.IGNORECASE | re.DOTALL)
    if len(fenced) == 1:
        return fenced[0].strip()
    if len(fenced) > 1:
        raise CapsuleError("Sender response contains multiple fenced blocks; provide exactly one JSON object.")
    return stripped


def _reject_constant(value: str) -> Any:
    raise CapsuleError(f"Non-standard JSON value '{value}' is not allowed.")


def _data(path: str) -> dict[str, Any]:
    try:
        raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
        value = json.loads(_strip_json_fence(raw), parse_constant=_reject_constant)
    except FileNotFoundError as exc:
        raise CapsuleError(f"Input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CapsuleError(f"Invalid input JSON in {path}: line {exc.lineno}, column {exc.colno}.") from exc
    if not isinstance(value, dict):
        raise CapsuleError("Create input must be a JSON object.")
    return normalize_input_content(value)


def _decision(value: str) -> dict[str, str]:
    if "|" not in value:
        raise argparse.ArgumentTypeError("Decision must be 'decision | rationale'.")
    decision, rationale = (part.strip() for part in value.split("|", 1))
    if not decision or not rationale:
        raise argparse.ArgumentTypeError("Decision and rationale must both be non-empty.")
    return {"decision": decision, "rationale": rationale}


def _agent_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise CapsuleError("Agent names must contain at least one letter or number.")
    return slug[:64]


def _sender_prompt(sender: str, receiver: str) -> str:
    template = {
        "project_goal": "string",
        "project_ethos": "string",
        "constraints": ["string"],
        "decisions": [{"decision": "string", "rationale": "string"}],
        "blockers": ["string"],
        "next_steps": ["string"],
        "provenance": {
            "handoff_from": sender,
            "handoff_to": receiver,
            "sources": [],
            "missing_artifacts": [],
        },
    }
    rendered = json.dumps(template, indent=2, ensure_ascii=False)
    return "\n".join([
        f"Prepare a Zeitgeister handoff from {sender} to {receiver} for this conversation.",
        "",
        "Return only one JSON object, without Markdown fences or explanatory text, using exactly this structure:",
        "",
        rendered,
        "",
        "Requirements:",
        "- Replace every placeholder value such as 'string' with the real conversation content.",
        "- Include only facts supported by this conversation.",
        "- Mark unfinished, uncertain, disputed, or externally unverified items explicitly as unconfirmed.",
        "- Keep constraints, blockers, and next_steps as arrays of plain strings.",
        "- Keep provenance as one JSON object; place source URLs and missing images/files inside it.",
        "- Do not claim to create, save, sign, authenticate, or verify the capsule.",
        "- A local Zeitgeister CLI will validate and authenticate the returned JSON.",
        "- If your interface automatically adds one `json` code fence, that is acceptable; do not add conversational prose.",
    ]) + "\n"


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def _refuse_existing(paths: list[Path], force: bool) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not force:
        rendered = ", ".join(str(path) for path in existing)
        raise CapsuleError(f"Refusing to overwrite existing handoff file(s): {rendered}. Re-run with --force to replace them.")


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(prog="zeitgeister", description="Portable, locally authenticated AI-agent handoffs.")
    command.add_argument("--key", help="Local signing-key path (default: platform state directory).")
    sub = command.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create", help="Create and locally authenticate a capsule.")
    create.add_argument("--input", required=True, help="Content JSON matching schema/zeitgeister-input.schema.json, or '-' for stdin.")
    create.add_argument("--output", required=True)
    validate = sub.add_parser("validate", help="Check JSON structure, without authenticating it.")
    validate.add_argument("capsule")
    verify = sub.add_parser("verify", help="Check structure, SHA-256, and local HMAC authentication.")
    verify.add_argument("capsule")
    resume = sub.add_parser("resume", help="Render an authenticated capsule for an agent handoff.")
    resume.add_argument("capsule")
    resume.add_argument("--format", choices=("prompt", "json"), default="prompt")
    resume.add_argument("--output", help="Atomically write verified output to this file instead of stdout.")
    update = sub.add_parser("update", help="Append updates and create a linked successor capsule.")
    update.add_argument("capsule")
    update.add_argument("--output", required=True)
    update.add_argument("--next-step", action="append", default=[])
    update.add_argument("--blocker", action="append", default=[])
    update.add_argument("--decision", action="append", type=_decision, default=[])
    lineage = sub.add_parser("verify-lineage", help="Verify capsule authentication and parent-hash sequence.")
    lineage.add_argument("capsules", nargs="+")
    sender_prompt = sub.add_parser("sender-prompt", help="Print the exact instruction to paste into a sender AI chat.")
    sender_prompt.add_argument("--from", dest="sender", default="GPT", help="Sender AI name (default: GPT).")
    sender_prompt.add_argument("--to", dest="receiver", required=True, help="Receiver AI name.")
    sender_prompt.add_argument("--output", help="Atomically write the instruction to this file instead of stdout.")
    handoff = sub.add_parser("handoff", help="Create, verify, and export a complete inter-agent handoff in one command.")
    handoff.add_argument("--from", dest="sender", required=True, help="Sender AI name used in output filenames.")
    handoff.add_argument("--to", dest="receiver", required=True, help="Receiver AI name used in the prompt and filenames.")
    handoff.add_argument("--input", required=True, help="Sender JSON file, or '-' to paste JSON through stdin.")
    handoff.add_argument("--key", dest="handoff_key", required=True, help="Ignored local key path. Created only if absent.")
    handoff.add_argument("--output-dir", default="generated-capsules", help="Destination directory (default: generated-capsules).")
    handoff.add_argument("--force", action="store_true", help="Replace an existing handoff with the same sender/receiver filenames.")
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        key = None
        if args.command == "create":
            key = load_or_create_key(args.key)
        elif args.command in {"verify", "resume", "update", "verify-lineage"}:
            key = load_existing_key(args.key)
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
            rendered = resume_prompt(capsule) if args.format == "prompt" else _json_text(capsule)
            if args.output:
                atomic_write_text(args.output, rendered)
                print(f"Verified {args.format} written atomically: {args.output}")
            else:
                print(rendered, end="" if rendered.endswith("\n") else "\n")
        elif args.command == "update":
            successor = update_capsule(read_capsule(args.capsule), key, {"next_steps": args.next_step, "blockers": args.blocker, "decisions": args.decision})
            write_capsule(args.output, successor)
            print(f"Created linked successor capsule: {args.output}")
        elif args.command == "verify-lineage":
            ok, message = verify_lineage([read_capsule(path) for path in args.capsules], key)
            print(message, file=sys.stdout if ok else sys.stderr)
            return 0 if ok else 1
        elif args.command == "sender-prompt":
            rendered = _sender_prompt(args.sender, args.receiver)
            if args.output:
                atomic_write_text(args.output, rendered)
                print(f"Sender instruction written atomically: {args.output}")
            else:
                print(rendered, end="")
        elif args.command == "handoff":
            content = _data(args.input)
            sender_slug = _agent_slug(args.sender)
            receiver_slug = _agent_slug(args.receiver)
            root = Path(args.output_dir)
            stem = f"{sender_slug}-to-{receiver_slug}"
            input_path = root / f"{stem}-input.json"
            capsule_path = root / f"{stem}.capsule.json"
            prompt_path = root / f"{stem}.prompt.txt"
            verified_path = root / f"{stem}.verified.json"
            outputs = [input_path, capsule_path, prompt_path, verified_path]
            _refuse_existing(outputs, args.force)
            handoff_key = load_or_create_key(args.handoff_key)
            capsule = create_capsule(content, handoff_key)
            ok, message = verify_capsule(capsule, handoff_key)
            if not ok:
                raise CapsuleError("Generated capsule failed self-verification. " + message)
            atomic_write_text(input_path, _json_text(content))
            write_capsule(capsule_path, capsule)
            atomic_write_text(prompt_path, resume_prompt(capsule, receiver=args.receiver))
            atomic_write_text(verified_path, _json_text(capsule))
            print(message)
            print("Handoff ready. Paste this file into " + args.receiver + ":")
            print(prompt_path.resolve())
            print("The signing key stayed local and was not displayed.")
    except (CapsuleError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
