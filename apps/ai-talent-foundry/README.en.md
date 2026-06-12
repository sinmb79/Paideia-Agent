# AI Talent Foundry

AI Talent Foundry is the Paideia subsystem that turns an owner request into a trained, assessed, packaged, installed, and hired local AI talent.

Default runtime storage is outside this repository:

```powershell
%AI22B_STORAGE_ROOT%\talent-foundry\runs
```

Set `AI22B_STORAGE_ROOT` to use a different isolated storage folder.

## Selectable Role-Model Tracks

The first deep role-model track is `graham_value_investing` for a Benjamin Graham process-replication securities research AI talent.

The role model is not used to preload a personality, worldview, or investment style. It is used to reconstruct sourced learning conditions, coursework pressure, assignments, exams, reports, and feedback loops so the talent develops its own **Reasoning Ledger** over time. The internal compatibility file is still named `reasoning_kibo.jsonl`.

The generated ledger is cumulative rather than final. It starts from elementary-school learning records, continues through middle school, high school, university, service discipline, graduate school, and doctoral work, then stays open after hiring so real agent work can extend or revise it.

The public catalog now also includes selectable metadata-only tracks for common agent roles:

- software engineering: `hopper_software_tooling`, `dijkstra_verified_programming`
- data/BI: `tukey_data_analysis`
- customer support and quality operations: `deming_quality_ops`
- cybersecurity: `anderson_security_engineering`
- marketing and sales: `ogilvy_research_copywriting`
- healthcare operations: `nightingale_healthcare_statistics`
- education/tutoring: `montessori_learning_design`
- management/productivity: `drucker_management_knowledge_work`
- legal/compliance research: `ginsburg_legal_research`
- blockchain protocol research: `finney_blockchain_protocol`
- information systems research: `shannon_information_theory`

These are process templates, not impersonation targets. Exact copyrighted textbooks or private materials are represented as metadata and reading plans unless the owner provides a lawful local copy.

## Guided Onboarding

The first-run flow asks for the LLM service and chat surface before it asks for the talent request. The selected LLM acts as a curriculum researcher and dialogue engine; it does not become the talent identity.

```powershell
ai22b-talent-foundry start-console `
  --answers examples\graham_junior_onboarding.answers.json
```

```powershell
ai22b-talent-foundry list-role-models
ai22b-talent-foundry list-role-models --domain software_agent_engineering

ai22b-talent-foundry blueprint `
  --request "Raise a separate Graham learning-path sample AI." `
  --talent-name "grham-junior" `
  --gender "male" `
  --owner "Boss" `
  --domain securities_research `
  --role-model graham_value_investing

ai22b-talent-foundry raise `
  --blueprint %AI22B_STORAGE_ROOT%\talent-foundry\runs\agent_training_blueprint.json
```

The guided console and one-shot onboarding can select OpenAI/Codex, external API adapters, or local model adapters:

```powershell
ai22b-talent-foundry onboard-agent `
  --request "Raise a developer-tool agent that learns through debugging and tests." `
  --talent-name "hopper-junior" `
  --gender "male" `
  --owner "Boss" `
  --domain software_agent_engineering `
  --role-model hopper_software_tooling `
  --llm-service ollama_local `
  --llm-model "llama3.1:8b" `
  --llm-model-path "http://localhost:11434" `
  --chat-surface codex-bridge-chat
```

## Paideia Agent Program

After a talent is installed and hired, the foundry can export an installable Paideia Agent kit:

```powershell
ai22b-talent-foundry build-paideia-agent-kit `
  --employment-record C:\path\to\employment_record.json `
  --output-dir C:\path\to\paideia-agent-kit

ai22b-talent-foundry doctor-agent-program `
  --program C:\path\to\paideia-agent-kit\22b_paideia_agent_program.json
```

The kit contains onboarding files, adapter manifests, memory records, a hiring dossier, and a local chat entrypoint. External Hermes/OpenClaw/generic skills can be imported with `migrate-agent-assets`, but they remain disabled until reviewed.

## Closed Growth Contract

The foundry now emits a `paideia-closed-growth-contract/v1` with every blueprint, manifest, runtime doctor, and release bundle. This contract states that a Paideia talent is not assembled by copying plugins or prompts. Knowledge must be internalized through curriculum mapping, guided practice, timed exams, feedback, correction, reasoning-kibo consolidation, and varied work application.

Important runtime consequences:

- Imported Hermes/OpenClaw/community skills are stored as `REFERENCE.md` and `SOURCE_SKILL_REFERENCE.md`, not active `SKILL.md` descriptors.
- Team members must each have their own training evidence, dossier, resume, memory substrate, and employment record.
- Chat learning candidates are quarantined before Boss review and cannot directly update the reasoning kibo.
- ChatGPT/Codex OAuth can be used as an LLM backend, but it remains an application engine. It does not become the talent identity.

## Public Release Boundary

Do not commit generated runs, installed agent bundles, private curricula, model checkpoints, or local memory artifacts. Run the root hygiene check before publishing:

```powershell
.\scripts\check_public_repo_hygiene.ps1
```
