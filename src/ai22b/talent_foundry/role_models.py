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
ROLE_MODEL_CURRICULUM_CATALOG_SCHEMA = "paideia-role-model-curriculum-catalog/v1"
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
    if not CURRICULUM_CATALOG_DIR.exists():
        raise RoleModelNotFoundError(f"No curriculum catalog directory for role model: {role_model_id}")
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


def _summarize_curriculum(curriculum: dict[str, Any]) -> dict[str, Any]:
    stages = list(curriculum.get("stages", []))
    course_count = sum(len(stage.get("courses", [])) for stage in stages)
    assessment_count = sum(len(stage.get("assessments", [])) for stage in stages)
    assessment_ladder = curriculum.get("assessment_ladder", {})
    required_for_hiring = list(assessment_ladder.get("required_for_hiring", []))
    major_defaults = curriculum.get("major_defaults", {})
    return {
        "status": "connected",
        "curriculum_id": curriculum.get("curriculum_id"),
        "language": curriculum.get("language"),
        "track_id": major_defaults.get("track_id"),
        "track_name": major_defaults.get("track_name"),
        "specialty": major_defaults.get("specialty"),
        "target_role": major_defaults.get("target_role"),
        "university": major_defaults.get("university"),
        "graduate_school": major_defaults.get("graduate_school"),
        "doctoral_project": major_defaults.get("doctoral_project"),
        "stage_count": len(stages),
        "course_count": course_count,
        "assessment_count": assessment_count,
        "required_for_hiring_count": len(required_for_hiring),
        "required_for_hiring": required_for_hiring,
        "stage_cards": [
            {
                "id": stage.get("id"),
                "label": stage.get("label"),
                "course_count": len(stage.get("courses", [])),
                "assessment_count": len(stage.get("assessments", [])),
            }
            for stage in stages
        ],
        "record_policy": assessment_ladder.get("record_policy"),
        "reasoning_ledger_policy": curriculum.get("process_replication", {}).get("reasoning_kibo_policy"),
        "material_policy": curriculum.get("material_policy", {}),
    }


def _missing_curriculum_summary(role_model: dict[str, Any], error: Exception) -> dict[str, Any]:
    return {
        "status": "missing",
        "curriculum_id": None,
        "role_model_id": role_model.get("role_model_id"),
        "reason": str(error),
        "stage_count": 0,
        "course_count": 0,
        "assessment_count": 0,
        "required_for_hiring_count": 0,
        "required_for_hiring": [],
        "stage_cards": [],
    }


def summarize_role_model_curriculum(role_model: dict[str, Any]) -> dict[str, Any]:
    role_summary = summarize_role_model(role_model)
    try:
        curriculum_summary = _summarize_curriculum(_curriculum_for(role_model))
    except RoleModelNotFoundError as exc:
        curriculum_summary = _missing_curriculum_summary(role_model, exc)
    role_model_id = role_summary["role_model_id"]
    return {
        **role_summary,
        "selection_card": {
            "id": role_model_id,
            "label": role_summary["display_name"],
            "domain": role_summary["domain"],
            "primary_agent_use_case": role_summary["primary_agent_use_case"],
            "curriculum_status": curriculum_summary["status"],
            "track_name": curriculum_summary.get("track_name"),
            "stage_count": curriculum_summary["stage_count"],
            "assessment_count": curriculum_summary["assessment_count"],
            "required_for_hiring_count": curriculum_summary["required_for_hiring_count"],
        },
        "curriculum": curriculum_summary,
        "blueprint_command": (
            "ai22b-talent-foundry blueprint "
            f"--domain {role_summary['domain']} "
            f"--role-model {role_model_id} "
            "--talent-name <name> --gender <gender> --owner <owner> --request <goal>"
        ),
        "raise_command": "ai22b-talent-foundry raise --blueprint <blueprint.json>",
        "hiring_outputs": [
            "assessment_transcript.json",
            "reasoning_kibo.jsonl",
            "hiring_dossier.json",
            "HIRING_DOSSIER.ko.md",
            "agent_identity_envelope.json",
            "agent_warrent_registration_request.json",
        ],
        "policy": {
            "impersonation": "forbidden",
            "personality_injection": "forbidden",
            "copyright": role_model.get("copyright_policy", {}).get("public_repo_policy"),
            "saju_birth_seed": role_model.get("emulation_policy", {}).get(
                "saju_role",
                "symbolic_initial_condition_generator_only",
            ),
            "private_materials": "metadata_only_until_owner_supplies_local_copy",
        },
    }


def build_role_model_curriculum_catalog(
    domain: str | None = None,
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    cards = [summarize_role_model_curriculum(item) for item in list_role_models(domain)]
    connected = [item for item in cards if item["curriculum"]["status"] == "connected"]
    missing = [item for item in cards if item["curriculum"]["status"] != "connected"]
    result = {
        "schema": ROLE_MODEL_CURRICULUM_CATALOG_SCHEMA,
        "domain": domain,
        "summary": {
            "role_model_count": len(cards),
            "curriculum_connected_count": len(connected),
            "missing_curriculum_count": len(missing),
            "ready_for_onboarding": bool(cards) and not missing,
            "domains": sorted({str(item["domain"]) for item in cards if item.get("domain")}),
            "role_model_ids": [item["role_model_id"] for item in cards],
            "missing_role_model_ids": [item["role_model_id"] for item in missing],
        },
        "onboarding_use": {
            "first_screen": "Choose a role model process template after selecting the LLM service and chat surface.",
            "selection_policy": "education_process_replication_not_impersonation",
            "llm_identity_policy": "application_engine_not_identity",
            "curriculum_gate": "A role model is ready for onboarding only when curriculum_status is connected.",
        },
        "public_safe": {
            "network_call_performed": False,
            "secret_values_exported": False,
            "private_materials_included": False,
            "local_absolute_paths_exported": False,
            "copyrighted_bodies_included": False,
        },
        "role_models": cards,
    }
    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
