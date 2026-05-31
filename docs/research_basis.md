# Paideia Agent Research Basis

This document maps reference programs, papers, and reports to concrete Paideia Agent design choices. It is intentionally practical: each source should explain what changed in the product.

## Agent Runtime Programs

| Source | What It Shows | Reflected In Paideia Agent |
| --- | --- | --- |
| OpenClaw onboarding wizard | First-run setup should choose provider/model, gateway mode, chat/channel path, skills, and next steps. | `start-console` now asks for LLM service and chat surface before the owner request. The terminal prompt shows a compact recommended provider/channel list, while `build-openclaw-onboarding-menu` and every console run write a full `OPENCLAW_ONBOARDING_MENU.md` covering all OpenClaw providers and channels. Each onboarding run writes an OpenClaw runtime bundle, provider/channel doctors, gateway/channel setup files, native OpenClaw handoff commands, `OPENCLAW_NATIVE_ONBOARDING_RUNBOOK.md` for the `openclaw onboard` -> model/auth -> workspace -> Gateway -> channels -> `openclaw agents add` -> health/smoke sequence, and a Gateway LLM doctor when `openclaw_gateway_http` is selected. `paideia_onboarding.template.json` records the selected service, selected surface, catalogs, and first-run flow. |
| OpenClaw model provider docs | Agent programs need explicit `provider/model` selection, provider auth, local model support, fallback semantics, canonical provider IDs, and plugin-owned provider behavior. | `llm_service_catalog` now accepts OpenClaw-style `provider/model` strings and exposes OpenAI/Codex, Claude, Gemini, Mistral, OpenRouter, Ollama, Ollama Cloud, LM Studio (`lmstudio`), OpenAI-compatible providers such as DeepSeek/Groq/GMI/Novita/Hugging Face/Kilo/xAI/Perplexity/Together/Fireworks/DeepInfra/Arcee/Chutes/Qianfan/StepFun/Volcengine/Xiaomi/vLLM/SGLang, Anthropic-compatible Synthetic and MiniMax, plus manifest-only provider entries for provider-plugin/OAuth/custom-runner surfaces. `list-openclaw-provider-connectors`, `doctor-openclaw-provider-connectors`, and `doctor-openclaw-provider-auth` separate direct live adapters, local servers, API-key env readiness, OAuth/account-session providers, cloud profiles, and OpenClaw Gateway handoff without storing API keys or local config paths. |
| OpenClaw channel docs | Chat channels are Gateway-routed and can be enabled per platform after pairing, allowlist, and plugin setup. Replies return to the origin channel/session; the model does not choose the destination channel. | `chat_surface_catalog` exposes OpenClaw channel manifests such as Telegram, Discord, Slack, BlueBubbles, WhatsApp, Signal, Teams, Google Chat, legacy iMessage, Matrix, Mattermost, IRC, LINE, WeChat, Zalo, and WebChat. `build-openclaw-gateway-config`, `run-openclaw-channel-message`, `run-openclaw-channel-gateway-server`, `doctor-openclaw-channel-flow`, and `run-openclaw-webchat-server` route channel/WebChat envelopes through Paideia chat. `doctor-openclaw-channel-pairing` separates QR session, local CLI bridge, enterprise bot, and legacy migration readiness without storing secret/session/path values. `build-openclaw-channel-delivery-config` and `send-openclaw-channel-outbound` add dry-run-first delivery adapters while keeping platform tokens in environment variables only. |
| OpenClaw installer readiness patterns | Users need a single honest surface that says what is ready locally, what needs a provider key, what needs a local server, and what must remain an OpenClaw plugin/OAuth/channel bridge handoff. | `build-openclaw-support-matrix` writes a one-file provider/channel matrix that groups every catalog entry into Paideia direct-ready, OpenClaw Gateway-ready, local-server ready, or plugin/OAuth/bridge required. Runtime bundles and bridge setup kits now include `openclaw_provider_auth_doctor.json` and `openclaw_channel_pairing_doctor.json` so provider auth plus QR, local bridge, tenant, and session setup steps are visible before live use. `doctor-openclaw-runtime-preflight` then re-checks the current runtime bundle across provider auth, channel pairing, native handoff, Gateway LLM compatibility, and optional offline channel-flow dry runs without storing secret values. |
| Telegram/Discord/Slack API docs | The common live-send path is Telegram Bot API `sendMessage`, Discord webhook or bot channel message, and Slack Web API `chat.postMessage`; all need explicit bot token/webhook configuration. | Delivery adapters prepare platform payloads from OpenClaw conversation/session keys, preserve thread/topic hints where possible, redact auth headers, and require `--mode live` plus environment variables before any external network call. |
| Telegram Update, Discord MESSAGE_CREATE, and Slack Events API docs | Inbound platform payloads have different event shapes and must be normalized before a talent can safely process them. | `build-openclaw-channel-access-config` creates a deny-by-default allowlist. `translate-openclaw-platform-event` converts Telegram/Discord/Slack raw events into the Paideia OpenClaw channel message schema without storing raw payloads. The HTTP gateway can route `/openclaw/platform-event/{channel}` only when the sender or conversation is allowlisted. |
| OpenClaw full channel directory | OpenClaw supports chat channels across mainstream messaging, developer/self-hosted systems, regional platforms, WebChat, and voice call plugins; current docs recommend BlueBubbles for new iMessage setups and keep legacy iMessage separate. | `list-openclaw-channel-connectors`, `doctor-openclaw-channel-connectors`, and `doctor-openclaw-channel-pairing` now cover every channel in the OpenClaw manifest. The doctors distinguish direct Paideia adapters from normalized-gateway-only channels and record plugin/bridge requirements such as BlueBubbles migration, WhatsApp/WeChat/Zalo Personal QR pairing, signal-cli, imsg, Matrix credentials, Twilio, or regional platform tokens. |
| OpenClaw agent runtime docs | OpenAI/Codex can be a runtime surface without making the model provider equal to the agent identity. | Paideia records `llm_identity_policy: application_engine_not_identity` and stores talent identity in local education artifacts. |
| Hermes Agent repository | Modern agents expose setup, model switching, CLI chat, tools, skills, memory, gateways, and migration. | Paideia adds install kits, doctor checks, skill migration wrappers, adapter manifests, and the `Reasoning Ledger` as a growth record. |
| OpenHands | Workspace agents should leave inspectable files, plans, traces, and runnable evidence. | Hired-agent workspace/dataflow runs write local plans, results, traces, and learning promotion records. |
| Agent ID Card | Agent identity should bind display name, owner, role, scope, credentials, and verification status. | Planned integration: export an Agent ID Card payload from the hiring dossier and installed manifest, with registration disabled unless the owner explicitly runs it. |

