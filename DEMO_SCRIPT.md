# Zeitgeister AI Capsule — 2:45 demo script

Target runtime: **2 minutes 45 seconds**. The video must stay under three minutes.

## Before recording

Open Terminal, enlarge the text enough to read, and run these exact commands:

```sh
cd "/Users/dmo/Documents/DevPost AI Project"
python3 demo.py --guided
```

The guided program displays the underlying CLI commands with the temporary signing-key path redacted. Press Return once at each stage when the narration reaches the indicated cue. Do not show any GitHub token, signing key, credential, or private data.

## Narration

### 0:00–0:15 — Problem

“AI work often loses its context when a session ends or a project moves to another agent. Zeitgeister AI Capsule preserves the goal, ethos, constraints, decisions, blockers, next steps, and provenance in a portable JSON handoff. I built this developer tool with Codex using GPT-5.6.”

### 0:15–0:45 — Create

**Press Return for stage 1.**

“This fictional Political Economy example represents a country-quarter research workflow. The create command reads non-sensitive handoff content, serializes it as deterministic canonical JSON, computes a SHA-256 content hash, and adds local HMAC-SHA256 authentication. The random local key is temporary, redacted from the display, and never committed.”

### 0:45–1:15 — Validate and verify

**Press Return for stage 2.**

“Validate checks the documented capsule structure. Verify then recomputes the content hash and checks the HMAC with the local key. The successful result shows that the capsule has the expected structure and has not changed since a holder of this key authenticated it. This is local authentication—not encryption, immutability, or third-party proof of authorship.”

### 1:15–1:30 — Tamper detection

**Press Return for stage 3.**

“The demo changes one next step without re-authenticating the capsule. Verification now fails with an actionable content-hash mismatch, demonstrating local tamper evidence.”

### 1:30–2:00 — Resume

**Press Return for stage 4.**

“Resume first verifies the original capsule, then renders an agent-ready prompt. A fresh agent can immediately see the research goal, ethos, constraints, decision rationale, blocker, and next actions. The trust note stays attached so the next agent does not overstate what HMAC proves.”

### 2:00–2:30 — Update and lineage

**Press Return for stage 5, then stage 6.**

“Update refuses an unverified parent, appends the new decision and next step, and creates a signed successor whose parent hash points to the original. Verify-lineage authenticates both capsules and confirms their order, giving the handoff a reproducible local history.”

### 2:30–2:45 — Close and disclose Codex/GPT-5.6 use

“Zeitgeister AI Capsule was built in Codex with GPT-5.6. Codex accelerated the architecture, canonical signing boundary, CLI implementation, threat-model wording, schema, demo, documentation, and eighteen tests. GPT-5.6 was the build-time reasoning model, not a runtime dependency. Zeitgeister keeps AI-agent continuity portable, explicit, and honestly scoped.”

## Recording checklist

- Keep the final video at or below 2:55, preferably 2:45.
- Include the spoken Codex/GPT-5.6 disclosure in the closing segment.
- Upload to YouTube as **Public**, then test the URL in a private browser window.
- If a stage runs long, shorten pauses rather than removing the trust-model explanation.
