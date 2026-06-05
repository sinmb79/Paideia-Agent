# Public Release Readiness

Paideia Agent is a local-first agent research preview. Public release readiness is not only "tests pass"; it also means the repository can be inspected without exposing the owner's private training material, local memories, generated run state, credentials, or model checkpoints.

## Required Gates

Before publishing or merging a release branch, run:

```powershell
python -m compileall src\ai22b\talent_foundry
$env:PYTHONPATH = "src"
python -B -m pytest tests\test_package_smoke.py tests\test_cli_smoke.py -q
.\scripts\check_public_repo_hygiene.ps1
ai22b-talent-foundry audit-public-release-readiness --repo-root . --strict --output .\public_release_readiness.json
```

The hygiene script now checks two classes of release risk:

- blocked paths and blocked content such as private folders, local owner paths, API keys, tokens, and generated runtime outputs;
- required public-release files such as `README.md`, `README.ko.md`, `SECURITY.md`, `LICENSE`, and `pyproject.toml` with package license metadata.

The Python readiness audit writes a reviewable `paideia-public-release-readiness/v1` report. It checks source repository metadata and CI gates only; it does not call the network, execute subprocesses, or inspect private generated runtime state.

## Agent Bundle Gates

Generated agents are not committed to the source repository. To prepare a reviewable local package, use:

```powershell
ai22b-talent-foundry bundle --installed-manifest <installed_agent_manifest.json> --output-dir <bundle_dir>
ai22b-talent-foundry doctor-bundle --bundle-dir <bundle_dir> --output <bundle_dir>\release_doctor_report.json
ai22b-talent-foundry package-bundle --bundle-dir <bundle_dir> --output-zip <bundle_dir>.zip
```

The package manifest and `.sha256` file prove the archive checksum. `install-package` verifies the checksum again before installing the agent into a local registry.

## Identity Registration

Agent ID Card / Agent_warrent integration is a local export path by default. Paideia can produce registration payloads and verify that no local paths, raw owner emails, or credential-like tokens leak into the files. External registration remains a manual owner action.