## Hardware And Dataflow Benchmarks

| Source | What It Shows | Reflected In Paideia Agent |
| --- | --- | --- |
| Tesla AI & Robotics | AI systems need high throughput, low latency, determinism, correctness, and memory-efficient handling of large sensor/data streams. | Paideia treats the selected LLM as compute, while `memory_substrate` and the Codex bridge keep only the current hot context near the answer path. |
| Tesla Hot Chips 31 FSD Computer presentation | The FSD Chip presentation emphasizes neural accelerator data alignment, local SRAM, weight buffers, data sharing, reduced DRAM/SRAM activity, and in-place reuse. | Boss's board analogy became the **Memory Board Architecture**: inline context formatting, hot/evidence/safety lanes, staged learning updates, and local reuse of verified Reasoning Ledger paths. |
| Computing's Energy Problem | Data movement and energy cost can dominate raw arithmetic, so locality and specialization matter. | Paideia avoids dumping whole archives into prompts; it selects, compresses, stages, and promotes memory like a software dataflow board. |

Detailed note: [Tesla-style dataflow board benchmark](tesla_board_benchmark.md).

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
- Role models are now a selectable public-metadata catalog for common agent roles such as software engineering, data/BI, support quality, cybersecurity, marketing, healthcare operations, education, management, legal/compliance, blockchain, and information systems.
- New role-model curricula use `role_model_foundation_core` plus university, graduate, doctoral, and assessment-ladder stages so non-Graham talents also produce transcripts, dossiers, and Reasoning Ledger entries.
- The bundled first test path is `examples/graham_junior_onboarding.answers.json`.
- Additional public onboarding samples live in `examples/role_model_onboarding_samples.json`.
- `Reasoning kibo` remains an internal file name for compatibility, but the public term is **Reasoning Ledger / Ariadne Thread**.
- The LLM is a researcher and dialogue engine; the trained talent identity comes from local records.
- The hiring dossier is a first-class product artifact, not an afterthought.
- External identity is planned as a dossier/install-manifest export path, not as automatic upload.
- External gateway channels and migrated skills stay disabled until owner review and doctor checks pass.
- The earlier Shinyong growth system is not discarded; it is a legacy life-development foundation for future Paideia talents. See [Legacy 22B-AI system integration](legacy_system_integration.md).
- Boss's Tesla board analogy is reflected as Memory Board Architecture, not as a claim that Paideia implements Tesla hardware.

