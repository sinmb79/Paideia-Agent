# AI Talent Foundry

AI Talent Foundry is the Paideia subsystem that turns an owner request into a trained, assessed, packaged, installed, and hired local AI talent.

Default runtime storage is outside this repository:

```powershell
%AI22B_STORAGE_ROOT%\talent-foundry\runs
```

Set `AI22B_STORAGE_ROOT` to use a different isolated storage folder.

## Graham Securities Research Track

The first deep role-model track is `graham_value_investing` for a Benjamin Graham process-replication securities research AI talent.

The role model is not used to preload a personality, worldview, or investment style. It is used to reconstruct sourced learning conditions, coursework pressure, assignments, exams, reports, and feedback loops so the talent develops its own **Reasoning Ledger** over time. The internal compatibility file is still named `reasoning_kibo.jsonl`.

The generated ledger is cumulative rather than final. It starts from elementary-school learning records, continues through middle school, high school, university, service discipline, graduate school, and doctoral work, then stays open after hiring so real agent work can extend or revise it.

## Guided Onboarding

The first-run flow asks for the LLM service and chat surface before it asks for the talent request. The selected LLM acts as a curriculum researcher and dialogue engine; it does not become the talent identity.

```powershell
ai22b-talent-foundry start-console `
  --answers examples\graham_junior_onboarding.answers.json
```

```powershell
ai22b-talent-foundry list-role-models --domain securities_research

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

## Public Release Boundary

Do not commit generated runs, installed agent bundles, private curricula, model checkpoints, or local memory artifacts. Run the root hygiene check before publishing:

```powershell
.\scripts\check_public_repo_hygiene.ps1
```
