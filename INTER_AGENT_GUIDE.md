# Zeitgeister inter-agent guide

Zeitgeister moves deliberate project context between AI chats without requiring a provider API, SDK, plugin, or Codex intermediary. GPT/ChatGPT, Kimi, Gemini, Claude, Grok, Qwen, Copilot, Perplexity, local models, future text-capable agents, and human collaborators are all handled as labels. The protocol does not depend on a provider-specific feature.

The sender writes proposed handoff content. The user-controlled local CLI validates and authenticates it. The receiver gets a verified continuation prompt, never the signing key.

## Recommended: one-command guided transfer

On macOS, run:

```sh
python3 -m zeitgeister guided-transfer --from GPT --to Qwen --key local-state/gpt-to-qwen.key
```

The CLI copies the GPT instruction, displays four numbered steps, and waits. Paste into GPT, copy its completed response, return to the same Terminal, and press Return. Zeitgeister then validates and verifies the capsule and replaces the clipboard with the Qwen prompt. The longer workflow below remains useful when you want to see each independent command.

## Exact manual GPT to Kimi workflow on macOS

Run the following from the cloned Zeitgeister repository. Every Terminal command below is one line; do not copy the explanatory text into Terminal.

### Step 1 — Terminal copies the sender instruction

Paste this one line into Terminal and press Return:

```sh
python3 -m zeitgeister sender-prompt --from GPT --to Kimi --copy
```

Terminal now prints four explicit lines beginning with `COPIED:` and `NEXT:`. Follow the `NEXT:` instruction. Do not select or copy the Terminal confirmation; the full sender instruction is already in the clipboard.

### Step 2 — GPT produces the handoff content

Open the GPT conversation you want to continue. Press Command-V in the GPT message box and send the pasted instruction.

GPT should return one JSON object. Copy GPT's complete response. Zeitgeister locates one complete handoff object in clean JSON, a `json` code block, or ordinary model prose. It also ignores common byte-order marks, zero-width characters, and clipboard boundary noise. Two different complete handoff objects remain an error because choosing between them would be unsafe.

Do not ask GPT to sign or verify anything. Browser GPT normally cannot access the local repository or ignored signing key, and it does not need to.

### Step 3 — Terminal creates, verifies, and copies the Kimi prompt

With GPT's response still copied, paste this one line into Terminal and press Return:

```sh
python3 -m zeitgeister transfer --from GPT --to Kimi --input-clipboard --key local-state/gpt-to-kimi.key --output-dir generated-capsules --copy-prompt
```

Terminal should say that verification succeeded and the prompt is copied. This command performs the local work: schema validation, canonical JSON serialization, SHA-256 hashing, HMAC-SHA256 authentication, verification, bundle creation, and prompt export.

### Step 4 — Kimi accepts the handoff

Open Kimi. Press Command-V in its message box and send. The pasted text is the verified receiver prompt—not the signing key and not a shell command.

Kimi is asked to acknowledge the goal, confirmed decisions, unconfirmed claims, missing artifacts, and first action before continuing.

That is the complete transfer. Codex is not involved.

## Use any sender and receiver

Replace only the two agent labels and the key filename. The same four steps work in either direction and for arbitrary text-capable agents.

| Transfer | Sender command | Transfer command |
| --- | --- | --- |
| Gemini to Claude | `python3 -m zeitgeister sender-prompt --from Gemini --to Claude --copy` | `python3 -m zeitgeister transfer --from Gemini --to Claude --input-clipboard --key local-state/gemini-to-claude.key --output-dir generated-capsules --copy-prompt` |
| Claude to Grok | `python3 -m zeitgeister sender-prompt --from Claude --to Grok --copy` | `python3 -m zeitgeister transfer --from Claude --to Grok --input-clipboard --key local-state/claude-to-grok.key --output-dir generated-capsules --copy-prompt` |
| Grok to Qwen | `python3 -m zeitgeister sender-prompt --from Grok --to Qwen --copy` | `python3 -m zeitgeister transfer --from Grok --to Qwen --input-clipboard --key local-state/grok-to-qwen.key --output-dir generated-capsules --copy-prompt` |
| Qwen to Kimi | `python3 -m zeitgeister sender-prompt --from Qwen --to Kimi --copy` | `python3 -m zeitgeister transfer --from Qwen --to Kimi --input-clipboard --key local-state/qwen-to-kimi.key --output-dir generated-capsules --copy-prompt` |
| Kimi to GPT | `python3 -m zeitgeister sender-prompt --from Kimi --to GPT --copy` | `python3 -m zeitgeister transfer --from Kimi --to GPT --input-clipboard --key local-state/kimi-to-gpt.key --output-dir generated-capsules --copy-prompt` |
| Any future agent | `python3 -m zeitgeister sender-prompt --from "Agent A" --to "Agent B" --copy` | `python3 -m zeitgeister transfer --from "Agent A" --to "Agent B" --input-clipboard --key local-state/agent-a-to-agent-b.key --output-dir generated-capsules --copy-prompt` |