## Primary Links

- Tesla AI & Robotics: https://www.tesla.com/AI?redirect=no
- Tesla Hot Chips 31 FSD Computer presentation: https://old.hotchips.org/hc31/HC31_2.3_Tesla_Hotchips_ppt_Final_0817.pdf
- Mark Horowitz, Computing's Energy Problem: https://doi.org/10.1109/ISSCC.2014.6757323
- OpenClaw onboarding reference: https://docs.openclaw.ai/reference/wizard
- OpenClaw provider directory: https://docs.openclaw.ai/providers
- OpenClaw provider directory legacy path: https://docs.openclaw.ai/providers/index
- OpenClaw model providers: https://docs.openclaw.ai/concepts/model-providers
- OpenClaw channels: https://docs.openclaw.ai/channels
- OpenClaw channel routing: https://docs.openclaw.ai/channels/channel-routing
- Telegram Bot API sendMessage: https://core.telegram.org/bots/api#sendmessage
- Telegram Bot API Update: https://core.telegram.org/bots/api#update
- Discord Gateway MESSAGE_CREATE: https://docs.discord.com/developers/docs/topics/gateway-events#message-create
- Discord execute webhook: https://discord.com/developers/docs/resources/webhook#execute-webhook
- Slack Events API: https://docs.slack.dev/apis/events-api/
- Slack message event: https://docs.slack.dev/reference/events/message/
- Slack chat.postMessage: https://api.slack.com/methods/chat.postMessage
- OpenClaw agent runtimes: https://docs.openclaw.ai/concepts/agent-runtimes
- Agent ID Card: https://www.agentidcard.org/
- Hermes Agent repository: https://github.com/NousResearch/hermes-agent
- OpenHands overview: https://docs.openhands.dev/overview/introduction
- Grace Hopper public biography: https://president.yale.edu/biography-grace-murray-hopper
- Edsger Dijkstra pioneer profile: https://history.computer.org/pioneers/dijkstra.html
- John Tukey public biography: https://www.britannica.com/biography/John-Wilder-Tukey
- W. Edwards Deming public biography: https://deming.org/deming/deming-the-man/
- Ross Anderson public page: https://www.cl.cam.ac.uk/~rja14/
- David Ogilvy public biography: https://www.ogilvy.com/about/david-ogilvy
- Florence Nightingale public biography: https://www.florence-nightingale.co.uk/florence-nightingale/biography/
- Maria Montessori public biography: https://montessori-ami.org/resource-library/facts/biography-maria-montessori
- Peter Drucker public biography: https://www.drucker.institute/about-peter-drucker/
- Ruth Bader Ginsburg public biography: https://www.supremecourt.gov/about/biographies.aspx
- Hal Finney public writings index: https://nakamotoinstitute.org/hal-finney/
- Claude Shannon public profile: https://www.itsoc.org/about/shannon
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
