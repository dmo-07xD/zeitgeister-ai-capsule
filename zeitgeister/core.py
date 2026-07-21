"""Standard-library core for signed Zeitgeister capsules."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import stat
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FORMAT = "zeitgeister-ai-capsule"
VERSION = 1
CONTENT_SCHEMA_VERSION = "1.1"
REQUIRED_CONTENT = ("project_goal", "project_ethos", "constraints", "decisions", "blockers", "next_steps", "provenance")
OPTIONAL_CONTENT = ("schema_version", "claims", "artifacts")
CLAIM_STATUSES = {"confirmed", "unconfirmed", "inferred", "disputed"}
ARTIFACT_STATUSES = {"included", "missing", "external"}


class CapsuleError(ValueError):
    """A capsule is malformed, unverifiable, or cannot be handled safely."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    """Return the one stable byte representation used for hashes and MACs."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def default_key_path() -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return root / "zeitgeister" / "signing.key"


def load_or_create_key(path: str | Path | None = None) -> bytes:
    key_path = Path(path) if path else default_key_path()
    if key_path.exists():
        key = key_path.read_bytes()
        if len(key) < 32:
            raise CapsuleError(f"Signing key at {key_path} is too short; replace it with a fresh 32-byte key.")
        return key
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_bytes(32)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(key_path, flags, 0o600)
    except FileExistsError:
        return load_or_create_key(key_path)
    with os.fdopen(fd, "wb") as handle:
        handle.write(key)
    try:
        key_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return key


def load_existing_key(path: str | Path | None = None) -> bytes:
    """Load a key for verification without ever creating a replacement."""
    key_path = Path(path) if path else default_key_path()
    try:
        key = key_path.read_bytes()
    except FileNotFoundError as exc:
        raise CapsuleError(
            f"Signing key not found: {key_path}. Verification and resume never create keys; "
            "use the same local key that created the capsule."
        ) from exc
    if len(key) < 32:
        raise CapsuleError(f"Signing key at {key_path} is too short; replace it with a fresh 32-byte key.")
    return key


def _payload(capsule: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in capsule.items() if key != "integrity"}


def _content_hash(capsule: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(_payload(capsule))).hexdigest()


def _signature(capsule: dict[str, Any], key: bytes) -> str:
    return hmac.new(key, canonical_json(_payload(capsule)), hashlib.sha256).hexdigest()


def _key_id(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:16]


