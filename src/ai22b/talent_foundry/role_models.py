from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from ai22b.config import PROJECT_ROOT, storage_path


ROLE_MODEL_SCHEMA = "ai-talent-role-model/v1"
ROLE_MODEL_CATALOG_SCHEMA = "ai-talent-role-model-catalog/v1"
CURRICULUM_MANIFEST_SCHEMA = "ai-talent-curriculum-manifest/v1"
CURRICULUM_CATALOG_SCHEMA = "ai-talent-curriculum-catalog/v1"
ROLE_MODEL_CATALOG_DIR = PROJECT_ROOT / "apps" / "ai-talent-foundry" / "catalogs" / "role_models"
CURRICULUM_CATALOG_DIR = PROJECT_ROOT / "apps" / "ai-talent-foundry" / "catalogs" / "curricula"
DEFAULT_PRIVATE_CURRICULUM_DIR = storage_path("private", "curricula", "graham_securities")


class RoleModelNotFoundError(ValueError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_role_models(domain: str | None = None) -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = []
    if not ROLE_MODEL_CATALOG_DIR.exists():
        return models
    for path in sorted(ROLE_MODEL_CATALOG_DIR.glob("*.json")):
        item = _read_json(path)
        if item.get("schema") == ROLE_MODEL_SCHEMA:
            candidates = [item]
        elif item.get("schema") == ROLE_MODEL_CATALOG_SCHEMA:
            candidates = list(item.get("role_models", []))
        else:
            continue
        for candidate in candidates:
            if candidate.get("schema") != ROLE_MODEL_SCHEMA:
                continue
            if domain and candidate.get("domain") != domain:
                continue
            models.append(candidate)
    return models


def get_role_model(role_model_id: str) -> dict[str, Any]:
    for item in list_role_models():
        if item.get("role_model_id") == role_model_id:
            return item
    raise RoleModelNotFoundError(f"Unknown role model: {role_model_id}")


def _curriculum_for(role_model: dict[str, Any]) -> dict[str, Any]:
    role_model_id = role_model["role_model_id"]
    for path in sorted(CURRICULUM_CATALOG_DIR.glob("*.json")):
        item = _read_json(path)
        if item.get("schema") == CURRICULUM_MANIFEST_SCHEMA:
            candidates = [item]
        elif item.get("schema") == CURRICULUM_CATALOG_SCHEMA:
            candidates = list(item.get("curricula", []))
        else:
            continue
        for candidate in candidates:
            if candidate.get("schema") != CURRICULUM_MANIFEST_SCHEMA:
                continue
            if candidate.get("role_model_id") == role_model_id:
                return candidate
    raise RoleModelNotFoundError(f"No curriculum manifest for role model: {role_model_id}")


def build_role_model_profile(role_model_id: str) -> dict[str, Any]:
    role_model = deepcopy(get_role_model(role_model_id))
    role_model["use_policy"] = {
        "identity": "process_template_only",
        "impersonation": "forbidden",
        "personality_injection": "forbidden",
        "worldview_keyword_injection": "forbidden",
        "claims": (
            "The local AI talent is not the public figure. The system replicates sourced learning "
            "conditions, coursework, assessments, and feedback loops so the talent can form its own "
            "reasoning habits."
        ),
    }
    return role_model


def build_curriculum_manifest(
    role_model_id: str,
    *,
    private_curriculum_dir: str | Path | None = None,
) -> dict[str, Any]:
    role_model = get_role_model(role_model_id)
    manifest = deepcopy(_curriculum_for(role_model))
    private_dir = (
        Path(private_curriculum_dir)
        if private_curriculum_dir
        else storage_path("private", "curricula", role_model_id)
    )
    manifest["private_curriculum"] = {
        "path": str(private_dir),
        "public_export_label": f"[AI22B_STORAGE_ROOT]/private/curricula/{role_model_id}",
        "allowed_file_policy": "local_user_provided_materials_only",
        "public_release": "redact_or_metadata_only",
    }
    return manifest


def summarize_role_model(role_model: dict[str, Any]) -> dict[str, Any]:
    identity = role_model.get("public_identity", {})
    return {
        "role_model_id": role_model.get("role_model_id"),
        "domain": role_model.get("domain"),
        "display_name": role_model.get("display_name"),
        "inspiration_mode": role_model.get("inspiration_mode"),
        "birth_date": identity.get("birth_date"),
        "status": role_model.get("catalog_status", "ready"),
        "primary_agent_use_case": role_model.get("primary_agent_use_case"),
        "source_count": len(role_model.get("source_facts", [])),
        "copyright_policy": role_model.get("copyright_policy", {}).get("public_repo_policy"),
    }
