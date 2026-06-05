from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AGENT_ID_CARD_PAYLOAD_SCHEMA = "ai-talent-agent-id-card-payload/v1"
AGENT_IDENTITY_LAYER_ENVELOPE_SCHEMA = "agent-identity-layer-envelope/ail.v1"
AGENT_ID_CARD_VERIFICATION_SCHEMA = "paideia-agent-id-card-verification/v1"
AGENT_ID_CARD_REGISTRATION_IMPORT_SCHEMA = "paideia-agent-id-card-registration-import/v1"
AGENT_WARRENT_REPO_URL = "https://github.com/sinmb79/Agent_warrent"
AGENT_WARRENT_EXTERNAL_REGISTRATION_STATES = {
    "manual_owner_action_only",
    "owner_completed_outside_paideia",
}
WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"[A-Za-z]:\\")
POSIX_HOME_PATH_RE = re.compile(r"(/home/|/Users/)[^\s\"']+")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]+|api[_-]?key\s*[:=])", re.I)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _fingerprint(*parts: str) -> str:
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _canonical_hash(value: dict[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _secret_hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _artifact_blob(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _required_path_missing(value: dict[str, Any], paths: list[tuple[str, ...]]) -> list[str]:
    missing: list[str] = []
    for path in paths:
        cursor: Any = value
        for key in path:
            cursor = cursor.get(key) if isinstance(cursor, dict) else None
        if cursor is None or cursor == "":
            missing.append(".".join(path))
    return missing


def _privacy_issues(value: dict[str, Any]) -> list[dict[str, Any]]:
    blob = _artifact_blob(value)
    issues: list[dict[str, Any]] = []
    if WINDOWS_ABSOLUTE_PATH_RE.search(blob) or POSIX_HOME_PATH_RE.search(blob):
        issues.append(
            {
                "id": "local_absolute_path_exported",
                "severity": "error",
                "message": "Agent identity artifacts must not export local absolute paths.",
            }
        )
    if SECRET_RE.search(blob):
        issues.append(
            {
                "id": "credential_like_value_exported",
                "severity": "error",
                "message": "Agent identity artifacts must not export API keys, bearer tokens, or credential-like values.",
            }
        )
    if EMAIL_RE.search(blob):
        issues.append(
            {
                "id": "raw_owner_email_exported",
                "severity": "error",
                "message": "Agent identity artifacts must avoid raw owner email addresses before external registration.",
            }
        )
    return issues


def _nested_value(value: dict[str, Any], path: tuple[str, ...]) -> Any:
    cursor: Any = value
    for key in path:
        cursor = cursor.get(key) if isinstance(cursor, dict) else None
    return cursor


def _first_text(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1", "signed", "verified"}
    return bool(value)


def _slug(value: str | None, *, fallback: str = "agent") -> str:
    if not value:
        return fallback
    slug = "".join(char.lower() if char.isalnum() else "_" for char in value)
    return "_".join(part for part in slug.split("_") if part) or fallback


def _load_identity_sources(
    installed_manifest_path: Path,
    employment_record_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    installed_manifest = _read_json(installed_manifest_path)
    if installed_manifest.get("schema") != "ai-talent-installed-agent/v1":
        raise ValueError("Unsupported installed agent manifest schema")

    target_root = installed_manifest_path.parent
    entrypoints = installed_manifest.get("entrypoints", {})
    agent_manifest = _read_json(target_root / entrypoints["agent_manifest"])
    dossier_path = target_root / entrypoints.get("hiring_dossier", "hiring_dossier.json")
    dossier = _read_json(dossier_path) if dossier_path.exists() else {}
    employment_record = _read_json(employment_record_path) if employment_record_path else {}
    return installed_manifest, agent_manifest, dossier, employment_record


def build_agent_id_card_payload(
    *,
    installed_manifest_path: Path,
    employment_record_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Build a local-only Agent ID Card registration payload.

    This does not register or upload anything. It gives the owner a reviewable
    payload that can later be submitted to an external identity provider.
    """

    installed_manifest, agent_manifest, dossier, employment_record = _load_identity_sources(
        installed_manifest_path,
        employment_record_path,
    )
    entrypoints = installed_manifest.get("entrypoints", {})

    agent = agent_manifest.get("agent", {})
    role = (
        employment_record.get("agent", {}).get("role")
        or agent.get("role")
        or dossier.get("candidate", {}).get("target_role")
        or "local_ai_talent_agent"
    )
    owner = employment_record.get("employer") or dossier.get("owner") or "local_owner"
    scope = {
        "runtime": "local_first_paideia_agent",
        "allowed": ["local_chat", "local_workspace_jobs", "reviewable_memory_updates"],
        "blocked": agent_manifest.get("tool_policy", {}).get("blocked_tools", []),
        "private_data_upload": "forbidden_without_explicit_owner_action",
        "registration_side_effect": "none_payload_only",
    }
    credential_subject = {
        "display_name": agent.get("name"),
        "role": role,
        "owner_org": owner,
        "provider": employment_record.get("llm_service", {}).get("service_id")
        or agent_manifest.get("llm_policy", {}).get("role")
        or "user_selected_llm",
        "scope": scope,
    }
    payload_fingerprint = _fingerprint(
        str(credential_subject.get("display_name") or ""),
        str(role),
        str(owner),
        str(installed_manifest.get("source_sha256") or ""),
    )
    payload = {
        "schema": AGENT_ID_CARD_PAYLOAD_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "agentidcard.org",
        "provider_url": "https://www.agentidcard.org/",
        "status": "payload_ready_not_registered",
        "network_action_performed": False,
        "owner_review_required": True,
        "credential_subject": credential_subject,
        "local_lineage": {
            "install_id": installed_manifest.get("install_id"),
            "employment_id": employment_record.get("employment_id"),
            "source_sha256": installed_manifest.get("source_sha256"),
            "hiring_dossier": entrypoints.get("hiring_dossier", "hiring_dossier.json"),
            "installed_manifest": installed_manifest_path.name,
        },
        "payload_fingerprint_sha256": payload_fingerprint,
        "agent_identity_layer": {
            "compatible_envelope_version": "ail.v1",
            "provider_repo": AGENT_WARRENT_REPO_URL,
            "local_export_command": "ai22b-talent-foundry export-agent-identity-envelope",
            "external_registration": "manual_owner_action_only",
        },
        "next_steps": [
            "Review display_name, owner_org, role, and scope.",
            "Register through Agent ID Card only if the owner explicitly chooses external registration.",
            "Store returned AIL ID and credential token outside public source control.",
        ],
    }
    if output_path is not None:
        _write_json(output_path, payload)
    return payload


def build_agent_identity_layer_envelope(
    *,
    installed_manifest_path: Path,
    employment_record_path: Path | None = None,
    output_path: Path | None = None,
    surface: str = "paideia_cli",
    task_ref: str | None = None,
) -> dict[str, Any]:
    """Build an Agent_warrent/Agent Identity Layer compatible v1 envelope.

    The generated envelope is local and unregistered: `ail_id`, `credential`,
    and signed verification fields stay empty until the owner explicitly
    registers through an external identity service.
    """

    installed_manifest, agent_manifest, dossier, employment_record = _load_identity_sources(
        installed_manifest_path,
        employment_record_path,
    )
    entrypoints = installed_manifest.get("entrypoints", {})
    agent = agent_manifest.get("agent", {})
    employment_agent = employment_record.get("agent", {})
    llm_service = employment_record.get("llm_service", {})
    llm_runtime = employment_record.get("llm_runtime", {})
    owner_label = employment_record.get("employer") or dossier.get("owner") or "local_owner"
    role = (
        employment_agent.get("role")
        or agent.get("role")
        or dossier.get("candidate", {}).get("target_role")
        or "local_ai_talent_agent"
    )
    display_name = agent.get("name") or dossier.get("candidate", {}).get("name") or "Paideia Agent"
    provider = (
        llm_service.get("service_id")
        or llm_runtime.get("service")
        or agent_manifest.get("llm_policy", {}).get("role")
        or "user_selected_llm"
    )
    model = llm_service.get("selected_model") or llm_runtime.get("model")
    scope = {
        "workspace": ["local_paideia_agent_install"],
        "repos": ["Paideia-Agent"],
        "network": "restricted" if provider != "deterministic_local" else "none",
        "secrets": "indirect" if provider not in {"deterministic_local", "bigram_local"} else "none",
        "write_access": True,
        "approval_policy": {
            "irreversible_actions": "human_required",
            "external_posting": "human_required",
            "destructive_file_ops": "human_required",
            "external_registration": "human_required",
        },
    }
    local_behavior = {
        "role": role,
        "network": scope["network"],
        "secrets": scope["secrets"],
        "write_access": scope["write_access"],
        "provider": provider,
        "blocked_tools": agent_manifest.get("tool_policy", {}).get("blocked_tools", []),
    }
    agent_id = "paideia_" + _fingerprint(
        str(display_name),
        str(role),
        str(installed_manifest.get("install_id") or ""),
        str(installed_manifest.get("source_sha256") or ""),
    )[:16]
    now = datetime.now(timezone.utc).isoformat()
    envelope = {
        "version": "ail.v1",
        "ail_id": None,
        "credential": None,
        "agent": {
            "id": agent_id,
            "display_name": display_name,
            "role": role,
            "provider": provider,
            "model": model,
            "runtime": employment_record.get("chat_surface", {}).get("surface_id") or surface,
        },
        "owner": None,
        "scope": scope,
        "signal_glyph": None,
        "behavior_fingerprint": None,
        "delegation": {
            "mode": "direct",
            "delegated_by": None,
            "approved_by": {
                "type": "human",
                "id": _slug(str(owner_label), fallback="owner"),
            },
            "chain_depth": 0,
            "task_ref": task_ref or "paideia-agent-local-identity-export",
        },
        "runtime": {
            "session_id": employment_record.get("employment_id") or installed_manifest.get("install_id"),
            "run_id": f"run_{agent_id}_{now[:10].replace('-', '')}",
            "surface": surface,
            "host": "local-paideia-runtime",
            "cwd": "local_paideia_agent_install",
            "time": now,
        },
        "verification": {
            "strength": "local_runtime_asserted",
            "signed": False,
            "evidence": [
                "installed_manifest_sha256",
                "agent_manifest_entrypoint",
                "hiring_dossier_present" if entrypoints.get("hiring_dossier") else "hiring_dossier_optional",
                "employment_record_binding" if employment_record else "employment_record_optional",
            ],
            "attestation_ref": None,
        },
        "extensions": {
            "agent_warrent": {
                "repo_url": AGENT_WARRENT_REPO_URL,
                "schema": AGENT_IDENTITY_LAYER_ENVELOPE_SCHEMA,
                "spec_version": "ail.v1",
                "registration_state": "local_unregistered",
                "external_registration": "manual_owner_action_only",
            },
            "paideia": {
                "payload_schema": AGENT_ID_CARD_PAYLOAD_SCHEMA,
                "install_id": installed_manifest.get("install_id"),
                "employment_id": employment_record.get("employment_id"),
                "source_sha256": installed_manifest.get("source_sha256"),
                "entrypoints": {
                    "agent_manifest": entrypoints.get("agent_manifest"),
                    "hiring_dossier": entrypoints.get("hiring_dossier"),
                    "memory_substrate": entrypoints.get("memory_substrate"),
                    "growth_profile": entrypoints.get("growth_profile"),
                },
                "owner_label": owner_label,
                "local_behavior_fingerprint": {
                    "hash": _canonical_hash(local_behavior),
                    "algorithm": "sha256",
                    "inputs": [
                        "role",
                        "scope.network",
                        "scope.secrets",
                        "scope.write_access",
                        "provider",
                        "blocked_tools",
                    ],
                },
                "privacy": {
                    "absolute_paths_exported": False,
                    "raw_owner_email_exported": False,
                    "credential_token_exported": False,
                    "network_action_performed": False,
                },
            },
        },
    }
    if output_path is not None:
        _write_json(output_path, envelope)
    return envelope


def validate_agent_id_card_payload(payload: dict[str, Any]) -> dict[str, Any]:
    missing = _required_path_missing(
        payload,
        [
            ("schema",),
            ("status",),
            ("credential_subject", "display_name"),
            ("credential_subject", "role"),
            ("credential_subject", "owner_org"),
            ("credential_subject", "scope"),
            ("local_lineage", "install_id"),
            ("agent_identity_layer", "compatible_envelope_version"),
            ("agent_identity_layer", "provider_repo"),
        ],
    )
    issues: list[dict[str, Any]] = []
    if payload.get("schema") != AGENT_ID_CARD_PAYLOAD_SCHEMA:
        issues.append(
            {
                "id": "unsupported_payload_schema",
                "severity": "error",
                "message": "Agent ID Card payload schema is not supported.",
            }
        )
    if payload.get("network_action_performed") is not False:
        issues.append(
            {
                "id": "network_action_performed",
                "severity": "error",
                "message": "Verification expects a local-only payload with no automatic registration or upload.",
            }
        )
    if payload.get("owner_review_required") is not True:
        issues.append(
            {
                "id": "owner_review_not_required",
                "severity": "error",
                "message": "Owner review must remain required before external Agent ID Card registration.",
            }
        )
    if payload.get("agent_identity_layer", {}).get("external_registration") != "manual_owner_action_only":
        issues.append(
            {
                "id": "external_registration_not_manual",
                "severity": "error",
                "message": "External identity registration must remain manual owner action only.",
            }
        )
    issues.extend(_privacy_issues(payload))
    if missing:
        issues.append(
            {
                "id": "required_fields_missing",
                "severity": "error",
                "message": "Agent ID Card payload is missing required fields.",
                "missing": missing,
            }
        )
    blocking = [issue for issue in issues if issue["severity"] == "error"]
    return {
        "schema": "agent-id-card-payload-validation/v1",
        "artifact_type": "agent_id_card_payload",
        "valid": not blocking,
        "registered": payload.get("status") not in {None, "payload_ready_not_registered"},
        "network_action_performed": bool(payload.get("network_action_performed")),
        "missing": missing,
        "issues": issues,
        "privacy": {
            "local_absolute_paths_exported": any(issue["id"] == "local_absolute_path_exported" for issue in issues),
            "credential_like_values_exported": any(issue["id"] == "credential_like_value_exported" for issue in issues),
            "raw_owner_email_exported": any(issue["id"] == "raw_owner_email_exported" for issue in issues),
        },
    }


def validate_agent_identity_layer_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    missing: list[str] = []
    if envelope.get("version") != "ail.v1":
        missing.append("version")
    missing.extend(
        _required_path_missing(
            envelope,
            [
                ("agent", "id"),
                ("agent", "display_name"),
                ("agent", "role"),
                ("delegation", "mode"),
                ("scope", "approval_policy"),
                ("verification", "strength"),
                ("extensions", "agent_warrent", "repo_url"),
                ("extensions", "agent_warrent", "registration_state"),
            ],
        )
    )
    runtime = envelope.get("runtime", {})
    if not runtime.get("run_id") and not runtime.get("session_id"):
        missing.append("runtime.run_id_or_session_id")
    issues = _privacy_issues(envelope)
    if envelope.get("credential") not in {None, ""} and not envelope.get("verification", {}).get("signed"):
        issues.append(
            {
                "id": "unsigned_credential_present",
                "severity": "error",
                "message": "Credential tokens must not be present in an unsigned local envelope.",
            }
        )
    agent_warrent = envelope.get("extensions", {}).get("agent_warrent", {})
    external_registration = agent_warrent.get("external_registration")
    registration_state = agent_warrent.get("registration_state")
    if external_registration not in AGENT_WARRENT_EXTERNAL_REGISTRATION_STATES:
        issues.append(
            {
                "id": "external_registration_not_manual",
                "severity": "error",
                "message": "Agent_warrent external registration must remain manual owner action only or owner-completed outside Paideia.",
            }
        )
    if external_registration == "owner_completed_outside_paideia" and not envelope.get("ail_id"):
        issues.append(
            {
                "id": "external_registration_missing_ail_id",
                "severity": "error",
                "message": "Owner-imported external registration requires an AIL ID.",
            }
        )
    if registration_state == "owner_imported_registered" and not envelope.get("verification", {}).get("signed"):
        issues.append(
            {
                "id": "registered_envelope_not_signed",
                "severity": "error",
                "message": "Owner-imported registered envelopes must mark verification as signed.",
            }
        )
    if missing:
        issues.append(
            {
                "id": "required_fields_missing",
                "severity": "error",
                "message": "Agent Identity Layer envelope is missing required fields.",
                "missing": missing,
            }
        )
    blocking = [issue for issue in issues if issue["severity"] == "error"]
    return {
        "schema": "agent-identity-layer-envelope-validation/v1",
        "artifact_type": "agent_identity_layer_envelope",
        "valid": not blocking,
        "missing": missing,
        "registered": bool(envelope.get("ail_id") and (envelope.get("credential") or envelope.get("credential_fingerprint_sha256"))),
        "signed": bool(envelope.get("verification", {}).get("signed")),
        "issues": issues,
        "privacy": {
            "local_absolute_paths_exported": any(issue["id"] == "local_absolute_path_exported" for issue in issues),
            "credential_like_values_exported": any(issue["id"] == "credential_like_value_exported" for issue in issues),
            "raw_owner_email_exported": any(issue["id"] == "raw_owner_email_exported" for issue in issues),
        },
    }


def verify_agent_identity_artifacts(
    *,
    payload_path: Path | None = None,
    envelope_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    if payload_path is None and envelope_path is None:
        raise ValueError("Provide --payload, --envelope, or both.")

    validations: dict[str, Any] = {}
    if payload_path is not None:
        validations["payload"] = validate_agent_id_card_payload(_read_json(payload_path))
    if envelope_path is not None:
        validations["envelope"] = validate_agent_identity_layer_envelope(_read_json(envelope_path))

    all_issues = [
        {"artifact": artifact, **issue}
        for artifact, validation in validations.items()
        for issue in validation.get("issues", [])
    ]
    blocking = [issue for issue in all_issues if issue["severity"] == "error"]
    report = {
        "schema": AGENT_ID_CARD_VERIFICATION_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not blocking else "failed",
        "valid": not blocking,
        "network_action_performed": False,
        "external_registration": "not_performed_manual_owner_action_only",
        "artifacts": {
            "payload": payload_path.name if payload_path else None,
            "envelope": envelope_path.name if envelope_path else None,
        },
        "validations": validations,
        "issues": all_issues,
        "next_actions": (
            [
                "Review the local payload/envelope with the owner before external registration.",
                "Keep returned credentials, JWTs, AIL IDs, and owner contact data outside public source control.",
            ]
            if not blocking
            else [
                "Fix missing fields or privacy issues before using these identity artifacts.",
                "Regenerate the payload/envelope from the installed manifest if lineage fields are missing.",
            ]
        ),
    }
    if output_path is not None:
        _write_json(output_path, report)
    return report


def import_agent_identity_registration(
    *,
    envelope_path: Path,
    registration_result_path: Path,
    output_path: Path | None = None,
    updated_envelope_path: Path | None = None,
    include_credential_token: bool = False,
) -> dict[str, Any]:
    """Import an owner-performed external Agent ID Card/AIL registration result.

    Paideia does not register or upload anything here. The owner provides a local
    registration result file, and Paideia writes a redacted local receipt plus an
    optional updated envelope. Credential tokens are omitted by default.
    """

    envelope = _read_json(envelope_path)
    registration_result = _read_json(registration_result_path)
    envelope_validation = validate_agent_identity_layer_envelope(envelope)
    ail_id = _first_text(
        registration_result.get("ail_id"),
        registration_result.get("AIL_ID"),
        registration_result.get("id"),
        _nested_value(registration_result, ("agent_identity", "ail_id")),
        _nested_value(registration_result, ("agent_id_card", "ail_id")),
        _nested_value(registration_result, ("credential_subject", "ail_id")),
    )
    credential = _first_text(
        registration_result.get("credential"),
        registration_result.get("credential_token"),
        registration_result.get("jwt"),
        _nested_value(registration_result, ("agent_identity", "credential")),
        _nested_value(registration_result, ("agent_id_card", "credential")),
    )
    signed = _to_bool(
        _nested_value(registration_result, ("verification", "signed"))
        if _nested_value(registration_result, ("verification", "signed")) is not None
        else registration_result.get("signed")
    )
    verification_strength = _first_text(
        _nested_value(registration_result, ("verification", "strength")),
        registration_result.get("verification_strength"),
        "owner_imported_external_registration",
    )
    attestation_ref = _first_text(
        registration_result.get("attestation_ref"),
        _nested_value(registration_result, ("verification", "attestation_ref")),
        _nested_value(registration_result, ("agent_id_card", "attestation_ref")),
    )
    issues: list[dict[str, Any]] = []
    if not envelope_validation["valid"]:
        issues.append(
            {
                "id": "source_envelope_invalid",
                "severity": "error",
                "message": "Source Agent_warrent envelope must pass local validation before importing registration.",
                "source_issues": envelope_validation.get("issues", []),
            }
        )
    if not ail_id:
        issues.append(
            {
                "id": "ail_id_missing",
                "severity": "error",
                "message": "Registration result must include an AIL ID or equivalent external agent identity id.",
            }
        )
    if not signed:
        issues.append(
            {
                "id": "signed_verification_missing",
                "severity": "error",
                "message": "Registration result must indicate signed or verified external identity status.",
            }
        )
    blocking = [issue for issue in issues if issue["severity"] == "error"]
    updated_envelope: dict[str, Any] | None = None
    updated_envelope_validation: dict[str, Any] | None = None
    credential_fingerprint = _secret_hash(credential) if credential else None
    if not blocking:
        updated_envelope = json.loads(json.dumps(envelope, ensure_ascii=False))
        updated_envelope["ail_id"] = ail_id
        updated_envelope["credential"] = credential if include_credential_token else None
        if credential_fingerprint:
            updated_envelope["credential_fingerprint_sha256"] = credential_fingerprint
        verification = updated_envelope.setdefault("verification", {})
        verification["signed"] = True
        verification["strength"] = verification_strength
        verification["attestation_ref"] = attestation_ref
        agent_warrent = updated_envelope.setdefault("extensions", {}).setdefault("agent_warrent", {})
        agent_warrent["registration_state"] = "owner_imported_registered"
        agent_warrent["external_registration"] = "owner_completed_outside_paideia"
        agent_warrent["credential_storage"] = (
            "raw_token_included_by_explicit_owner_request"
            if include_credential_token and credential
            else "token_omitted_hash_only"
        )
        paideia = updated_envelope.setdefault("extensions", {}).setdefault("paideia", {})
        privacy = paideia.setdefault("privacy", {})
        privacy["credential_token_exported"] = bool(include_credential_token and credential)
        privacy["network_action_performed"] = False
        paideia["agent_id_card_import"] = {
            "schema": AGENT_ID_CARD_REGISTRATION_IMPORT_SCHEMA,
            "imported_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_result": registration_result_path.name,
            "network_action_performed_by_paideia": False,
            "credential_token_exported": bool(include_credential_token and credential),
        }
        updated_envelope_validation = validate_agent_identity_layer_envelope(updated_envelope)
        if not updated_envelope_validation["valid"]:
            issues.append(
                {
                    "id": "updated_envelope_invalid",
                    "severity": "error",
                    "message": "Updated envelope failed local validation after registration import.",
                    "source_issues": updated_envelope_validation.get("issues", []),
                }
            )
            blocking = [issue for issue in issues if issue["severity"] == "error"]
            updated_envelope = None
    report = {
        "schema": AGENT_ID_CARD_REGISTRATION_IMPORT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "imported" if not blocking else "failed",
        "valid": not blocking,
        "network_action_performed": False,
        "external_registration": "owner_completed_outside_paideia" if ail_id else "not_imported",
        "source_envelope": envelope_path.name,
        "registration_result": {
            "file": registration_result_path.name,
            "fingerprint_sha256": _canonical_hash(registration_result),
            "ail_id_present": bool(ail_id),
            "credential_token_present": bool(credential),
            "credential_token_exported": bool(include_credential_token and credential),
            "credential_fingerprint_sha256": credential_fingerprint,
            "signed": signed,
            "verification_strength": verification_strength,
        },
        "source_envelope_validation": envelope_validation,
        "updated_envelope_validation": updated_envelope_validation,
        "updated_envelope": updated_envelope_path.name if updated_envelope_path and updated_envelope else None,
        "issues": issues,
        "next_actions": (
            [
                "Keep any raw credential token outside public source control.",
                "Use the updated envelope for local hiring dossier linkage and future Agent_warrent checks.",
            ]
            if not blocking
            else [
                "Fix the registration result or regenerate the source envelope before importing again.",
            ]
        ),
    }
    if output_path is not None:
        _write_json(output_path, report)
    if updated_envelope_path is not None and updated_envelope is not None:
        _write_json(updated_envelope_path, updated_envelope)
    return report