def normalize_content(content: dict[str, Any]) -> dict[str, Any]:
    missing = [name for name in REQUIRED_CONTENT if name not in content]
    if missing:
        raise CapsuleError("Missing required content field(s): " + ", ".join(missing) + ".")
    normalized = dict(content)
    for name in ("constraints", "decisions", "blockers", "next_steps"):
        if not isinstance(normalized[name], list):
            raise CapsuleError(f"'{name}' must be a JSON list.")
    if not isinstance(normalized["provenance"], dict):
        raise CapsuleError("'provenance' must be a JSON object.")
    for name in ("project_goal", "project_ethos"):
        if not isinstance(normalized[name], str) or not normalized[name].strip():
            raise CapsuleError(f"'{name}' must be a non-empty string.")
    normalized["decisions"] = [
        item if isinstance(item, dict) and item.get("decision") and item.get("rationale")
        else _raise("Each decision must be an object with non-empty 'decision' and 'rationale'.")
        for item in normalized["decisions"]
    ]
    for name in ("constraints", "blockers", "next_steps"):
        for index, item in enumerate(normalized[name]):
            if not isinstance(item, str) or not item.strip():
                raise CapsuleError(
                    f"'{name}[{index}]' must be a non-empty string; received {type(item).__name__}."
                )
    schema_version = normalized.get("schema_version", CONTENT_SCHEMA_VERSION)
    if schema_version != CONTENT_SCHEMA_VERSION:
        raise CapsuleError(f"'schema_version' must equal '{CONTENT_SCHEMA_VERSION}'.")
    normalized["schema_version"] = schema_version
    claims = normalized.get("claims", [])
    if not isinstance(claims, list):
        raise CapsuleError("'claims' must be a JSON list.")
    normalized_claims: list[dict[str, Any]] = []
    for index, item in enumerate(claims):
        if not isinstance(item, dict):
            raise CapsuleError(f"'claims[{index}]' must be a JSON object.")
        unexpected = sorted(set(item) - {"claim", "status", "source_refs"})
        if unexpected:
            raise CapsuleError(f"Unexpected field(s) in 'claims[{index}]': {', '.join(unexpected)}.")
        claim = item.get("claim")
        status_value = item.get("status")
        source_refs = item.get("source_refs")
        if not isinstance(claim, str) or not claim.strip():
            raise CapsuleError(f"'claims[{index}].claim' must be a non-empty string.")
        if status_value not in CLAIM_STATUSES:
            raise CapsuleError(
                f"'claims[{index}].status' must be one of: {', '.join(sorted(CLAIM_STATUSES))}."
            )
        if not isinstance(source_refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in source_refs):
            raise CapsuleError(f"'claims[{index}].source_refs' must be a list of non-empty strings.")
        normalized_claims.append({"claim": claim, "status": status_value, "source_refs": list(source_refs)})
    normalized["claims"] = normalized_claims
    artifacts = normalized.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise CapsuleError("'artifacts' must be a JSON list.")
    normalized_artifacts: list[dict[str, Any]] = []
    for index, item in enumerate(artifacts):
        if not isinstance(item, dict):
            raise CapsuleError(f"'artifacts[{index}]' must be a JSON object.")
        unexpected = sorted(set(item) - {"name", "transfer_status", "sha256", "bundle_path", "note"})
        if unexpected:
            raise CapsuleError(f"Unexpected field(s) in 'artifacts[{index}]': {', '.join(unexpected)}.")
        name = item.get("name")
        transfer_status = item.get("transfer_status")
        digest = item.get("sha256")
        if not isinstance(name, str) or not name.strip():
            raise CapsuleError(f"'artifacts[{index}].name' must be a non-empty string.")
        if transfer_status not in ARTIFACT_STATUSES:
            raise CapsuleError(
                f"'artifacts[{index}].transfer_status' must be one of: {', '.join(sorted(ARTIFACT_STATUSES))}."
            )
        if transfer_status == "included" and (not isinstance(digest, str) or not _is_sha256_hex(digest)):
            raise CapsuleError(f"'artifacts[{index}]' marked included must have a 64-character SHA-256 value.")
        if digest is not None and (not isinstance(digest, str) or not _is_sha256_hex(digest)):
            raise CapsuleError(f"'artifacts[{index}].sha256' must be null or a 64-character lowercase SHA-256 value.")
        for optional_name in ("bundle_path", "note"):
            if optional_name in item and (not isinstance(item[optional_name], str) or not item[optional_name].strip()):
                raise CapsuleError(f"'artifacts[{index}].{optional_name}' must be a non-empty string when present.")
        normalized_artifacts.append(dict(item))
    normalized["artifacts"] = normalized_artifacts
    return normalized


def normalize_input_content(content: dict[str, Any]) -> dict[str, Any]:
    """Validate the content-only document accepted by create and handoff."""
    normalized = normalize_content(content)
    accepted = set(REQUIRED_CONTENT) | set(OPTIONAL_CONTENT)
    unexpected = sorted(set(content) - accepted)
    if unexpected:
        rendered = ", ".join(unexpected)
        raise CapsuleError(
            f"Unexpected input field(s): {rendered}. Create input accepts only "
            f"{', '.join(REQUIRED_CONTENT + OPTIONAL_CONTENT)}; move source metadata under 'provenance'."
        )
    return {name: normalized[name] for name in REQUIRED_CONTENT + OPTIONAL_CONTENT}


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _raise(message: str) -> Any:
    raise CapsuleError(message)


