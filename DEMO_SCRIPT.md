# Zeitgeister AI Capsule — GPT-to-Kimi demo script

Target finished runtime: **2 minutes 40 seconds**. The submitted video must remain under three minutes.

This version demonstrates the most important evolution of the project: Zeitgeister began as a capsule integrity workflow and became a guided, model-neutral bridge between ordinary AI browser conversations. GPT prepares the proposed handoff content. The user-controlled local CLI validates, authenticates, verifies, and packages it. Kimi receives the verified continuation prompt. Codex is not required during the transfer.

## Story profile

The video should communicate five ideas in this order:

1. **The failure:** conversational continuity can lose provenance, uncertainty, and decision rationale.
2. **The design choice:** replace invisible memory with an inspectable capsule.
3. **The crossing:** move a real conversation from GPT to Kimi with one guided Terminal command.
4. **The proof:** show local SHA-256 and HMAC-SHA256 verification plus the transfer bundle.
5. **The boundary:** local authentication is not encryption, immutability, factual truth, or public authorship proof.

## Before recording

### 1. Prepare a short, non-sensitive GPT conversation

Open a new GPT conversation and send this text before recording:

```text
We are planning a fictional Political Economy country-quarter dataset. The confirmed goal is to build a reproducible country-quarter panel. The ethos is to preserve provenance, distinguish observations from plans, and never invent evidence. We decided to build the country-quarter spine before merging measures because it makes coverage gaps and country coding visible. The policy-rate coding convention remains unconfirmed. The next action is to review the spine and document source-specific transformations. No private data or physical artifacts are attached.
```

Leave that conversation open. Do not ask GPT to create or verify a capsule yet.

### 2. Prepare the screen

Arrange three windows or tabs:

- Terminal, with large readable text;
- the prepared GPT conversation;
- a new Kimi conversation.

Hide notifications, passwords, GitHub tokens, clipboard managers, unrelated chats, and private data. The key **path** may appear. The key **contents** must never appear.

### 3. Prepare Terminal

Run this before recording:

```sh
cd "/Users/dmo/Documents/DevPost AI Project"
```

During recording, use this exact command:

```sh
python3 -m zeitgeister guided-transfer --from GPT --to Kimi --key local-state/gpt-to-kimi-demo.key --force
```

`--force` replaces only the existing generated GPT-to-Kimi bundle. It does not expose or replace an existing signing key.

If either model takes more than five seconds to respond, remove or accelerate only the waiting footage. Keep the complete sender instruction, verification result, and receiver acknowledgement visible. A small caption such as **Response wait shortened** keeps the edit honest.

## Shot list and narration

### 0:00–0:18 — Hook

**Screen:** Project title, then the prepared GPT conversation.

**Voiceover:**

“An AI conversation can preserve a conclusion while losing the reason behind it. The next agent receives continuity without provenance, and a misunderstanding can return with greater confidence. Zeitgeister turns that invisible handoff into an object that the user can inspect and verify.”

### 0:18–0:38 — Start the guided crossing

**Screen:** Terminal. Run the exact `guided-transfer` command.

**Voiceover:**

“One command begins a guided transfer from GPT to Kimi. These names are ordinary labels, not provider integrations. Zeitgeister needs no model API, SDK, plugin, or Codex intermediary. The local CLI copies a schema-constrained sender instruction and tells me exactly what to do next.”

### 0:38–1:03 — GPT proposes the handoff

**Screen:** Switch to GPT, paste with Command-V, send, and show the returned JSON. Copy the complete GPT response.

**Voiceover:**

“GPT records the goal, ethos, constraints, decision rationale, unconfirmed policy-rate rule, next action, and provenance. GPT does not sign or verify anything. It cannot see the local key. It only proposes structured content for the user-controlled tool.”

### 1:03–1:32 — Local validation and authentication

**Screen:** Return to Terminal and press Return. Hold on the successful verification and transfer-ready output.

**Voiceover:**

“Zeitgeister finds one complete handoff object even when a model wraps it in a code fence or brief prose. It validates the schema, creates deterministic canonical JSON, calculates a SHA-256 content hash, authenticates the same bytes with HMAC-SHA256, verifies the result, and builds a manifest, verification report, capsule, and receiver prompt. The signing key stays local and never enters either chat.”

