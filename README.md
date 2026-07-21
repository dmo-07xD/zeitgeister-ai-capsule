# Zeitgeister AI Capsule

Zeitgeister is a zero-dependency Python CLI for handing a project from one AI agent (or person) to another without losing the project’s intent, decisions, blockers, and next action. It is model-neutral and works with GPT/ChatGPT, Gemini, Claude, Grok, Qwen, Kimi, local models, other text-capable agents, and human collaborators. A capsule is deterministic canonical JSON with a SHA-256 content hash and HMAC-SHA256 local authentication.

It is built for the moment when an AI conversation ends but the work should continue coherently: ask the sender AI for structured content, authenticate it locally, then give the generated continuation prompt to any receiver AI. The browser AIs never need access to the signing key or local filesystem.

> **Trust model, plainly:** Zeitgeister detects edits and authenticates a capsule to holders of the same local secret key. It does **not** encrypt capsule content, make it immutable, prove who authored it to a third party, or protect a machine/key that has been compromised. Treat the signing key like a local credential and never share or commit it.

## Simplest GPT-to-Kimi workflow — no Codex intermediary

Requires Python 3.10+ and no packages beyond the standard library.

On macOS, clone the project once, then use two clipboard-safe one-line commands:

```sh
git clone https://github.com/dmo-07xD/zeitgeister-ai-capsule.git
cd zeitgeister-ai-capsule
python3 -m zeitgeister sender-prompt --from GPT --to Kimi --copy
```

Paste into the GPT conversation you want to continue and send. Copy GPT's complete JSON response, return to Terminal, and run this one line:

```sh
python3 -m zeitgeister transfer --from GPT --to Kimi --input-clipboard --key local-state/gpt-to-kimi.key --output-dir generated-capsules --copy-prompt
```

Paste into Kimi and send. Zeitgeister has already validated the sender content, created and locally authenticated the capsule, verified it, written a self-describing ignored bundle, and copied the exact receiver prompt. No JSON file editing, multiline Terminal input, `Ctrl-D`, provider API, or Codex step is required.

The same commands work for Gemini, Claude, Grok, Qwen, Kimi, local models, and any future text-capable agent: replace the sender and receiver labels. These names are not hard-coded integrations or an allowlist. A single JSON fence or one fenced block with brief explanatory prose is accepted.

The browser AI supplies proposed handoff content only. It must not claim that it created or verified a capsule. Local authentication happens exclusively in the user-controlled Zeitgeister CLI, and the key never enters either AI chat.

See [INTER_AGENT_GUIDE.md](INTER_AGENT_GUIDE.md) for exact copy/paste locations, all-provider examples, physical attachments, strict mode, reverse handoffs, non-macOS fallback, and trust boundaries. The neutral [inter-agent input example](examples/inter-agent-handoff-input.json) can be used for a smoke test.

## Manual command workflow

The original individual commands remain available:

```sh
python3 -m zeitgeister --key ./local-state/demo.key create \
  --input examples/dataset-handoff-input.json --output capsule-01.json
python3 -m zeitgeister validate capsule-01.json
python3 -m zeitgeister --key ./local-state/demo.key verify capsule-01.json
python3 -m zeitgeister --key ./local-state/demo.key resume capsule-01.json \
  --format prompt --output generated-capsules/receiver-prompt.txt
```

The first `create`, `handoff`, or `transfer` operation securely generates a random 32-byte key using `secrets.token_bytes`, stores it with owner-only permissions where the platform permits, and never prints it. `transfer` checks that a project-local key path is ignored by Git before creating it. Verification, resume, update, lineage, and receiver-prompt commands never create missing keys; they fail with an actionable message instead. With no global `--key`, the default is `~/.local/state/zeitgeister/signing.key` (or `$XDG_STATE_HOME/zeitgeister/signing.key`). Use a project-local ignored path such as `./local-state/demo.key` for the demo.

## Commands