def create_capsule(content: dict[str, Any], key: bytes, parent_hash: str | None = None, created_at: str | None = None) -> dict[str, Any]:
    content = normalize_content(content)
    now = utc_now()
    capsule: dict[str, Any] = {
        "format": FORMAT,
        "version": VERSION,
        "schema_version": content["schema_version"],
        "capsule_id": str(uuid.uuid4()),
        "project_goal": content["project_goal"],
        "project_ethos": content["project_ethos"],
        "constraints": content["constraints"],
        "decisions": content["decisions"],
        "blockers": content["blockers"],
        "next_steps": content["next_steps"],
        "provenance": content["provenance"],
        "claims": content["claims"],
        "artifacts": content["artifacts"],
        "timestamps": {"created_at": created_at or now, "updated_at": now},
        "parent_hash": parent_hash,
    }
    capsule["integrity"] = {
        "content_hash_algorithm": "SHA-256",
        "authentication_algorithm": "HMAC-SHA256",
        "key_id": _key_id(key),
        "content_hash": _content_hash(capsule),
        "signature": _signature(capsule, key),
    }
    return capsule


def validate_capsule(capsule: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(capsule, dict):
        return ["Capsule root must be a JSON object."]
    if capsule.get("format") != FORMAT:
        errors.append(f"'format' must equal '{FORMAT}'.")
    if capsule.get("version") != VERSION:
        errors.append(f"'version' must equal {VERSION}.")
    for field in ("capsule_id", "parent_hash"):
        if field not in capsule:
            errors.append(f"Missing '{field}'.")
    try:
        normalize_content(capsule)
    except CapsuleError as exc:
        errors.append(str(exc))
    timestamps = capsule.get("timestamps")
    if not isinstance(timestamps, dict) or not all(isinstance(timestamps.get(k), str) for k in ("created_at", "updated_at")):
        errors.append("'timestamps' must contain string 'created_at' and 'updated_at'.")
    integrity = capsule.get("integrity")
    if not isinstance(integrity, dict):
        errors.append("Missing 'integrity' metadata object.")
    else:
        for field in ("content_hash_algorithm", "authentication_algorithm", "key_id", "content_hash", "signature"):
            if not isinstance(integrity.get(field), str) or not integrity[field]:
                errors.append(f"Integrity metadata missing non-empty '{field}'.")
        if integrity.get("content_hash_algorithm") != "SHA-256":
            errors.append("'content_hash_algorithm' must equal 'SHA-256'.")
        if integrity.get("authentication_algorithm") != "HMAC-SHA256":
            errors.append("'authentication_algorithm' must equal 'HMAC-SHA256'.")
        for field in ("content_hash", "signature"):
            value = integrity.get(field)
            if isinstance(value, str) and not _is_sha256_hex(value):
                errors.append(f"Integrity '{field}' must be 64 lowercase hexadecimal characters.")
    return errors


def verify_capsule(capsule: Any, key: bytes) -> tuple[bool, str]:
    errors = validate_capsule(capsule)
    if errors:
        return False, "Invalid capsule structure: " + " ".join(errors)
    assert isinstance(capsule, dict)
    integrity = capsule["integrity"]
    expected_hash = _content_hash(capsule)
    if not hmac.compare_digest(integrity["content_hash"], expected_hash):
        return False, "Content hash mismatch: the capsule content was changed or damaged after signing."
    if integrity.get("key_id") != _key_id(key):
        return False, "Signing-key mismatch: use the same local key that authenticated this capsule."
    expected_signature = _signature(capsule, key)
    if not hmac.compare_digest(integrity["signature"], expected_signature):
        return False, "Authentication failed: this capsule was not authenticated by the supplied local key."
    return True, f"Verified: SHA-256 and HMAC-SHA256 match (content {expected_hash[:12]}…)."


def read_capsule(path: str | Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CapsuleError(f"Capsule file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CapsuleError(f"Invalid JSON in {path}: line {exc.lineno}, column {exc.colno}.") from exc


def atomic_write_bytes(path: str | Path, value: bytes) -> None:
    """Replace a file only after its complete contents are safely staged."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=f".{destination.name}.", delete=False) as handle:
            temporary_name = handle.name
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    except Exception:
        if temporary_name:
            try:
                Path(temporary_name).unlink()
            except FileNotFoundError:
                pass
        raise


def atomic_write_text(path: str | Path, value: str) -> None:
    atomic_write_bytes(path, value.encode("utf-8"))


def write_capsule(path: str | Path, capsule: dict[str, Any]) -> None:
    atomic_write_bytes(path, canonical_json(capsule) + b"\n")


def update_capsule(existing: dict[str, Any], key: bytes, additions: dict[str, list[Any]]) -> dict[str, Any]:
    ok, message = verify_capsule(existing, key)
    if not ok:
        raise CapsuleError("Refusing update of an unverified capsule. " + message)
    content = {name: existing[name] for name in REQUIRED_CONTENT}
    for name in OPTIONAL_CONTENT:
        if name in existing:
            content[name] = existing[name]
    for field in ("decisions", "blockers", "next_steps"):
        content[field] = list(content[field]) + list(additions.get(field, []))
    return create_capsule(content, key, parent_hash=existing["integrity"]["content_hash"], created_at=existing["timestamps"]["created_at"])


def _bullets(values: list[str], empty: str) -> str:
    return "\n".join(f"- {value}" for value in values) if values else f"- {empty}"


def resume_prompt(capsule: dict[str, Any], receiver: str | None = None) -> str:
    receiver_label = receiver.strip() if receiver and receiver.strip() else "Receiving AI"
    decisions = "\n".join(
        f"- **{item['decision']}**\n  Rationale: {item['rationale']}" for item in capsule["decisions"]
    ) or "- None recorded."
    provenance = json.dumps(capsule["provenance"], indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
    claims = capsule.get("claims", [])
    claim_lines = "\n".join(
        f"- **{item['status'].upper()}** — {item['claim']}"
        + (f" (sources: {', '.join(item['source_refs'])})" if item["source_refs"] else " (no source supplied)")
        for item in claims
    ) or "- No structured claims recorded."
    artifacts = capsule.get("artifacts", [])
    artifact_lines = "\n".join(
        f"- **{item['transfer_status'].upper()}** — {item['name']}"
        + (f" (`{item['bundle_path']}`)" if item.get("bundle_path") else "")
        + (f" — {item['note']}" if item.get("note") else "")
        for item in artifacts
    ) or "- No artifacts recorded."
    return "\n".join([
        "# Zeitgeister handoff",
        "",
        "## Goal",
        capsule["project_goal"],
        "",
        "## Ethos",
        capsule["project_ethos"],
        "",
        "## Constraints",
        _bullets(capsule["constraints"], "None recorded."),
        "",
        "## Recorded decisions",
        decisions,
        "",
        "## Blockers and unconfirmed items",
        _bullets(capsule["blockers"], "None recorded."),
        "",
        "## Claims and evidence status",
        claim_lines,
        "",
        "## Artifact transfer status",
        artifact_lines,
        "",
        "## Next steps",
        "\n".join(f"{index}. {value}" for index, value in enumerate(capsule["next_steps"], 1)) or "1. None recorded.",
        "",
        "## Sources and provenance",
        "```json",
        provenance,
        "```",
        "",
        "## Action requested",
        f"{receiver_label}: continue from this handoff. Preserve the goal, ethos, recorded decisions, uncertainties, and sources. Begin with the listed next steps, and do not invent missing facts or artifacts.",
        "",
        "## Receiver acknowledgement",
        "Before doing substantive work, briefly state: (1) handoff accepted, (2) the goal you will preserve, (3) the confirmed decisions you will respect, (4) any unconfirmed claims or missing artifacts, and (5) your first action.",
        "",
        "## Trust scope",
        "This prompt was exported only after local SHA-256 and HMAC-SHA256 verification by the user-controlled Zeitgeister CLI.",
        "A receiving AI without the local key cannot independently authenticate it.",
        "It is locally authenticated, not encrypted, immutable, or independently authored. Authentication detects changes and proves possession of the shared local key; it does not establish that external claims are factually true.",
    ]) + "\n"


def verify_lineage(capsules: list[dict[str, Any]], key: bytes) -> tuple[bool, str]:
    if not capsules:
        return False, "No capsules supplied for lineage verification."
    previous_hash: str | None = None
    for index, capsule in enumerate(capsules, 1):
        ok, message = verify_capsule(capsule, key)
        if not ok:
            return False, f"Capsule {index} failed verification. {message}"
        if capsule.get("parent_hash") != previous_hash:
            expected = previous_hash or "null (a root capsule)"
            return False, f"Lineage break at capsule {index}: expected parent_hash {expected}."
        previous_hash = capsule["integrity"]["content_hash"]
    return True, f"Lineage verified: {len(capsules)} locally authenticated capsule(s) link in order."
