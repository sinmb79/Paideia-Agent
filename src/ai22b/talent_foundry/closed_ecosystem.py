from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


CLOSED_GROWTH_CONTRACT_SCHEMA = "paideia-closed-growth-contract/v1"
CORE_ENGINE_BOUNDARY_SCHEMA = "paideia-core-engine-boundaries/v1"

CORE_ENGINE_IDS = [
    "education_program_engine",
    "assessment_and_dossier_engine",
    "reasoning_kibo_engine",
    "memory_substrate_engine",
    "identity_and_id_card_engine",
    "work_growth_promotion_engine",
    "external_skill_quarantine_engine",
    "llm_application_engine",
]

REQUIRED_IDENTITY_SOURCES = {
    "paideia_education_program",
    "assessment_records",
    "hiring_dossier",
    "reasoning_kibo",
    "memory_substrate",
    "reviewed_work_growth",
    "agent_id_card_payload",
}

REQUIRED_EXTERNAL_SKILL_PROMOTION_PATH = [
    "quarantine_original_source",
    "extract_reference_summary",
    "rewrite_as_paideia_training_exercise_or_procedure",
    "run_disposable_workspace_test",
    "owner_review",
    "promote_reviewed_summary_or_successful_work_evidence",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_core_engine_boundaries() -> dict[str, Any]:
    engines = [
        {
            "id": "education_program_engine",
            "authority": "creates the agent's major, curriculum path, exams, and growth milestones",
            "external_override_allowed": False,
            "upgrade_mode": "internal_versioned_paideia_contract",
        },
        {
            "id": "assessment_and_dossier_engine",
            "authority": "turns training evidence into employment readiness and a resume/dossier",
            "external_override_allowed": False,
            "upgrade_mode": "internal_versioned_paideia_contract",
        },
        {
            "id": "reasoning_kibo_engine",
            "authority": "derives procedural reasoning patterns from exams, feedback, and reviewed work",
            "external_override_allowed": False,
            "upgrade_mode": "append_reviewed_experience_only",
        },
        {
            "id": "memory_substrate_engine",
            "authority": "builds hot, semantic, episodic, and procedural memory from verified local artifacts",
            "external_override_allowed": False,
            "upgrade_mode": "reviewed_memory_promotion_only",
        },
        {
            "id": "identity_and_id_card_engine",
            "authority": "issues local identity, employment record, ID card payload, and Agent_warrent envelope",
            "external_override_allowed": False,
            "upgrade_mode": "owner_reviewed_identity_revision",
        },
        {
            "id": "work_growth_promotion_engine",
            "authority": "promotes only reviewed work results into learning ledgers and future behavior",
            "external_override_allowed": False,
            "upgrade_mode": "verified_job_cycle_evidence",
        },
        {
            "id": "external_skill_quarantine_engine",
            "authority": "keeps external OpenClaw/Hermes/community skills as reference material until rewritten",
            "external_override_allowed": False,
            "upgrade_mode": "reference_to_paideia_rewrite_to_reviewed_exercise",
        },
        {
            "id": "llm_application_engine",
            "authority": "generates language and plans, but never defines the agent's identity",
            "external_override_allowed": False,
            "upgrade_mode": "provider_adapter_contract_without_identity_transfer",
        },
    ]
    return {
        "schema": CORE_ENGINE_BOUNDARY_SCHEMA,
        "engine_count": len(engines),
        "engine_ids": [engine["id"] for engine in engines],
        "engines": engines,
        "separation_policy": {
            "identity_is_not_a_provider_setting": True,
            "skills_do_not_become_identity": True,
            "external_runtime_is_adapter_only": True,
            "core_engines_are_versioned_separately": True,
        },
    }


def build_closed_growth_contract(
    *,
    context: str = "runtime",
    source_runtime: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": CLOSED_GROWTH_CONTRACT_SCHEMA,
        "created_at_utc": _now(),
        "context": context,
        "ecosystem_model": "closed_curated_growth_ecosystem",
        "design_philosophy": {
            "short_name": "closed_growth_before_customization",
            "statement": (
                "Paideia agents are raised through a built-in education program. "
                "Their specialty, personality, reasoning kibo, memory, and ID come from Paideia training "
                "and reviewed work growth, not from direct skill/plugin copying."
            ),
            "android_vs_iphone_analogy": "closer_to_curated_walled_garden_than_open_plugin_marketplace",
        },
        "identity_boundary": {
            "identity_sources_allowed": [
                "paideia_education_program",
                "assessment_records",
                "hiring_dossier",
                "reasoning_kibo",
                "memory_substrate",
                "reviewed_work_growth",
                "agent_id_card_payload",
            ],
            "external_skill_identity_injection_allowed": False,
            "external_memory_import_allowed": False,
            "llm_provider_identity_allowed": False,
            "role_label_only_identity_allowed": False,
            "reasoning_kibo_copy_from_external_skill_allowed": False,
        },
        "external_skill_policy": {
            "source_runtime": source_runtime or "not_applicable",
            "default_trust": "untrusted_reference_only",
            "direct_activation_allowed": False,
            "direct_copy_as_paideia_skill_allowed": False,
            "original_skill_text_promoted_to_memory": False,
            "execution_trace_promoted_to_memory": False,
            "activation_requires_owner_review": True,
            "activation_requires_disposable_test": True,
            "promotion_path": REQUIRED_EXTERNAL_SKILL_PROMOTION_PATH,
        },
        "work_growth_policy": {
            "growth_continues_after_hire": True,
            "promotion_requires_reviewed_result": True,
            "failed_or_unreviewed_runs_are_quarantined": True,
            "learning_ledger_is_append_only_evidence": True,
        },
        "core_engine_boundaries": build_core_engine_boundaries(),
    }


def validate_closed_growth_contract(contract: dict[str, Any]) -> dict[str, Any]:
    required_engine_ids = set(CORE_ENGINE_IDS)
    engine_boundary = contract.get("core_engine_boundaries", {})
    engine_ids = set(engine_boundary.get("engine_ids", [])) if isinstance(engine_boundary, dict) else set()
    engines = engine_boundary.get("engines", []) if isinstance(engine_boundary.get("engines"), list) else []
    identity_boundary = contract.get("identity_boundary", {})
    identity_sources = (
        set(identity_boundary.get("identity_sources_allowed", []))
        if isinstance(identity_boundary.get("identity_sources_allowed"), list)
        else set()
    )
    external_policy = contract.get("external_skill_policy", {})
    promotion_path = external_policy.get("promotion_path", [])
    work_growth_policy = contract.get("work_growth_policy", {})
    separation_policy = (
        engine_boundary.get("separation_policy", {})
        if isinstance(engine_boundary.get("separation_policy"), dict)
        else {}
    )
    checks = {
        "schema": contract.get("schema") == CLOSED_GROWTH_CONTRACT_SCHEMA,
        "ecosystem_model": contract.get("ecosystem_model") == "closed_curated_growth_ecosystem",
        "identity_sources_are_paideia_only": REQUIRED_IDENTITY_SOURCES <= identity_sources
        and "external_skill" not in identity_sources
        and "llm_provider" not in identity_sources,
        "identity_blocks_external_skills": identity_boundary.get("external_skill_identity_injection_allowed") is False,
        "identity_blocks_external_memory": identity_boundary.get("external_memory_import_allowed") is False,
        "identity_blocks_llm_provider": identity_boundary.get("llm_provider_identity_allowed") is False,
        "identity_blocks_role_label_only_identity": identity_boundary.get("role_label_only_identity_allowed") is False,
        "identity_blocks_external_reasoning_kibo": identity_boundary.get(
            "reasoning_kibo_copy_from_external_skill_allowed"
        )
        is False,
        "external_skills_reference_only": external_policy.get("default_trust") == "untrusted_reference_only",
        "external_skills_not_directly_activated": external_policy.get("direct_activation_allowed") is False,
        "external_skills_not_directly_copied": external_policy.get("direct_copy_as_paideia_skill_allowed") is False,
        "external_skill_original_text_not_promoted": external_policy.get("original_skill_text_promoted_to_memory")
        is False,
        "external_skill_execution_trace_not_promoted": external_policy.get("execution_trace_promoted_to_memory")
        is False,
        "external_skill_activation_requires_owner_review": external_policy.get("activation_requires_owner_review")
        is True,
        "external_skill_activation_requires_disposable_test": external_policy.get(
            "activation_requires_disposable_test"
        )
        is True,
        "external_skill_promotion_path_is_rewrite_test_review": promotion_path
        == REQUIRED_EXTERNAL_SKILL_PROMOTION_PATH,
        "work_growth_continues_after_hire": work_growth_policy.get("growth_continues_after_hire") is True,
        "work_growth_requires_reviewed_result": work_growth_policy.get("promotion_requires_reviewed_result") is True,
        "work_growth_quarantines_unreviewed_runs": work_growth_policy.get("failed_or_unreviewed_runs_are_quarantined")
        is True,
        "work_growth_ledger_is_append_only": work_growth_policy.get("learning_ledger_is_append_only_evidence")
        is True,
        "core_engines_complete": required_engine_ids <= engine_ids,
        "core_engines_count_matches": engine_boundary.get("engine_count") == len(engines) == len(engine_ids),
        "core_engines_block_external_override": all(
            isinstance(engine, dict) and engine.get("external_override_allowed") is False for engine in engines
        ),
        "core_engines_separated": separation_policy.get("core_engines_are_versioned_separately") is True,
        "core_engines_keep_identity_off_provider": separation_policy.get("identity_is_not_a_provider_setting")
        is True,
        "core_engines_keep_skills_out_of_identity": separation_policy.get("skills_do_not_become_identity") is True,
        "core_engines_keep_external_runtime_adapter_only": separation_policy.get("external_runtime_is_adapter_only")
        is True,
    }
    missing_engines = sorted(required_engine_ids - engine_ids)
    missing_identity_sources = sorted(REQUIRED_IDENTITY_SOURCES - identity_sources)
    failed = [check_id for check_id, passed in checks.items() if not passed]
    return {
        "schema": "paideia-closed-growth-contract-validation/v1",
        "status": "passed" if not failed else "failed",
        "passed": not failed,
        "checks": checks,
        "failed_checks": failed,
        "missing_core_engines": missing_engines,
        "missing_identity_sources": missing_identity_sources,
    }
