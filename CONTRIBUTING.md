# Contributing

[English](CONTRIBUTING.md) | [한국어](CONTRIBUTING.ko.md)

Paideia Agent is a local-first research preview. Contributions should keep the first-run path understandable, testable, and public-safe.

## Development Principles

- Keep the MVP path working before adding new surfaces.
- Prefer small PRs that change one boundary at a time.
- Do not commit private curricula, generated agents, local memories, model checkpoints, credentials, or run artifacts.
- Treat imported skills, provider payloads, and generated memory candidates as untrusted until reviewed.
- Document public behavior in English and Korean when the change affects onboarding or first use.

## Local Setup

```powershell
python -m pip install -e ".[dev]"
$env:PYTHONPATH = "src"
```

Recommended checks before opening a PR:

```powershell
python -m compileall src/ai22b/talent_foundry
python -B -m pytest tests -q
python -m build
ruff check src tests --select E9,F63,F7,F82
.\scripts\check_public_repo_hygiene.ps1
```

## Public-Safe Rules

- Use relative paths in public artifacts.
- Do not include raw provider responses, secrets, private reasoning traces, or personal local paths.
- Keep copyrighted or owner-provided materials as metadata and reading plans unless they are lawful local private copies outside the public repository.
- Live provider tests must be explicit and must not run in default offline checks.

## Refactor Rules

Large modules are allowed only while boundaries are still being discovered. When splitting them, preserve public CLI names and add compatibility shims or tests before moving behavior.

Priority split order:

1. `action_policy.py` into policy models, evaluator, approvals, and risk levels.
2. `tool_registry.py` into specs, planners, executors, and verifiers.
3. `llm_clients.py` into a typed result contract plus provider adapters.
4. `agent_execution_loop.py` into planner, executor, verifier, and result models.

## PR Checklist

- The 3-minute offline demo still works.
- First-run doctor and runtime doctors pass without network calls.
- Generated outputs stay in ignored runtime folders.
- Public release hygiene passes.
- Documentation names any experimental feature as Beta, Experimental, or Future.
