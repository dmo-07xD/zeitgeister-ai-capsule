"""Command-line interface for Zeitgeister AI Capsule."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .core import CapsuleError, atomic_write_bytes, atomic_write_text, create_capsule, load_existing_key, load_or_create_key, normalize_input_content, read_capsule, resume_prompt, update_capsule, validate_capsule, verify_capsule, verify_lineage, write_capsule


_IGNORABLE_BOUNDARY_CHARACTERS = " \t\r\n\ufeff\u200b\u200c\u200d\u2060"
_HANDOFF_HINT_FIELDS = {"project_goal", "project_ethos", "provenance"}


def _reject_constant(value: str) -> Any:
    raise CapsuleError(f"Non-standard JSON value '{value}' is not allowed.")


def _clean_json_boundary(value: str) -> str:
    return value.strip(_IGNORABLE_BOUNDARY_CHARACTERS)


def _decode_json_object(raw: str, label: str) -> dict[str, Any]:
    """Find one handoff object in clean JSON, a code fence, or ordinary model prose."""
    if "Sender instruction copied. Paste it into" in raw:
        raise CapsuleError(
            "The clipboard contains the Terminal confirmation, not the sender AI's JSON. "
            "Run sender-prompt --copy again, paste into the sender chat without copying Terminal output, "
            "then copy the AI's completed JSON response."
        )
    if "Prepare a Zeitgeister handoff from" in raw and '"project_goal"' in raw:
        raise CapsuleError(
            "The clipboard still contains the sender instruction template. Paste it into the sender chat, "
            "send it, then copy the AI's completed JSON response."
        )
    cleaned = _clean_json_boundary(raw)
    decoder = json.JSONDecoder(parse_constant=_reject_constant)
    direct_error: json.JSONDecodeError | None = None
    try:
        value = decoder.decode(cleaned)
    except json.JSONDecodeError as exc:
        direct_error = exc
    else:
        if not isinstance(value, dict):
            raise CapsuleError(f"The JSON in {label} is a {type(value).__name__}; a handoff must be one JSON object.")
        return value

    candidates: list[dict[str, Any]] = []
    fenced_blocks = re.findall(
        r"```(?:json)?[^\r\n]*\r?\n(.*?)\r?\n```", cleaned, flags=re.IGNORECASE | re.DOTALL
    )
    search_texts = [_clean_json_boundary(block) for block in fenced_blocks]
    search_texts.append(cleaned)
    for search_text in search_texts:
        for match in re.finditer(r"\{", search_text):
            try:
                candidate, _ = decoder.raw_decode(search_text, match.start())
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict) and _HANDOFF_HINT_FIELDS.issubset(candidate):
                candidates.append(candidate)
                break
    unique: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        fingerprint = json.dumps(candidate, sort_keys=True, ensure_ascii=False, allow_nan=False)
        unique[fingerprint] = candidate
    if len(unique) == 1:
        return next(iter(unique.values()))
    if len(unique) > 1:
        raise CapsuleError(
            f"Multiple complete Zeitgeister JSON objects were found in {label}. Copy only the one response to transfer."
        )
    assert direct_error is not None
    raise CapsuleError(
        f"Could not find one complete Zeitgeister JSON object in {label}. "
        "Copy the entire sender response from its opening '{' through its matching '}'. "
        f"Parser detail: {direct_error.msg} at line {direct_error.lineno}, column {direct_error.colno}."
    ) from direct_error


def _data_text(raw: str, label: str) -> dict[str, Any]:
    value = _decode_json_object(raw, label)
    return normalize_input_content(value)


def _data(path: str) -> dict[str, Any]:
    try:
        raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CapsuleError(f"Input file not found: {path}") from exc
    return _data_text(raw, "standard input" if path == "-" else path)


def _clipboard_read() -> str:
    if sys.platform != "darwin":
        raise CapsuleError("Clipboard input currently uses macOS 'pbpaste'. Use --input FILE on this platform.")
    try:
        result = subprocess.run(["pbpaste"], check=True, capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise CapsuleError("Could not read the macOS clipboard. Copy the sender response, then retry, or use --input FILE.") from exc
    if not result.stdout.strip():
        raise CapsuleError("The clipboard is empty. Copy the sender AI's complete JSON response, then retry.")
    return result.stdout


def _clipboard_write(value: str) -> None:
    if sys.platform != "darwin":
        raise CapsuleError("Clipboard output currently uses macOS 'pbcopy'. Open the generated text file instead.")
    try:
        subprocess.run(["pbcopy"], input=value, text=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise CapsuleError("Could not write to the macOS clipboard. Open the generated text file instead.") from exc


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
        "schema_version": "1.1",
        "project_goal": "string",
        "project_ethos": "string",
        "constraints": ["string"],
        "decisions": [{"decision": "string", "rationale": "string"}],
        "blockers": ["string"],
        "next_steps": ["string"],
        "claims": [
            {"claim": "string", "status": "confirmed | unconfirmed | inferred | disputed", "source_refs": ["string"]}
        ],
        "artifacts": [
            {"name": "string", "transfer_status": "missing | external", "sha256": None, "note": "string"}
        ],
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
        "- Use claims for factual assertions that need evidence status; source_refs may be empty only when the claim is not confirmed.",
        "- Use artifacts to name images/files that are missing or external. Do not mark an artifact included; the local CLI does that only when the file is physically bundled.",
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


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _key_git_ignore_status(key_path: str) -> str:
    candidate = Path(key_path)
    absolute = (Path.cwd() / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    probe = absolute.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        result = subprocess.run(
            ["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return "git-unavailable"
    if result.returncode != 0:
        return "outside-git-repository"
    root = Path(result.stdout.strip()).resolve()
    try:
        relative = absolute.relative_to(root)
    except ValueError:
        return "outside-git-repository"
    ignored = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "-q", "--", str(relative)],
        check=False,
        capture_output=True,
        text=True,
    )
    if ignored.returncode == 0:
        return "ignored"
    if ignored.returncode == 1:
        return "not-ignored"
    return "check-failed"


def _prepare_artifacts(
    content: dict[str, Any], paths: list[str], fail_on_missing: bool
) -> tuple[dict[str, Any], list[tuple[bytes, str]], list[str]]:
    prepared = dict(content)
    records = [dict(item) for item in prepared.get("artifacts", [])]
    by_name = {item["name"]: item for item in records}
    copies: list[tuple[bytes, str]] = []
    physical_names: set[str] = set()
    physical_order: list[str] = []
    for raw_path in paths:
        source = Path(raw_path)
        if not source.is_file():
            raise CapsuleError(f"Artifact file not found or not a regular file: {source}")
        name = source.name
        if name in physical_names:
            raise CapsuleError(f"Two supplied artifacts use the same filename: {name}")
        physical_names.add(name)
        physical_order.append(name)
        payload = source.read_bytes()
        payload_digest = hashlib.sha256(payload).hexdigest()
        record: dict[str, Any] = {
            "name": name,
            "transfer_status": "included",
            "sha256": payload_digest,
            "bundle_path": f"artifacts/{name}",
        }
        if name in by_name and by_name[name].get("note"):
            record["note"] = by_name[name]["note"]
        by_name[name] = record
        copies.append((payload, f"artifacts/{name}"))
    for record in records:
        if record["transfer_status"] == "included" and record["name"] not in physical_names:
            raise CapsuleError(
                f"Artifact '{record['name']}' claims to be included but no matching --artifact file was supplied."
            )
    ordered_names = [item["name"] for item in records]
    for name in physical_order:
        if name not in ordered_names:
            ordered_names.append(name)
    prepared["artifacts"] = [by_name[name] for name in ordered_names]
    missing = [item["name"] for item in prepared["artifacts"] if item["transfer_status"] != "included"]
    provenance_missing = prepared["provenance"].get("missing_artifacts", [])
    if isinstance(provenance_missing, list):
        missing.extend(str(item) for item in provenance_missing if str(item).strip())
    warnings = [f"Artifact not bundled: {name}" for name in dict.fromkeys(missing)]
    if warnings and fail_on_missing:
        raise CapsuleError("Missing artifacts are not allowed in this mode. " + " ".join(warnings))
    return normalize_input_content(prepared), copies, warnings


def _check_claims(content: dict[str, Any], fail_on_unconfirmed: bool) -> None:
    if not fail_on_unconfirmed:
        return
    failures = [
        item["claim"]
        for item in content.get("claims", [])
        if item["status"] != "confirmed" or not item["source_refs"]
    ]
    if failures:
        raise CapsuleError(
            "Unconfirmed or unsourced claims are not allowed in this mode: " + "; ".join(failures)
        )


def _manifest_entry(path: Path, bundle: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(bundle).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": _sha256_path(path),
    }


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
    sender_prompt.add_argument("--copy", action="store_true", help="Copy the instruction to the macOS clipboard.")
    guided = sub.add_parser("guided-transfer", help="Guide a complete clipboard handoff from sender to receiver.")
    guided.add_argument("--from", dest="sender", required=True, help="Sender AI or human label.")
    guided.add_argument("--to", dest="receiver", required=True, help="Receiver AI or human label.")
    guided.add_argument("--key", dest="guided_key", required=True, help="Ignored local key path. Created only if absent.")
    guided.add_argument("--output-dir", default="generated-capsules", help="Parent of the transfer bundle directory.")
    guided.add_argument("--artifact", action="append", default=[], help="Physically include this file; may be repeated.")
    guided.add_argument("--strict", action="store_true", help="Fail on missing artifacts and unconfirmed or unsourced claims.")
    guided.add_argument("--force", action="store_true", help="Replace an existing same-name generated bundle.")
    handoff = sub.add_parser("handoff", help="Create, verify, and export a complete inter-agent handoff in one command.")
    handoff.add_argument("--from", dest="sender", required=True, help="Sender AI name used in output filenames.")
    handoff.add_argument("--to", dest="receiver", required=True, help="Receiver AI name used in the prompt and filenames.")
    handoff.add_argument("--input", required=True, help="Sender JSON file, or '-' to paste JSON through stdin.")
    handoff.add_argument("--key", dest="handoff_key", required=True, help="Ignored local key path. Created only if absent.")
    handoff.add_argument("--output-dir", default="generated-capsules", help="Destination directory (default: generated-capsules).")
    handoff.add_argument("--force", action="store_true", help="Replace an existing handoff with the same sender/receiver filenames.")
    transfer = sub.add_parser("transfer", help="Preferred end-to-end transfer: verify and build a self-describing receiver bundle.")
    transfer.add_argument("--from", dest="sender", required=True, help="Sender AI or human label.")
    transfer.add_argument("--to", dest="receiver", required=True, help="Receiver AI or human label.")
    transfer_input = transfer.add_mutually_exclusive_group(required=True)
    transfer_input.add_argument("--input", help="Sender JSON response file, or '-' for standard input.")
    transfer_input.add_argument("--input-clipboard", action="store_true", help="Read the copied sender response with macOS pbpaste.")
    transfer.add_argument("--key", dest="transfer_key", required=True, help="Ignored local key path. Created only if absent.")
    transfer.add_argument("--output-dir", default="generated-capsules", help="Parent of the transfer bundle directory.")
    transfer.add_argument("--artifact", action="append", default=[], help="Physically include this file; may be repeated.")
    transfer.add_argument("--copy-prompt", action="store_true", help="Copy the verified receiver prompt with macOS pbcopy.")
    transfer.add_argument("--dry-run", action="store_true", help="Validate and show the plan without creating a key or files.")
    transfer.add_argument("--strict", action="store_true", help="Fail on missing artifacts and unconfirmed or unsourced claims.")
    transfer.add_argument("--fail-on-missing-artifacts", action="store_true")
    transfer.add_argument("--fail-on-unconfirmed-sources", action="store_true")
    transfer.add_argument("--force", action="store_true", help="Replace known files in an existing same-name bundle.")
    receiver_prompt = sub.add_parser("receiver-prompt", help="Verify an existing capsule and render its receiver prompt.")
    receiver_prompt.add_argument("capsule")
    receiver_prompt.add_argument("--key", dest="receiver_key", required=True, help="The existing local key used for this capsule.")
    receiver_prompt.add_argument("--to", dest="receiver", required=True, help="Receiver AI or human label.")
    receiver_prompt.add_argument("--output", help="Atomically write the prompt to this file.")
    receiver_prompt.add_argument("--copy", action="store_true", help="Copy the verified prompt with macOS pbcopy.")
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
            if args.copy:
                _clipboard_write(rendered)
                print("COPIED: the full sender instruction is now in your clipboard.")
                print(f"NEXT: switch to {args.sender}, press Command-V, and send the pasted instruction.")
                print("DO NOT copy this Terminal message. After the AI responds, copy its complete JSON response.")
                print(f"The pasted instruction begins: Prepare a Zeitgeister handoff from {args.sender} to {args.receiver}")
            elif not args.output:
                print(rendered, end="")
        elif args.command == "guided-transfer":
            rendered = _sender_prompt(args.sender, args.receiver)
            _clipboard_write(rendered)
            print("COPIED: the sender instruction is now in your clipboard.")
            print(f"1. Switch to {args.sender} and open the conversation you want to transfer.")
            print("2. Press Command-V, send the instruction, and wait for the complete response.")
            print("3. Copy the AI's complete JSON response.")
            try:
                input("4. Return to this Terminal and press Return to continue: ")
            except EOFError as exc:
                raise CapsuleError(
                    "Guided transfer needs an interactive Terminal. Use transfer --input FILE for automation."
                ) from exc
            transfer_args = [
                "transfer",
                "--from", args.sender,
                "--to", args.receiver,
                "--input-clipboard",
                "--key", args.guided_key,
                "--output-dir", args.output_dir,
                "--copy-prompt",
            ]
            for artifact in args.artifact:
                transfer_args.extend(["--artifact", artifact])
            if args.strict:
                transfer_args.append("--strict")
            if args.force:
                transfer_args.append("--force")
            return main(transfer_args)
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
        elif args.command == "transfer":
            raw = _clipboard_read() if args.input_clipboard else None
            content = _data_text(raw, "the clipboard") if raw is not None else _data(args.input)
            if args.input_clipboard:
                print("Clipboard response recognized: one complete Zeitgeister JSON object found and validated.")
            content = dict(content)
            content["provenance"] = dict(content["provenance"])
            content["provenance"]["zeitgeister_transfer"] = {
                "from": args.sender,
                "to": args.receiver,
                "broker": "user-controlled local CLI",
            }
            content, artifact_copies, warnings = _prepare_artifacts(
                content,
                args.artifact,
                args.strict or args.fail_on_missing_artifacts,
            )
            _check_claims(content, args.strict or args.fail_on_unconfirmed_sources)
            sender_slug = _agent_slug(args.sender)
            receiver_slug = _agent_slug(args.receiver)
            stem = f"{sender_slug}-to-{receiver_slug}"
            bundle = Path(args.output_dir) / stem
            key_status = _key_git_ignore_status(args.transfer_key)
            if key_status == "not-ignored":
                raise CapsuleError(
                    f"Refusing to create a key at {args.transfer_key}: it is inside this Git repository but is not ignored. "
                    "Add its directory or filename to .gitignore, then retry."
                )
            if args.strict and key_status in {"git-unavailable", "check-failed"}:
                raise CapsuleError(f"Strict preflight could not confirm the key's Git-ignore status ({key_status}).")
            if args.dry_run:
                print("Transfer dry run passed. No key or output files were created.")
                print(f"Sender: {args.sender}")
                print(f"Receiver: {args.receiver}")
                print(f"Planned bundle: {bundle.resolve()}")
                print(f"Key Git status: {key_status}")
                print(f"Physical artifacts to include: {len(artifact_copies)}")
                for warning in warnings:
                    print("Warning: " + warning)
                return 0
            _refuse_existing([bundle], args.force)
            if bundle.exists() and args.force:
                if bundle.is_symlink() or not bundle.is_dir():
                    raise CapsuleError(f"Refusing --force because the transfer target is not a regular directory: {bundle}")
                shutil.rmtree(bundle)
            transfer_key = load_or_create_key(args.transfer_key)
            capsule = create_capsule(content, transfer_key)
            ok, message = verify_capsule(capsule, transfer_key)
            if not ok:
                raise CapsuleError("Generated capsule failed self-verification. " + message)
            input_path = bundle / "input.json"
            capsule_path = bundle / "capsule.json"
            signature_path = bundle / "capsule.sig"
            report_path = bundle / "verification-report.json"
            prompt_path = bundle / "receiver-prompt.txt"
            summary_path = bundle / "transfer-summary.txt"
            manifest_path = bundle / "manifest.json"
            prompt_text = resume_prompt(capsule, receiver=args.receiver)
            signature_document = {
                "authentication_algorithm": capsule["integrity"]["authentication_algorithm"],
                "key_id": capsule["integrity"]["key_id"],
                "signature": capsule["integrity"]["signature"],
                "note": "This HMAC is not a secret, encryption, or third-party authorship proof.",
            }
            report = {
                "verified": True,
                "message": message,
                "sender": args.sender,
                "receiver": args.receiver,
                "content_hash": capsule["integrity"]["content_hash"],
                "key_id": capsule["integrity"]["key_id"],
                "key_git_ignore_status": key_status,
                "warnings": warnings,
                "trust_scope": "Local HMAC verification detects changes and proves possession of the local key; it does not prove external facts or third-party authorship.",
            }
            artifact_counts = {
                status: sum(1 for item in content["artifacts"] if item["transfer_status"] == status)
                for status in ("included", "missing", "external")
            }
            summary = "\n".join([
                f"Zeitgeister transfer: {args.sender} -> {args.receiver}",
                "Verification: succeeded",
                "Receiver prompt: receiver-prompt.txt",
                f"Artifacts: {artifact_counts['included']} included, {artifact_counts['missing']} missing, {artifact_counts['external']} external",
                f"Warnings: {len(warnings)}",
                "Trust: locally authenticated only; not encrypted, immutable, or third-party authorship verification.",
                "The signing key is not part of this bundle.",
                "",
            ])
            atomic_write_text(input_path, _json_text(content))
            write_capsule(capsule_path, capsule)
            atomic_write_text(signature_path, _json_text(signature_document))
            atomic_write_text(report_path, _json_text(report))
            atomic_write_text(prompt_path, prompt_text)
            atomic_write_text(summary_path, summary)
            for payload, relative_destination in artifact_copies:
                atomic_write_bytes(bundle / relative_destination, payload)
            manifest_files = sorted(
                (path for path in bundle.rglob("*") if path.is_file() and path != manifest_path),
                key=lambda path: path.relative_to(bundle).as_posix(),
            )
            manifest = {
                "format": "zeitgeister-transfer-bundle",
                "version": 1,
                "sender": args.sender,
                "receiver": args.receiver,
                "files": [_manifest_entry(path, bundle) for path in manifest_files],
                "key_included": False,
                "manifest_self_hash_omitted": True,
            }
            atomic_write_text(manifest_path, _json_text(manifest))
            copied = False
            if args.copy_prompt:
                try:
                    _clipboard_write(prompt_text)
                    copied = True
                except CapsuleError as exc:
                    print(f"Warning: {exc}", file=sys.stderr)
            print(message)
            if copied:
                print("COPIED: the verified receiver prompt is now in your clipboard.")
                print(f"NEXT: switch to {args.receiver}, press Command-V, confirm it begins '# Zeitgeister handoff', and send.")
                print("DO NOT copy this Terminal message; the receiver prompt is already copied.")
            else:
                print(f"Transfer ready. Paste this file into {args.receiver}:")
                print(prompt_path.resolve())
            print("Bundle: " + str(bundle.resolve()))
            print("The signing key stayed local and was not displayed or bundled.")
        elif args.command == "receiver-prompt":
            receiver_key = load_existing_key(args.receiver_key)
            capsule = read_capsule(args.capsule)
            ok, message = verify_capsule(capsule, receiver_key)
            if not ok:
                print("Cannot render receiver prompt. " + message, file=sys.stderr)
                return 1
            rendered = resume_prompt(capsule, receiver=args.receiver)
            if args.output:
                atomic_write_text(args.output, rendered)
                print(f"Verified receiver prompt written atomically: {args.output}")
            if args.copy:
                _clipboard_write(rendered)
                print(f"Verified receiver prompt copied. Paste it into {args.receiver}.")
            elif not args.output:
                print(rendered, end="")
    except (CapsuleError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
