from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AGENT_ID_CARD_PAYLOAD_SCHEMA = "ai-talent-agent-id-card-payload/v1"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _fingerprint(*parts: str) -> str:
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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

    installed_manifest = _read_json(installed_manifest_path)
    if installed_manifest.get("schema") != "ai-talent-installed-agent/v1":
        raise ValueError("Unsupported installed agent manifest schema")

    target_root = installed_manifest_path.parent
    entrypoints = installed_manifest.get("entrypoints", {})
    agent_manifest = _read_json(target_root / entrypoints["agent_manifest"])
    dossier_path = target_root / entrypoints.get("hiring_dossier", "hiring_dossier.json")
    dossier = _read_json(dossier_path) if dossier_path.exists() else {}
    employment_record = _read_json(employment_record_path) if employment_record_path else {}

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
        "next_steps": [
            "Review display_name, owner_org, role, and scope.",
            "Register through Agent ID Card only if the owner explicitly chooses external registration.",
            "Store returned AIL ID and credential token outside public source control.",
        ],
    }
    if output_path is not None:
        _write_json(output_path, payload)
    return payload
