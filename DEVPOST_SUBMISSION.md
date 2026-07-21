# Devpost submission copy

## Project Name

Zeitgeister AI Capsule

## One-sentence pitch

A zero-dependency Python CLI that packages an AI project’s intent, decisions, provenance, and next steps into portable, locally authenticated handoffs.

## Project description

AI-assisted work can lose its reasoning and project ethos when a chat ends, context windows change, or work moves to another agent. Copying a transcript preserves noise rather than a deliberate continuation state, while an ordinary summary does not provide a repeatable way to detect later edits.

Zeitgeister AI Capsule creates a compact JSON handoff containing the project goal, ethos, constraints, decisions with rationales, blockers, next steps, provenance, evidence-status claims, artifact status, timestamps, and parent lineage. The Python CLI supports the original `create`, `validate`, `verify`, `resume`, `update`, and `verify-lineage` workflow plus `sender-prompt`, backward-compatible `handoff`, a preferred end-to-end `transfer`, and verified `receiver-prompt` export. `transfer` can read a copied sender response, physically bundle attachments with hashes, create a manifest and verification report, and copy the exact receiver prompt. It is model-neutral: GPT/ChatGPT, Gemini, Claude, Grok, Qwen, Kimi, local models, future agents, and other text-capable collaborators can serve as sender or receiver without provider SDKs or runtime APIs. It uses deterministic canonical JSON, SHA-256 content hashing, and HMAC-SHA256 with a local key. Updates link successors through their parent content hashes.

The demonstration uses fictional, non-sensitive Political Economy country-quarter research to show why provenance and continuity matter in long-running analytical work. Zeitgeister’s security claim is intentionally narrow: it provides local authentication and edit detection for holders of the same key. It does not encrypt content, make records immutable, or prove authorship to third parties.

## How I used Codex/GPT-5.6

I built the MVP in a primary Codex task with GPT-5.6 as the implementation and reasoning collaborator. Codex helped translate the handoff concept into a standard-library architecture, define which fields belong inside the authenticated canonical payload, implement the CLI workflow, document separate sender-input and authenticated-capsule schemas, and create the guided demonstration. It also helped reason through failure cases such as malformed model JSON, wrong or missing keys, empty redirected outputs, missing provenance, tampered content, guarded updates, and broken lineage.

GPT-5.6 was especially useful for refining the threat model and preventing exaggerated security claims. Together, we kept the distinction between SHA-256 content hashing, shared-secret HMAC authentication, encryption, immutability, and public authorship verification explicit. Codex also generated and iterated on the README, sample data, and a 42-test unit/integration suite, which I ran locally. GPT-5.6 is part of the build workflow; Zeitgeister itself has no model or API runtime dependency.

## Track

Developer Tools

## GitHub URL

https://github.com/dmo-07xD/zeitgeister-ai-capsule

## Demo video URL

**UNCONFIRMED — leave blank until the narrated public YouTube video is uploaded.**

## /feedback Session ID

`019f811f-ebab-70a1-808f-bd37b1c2dea7`

## Setup instructions

Requires Python 3.10+ and no third-party packages.

```sh
git clone https://github.com/dmo-07xD/zeitgeister-ai-capsule.git
cd zeitgeister-ai-capsule
python3 -m zeitgeister --key ./local-state/demo.key create \
  --input examples/dataset-handoff-input.json --output capsule-01.json
python3 -m zeitgeister --key ./local-state/demo.key validate capsule-01.json
python3 -m zeitgeister --key ./local-state/demo.key verify capsule-01.json
python3 -m zeitgeister --key ./local-state/demo.key resume capsule-01.json --format prompt
python3 -m unittest discover -s tests -v
python3 demo.py --guided
```

The local key path, generated capsules, local state, credentials, and temporary files are ignored by Git.

## What was the hardest part

The hardest part was defining a useful integrity boundary without turning a local trust mechanism into an inflated security claim. Canonicalization must be deterministic, the integrity metadata must not authenticate itself recursively, updates must verify their parent before extending it, and lineage must be understandable to both humans and agents. At the same time, the product language has to make clear that a shared local HMAC key cannot independently prove who authored a capsule.

## What I learned

I learned that continuity is not just a larger context window. A durable handoff needs a deliberately small schema, decision rationales, provenance, explicit uncertainty, and a verification path. I also learned that security language is part of implementation quality: clearly stating what a mechanism does not provide is as important as demonstrating the successful path.
