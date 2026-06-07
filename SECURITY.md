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
- `dist/**`
- `target/**`

Run before publishing:

```powershell
.\scripts\check_public_repo_hygiene.ps1
```

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
