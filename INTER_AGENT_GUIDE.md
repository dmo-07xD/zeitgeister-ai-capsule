# Zeitgeister inter-agent guide

Zeitgeister is model-neutral. It can broker a handoff between GPT/ChatGPT, Gemini, Claude, Grok, Qwen, Kimi, another AI chat, or a human collaborator. No provider plugin, API key, model SDK, or Codex session is required.

The local CLI is the broker:

1. The sender AI proposes structured JSON.
2. Zeitgeister validates, authenticates, verifies, and exports it on your computer.
3. The receiver AI gets the generated prompt, never the signing key.

Ordinary browser chats cannot access your local repository or ignored key. Do not ask them to create or verify a capsule; use `sender-prompt` to ask only for the content they can actually provide.

## Universal three-step workflow

Run commands from the Zeitgeister repository.

### 1. Generate the sender instruction

Replace the names with any sender and receiver:

```sh
python3 -m zeitgeister sender-prompt --from GPT --to Qwen
```

Paste the printed instruction into the sender chat. The instruction requires the current content-only schema, tells the sender to label uncertainty, and prevents it from falsely claiming local execution or verification.

### 2. Create the verified handoff locally

The shortest route does not require saving the sender response first:

```sh
python3 -m zeitgeister handoff \
  --from GPT \
  --to Qwen \
  --input - \
  --key local-state/gpt-to-qwen.key \
  --output-dir generated-capsules
```

Paste the sender's complete JSON into Terminal and press Ctrl-D on macOS/Linux. Zeitgeister accepts a bare JSON object, one `json` fenced block, or one fenced block surrounded by a sender's explanatory prose. It refuses ambiguous responses containing multiple fenced blocks.

To use a saved response instead, replace `--input -` with its path:

```sh
python3 -m zeitgeister handoff \
  --from GPT \
  --to Qwen \
  --input generated-capsules/gpt-response.json \
  --key local-state/gpt-to-qwen.key \
  --output-dir generated-capsules
```

### 3. Paste the receiver prompt

After successful verification, Zeitgeister prints an absolute prompt path such as:

```text
Handoff ready. Paste this file into Qwen:
/path/to/generated-capsules/gpt-to-qwen.prompt.txt
```

Paste that file's complete contents into the receiver. It already contains the goal, ethos, constraints, recorded decisions, blockers, next steps, complete provenance, sources, missing-artifact notes, receiver action, and honest trust scope. No extra command or wrapper prompt is required.

## Provider examples

All names are labels rather than hard-coded provider integrations:

```sh
python3 -m zeitgeister sender-prompt --from GPT --to Gemini
python3 -m zeitgeister sender-prompt --from Gemini --to Claude
python3 -m zeitgeister sender-prompt --from Claude --to Grok
python3 -m zeitgeister sender-prompt --from Grok --to Qwen
python3 -m zeitgeister sender-prompt --from Qwen --to Kimi
python3 -m zeitgeister sender-prompt --from Kimi --to GPT
python3 -m zeitgeister sender-prompt --from "Local Model" --to "Research Agent"
```

Use the same names in `handoff`. Zeitgeister safely normalizes them only for output filenames; the human-readable receiver name remains in the prompt.

## Files produced

For `--from GPT --to Qwen`, `handoff` atomically writes:

- `gpt-to-qwen-input.json` — normalized sender content;
- `gpt-to-qwen.capsule.json` — canonical authenticated capsule;
- `gpt-to-qwen.prompt.txt` — the only file normally pasted into Qwen;
- `gpt-to-qwen.verified.json` — readable verified capsule JSON.

The key remains at the specified local path and is never displayed or placed in the prompt. Use an ignored directory such as `local-state/`; use an ignored output directory such as `generated-capsules/`. Zeitgeister refuses to replace an existing same-name package unless you deliberately add `--force`.

## Returning work to the original agent

For a return handoff, repeat the workflow in the opposite direction. Ask the current agent for a fresh sender JSON, then run:

```sh
python3 -m zeitgeister handoff \
  --from Qwen \
  --to GPT \
  --input - \
  --key local-state/qwen-to-gpt.key \
  --output-dir generated-capsules
```

Do not treat a receiver's narrative response as authenticated merely because the earlier incoming prompt was authenticated. Create a new local capsule for the return transfer.

## Facts, sources, and attachments

HMAC verification establishes that the locally authenticated capsule has not changed and that its creator possessed the local shared key. It does not establish that an external quote, job listing, historical claim, or web page is true.

The sender should place source URLs, verification timestamps, evidence status, and missing attachments inside `provenance`. The receiver prompt includes that entire object. Images and other attachments are not embedded automatically; attach them separately or record their absence under `missing_artifacts`.

## Common errors

- **The sender says it cannot access the repository or key:** expected. Use `sender-prompt`; the sender should return JSON only.
- **A list item is an object:** ask the sender to return plain strings for constraints, blockers, and next steps.
- **Provenance is an array:** ask for one provenance object containing arrays such as `sources` and `missing_artifacts`.
- **A prompt file already exists:** use a different sender/receiver label or review the existing package before deliberately adding `--force`.
- **A key is missing during verification:** locate the original key. Verification never generates a replacement.
- **The receiver cannot independently verify:** expected for an ordinary web chat without the key. The local user-controlled CLI performed the verification before export.