### 1:32–2:00 — Kimi receives visible continuity

**Screen:** Switch to Kimi, paste with Command-V, send, and show the acknowledgement.

**Voiceover:**

“The verified Kimi prompt is already in the clipboard. Kimi receives the project goal, confirmed decision, unresolved claim, missing-artifact status, sources, and requested next action. Before continuing, the receiver is asked to acknowledge what it will preserve and what remains uncertain.”

### 2:00–2:20 — Show the proof again

**Screen:** Return to Terminal and run:

```sh
python3 -m zeitgeister --key local-state/gpt-to-kimi-demo.key verify generated-capsules/gpt-to-kimi/capsule.json
```

**Voiceover:**

“The capsule can be verified again from disk. Updates can link successors through parent content hashes, while structured claims and artifact states prevent a source, image, or file from silently becoming more certain during the journey.”

### 2:20–2:40 — Trust boundary and close

**Screen:** README architecture or logo, then the repository URL.

**Voiceover:**

“Zeitgeister provides local authentication and edit detection. It is not encryption, immutability, factual truth, or third-party authorship proof. I built it in Codex with GPT-5.6, which helped shape the architecture, adversarial tests, guided workflow, and honest security language. Forty-two tests now stand between the idea and an easy illusion.”

## Expected Kimi acknowledgement

The exact wording may differ, but the response should visibly cover:

- handoff accepted;
- preserved goal;
- confirmed decision and rationale;
- unconfirmed policy-rate convention;
- no physical artifacts transferred;
- first action: review the spine or document transformations.

If Kimi invents a completed task, source, or artifact, do not hide the mistake. Restart with a clean Kimi conversation and paste the same verified prompt. The demonstration should show the intended receiver acknowledgement, not a fabricated project result.

## Improvements represented in the video

| Earlier friction | Implemented improvement | Visible moment |
| --- | --- | --- |
| A browser AI could not access the ignored key | The agent produces content; the local CLI performs authentication | GPT stage followed by Terminal verification |
| Multiline JSON pasted into a shell caused continuation prompts | Clipboard-safe guided transfer | One Terminal command and Command-V workflow |
| Models wrapped JSON in fences, prose, or invisible characters | Robust extraction of one complete handoff object | Terminal accepts the copied GPT response |
| A receiver could confuse authenticated transport with factual truth | Claim status, provenance, trust scope, and receiver acknowledgement | Kimi states confirmed and unconfirmed items separately |
| Mentioned files vanished between conversations | `included`, `missing`, and `external` artifact states | Kimi sees that no physical artifact was transferred |
| The transfer was difficult to audit | Capsule, signature metadata, manifest, verification report, summary, and prompt bundle | Terminal prints the bundle path |
| Provider-specific instructions multiplied | Sender and receiver are model-neutral labels | GPT-to-Kimi command uses the same generic CLI |

## Recording checklist

- [ ] Finished video is no longer than 2:55; target 2:40.
- [ ] GPT and Kimi names are visible as sender and receiver.
- [ ] The exact guided command appears on screen.
- [ ] The GPT response is copied, not pasted into Terminal as multiline shell text.
- [ ] Successful SHA-256 and HMAC-SHA256 verification is readable.
- [ ] Kimi acknowledges confirmed, unconfirmed, and missing-artifact information.
- [ ] The signing key contents never appear.
- [ ] No GitHub personal access token, credential, private chat, or sensitive data appears.
- [ ] Voiceover explains Codex and GPT-5.6 use.
- [ ] Voiceover says local authentication, not encryption, immutability, factual truth, or public authorship verification.
- [ ] Video is uploaded as **Public** and tested in a signed-out browser window.

## Backup plan

If live browser latency or clipboard permissions make the GPT-to-Kimi recording unreliable, record the same sequence in short continuous clips and join them in order. Do not replace the local verification result with a mock screen. The repository also retains the deterministic fallback demonstration:

```sh
python3 demo.py --guided
```

That fallback proves creation, validation, verification, expected tamper failure, resume, authenticated update, and lineage verification with fictional non-sensitive data.
