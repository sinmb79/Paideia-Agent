# Legacy 22B-AI System Integration

The earlier AI system has not been abandoned. Paideia Agent is not a replacement that discards it; it is a larger education-center/runtime that absorbs the original Shinyong growth system, small from-scratch models, local verification scripts, the idea-coach app, and domain-agent notes.

## Existing Assets

| Asset | Location | Role In Paideia |
| --- | --- | --- |
| Shinyong growth system | `src/ai22b/shinyong/` | Legacy life-simulation seed for prenatal growth, sensory development, family interaction, and staged experiences. |
| Shinyong growth docs | `docs/10_shinyong_birth_curriculum_ko.md`, `docs/20_shinyong_human_shaped_learning_architecture_ko.md`, `docs/24_shinyong_birth_clock_and_yangju_context_ko.md` | Basis for language development, social learning, sensory/affective development, and daily conversation training. |
| From-scratch bigram | `src/ai22b/from_scratch/bigram.py` | Smallest local model loop for understanding training and testing on Boss's machine. |
| Talent Foundry | `src/ai22b/talent_foundry/` | Current Paideia training, hiring, chat, and work-runtime core. |
| Physical AI simulation notes | `docs/physical_ai_sim_rl_benchmark.md` | Parallel episode rollout, domain randomization, and sim-to-real equivalent for growing talents. |
| AI Idea Coach | `apps/ai-idea-coach/` | Candidate local UI foundation for future onboarding and curriculum-authoring screens. |
| Life/health agent plans | `docs/30_life_health_agent_masterplan_ko.md` and related docs | Future domain template for non-securities role-model tracks. |

## Why Paideia Was Added

The original Shinyong system focused on growing one AI child in a human-like sequence. Boss's later requirement became broader:

1. Multiple AI talents must be raised separately and compared.
2. Users must choose role models and occupations.
3. Schoolwork, exams, assignments, grades, and hiring dossiers must be generated.
4. The connected LLM is a chat/reasoning engine, while identity comes from local learning records.
5. The result must be installable as an agent program.

Paideia therefore keeps Shinyong as a **legacy life-development layer** and adds Talent Foundry, agent kits, onboarding, and hiring dossiers on top.

## Integration Rules

- Preserve the existing Shinyong data as its own original talent line.
- Reuse Shinyong's language, social, sensory, and affective growth design as a foundation layer for future talents.
- Keep each new role-model talent, such as Graham Junior, in a separate talent id and storage root.
- Do not publish private run outputs, local absolute paths, family details, private curricula, or model checkpoints.
- Publish only code, templates, documentation, tests, and safe sample settings.

## Next Development Tasks

1. Promote `src/ai22b/shinyong` episode generation into a common Paideia `life_foundation` module.
2. Add language development, ordinary conversation, and social repair training before specialized role-model curricula.
3. Keep Shinyong corpus and role-model corpora separated by talent id, storage root, and privacy policy.
4. Keep `from_scratch.bigram` as an educational/test local engine; use the Codex/selected-LLM bridge for real chat quality.
5. Treat AI Idea Coach as a candidate UI for role-model selection, LLM selection, curriculum design, and dossier review.

## Conclusion

The earlier system is Paideia's root, not discarded work. Paideia should treat it as a common growth foundation and legacy seed while keeping each new AI talent isolated and comparable.