| Command | What it does |
| --- | --- |
| `sender-prompt --from GPT --to Kimi [--copy]` | Prints or copies the exact schema-constrained instruction for the sender AI. |
| `transfer --from GPT --to Kimi --input-clipboard --key KEY --output-dir DIR --copy-prompt` | Preferred flow: validates, authenticates, verifies, builds a manifest-backed bundle, and copies the receiver prompt. |
| `handoff --from GPT --to Qwen --input INPUT.json --key KEY --output-dir DIR` | Validates, creates, self-verifies, and atomically exports the complete receiver package. |
| `receiver-prompt CAPSULE --key KEY --to Kimi` | Re-verifies an existing capsule before rendering or copying its receiver prompt. |
| `create --input CONTENT.json --output CAPSULE.json` | Creates and HMAC-authenticates a new root capsule. |
| `validate CAPSULE.json` | Checks required structure only; no key required. |
| `verify CAPSULE.json` | Checks structure, content hash, key identity, and HMAC. |
| `resume CAPSULE.json --format prompt [--output FILE]` | Verifies then prints or atomically writes an agent-ready brief. `--format json` exports verified JSON. |
| `update CAPSULE.json --output NEXT.json --next-step TEXT` | Verifies the parent, appends changes, and signs a successor with its parent hash. |
| `verify-lineage FIRST.json NEXT.json ...` | Checks authentication and each ordered parent hash. |

`update` also accepts repeated `--blocker TEXT` and `--decision "decision | rationale"` arguments. It refuses to extend a capsule that does not verify. `transfer` supports `--artifact`, `--dry-run`, `--strict`, focused failure switches, and guarded `--force`; the legacy flat-file `handoff` command remains available for compatibility.

## Capsule format

The sender-facing schema is [schema/zeitgeister-input.schema.json](schema/zeitgeister-input.schema.json). It describes exactly what a GPT, Qwen, Grok, Gemini, Kimi, or other sender chat should return. The authenticated output schema is [schema/zeitgeister-capsule.schema.json](schema/zeitgeister-capsule.schema.json). Every capsule includes:

- `project_goal`, `project_ethos`, `constraints`, decisions with rationales, blockers, next steps, and free-form `provenance` metadata;
- structured claims with `confirmed`, `unconfirmed`, `inferred`, or `disputed` status and source references;
- artifact records marked `included`, `missing`, or `external`; included files must have a SHA-256 hash and be physically supplied to `transfer`;
- UTC creation/update timestamps plus a `parent_hash` (`null` for a root capsule);
- integrity metadata: SHA-256 content hash, HMAC-SHA256 signature, algorithm labels, and a non-secret key identifier.

Constraints, blockers, and next steps must be arrays of non-empty strings; decisions require non-empty `decision` and `rationale` strings; provenance must be one JSON object. These strict checks produce indexed error messages such as `blockers[0] must be a non-empty string` instead of allowing malformed model output to fail later.

The receiver prompt uses readable Markdown sections and includes the complete provenance object, claim status, artifact status, sources, unconfirmed items, a direct receiver action, a short acknowledgement protocol, and an explicit trust scope. This prevents source URLs or missing-artifact warnings from disappearing between chats.

For stable verification, the signed payload is every top-level field except `integrity`, serialized as UTF-8 JSON with lexically sorted keys, compact separators, and no NaN values. The `content_hash` is SHA-256 of that payload. The signature is HMAC-SHA256 of the same payload. The signature and key are deliberately not embedded in a way that exposes the secret: only the HMAC output and a truncated public key identifier appear in a capsule.

## Three-minute presentation demo

```sh
python3 demo.py --guided
```

The guided demo pauses after creation; validation and verification; deliberate tampering and expected verification failure; `resume --format prompt`; authenticated update; and lineage verification. It uses a fictional Political Economy country-quarter workflow, a throwaway local key, and non-sensitive data. Press Enter at each pause; if run without an interactive terminal, it continues automatically.

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

There are 42 unit/integration tests covering deterministic serialization, key permissions, normal verification, malformed and fenced AI input, structured claim and artifact validation, physical artifact hashing, strict preflight failures, dry runs, Git-ignore protection, clipboard transfer, tampering, wrong or missing keys, atomic prompt output, guarded updates, provenance-aware prompt rendering, transfer bundles and manifests, overwrite protection, lineage, and all CLI commands.

## How Codex and GPT-5.6 were used

This MVP was created in a Codex task with GPT-5.6 as the implementation collaborator. The model helped turn the handoff concept into the Python CLI, documentation, demonstration story, and tests; the developer reviewed the stated threat model and ran the verification commands locally. Zeitgeister itself makes no claim that an AI model is a security authority: its assurance comes only from the local HMAC key and repeatable verification.

## License

MIT. See [LICENSE](LICENSE).