Agent names are not an allowlist. They label provenance and filenames; adding a new provider requires no Zeitgeister code change.

## Transfer files and attachments

If the receiving agent needs an image, PDF, dataset, or other file, physically include it:

```sh
python3 -m zeitgeister transfer --from Qwen --to Grok --input-clipboard --key local-state/qwen-to-grok.key --output-dir generated-capsules --artifact "/full/path/to/quote-image.png" --copy-prompt
```

Zeitgeister copies the file into the bundle, records its SHA-256 hash, and marks it `included`. A sender AI cannot mark a file included by assertion alone. Files that are merely mentioned remain `missing` or `external`, and the receiver prompt displays that status.

## What the bundle contains

For GPT to Kimi, the directory `generated-capsules/gpt-to-kimi/` contains:

- `input.json` — normalized sender content;
- `capsule.json` — canonical locally authenticated capsule;
- `capsule.sig` — non-secret HMAC metadata, not the key;
- `manifest.json` — filenames, byte counts, and SHA-256 hashes;
- `verification-report.json` — local verification result, warnings, and key-ignore status;
- `receiver-prompt.txt` — the only text normally pasted into Kimi;
- `transfer-summary.txt` — short human-readable status;
- `artifacts/` — only files physically supplied with `--artifact`.

The key is never copied into the bundle. `generated-capsules/` and `local-state/` are ignored by this repository.

## Strict and preview modes

Preview without creating a key or files:

```sh
python3 -m zeitgeister transfer --from GPT --to Kimi --input-clipboard --key local-state/gpt-to-kimi.key --output-dir generated-capsules --dry-run
```

Reject missing artifacts plus unconfirmed or unsourced structured claims:

```sh
python3 -m zeitgeister transfer --from GPT --to Kimi --input-clipboard --key local-state/gpt-to-kimi.key --output-dir generated-capsules --strict
```

The narrower switches are `--fail-on-missing-artifacts` and `--fail-on-unconfirmed-sources`. Zeitgeister also refuses to create a project-local key when Git reports that the path is not ignored.

Source strictness is structural: it checks the recorded claim status and presence of source references. It does not browse the web or decide whether an external source is factually correct.

## File-based fallback for other operating systems

The `--copy`, `--input-clipboard`, and `--copy-prompt` conveniences use the built-in macOS `pbcopy` and `pbpaste` commands. On another operating system, write and open files instead:

```sh
python3 -m zeitgeister sender-prompt --from GPT --to Kimi --output generated-capsules/gpt-to-kimi-sender.txt
python3 -m zeitgeister transfer --from GPT --to Kimi --input generated-capsules/gpt-response.json --key local-state/gpt-to-kimi.key --output-dir generated-capsules
```

Paste the complete contents of `generated-capsules/gpt-to-kimi/receiver-prompt.txt` into Kimi. This avoids interactive standard input and the shell continuation prompt that can appear after an incomplete multiline paste.

## Clipboard recovery messages

The CLI now distinguishes the most common mistakes:

- **Terminal confirmation copied:** rerun `sender-prompt --copy`, then press Command-V in the sender chat without copying the Terminal message.
- **Sender template still copied:** send that template to the sender AI, wait for its completed response, then copy the response.
- **One recoverable JSON object inside prose or invisible characters:** Zeitgeister extracts and validates it automatically.
- **Two different complete objects:** copy only the handoff you intend to transfer.
- **Malformed or incomplete JSON:** the error explains that the copy must run from the opening `{` through its matching `}` and preserves the decoder detail.

No manual `pbpaste`, `head`, or Unicode-cleanup command should be necessary.

## Returning work

A receiver's answer is not automatically authenticated by the incoming capsule. To move the updated work back, run a new transfer in the opposite direction. The receiver becomes the sender and returns a fresh JSON handoff.

## Trust scope

Successful verification means that the capsule matches its SHA-256 hash and HMAC under the supplied local key. It detects changes and demonstrates possession of that local key. It does not encrypt content, make records immutable, prove factual claims, authenticate a provider account, or establish third-party authorship. A web-chat receiver without the key cannot independently perform the local HMAC verification; the verification report records what the user-controlled CLI checked before export.
