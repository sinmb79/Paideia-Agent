from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


CLOSED_GROWTH_CONTRACT_SCHEMA = "paideia-closed-growth-contract/v1"
CORE_ENGINE_BOUNDARY_SCHEMA = "paideia-core-engine-boundaries/v1"

CORE_ENGINE_IDS = [
    "education_program_engine",
    "assessment_and_dossier_engine",
    "embodied_practice_and_exam_engine",
    "genius_derivation_engine",
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

REQUIRED_INTERNALIZATION_STAGES = [
    "perception_and_attention",
    "paideia_curriculum_mapping",
    "guided_practice",
    "timed_exam_or_task_trial",
    "feedback_and_error_correction",
    "reasoning_kibo_consolidation",
    "varied_work_application",
]

REQUIRED_PRACTICE_LOOP = [
    "understand_task",
    "choose_minimal_necessary_method",
    "solve_under_time_constraint",
    "review_result_and_errors",
    "extract_personal_method",
    "apply_method_to_new_domain",
]

REQUIRED_REINFORCEMENT_SIGNALS = [
    "exam_score",
    "rubric_feedback",
    "mistake_correction",
    "successful_work_evidence",
    "boss_or_oversight_review",
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
            "id": "embodied_practice_and_exam_engine",
            "authority": "forces knowledge to pass through practice, timed exams, feedback, and application",
            "external_override_allowed": False,
            "upgrade_mode": "curriculum_practice_exam_feedback_cycle",
        },
        {
            "id": "genius_derivation_engine",
            "authority": (
                "derives narrow domain excellence from fixed-capacity attention allocation, "
                "pattern chunking, deliberate practice, weakness guardrails, and reviewed transfer work"
            ),
            "external_override_allowed": False,
            "upgrade_mode": "exam_feedback_chunking_and_verified_transfer_only",
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
            "human_body_brain_analogy": (
                "The agent is treated like a learning body with a brain, not like a computer accepting USB copy. "
                "Knowledge must be attended to, practiced, tested, corrected, and consolidated."
            ),
            "android_vs_iphone_analogy": "closer_to_curated_walled_garden_than_open_plugin_marketplace",
        },
        "embodied_learning_policy": {
            "knowledge_transfer_model": "internalization_through_training_not_direct_copy",
            "direct_usb_style_data_transfer_allowed": False,
            "direct_memory_patch_allowed": False,
            "direct_solution_method_copy_allowed": False,
            "external_material_enters_as": "stimulus_reference_for_training",
            "internalization_stages": REQUIRED_INTERNALIZATION_STAGES,
        },
        "practice_reasoning_policy": {
            "goal": "develop_agent_owned_problem_solving_method",
            "genius_derivation_goal": "domain_specific_excellence_under_fixed_capacity",
            "broad_exhaustive_search_is_primary_method": False,
            "search_role": "reference_and_evidence_support_after_task_framing",
            "raw_compute_scaling_is_primary_path": False,
            "practice_loop": REQUIRED_PRACTICE_LOOP,
            "timed_exam_practice_required": True,
            "short_time_solution_training_required": True,
            "method_transfer_to_varied_work_required": True,
            "pattern_chunking_required": True,
            "explicit_weakness_guardrails_required": True,
        },
        "reinforcement_learning_policy": {
            "reinforcement_happens_during_training_and_work": True,
            "signals": REQUIRED_REINFORCEMENT_SIGNALS,
            "reinforces_agent_owned_methods": True,
            "raw_external_answer_reinforcement_allowed": False,
            "mistakes_are_converted_to_corrective_practice": True,
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
    embodied_policy = contract.get("embodied_learning_policy", {})
    internalization_stages = embodied_policy.get("internalization_stages", [])
    practice_policy = contract.get("practice_reasoning_policy", {})
    practice_loop = practice_policy.get("practice_loop", [])
    reinforcement_policy = contract.get("reinforcement_learning_policy", {})
    reinforcement_signals = reinforcement_policy.get("signals", [])
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
        "embodied_learning_blocks_usb_transfer": embodied_policy.get("direct_usb_style_data_transfer_allowed")
        is False,
        "embodied_learning_blocks_direct_memory_patch": embodied_policy.get("direct_memory_patch_allowed") is False,
        "embodied_learning_blocks_direct_method_copy": embodied_policy.get("direct_solution_method_copy_allowed")
        is False,
        "embodied_learning_requires_full_internalization": internalization_stages
        == REQUIRED_INTERNALIZATION_STAGES,
        "practice_reasoning_not_broad_search_first": practice_policy.get("broad_exhaustive_search_is_primary_method")
        is False,
        "practice_reasoning_not_raw_compute_scaling": practice_policy.get("raw_compute_scaling_is_primary_path")
        is False,
        "practice_reasoning_uses_required_loop": practice_loop == REQUIRED_PRACTICE_LOOP,
        "practice_reasoning_requires_timed_exam": practice_policy.get("timed_exam_practice_required") is True,
        "practice_reasoning_requires_short_time_solution_training": practice_policy.get(
            "short_time_solution_training_required"
        )
        is True,
        "practice_reasoning_transfers_method_to_varied_work": practice_policy.get(
            "method_transfer_to_varied_work_required"
        )
        is True,
        "practice_reasoning_requires_pattern_chunking": practice_policy.get("pattern_chunking_required") is True,
        "practice_reasoning_requires_weakness_guardrails": practice_policy.get(
            "explicit_weakness_guardrails_required"
        )
        is True,
        "reinforcement_uses_exam_feedback_work_signals": reinforcement_signals == REQUIRED_REINFORCEMENT_SIGNALS,
        "reinforcement_targets_agent_owned_methods": reinforcement_policy.get("reinforces_agent_owned_methods")
        is True,
        "reinforcement_blocks_raw_external_answers": reinforcement_policy.get(
            "raw_external_answer_reinforcement_allowed"
        )
        is False,
        "reinforcement_converts_mistakes_to_practice": reinforcement_policy.get(
            "mistakes_are_converted_to_corrective_practice"
        )
        is True,
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
