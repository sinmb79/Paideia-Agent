# Paideia Closed Growth Ecosystem

Korean: [Paideia 폐쇄형 성장 생태계 원칙](closed_growth_ecosystem.ko.md)

Paideia Agent is not an open skill marketplace. Its goal is to raise AI talents through a Boss-designed education program so each agent develops a specialty, memory, reasoning kibo, resume, and ID as a distinct professional.

## Human-Like Closure

Closure here is not merely a security block. It is a learning model closer to the human body and brain. A human cannot receive expertise by USB copy. Childhood learning accumulates through attention, practice, tests, feedback, correction, and application. Paideia Agent follows the same principle.

- External material does not become memory or kibo directly; it must pass through attention, curriculum mapping, practice, exam, feedback, and application.
- The primary goal is not broad exhaustive search across every possibility.
- The agent first thinks about how to solve the task, chooses the necessary method, then practices finding an answer under time constraints.
- Repeated exams, error correction, Boss or oversight review, and successful work evidence become reinforcement signals.
- Through that reinforcement, each agent forms its own problem-solving method instead of copying someone else's method.
- Genius is not treated as a direct result of larger models or more compute. Paideia derives narrow, asymmetric excellence inside a fixed capacity budget through attention allocation, pattern chunking, timed problem solving, weakness correction, and transfer practice.

## Core Difference

| Area | Open custom agent | Paideia Agent |
| --- | --- | --- |
| Identity | Assembled from prompts and skills per task | Formed from education, exams, dossier, kibo, and memory |
| External skills | Installed and activated directly | Quarantined as reference, rewritten into Paideia-native training, then reviewed |
| Growth | Settings and plugins change behavior | Reviewed work experience is promoted into the learning ledger and memory substrate |
| LLM | Provider/model heavily shapes behavior | LLM is a language/tool engine, not identity |
| Teams | Role labels are composed | Each member is separately raised, hired, and documented |

## System Flow

```mermaid
flowchart LR
  A["External skill or method"] --> B["Quarantined reference"]
  B --> C["Paideia education-axis rewrite"]
  C --> D["Training / exam / work experiment"]
  D --> E["Boss or oversight review"]
  E --> F["Learning ledger promotion"]
  F --> G["Memory substrate / reasoning kibo growth"]
  G --> H["Distinct professional agent with ID"]
```

## Core Engines

- `education_program_engine`: creates the major, curriculum, exams, and growth path.
- `assessment_and_dossier_engine`: creates the resume and hiring dossier.
- `embodied_practice_and_exam_engine`: forces knowledge to pass through practice, timed exams, feedback, and application instead of direct copy.
- `genius_derivation_engine`: derives domain-specific genius from fixed-capacity attention allocation, pattern chunking, timed practice, and weakness guardrails rather than raw compute scaling.
- `reasoning_kibo_engine`: forms procedural reasoning from exams, mistakes, feedback, and work.
- `memory_substrate_engine`: promotes only verified memory into active context.
- `identity_and_id_card_engine`: manages local identity, ID card payload, and Agent_warrent envelope.
- `work_growth_promotion_engine`: promotes only reviewed work results.
- `external_skill_quarantine_engine`: prevents direct use of community/OpenClaw/Hermes skills.
- `llm_application_engine`: uses ChatGPT/Codex/API models only as application engines.

## Runtime Contract

The codebase carries `paideia-closed-growth-contract/v1`.

- External skills default to `untrusted_reference_only`.
- Direct activation and direct copying of external skills are forbidden.
- External skill memory, prompts, profiles, and workflows cannot become Paideia identity.
- Imported external skills are stored as `REFERENCE.md` and `SOURCE_SKILL_REFERENCE.md`, not as active `SKILL.md` descriptors.
- USB-style direct data transfer, direct memory patching, and direct solution-method copying are forbidden.
- Problem solving follows `understand_task -> choose_minimal_necessary_method -> solve_under_time_constraint -> review_result_and_errors -> extract_personal_method -> apply_method_to_new_domain`.
- Domain genius derivation follows `domain_problem_selection -> worked_example_compression -> timed_trial -> error_taxonomy -> counterexample_drill -> method_distillation -> varied_transfer` and must not be framed as general superintelligence or model-size proof.
- Useful procedures must be rewritten as Paideia education axes or procedural exercises.
- Failed or unreviewed runs stay quarantined; only reviewed summaries and successful Paideia work evidence can be promoted.
- Chat learning candidates are forced into quarantine before Boss review and cannot immediately enter the memory substrate or reasoning kibo.
- External runtimes such as ChatGPT/Codex OAuth are language adapters only; Hermes roots must carry a Paideia review marker or explicit allowlist entry before execution.

## Research Rationale

Open agent skill ecosystems provide speed and reuse, but they also create supply-chain, prompt-injection, remote execution, and long-term-memory poisoning risks. A curated closed ecosystem gives up some frictionless extensibility to preserve identity coherence, safety, reviewability, and owner-controlled growth.

Paideia does not ignore external ideas. It studies them. But it does not copy them into an agent's identity. External methods become reference material, then Paideia-native training, then reviewed growth.
