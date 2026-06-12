# Paideia Agent Roadmap

[English](ROADMAP.md) | [한국어](ROADMAP.ko.md)

Paideia Agent is intentionally broad, but the public preview needs a narrow product spine. This roadmap fixes the MVP boundary so future features can grow without hiding the first usable path.

## Current MVP

```text
Graham Junior offline onboarding
-> assessment and curriculum artifacts
-> Reasoning Ledger / Ariadne Thread
-> hiring dossier
-> local agent kit readiness
-> first-run and runtime doctors
```

The MVP must run without private files, API keys, generated checkpoints, or network calls. Live LLMs, quarantined external references, Agent_warrent registration, and projection swarms can be connected later only after the local deterministic path is proven.

## Feature Status

| Area | Status | Release meaning |
| --- | --- | --- |
| Graham Junior onboarding | Core MVP | Must work offline and remain directly testable. |
| Reasoning Ledger / Ariadne Thread | Core MVP | Reviewable learning record, not hidden chain-of-thought. |
| Hiring dossier and transcript | Core MVP | Must describe education, assessments, reports, and readiness. |
| Local agent kit and doctors | Core MVP | Must install, smoke-test, and fail closed without secrets. |
| LLM provider selection | Core MVP / Optional live | Deterministic local is default; live providers require explicit setup. |
| Agent_warrent / Agent ID Card | Beta | Local export only; owner controls external registration. |
| External reference quarantine | Experimental | Hermes/OpenClaw/community procedures stay reference-only and cannot become active Paideia skills without native rewrite, practice, exam, and review. |
| Projection swarm | Experimental | Parent-controlled task projections; reviewed parent synthesis only. |
| Dashboard / studio UI | Future | Add after CLI runtime and doctors are stable. |
| Local fine-tuning | Future | Add only after data policy, evals, and security gates mature. |

## P0 Hardening

1. Keep the README 3-minute demo path current.
2. Run full tests, compile checks, package build, and public hygiene in CI.
3. Maintain a security threat model for prompt injection, memory poisoning, external reference sources, provider secrets, and generated kits.
4. Keep public artifacts schema-named and inventory them before introducing stricter validators.
5. Split large modules only in small reviewable steps, starting with policy and tool execution boundaries.

## P1 Structure

1. Introduce a typed `LLMResult` and provider contract fixtures.
2. Separate tool specs, planners, executors, and verifiers without breaking public CLI names.
3. Add JSON schema validation for core artifacts.
4. Add one fixed offline Graham Junior end-to-end integration fixture.
5. Add contributor guidance for Codex-assisted changes, release hygiene, and public-safe docs.

## P2 Productization

1. Add a web or desktop dashboard after CLI doctors are stable.
2. Add controlled plugin/skill marketplace flows only after sandbox policy matures.
3. Add OS/container isolation for subprocess and network tools before enabling high-risk execution.
4. Add package publishing automation after the MVP gates have passed repeatedly.

## Non-Goals For The Public Preview

- Cloning or impersonating real people.
- Storing copyrighted textbook bodies in the public repository.
- Uploading owner data, private memories, or generated agents.
- Running live LLM/provider checks without explicit owner action.
- Treating deterministic demos as proof of investment, medical, legal, or security advice.

