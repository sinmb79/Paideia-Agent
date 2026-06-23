from __future__ import annotations

from typing import Any


COMPATIBILITY_MANIFEST_SCHEMA = "paideia-cross-repo-compatibility/v1"
V2_SCHEMA_PREFIX = "paideia-kibo-v2-"
V2_SCHEMA_SUFFIX = "/v2"
REQUIRED_REPO_COMPATIBILITY_RANGES = {
    "paideia_agent": ">=0.x,<1.0",
    "paideia_engines": ">=0.x,<1.0",
    "genius_derivation": ">=0.x,<1.0",
}


def contract_name_from_schema(schema: str) -> str:
    if not schema.startswith(V2_SCHEMA_PREFIX) or not schema.endswith(V2_SCHEMA_SUFFIX):
        raise ValueError(f"Unsupported v2 schema id: {schema}")
    body = schema[len(V2_SCHEMA_PREFIX) : -len(V2_SCHEMA_SUFFIX)]
    return body.replace("-", "_")


def validate_compatibility_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != COMPATIBILITY_MANIFEST_SCHEMA:
        raise ValueError("Unsupported compatibility manifest schema")
    release = manifest.get("contracts_release")
    if not isinstance(release, str) or not release.startswith("2."):
        raise ValueError(f"Unsupported contracts_release: {release}")
    for repo_name, expected_range in REQUIRED_REPO_COMPATIBILITY_RANGES.items():
        if manifest.get(repo_name) != expected_range:
            raise ValueError(f"Compatibility manifest range mismatch for {repo_name}")
    if not isinstance(manifest.get("contract_hashes"), dict) or not manifest["contract_hashes"]:
        raise ValueError("Compatibility manifest requires contract_hashes")
    invalid_hashes = [
        name
        for name, value in manifest["contract_hashes"].items()
        if not isinstance(name, str) or not isinstance(value, str) or len(value) != 64
    ]
    if invalid_hashes:
        raise ValueError(f"Compatibility manifest has invalid contract hashes: {', '.join(map(str, invalid_hashes))}")


def validate_v2_contract_header(artifact: dict[str, Any], manifest: dict[str, Any]) -> str:
    validate_compatibility_manifest(manifest)
    schema_id = artifact.get("schema")
    if not isinstance(schema_id, str):
        raise ValueError("Artifact schema must be a string")
    contract_name = contract_name_from_schema(schema_id)
    schema_version = artifact.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version.startswith("2."):
        raise ValueError(f"Unsupported schema_version: {schema_version}")
    expected_hash = manifest["contract_hashes"].get(contract_name)
    if not expected_hash:
        raise ValueError(f"Compatibility manifest has no hash for {contract_name}")
    artifact_hash = artifact.get("contract_hash")
    if not isinstance(artifact_hash, str) or len(artifact_hash) != 64:
        raise ValueError(f"Artifact contract_hash for {contract_name} must be a 64-character string")
    if artifact_hash != expected_hash:
        raise ValueError(f"Contract hash mismatch for {contract_name}")
    return contract_name


def validate_v2_artifacts(artifacts: list[dict[str, Any]], manifest: dict[str, Any]) -> list[str]:
    contract_names: list[str] = []
    for artifact in artifacts:
        contract_name = validate_v2_contract_header(artifact, manifest)
        if contract_name == "case_graph":
            from .contracts_adapter import validate_case_graph_v2

            validate_case_graph_v2(artifact, manifest)
        elif contract_name == "action_pattern":
            from .contracts_adapter import validate_action_pattern_v2

            validate_action_pattern_v2(artifact, manifest)
        elif contract_name == "validation_profile":
            from .contracts_adapter import validation_profile_reuse_ceiling

            validation_profile_reuse_ceiling(artifact, manifest)
        elif contract_name == "outcome_evidence":
            from .contracts_adapter import validate_outcome_evidence_v2

            validate_outcome_evidence_v2(artifact, manifest)
        elif contract_name == "attribution_report":
            from .contracts_adapter import validate_attribution_report_v2

            validate_attribution_report_v2(artifact, manifest)
        elif contract_name == "pattern_revision":
            from .contracts_adapter import validate_pattern_revision_v2

            validate_pattern_revision_v2(artifact, manifest)
        else:
            raise ValueError(f"No Agent payload validator for {contract_name}")
        contract_names.append(contract_name)
    return contract_names
