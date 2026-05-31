# Paideia Agent Research Basis

This document maps reference programs, papers, and reports to concrete Paideia Agent design choices. It is intentionally practical: each source should explain what changed in the product.

## Agent Runtime Programs

| Source | What It Shows | Reflected In Paideia Agent |
| --- | --- | --- |
| OpenClaw onboarding wizard | First-run setup should choose provider/model, gateway mode, chat/channel path, skills, and next steps. | `start-console` now asks for LLM service and chat surface before the owner request. `paideia_onboarding.template.json` records the selected service, selected surface, catalogs, and first-run flow. |
| OpenClaw model provider docs | Agent programs need explicit provider/model selection and fallback semantics. | `llm_service_catalog` separates OpenAI/Codex, deterministic local, bigram, Transformers, and llama.cpp/GGUF paths. |
| OpenClaw agent runtime docs | OpenAI/Codex can be a runtime surface without making the model provider equal to the agent identity. | Paideia records `llm_identity_policy: application_engine_not_identity` and stores talent identity in local education artifacts. |
| Hermes Agent repository | Modern agents expose setup, model switching, CLI chat, tools, skills, memory, gateways, and migration. | Paideia adds install kits, doctor checks, skill migration wrappers, adapter manifests, and the `Reasoning Ledger` as a growth record. |
| OpenHands | Workspace agents should leave inspectable files, plans, traces, and runnable evidence. | Hired-agent workspace/dataflow runs write local plans, results, traces, and learning promotion records. |

## Learning And Memory Research

| Source | What It Shows | Reflected In Paideia Agent |
| --- | --- | --- |
| Reflexion | Verbal feedback can improve future task behavior without immediately changing model weights. | `learning_ledger.json` promotes reviewed work outcomes and feedback into reusable procedural memory. |
| Generative Agents | Agents need observation, memory retrieval, reflection, planning, and coherent behavior over time. | Paideia separates `memory_substrate.json`, active memory routing, recent chat summaries, and growth checkpoints. |
| CoALA | LLM agents can be modeled with working memory, episodic memory, semantic memory, procedural memory, and actions. | The memory substrate separates episodic fast store, semantic principles, procedural operators, and action surfaces. |
| ACT-R | Human-like cognition can be modeled with declarative and procedural memory. | Paideia's procedural operator store and learning axes treat habits as explicit, reviewable procedures. |
| Soar | Impasses and chunking can create new procedural knowledge from problem solving. | Failed exams, blocked work, corrections, and repaired answers become reviewed learning candidates. |
| Complementary Learning Systems | Fast episodic learning and slower structured learning serve different roles. | Raw-ish events stay local; only reviewed summaries and principles are promoted into active memory. |
| Retrieval practice / test-enhanced learning | Testing is itself a learning pressure, not only a measurement event. | School exams, CSAT-like gates, university exams, reports, and doctoral defense all update the Reasoning Ledger. |
| Self-regulated learning | Learning cycles include planning, performance, monitoring, and reflection. | Long-running goals and job cycles store success criteria, workspace traces, review labels, and next learning rules. |
| Insight problem-solving research | Solving hard problems often requires restructuring the problem representation. | Paideia records counterevidence, reframing, source-search decisions, and corrected principles rather than only final answers. |

## Physical AI And Simulation Benchmarks

| Source | What It Shows | Reflected In Paideia Agent |
| --- | --- | --- |
| NVIDIA Isaac Gym / Isaac Lab | Massive parallel simulation can accelerate embodied-policy learning. | Paideia's planned life-simulation loop uses parallel episode rollouts from the same age/stage checkpoint. |
| MuJoCo MJX / MuJoCo Playground | Vectorized environments can test many variations quickly. | Conversation, school, stress, social conflict, and research scenarios can be varied without breaking the growth timeline. |
| OpenAI dexterous manipulation / domain randomization | Simulated variation helps reduce the reality gap before deployment. | Paideia uses domain-randomized questions, API failures, missing files, conflicting sources, and social stress cases before promotion. |
| GR00T / robot foundation-model reports | Robot learning combines demonstrations, synthetic data, simulation, and deployment feedback. | Paideia treats generated episodes, exams, real chats, and real work as separate evidence classes with promotion/quarantine rules. |

## Product Decisions From These Sources

- Onboarding is now explicit: choose LLM service, choose chat surface, choose role model, then raise and review the talent.
- The bundled first test path is `examples/graham_junior_onboarding.answers.json`.
- `Reasoning kibo` remains an internal file name for compatibility, but the public term is **Reasoning Ledger / Ariadne Thread**.
- The LLM is a researcher and dialogue engine; the trained talent identity comes from local records.
- The hiring dossier is a first-class product artifact, not an afterthought.
- External gateway channels and migrated skills stay disabled until owner review and doctor checks pass.

## Primary Links

- OpenClaw onboarding reference: https://docs.openclaw.ai/reference/wizard
- OpenClaw model providers: https://docs.openclaw.ai/providers/models
- OpenClaw agent runtimes: https://docs.openclaw.ai/concepts/agent-runtimes
- Hermes Agent repository: https://github.com/NousResearch/hermes-agent
- OpenHands overview: https://docs.openhands.dev/overview/introduction
- Reflexion: https://arxiv.org/abs/2303.11366
- Generative Agents: https://arxiv.org/abs/2304.03442
- CoALA: https://arxiv.org/abs/2309.02427
- ACT-R: https://act-r.psy.cmu.edu/
- Soar: https://soar.eecs.umich.edu/
- Complementary Learning Systems: https://pubmed.ncbi.nlm.nih.gov/7624455/
- Test-enhanced learning: https://pubmed.ncbi.nlm.nih.gov/16507066/
- Self-regulated learning review: https://pmc.ncbi.nlm.nih.gov/articles/PMC5408091/
- Insight problem-solving review: https://www.nature.com/articles/s44159-023-00257-x
- NVIDIA Isaac Gym paper: https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/file/28dd2c7955ce926456240b2ff0100bde-Paper-round2.pdf
- NVIDIA Isaac Lab: https://docs.isaacsim.omniverse.nvidia.com/6.0.0/isaac_lab_tutorials/index.html
- MuJoCo MJX: https://mujoco.readthedocs.io/en/latest/mjx.html
- OpenAI dexterous manipulation: https://journals.sagepub.com/doi/full/10.1177/0278364919887447
