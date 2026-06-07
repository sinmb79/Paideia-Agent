# Security Policy

Paideia Agent is local-first. Private data, local memories, generated agent kits, model checkpoints, voice assets, credentials, and personal runtime artifacts must not be committed to this repository.

For the full attacker model, trust boundaries, permission policy, memory-promotion policy, and incident process, see [Security Threat Model](docs/security_threat_model.md).

## Private By Default

Ignored by default:

- `data/private/**`
- `data/processed/**`
- `runs/**`
- `apps/*/runs/**`
- `models/**`
- `.env*`
- `node_modules/**`
- `build/**`
- `dist/**`
- `target/**`

Run before publishing:

```powershell
.\scripts\check_public_repo_hygiene.ps1
```

## CI Supply Chain

GitHub Actions run with `permissions: contents: read`. Repository checkout uses
`actions/checkout@v6` with `persist-credentials: false`, and Dependabot monitors
official GitHub Actions updates. The public-preview policy uses official action
tags plus Dependabot for maintainability; formal release branches should revisit
full-length commit SHA pinning after the release branch is frozen. Security,
release-gate, and optional dependency audit artifacts are short-lived review
evidence and use a 14-day retention policy.

Optional dependency audits run outside the normal PR path because LLM, RAG, and
fine-tuning dependency trees can be large. Preview releases should review the
latest optional audit result before publication; stable releases should block on
unresolved high or critical vulnerabilities in optional extras.

## Imported Skills

External Hermes/OpenClaw/generic skills are treated as untrusted local code.

The migration command copies them into a Paideia kit as disabled wrappers:

```powershell
ai22b-talent-foundry migrate-agent-assets `
  --source C:\path\to\skill `
  --paideia-kit C:\path\to\kit `
  --source-runtime openclaw
```

Do not enable imported scripts until the wrapper manifest and source files have been reviewed, tested in a disposable workspace, and approved by the owner.

## Reporting Issues

For private deployments, keep sensitive details out of GitHub issues. Share only redacted paths, redacted logs, and reproducible steps.
