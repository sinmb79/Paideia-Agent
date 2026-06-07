# Artifact Schema Inventory

[English](README.md)

Paideia artifacts carry schema names such as `paideia-first-run-doctor/v1`, `paideia-llm-client-result/v1`, and `paideia-tool-execution-artifact-manifest/v1`. This folder is the public inventory for those artifact contracts and the machine-readable JSON Schema validators used by release gates.

## Current Policy

- Every public-safe generated artifact should include a stable `schema` string.
- Schema names must identify whether an artifact is a plan, execution result, doctor report, dossier, memory candidate, or release proof.
- Public artifacts should use summaries, digests, relative paths, and policy flags instead of raw private content.
- Hidden chain-of-thought, provider raw payloads, API keys, and local personal paths are not schema-valid public artifacts.

## First Validation Targets

| Artifact family | Example schema | First validator goal |
| --- | --- | --- |
| First-run readiness | `paideia-first-run-doctor/v1` | Required status, checks, public-safe flags. |
| LLM provider result | `paideia-llm-client-result/v1` | Typed result fields and redaction proof. |
| Tool execution artifact | `paideia-tool-execution-artifact-manifest/v1` | Relative paths, digests, no side-effect leakage. |
| Reasoning Ledger candidate | `paideia-reasoning-ledger-candidate/v1` | Review-gated summary, no private reasoning trace. |
| Hiring dossier | `ai-talent-hiring-dossier/v1` | Identity, transcript, readiness, public-safe metadata. |

## Machine-Readable v1 Schemas

The v1 contracts validate stable identifiers, pass/fail status, public-safe
flags, relative artifact paths, timestamp shape, and the policy fields that
must never permit raw provider payloads or hidden reasoning traces. General
metadata sections may still allow future fields, but public-safety and policy
blocks are intentionally narrow.

| File | Artifact schema |
| --- | --- |
| `first_run_doctor.v1.schema.json` | `paideia-first-run-doctor/v1` |
| `llm_client_result.v1.schema.json` | `paideia-llm-client-result/v1` |
| `tool_execution_artifact_manifest.v1.schema.json` | `paideia-tool-execution-artifact-manifest/v1` |
| `reasoning_ledger_candidate.v1.schema.json` | `paideia-reasoning-ledger-candidate/v1` |
| `hiring_dossier.v1.schema.json` | `ai-talent-hiring-dossier/v1` |

Regression tests cover both accepted generated artifacts and rejected unsafe
mutations, including raw output retention, private reasoning trace retention,
absolute artifact paths, side-effect flags, and malformed timestamps.
