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
| `task_fingerprint.v1.schema.json` | `paideia-task-fingerprint/v1` |
| `kibo_record.v1.schema.json` | `paideia-kibo-record/v1` |
| `reuse_decision.v1.schema.json` | `paideia-kibo-reuse-decision/v1` |
| `kibo_reuse_plan.v1.schema.json` | `paideia-kibo-reuse-plan/v1` |
| `pattern_candidate.v1.schema.json` | `paideia-pattern-candidate/v1` |
| `pattern_exam_result.v1.schema.json` | `paideia-pattern-exam-result/v1` |
| `real_world_outcome.v1.schema.json` | `paideia-real-world-outcome/v1` |
| `failure_memory.v1.schema.json` | `paideia-failure-memory/v1` |
| `user_decision_model.v1.schema.json` | `paideia-user-decision-model/v1` |
| `critic_report.v1.schema.json` | `paideia-critic-report/v1` |
| `skill_graph.v1.schema.json` | `paideia-skill-graph/v1` |

Regression tests cover both accepted generated artifacts and rejected unsafe
mutations, including raw output retention, private reasoning trace retention,
absolute artifact paths, side-effect flags, and malformed timestamps.
