# Zeitgeister AI Capsule

Zeitgeister is a zero-dependency Python CLI for handing a project from one AI agent (or person) to another without losing the project’s intent, decisions, blockers, and next action. A capsule is deterministic canonical JSON with a SHA-256 content hash and HMAC-SHA256 local authentication.

It is built for the moment when an AI conversation ends but the work should continue coherently: save a compact, reviewable handoff, verify it locally, then render it as a fresh agent prompt.

> **Trust model, plainly:** Zeitgeister detects edits and authenticates a capsule to holders of the same local secret key. It does **not** encrypt capsule content, make it immutable, prove who authored it to a third party, or protect a machine/key that has been compromised. Treat the signing key like a local credential and never share or commit it.

## Quick start

Requires Python 3.10+ and no packages beyond the standard library.

```sh
git clone https://github.com/dmo-07xD/zeitgeister-ai-capsule.git
cd zeitgeister-ai-capsule
python3 -m zeitgeister --key ./local-state/demo.key create \
  --input examples/dataset-handoff-input.json --output capsule-01.json
python3 -m zeitgeister --key ./local-state/demo.key validate capsule-01.json
python3 -m zeitgeister --key ./local-state/demo.key verify capsule-01.json
python3 -m zeitgeister --key ./local-state/demo.key resume capsule-01.json --format prompt
```

The first signing operation securely generates a random 32-byte key using `secrets.token_bytes`, stores it with owner-only permissions where the platform permits, and never prints it. With no `--key`, the default is `~/.local/state/zeitgeister/signing.key` (or `$XDG_STATE_HOME/zeitgeister/signing.key`). Use a project-local ignored path such as `./local-state/demo.key` for the demo.

## Commands

| Command | What it does |
| --- | --- |
| `create --input CONTENT.json --output CAPSULE.json` | Creates and HMAC-authenticates a new root capsule. |
| `validate CAPSULE.json` | Checks required structure only; no key required. |
| `verify CAPSULE.json` | Checks structure, content hash, key identity, and HMAC. |
| `resume CAPSULE.json --format prompt` | Verifies then prints an agent-ready continuation brief. `--format json` prints verified JSON. |
| `update CAPSULE.json --output NEXT.json --next-step TEXT` | Verifies the parent, appends changes, and signs a successor with its parent hash. |
| `verify-lineage FIRST.json NEXT.json ...` | Checks authentication and each ordered parent hash. |

`update` also accepts repeated `--blocker TEXT` and `--decision "decision | rationale"` arguments. It refuses to extend a capsule that does not verify.

## Capsule format

The documented machine-readable schema is [schema/zeitgeister-capsule.schema.json](schema/zeitgeister-capsule.schema.json). Every capsule includes:

- `project_goal`, `project_ethos`, `constraints`, decisions with rationales, blockers, next steps, and free-form `provenance` metadata;
- UTC creation/update timestamps plus a `parent_hash` (`null` for a root capsule);
- integrity metadata: SHA-256 content hash, HMAC-SHA256 signature, algorithm labels, and a non-secret key identifier.

For stable verification, the signed payload is every top-level field except `integrity`, serialized as UTF-8 JSON with lexically sorted keys, compact separators, and no NaN values. The `content_hash` is SHA-256 of that payload. The signature is HMAC-SHA256 of the same payload. The signature and key are deliberately not embedded in a way that exposes the secret: only the HMAC output and a truncated public key identifier appear in a capsule.

## Three-minute presentation demo

```sh
python3 demo.py --guided
```

The guided demo pauses after creation; validation and verification; `resume --format prompt`; deliberate tampering and expected verification failure; authenticated update; and lineage verification. It uses a fictional Political Economy country-quarter workflow, a throwaway local key, and non-sensitive data. Press Enter at each pause; if run without an interactive terminal, it continues automatically.

For reproducible screenshots, capture these terminal stages (never show the `*.key` file or its contents):

```sh
python3 demo.py --guided
# macOS: use Cmd-Shift-4 after each stage, or record the terminal with your preferred screen recorder.
```

Suggested frames: `01-create.png`, `02-verified-resume.png`, `03-tamper-failed.png`, `04-lineage-verified.png`. The supplied `Zeitgeister logo.png` and `Zeitgeister thumbnail.png` remain unchanged for the Devpost listing.

## Testing

```sh
python3 -m unittest discover -s tests -v
python3 demo.py --guided
```

There are 18 unit/integration tests covering deterministic serialization, key permissions, normal verification, malformed input, tampering, wrong keys, guarded updates, prompt rendering, lineage, and all required CLI commands.

## How Codex and GPT-5.6 were used

This MVP was created in a Codex task with GPT-5.6 as the implementation collaborator. The model helped turn the handoff concept into the Python CLI, documentation, demonstration story, and tests; the developer reviewed the stated threat model and ran the verification commands locally. Zeitgeister itself makes no claim that an AI model is a security authority: its assurance comes only from the local HMAC key and repeatable verification.

## License

MIT. See [LICENSE](LICENSE).
