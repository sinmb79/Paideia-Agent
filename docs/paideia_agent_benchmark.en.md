# Paideia Agent Benchmark: Lessons From Hermes And OpenClaw

This note summarizes which ideas Paideia Agent borrows from Hermes/OpenClaw-style agents and where it deliberately diverges.

## Why Benchmark These Agent Runtimes

Hermes and OpenClaw are useful references because they show what a modern installed agent needs beyond a chat prompt:

- installable runtime entrypoints,
- persistent memory,
- skills as reusable procedural knowledge,
- workspace files that shape behavior,
- model/provider configuration,
- tool and channel adapters,
- doctor or troubleshooting surfaces,
- migration paths from adjacent ecosystems.

Paideia needs those runtime conveniences, but it is not trying to be only an agent shell. Its core product is an AI education center: an owner raises an AI talent, verifies its curriculum and work record, then hires the resulting talent as an agent.

## Hermes Patterns To Reuse

Hermes presents itself as a self-improving agent with a built-in learning loop. The project emphasizes memory, skill creation, skill improvement during use, cross-session recall, toolsets, MCP integration, and multi-platform messaging.

Paideia adapts this as:

- Reasoning Ledger / Ariadne Thread for reviewable learning evolution (`reasoning_kibo.jsonl` remains the internal compatibility filename),
- `learning_ledger.json` for quality-gated experience promotion,
- `memory_substrate.json` for bounded recall,
- adapter manifests for future external runtimes,
- external-reference quarantine support for third-party procedure folders.

What Paideia does differently:

- no unlimited transcript replay,
- no hidden chain-of-thought storage,
- no automatic trust in community skills,
- no assumption that a runtime profile is the same as a trained AI talent.

## OpenClaw Patterns To Reuse

OpenClaw's repository and documentation make the workspace model very concrete: agent workspace, injected context files, skills in workspace folders, local configuration, gateway/channel routing, and active memory.

Paideia adapts this as:

- per-talent install kits,
- `doctor-agent-program`,
- local storage outside the source tree,
- `references/external/<runtime>/<reference>/` for quarantined external reference material,
- bounded active memory routing into chat/work runs,
- future gateway adapters that start disabled.

What Paideia does differently:

- external procedures are quarantined as reference material by default,
- external channels are disabled until explicitly configured,
- each hired talent receives isolated runtime records,
- useful ideas require Paideia-native rewrite, guided practice, timed exam or task trial, owner review, and test evidence before they can influence memory or reasoning kibo.

## External Reference Quarantine

Paideia supports this command:

```powershell
ai22b-talent-foundry intake-external-references `
  --source C:\path\to\hermes-or-openclaw-skill `
  --paideia-kit C:\path\to\paideia-agent-kit `
  --source-runtime hermes
```

The reference-intake layer detects `SKILL.md`, `skill.yaml`, `skill.yml`, `hermes.yaml`, `hermes.yml`, and README-based generic procedure folders. It copies source files into the Paideia kit as reference material, rewrites source `SKILL.md` files to `SOURCE_SKILL_REFERENCE.md`, writes `REFERENCE.md`, and creates `paideia_external_reference_manifest.json`, `paideia_reference_compatibility_profile.json`, and `paideia_reference_review.md`. It does not create an active `SKILL.md` descriptor.

Default policy:

- `execute_external_code = false`
- `direct_external_use.status = forbidden`
- `boss_review_required = true`
- `third_party_skills_trusted = false`
- `intake_mode = quarantine_reference_rewrite_as_training_only`
- `guided_practice_required = true`
- `timed_exam_or_task_trial_required = true`
- external procedures remain reference-only until useful ideas are rewritten as Paideia-native training, practiced, tested, and reviewed
- the internalization gate remains locked until rewrite, guided-practice, timed-exam, owner-review, and work-evidence artifacts exist

Risk scanning currently flags:

- remote shell pipes such as `curl | bash` or PowerShell download-then-execute patterns,
- `Invoke-Expression`,
- recursive delete commands,
- credential/token/private-key access patterns,
- local or network listener patterns.

## Paideia's Main Differentiator

Hermes/OpenClaw-style agents are strong once an agent already exists. Paideia adds the missing upstream layer:

```text
education -> assessment -> memory formation -> hiring dossier -> installable agent -> work -> reviewed growth
```

The agent's runtime behavior should be grounded in accumulated learning records and reviewable reasoning habits, not only in a persona prompt or a few memory snippets.

The 2026-06-12 to 2026-06-13 hardening adds an explicit closed-growth contract: knowledge is not USB-copied into an agent. It passes through attention, curriculum mapping, practice, timed exams, feedback, reinforcement, and applied work before it can shape the agent's reasoning kibo.

## References

- Hermes Agent repository: https://github.com/NousResearch/hermes-agent
- Hermes Agent documentation: https://hermes-agent.nousresearch.com/docs/
- OpenClaw repository: https://github.com/openclaw/openclaw
- OpenClaw active memory documentation: https://docs.openclaw.ai/concepts/active-memory
