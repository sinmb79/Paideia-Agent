# Public Release Readiness

Paideia Agent is a local-first agent research preview. Public release readiness is not only "tests pass"; it also means the repository can be inspected without exposing the owner's private training material, local memories, generated run state, credentials, or model checkpoints.

## Required Gates

Before publishing or merging a release branch, run:

```powershell
python -m compileall src\ai22b\talent_foundry
python -m pip install -e ".[security]"
python -m bandit -q -r src -c pyproject.toml
python -m pip_audit . --skip-editable
$env:PYTHONPATH = "src"
python -B -m pytest tests\test_package_smoke.py tests\test_cli_smoke.py -q
.\scripts\check_public_repo_hygiene.ps1
ai22b-talent-foundry audit-public-release-readiness --repo-root . --strict --output .\public_release_readiness.json
ai22b-talent-foundry build-source-sbom --repo-root . --output .\source_sbom.json
ai22b-talent-foundry build-llm-connection-profile --llm-engine deterministic_local --output .\llm_connection_profile.json
ai22b-talent-foundry doctor-package-install --repo-root . --strict --output .\package_install_doctor.json
ai22b-talent-foundry doctor-runtime-contract --repo-root . --strict --output .\runtime_contract_doctor.json
ai22b-talent-foundry doctor-first-run --repo-root . --strict --output .\first_run_doctor.json
```

Run the tests after `python -m pip install -e ".[dev]"`. Run the security gate
after `python -m pip install -e ".[security]"`. The package smoke test checks
installed distribution metadata and exposed console script entry points, not
only the static `pyproject.toml` file.

The hygiene script now checks two classes of release risk:

- blocked paths and blocked content such as private folders, local owner paths, API keys, tokens, and generated runtime outputs;
- hidden bidirectional Unicode controls that can make reviewed text render differently from stored text;
- required public-release files such as `README.md`, `README.ko.md`, `SECURITY.md`, `LICENSE`, `pyproject.toml`, and machine-readable files under `schemas/`.

The Python readiness audit writes a reviewable `paideia-public-release-readiness/v1` report. It checks source repository metadata, CI gates, and public candidate files under roots such as `src`, `docs`, `tests`, `scripts`, `examples`, and `data/public`. It does not call the network, execute subprocesses, or inspect private generated runtime state.

The first-run smoke suite also writes `paideia-llm-provider-matrix/v1`, builds `paideia-llm-onboarding-checklist/v1`, and materializes `paideia-llm-connection-profile/v1` with the deterministic local engine. This proves the LLM/service selection path can list all selectable providers and produce setup requirements, provider doctor, live-check, application smoke, agent runtime smoke, and first chat commands without calling a provider by default or exporting secrets.

The source SBOM writes `paideia-source-sbom/v1`. It records package metadata, optional dependency groups, console scripts, public candidate file SHA-256 values, and a repository public-candidate digest. It is a reproducible inventory for review; it is not a vulnerability scan.

The JSON Schema suite under `schemas/` now publishes v1 contracts for the
first-run doctor, LLM client result, tool artifact manifest, Reasoning Ledger
candidate, and hiring dossier. Regression tests validate both the schema files
and representative generated artifacts.

The package install doctor writes `paideia-package-install-doctor/v1`. It checks that the current Python environment exposes the installed distribution metadata, console scripts, optional extras, and callable entrypoint targets without running subprocesses or exporting local paths.

The runtime contract doctor writes `paideia-runtime-contract-doctor/v1`. It checks the live-like agent loop, LLM identity boundary, registered tool executor, memory review gate, and fail-closed live provider behavior without calling an external provider.

Agent runtime smoke reports include `paideia-live-llm-agent-proof/v1`, a public-safe proof packet that labels the selected path as offline verification, injected live-like client, built-in live provider client, adapter context, or fail-closed configuration gate. Release review can therefore distinguish no-network CI evidence from an actual live provider client run without storing raw provider payloads or hidden reasoning traces.

The first-run doctor writes `paideia-first-run-doctor/v1`. It bundles the role-model catalog, LLM provider matrix, selected deterministic checklist, connection profile, provider doctor, application smoke, full agent runtime smoke, runtime contract doctor, tool capability audit, action policy eval, public release readiness, source SBOM, and package install doctor into one install-time report. Add `--onboarding-session <console_session.json>` to include wizard health verification in the same report.

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
