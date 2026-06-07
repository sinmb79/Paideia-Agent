from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.config import PROJECT_ROOT
from ai22b.talent_foundry.public_inventory import load_pyproject, public_candidate_files, read_text, safe_rel
from ai22b.talent_foundry.public_release import (
    audit_public_release_readiness,
)


SOURCE_SBOM_SCHEMA = "paideia-source-sbom/v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _component_type(rel: str) -> str:
    if rel.startswith("src/"):
        return "source_code"
    if rel.startswith("tests/"):
        return "test"
    if rel.startswith("docs/") or rel.startswith("README"):
        return "documentation"
    if rel.startswith("scripts/") or rel.startswith(".github/"):
        return "automation"
    if rel.startswith("data/public/") or rel.startswith("evals/") or rel.startswith("examples/"):
        return "public_data_or_fixture"
    if rel in {"LICENSE", "pyproject.toml", "SECURITY.md"}:
        return "package_metadata"
    return "other_public_artifact"


def _root_key(rel: str) -> str:
    return rel.split("/", 1)[0] if "/" in rel else "."


def _repository_digest(components: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for item in sorted(components, key=lambda record: record["path"]):
        digest.update(item["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(item["sha256"].encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def build_source_sbom(
    repo_root: Path | None = None,
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Build a public-safe source SBOM/inventory without network access."""

    root = (repo_root or PROJECT_ROOT).resolve()
    pyproject = load_pyproject(root / "pyproject.toml")
    project = pyproject.get("project", {})
    optional = project.get("optional-dependencies", {})
    scripts = project.get("scripts", {})

    components: list[dict[str, Any]] = []
    for path in public_candidate_files(root):
        rel = safe_rel(path, root)
        components.append(
            {
                "path": rel,
                "type": _component_type(rel),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )

    by_root: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for item in components:
        by_root[_root_key(item["path"])] = by_root.get(_root_key(item["path"]), 0) + 1
        by_type[item["type"]] = by_type.get(item["type"], 0) + 1

    release_readiness = audit_public_release_readiness(root)
    license_text = read_text(root / "LICENSE") if (root / "LICENSE").is_file() else ""

    sbom = {
        "schema": SOURCE_SBOM_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root_name": root.name,
        "package": {
            "name": project.get("name"),
            "version": project.get("version"),
            "description": project.get("description"),
            "requires_python": project.get("requires-python"),
            "license_file": project.get("license", {}).get("file") if isinstance(project.get("license"), dict) else "LICENSE",
            "license_detected": "MIT" if "MIT License" in license_text else "unknown",
            "repository": project.get("urls", {}).get("Repository") if isinstance(project.get("urls"), dict) else None,
            "console_scripts": scripts,
        },
        "dependencies": {
            "direct": project.get("dependencies", []),
            "direct_count": len(project.get("dependencies", [])) if isinstance(project.get("dependencies", []), list) else 0,
            "optional_groups": {
                name: list(values) if isinstance(values, list) else [str(values)]
                for name, values in sorted(optional.items())
            },
            "optional_group_count": len(optional),
        },
        "components": components,
        "inventory": {
            "component_count": len(components),
            "by_root": dict(sorted(by_root.items())),
            "by_type": dict(sorted(by_type.items())),
            "repository_public_candidate_digest_sha256": _repository_digest(components),
        },
        "release_readiness": {
            "schema": release_readiness["schema"],
            "passed": release_readiness["passed"],
            "failed_count": release_readiness["summary"]["failed_count"],
            "public_candidate_file_count": release_readiness["summary"]["public_candidate_file_count"],
            "public_candidate_issue_count": release_readiness["summary"]["public_candidate_issue_count"],
        },
        "policy": {
            "scope": "source_repository_public_preview_inventory",
            "network_call_performed": False,
            "subprocess_executed": False,
            "private_runtime_outputs_scanned": False,
            "private_data_policy": "do_not_scan_or_export_private_runtime_state",
            "not_a_vulnerability_scan": True,
        },
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(sbom, ensure_ascii=False, indent=2), encoding="utf-8")
    return sbom
