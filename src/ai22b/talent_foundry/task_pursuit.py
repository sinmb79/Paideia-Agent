from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


TASK_PURSUIT_CONTRACT_SCHEMA = "paideia-task-pursuit-contract/v1"
TASK_PURSUIT_PLAN_SCHEMA = "paideia-task-pursuit-plan/v1"
TASK_PURSUIT_VALIDATION_SCHEMA = "paideia-task-pursuit-validation/v1"

SIX_W_FIELDS = ["who", "what", "when", "where", "why", "how"]

TASK_PURSUIT_LOOP = [
    "receive_owner_instruction",
    "define_objective_and_success_criteria",
    "frame_with_six_w",
    "inventory_local_context",
    "decide_necessary_research_only",
    "perform_needed_work_or_development",
    "verify_result_against_success_criteria",
    "repair_or_continue_next_iteration",
    "record_review_gated_learning_candidate",
]

NECESSARY_RESEARCH_GATES = [
    {
        "id": "local_context_first",
        "rule": "Inspect local project files, existing records, tests, and prior artifacts before external research.",
    },
    {
        "id": "targeted_external_research_only",
        "rule": "Use external search only when local context is insufficient, facts are high-drift, or source attribution is needed.",
    },
    {
        "id": "primary_or_owner_authorized_sources",
        "rule": "Prefer official documentation, papers, standards, or owner-provided materials over generic summaries.",
    },
    {
        "id": "no_broad_search_as_default",
        "rule": "Do not treat exhaustive search as the primary method; search supports a task method already framed by the agent.",
    },
]

STOP_CONDITIONS = [
    "objective_completed_and_verified",
    "safety_policy_blocks_execution",
    "owner_approval_or_credential_required",
    "same_blocker_repeated_three_times",
    "resource_limit_reached_with_reviewable_partial_result",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compact(value: Any, *, limit: int = 600) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _objective_from_request(owner_request: str, objective: str | None) -> str:
    selected = objective if objective and objective.strip() else owner_request
    selected = _compact(selected, limit=800)
    if not selected:
        raise ValueError("owner_request or objective must be non-empty")
    return selected


def build_task_pursuit_contract(
    *,
    context: str = "runtime",
    owner_label: str = "Boss",
    max_iterations: int = 8,
) -> dict[str, Any]:
    """Build the Paideia contract for plan-mode plus goal-pursuit execution.

    The contract intentionally stores reviewable summaries only. It never stores
    hidden chain-of-thought or treats provider output as agent identity.
    """

    return {
        "schema": TASK_PURSUIT_CONTRACT_SCHEMA,
        "created_at_utc": _now(),
        "context": context,
        "mode": "six_w_plan_and_goal_pursuit",
        "owner_label": owner_label,
        "purpose": (
            "Turn an owner instruction into a reviewable objective, necessary research/work queue, "
            "verification path, and persistent iteration until completion or a clear blocker."
        ),
        "six_w_frame_required": True,
        "six_w_fields": [
            {
                "id": "who",
                "question": "Who is responsible, affected, or needed for the task?",
                "expected_answer": "owner, assigned Paideia talent, required reviewers, and bounded collaborators",
            },
            {
                "id": "what",
                "question": "What concrete outcome must be completed?",
                "expected_answer": "objective, deliverables, acceptance criteria, and excluded work",
            },
            {
                "id": "when",
                "question": "When should each step happen and when does the loop stop?",
                "expected_answer": "start gate, iteration cadence, verification point, and stop condition",
            },
            {
                "id": "where",
                "question": "Where should context, work, and records live?",
                "expected_answer": "local workspace, selected chat/work surface, output artifacts, and memory route",
            },
            {
                "id": "why",
                "question": "Why is this task necessary for the owner and the agent's growth?",
                "expected_answer": "owner value, domain purpose, training value, and risk of not doing it",
            },
            {
                "id": "how",
                "question": "How will the agent solve it with the fewest necessary steps?",
                "expected_answer": "method, necessary research, implementation work, verification, and repair loop",
            },
        ],
        "loop": TASK_PURSUIT_LOOP,
        "research_policy": {
            "broad_exhaustive_search_is_primary_method": False,
            "necessary_research_gates": NECESSARY_RESEARCH_GATES,
            "external_research_is_supporting_action": True,
            "record_source_links_when_external_research_used": True,
        },
        "execution_policy": {
            "plan_before_work": True,
            "work_until_completed_or_blocked": True,
            "max_iterations_default": max_iterations,
            "registered_tools_remain_execution_authority": True,
            "llm_tool_suggestions_are_non_authoritative": True,
            "repair_before_declaring_failure": True,
        },
        "verification_policy": {
            "success_criteria_required": True,
            "verify_after_each_iteration": True,
            "evidence_artifact_required_when_work_is_materialized": True,
            "failed_claims_must_be_repaired_or_reported": True,
        },
        "learning_policy": {
            "growth_during_work": True,
            "automatic_memory_promotion_allowed": False,
            "promotion_requires": ["verification_passed", "boss_or_committee_review"],
            "mistakes_become_corrective_practice": True,
        },
        "stop_conditions": STOP_CONDITIONS,
        "privacy": {
            "private_reasoning_trace": "do_not_store",
            "raw_provider_payload_saved": False,
            "full_session_replay_stored": False,
            "summary_and_evidence_only": True,
        },
    }


def _default_success_criteria(objective: str) -> list[str]:
    return [
        "The objective is restated as a concrete, reviewable outcome.",
        "Only local context and necessary targeted research are used.",
        "Required work or development is completed as local artifacts where applicable.",
        "The result is verified against acceptance criteria before completion is claimed.",
        "Any blocker is reported with the next needed owner action instead of hidden failure.",
    ]


def _six_w_frame(
    *,
    objective: str,
    owner_label: str,
    agent: dict[str, Any] | None,
    success_criteria: list[str],
) -> dict[str, Any]:
    agent_name = str((agent or {}).get("name") or "assigned_paideia_talent")
    agent_role = str((agent or {}).get("role") or "local_ai_talent")
    return {
        "who": {
            "answer": f"{owner_label} gives the objective; {agent_name} handles it as {agent_role}.",
            "review_focus": "Confirm the owner, assigned talent, reviewer, and any external dependency.",
        },
        "what": {
            "answer": objective,
            "acceptance_criteria": success_criteria,
        },
        "when": {
            "answer": "Start after policy and readiness gates; iterate until verified completion or a clear stop condition.",
            "stop_conditions": STOP_CONDITIONS,
        },
        "where": {
            "answer": "Use the local workspace, selected chat/work surface, and reviewable output artifacts.",
            "memory_route": "Only verified summaries can become learning candidates.",
        },
        "why": {
            "answer": (
                "Complete the owner's requested outcome while strengthening the talent's own problem-solving method "
                "through verified work and review-gated learning."
            ),
        },
        "how": {
            "answer": (
                "Frame the task with 6W, inspect local context, run only necessary research, do the required work, "
                "verify, repair, and repeat until the objective is complete or blocked."
            ),
            "method_loop": TASK_PURSUIT_LOOP,
        },
    }


def build_task_pursuit_plan(
    owner_request: str,
    *,
    objective: str | None = None,
    success_criteria: list[str] | None = None,
    agent: dict[str, Any] | None = None,
    context: str = "runtime",
    owner_label: str = "Boss",
    max_iterations: int = 8,
) -> dict[str, Any]:
    objective_text = _objective_from_request(owner_request, objective)
    criteria = [_compact(item, limit=240) for item in (success_criteria or []) if str(item).strip()]
    if not criteria:
        criteria = _default_success_criteria(objective_text)
    contract = build_task_pursuit_contract(
        context=context,
        owner_label=owner_label,
        max_iterations=max_iterations,
    )
    six_w = _six_w_frame(
        objective=objective_text,
        owner_label=owner_label,
        agent=agent,
        success_criteria=criteria,
    )
    request_digest = hashlib.sha256(owner_request.encode("utf-8")).hexdigest()
    plan = {
        "schema": TASK_PURSUIT_PLAN_SCHEMA,
        "created_at_utc": _now(),
        "context": context,
        "request_digest_sha256": request_digest,
        "objective": objective_text,
        "agent": {
            "name": (agent or {}).get("name"),
            "role": (agent or {}).get("role"),
            "major_goal": (agent or {}).get("major_goal"),
        },
        "contract_schema": contract["schema"],
        "contract_digest_sha256": _digest(contract),
        "six_w_frame": six_w,
        "success_criteria": criteria,
        "necessary_research_plan": {
            "mode": "targeted_after_task_framing",
            "local_context_first": True,
            "external_search_default": "only_if_needed",
            "gates": NECESSARY_RESEARCH_GATES,
            "research_queue": [
                {
                    "id": "inspect_existing_local_context",
                    "trigger": "always",
                    "purpose": "Find current code, docs, tests, records, and owner-provided artifacts relevant to the objective.",
                },
                {
                    "id": "targeted_external_research",
                    "trigger": "only_when_local_context_is_insufficient_or_facts_are_high_drift",
                    "purpose": "Collect only the missing facts needed to complete or verify the objective.",
                },
                {
                    "id": "source_review",
                    "trigger": "when_external_research_was_used",
                    "purpose": "Attach source links or evidence summaries without importing external identity or skills.",
                },
            ],
        },
        "work_queue": [
            {
                "id": "plan",
                "status": "pending",
                "goal": "Convert the objective into a small ordered work plan.",
            },
            {
                "id": "gather",
                "status": "pending",
                "goal": "Gather only the local and external context needed for the plan.",
            },
            {
                "id": "execute",
                "status": "pending",
                "goal": "Perform the required work or development using registered local authority.",
            },
            {
                "id": "verify",
                "status": "pending",
                "goal": "Run tests, doctors, review checks, or artifact inspection that match the acceptance criteria.",
            },
            {
                "id": "repair_or_finish",
                "status": "pending",
                "goal": "Repair failed checks, continue the next iteration, or finish with evidence.",
            },
        ],
        "iteration_policy": {
            "continue_until": "objective_completed_or_stop_condition",
            "max_iterations": max_iterations,
            "same_blocker_threshold": 3,
            "repair_before_completion_claim": True,
            "report_partial_result_when_blocked": True,
        },
        "completion_packet_required": {
            "summary": True,
            "changed_artifacts": True,
            "verification_evidence": True,
            "remaining_blockers": True,
            "learning_candidate": "quarantine_until_review",
        },
        "private_reasoning_policy": {
            "hidden_chain_of_thought_stored": False,
            "reviewable_reasoning_summary_only": True,
        },
        "public_safe": {
            "network_call_performed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
        },
    }
    validation = validate_task_pursuit_plan(plan, contract=contract)
    plan["validation"] = validation
    return plan


def validate_task_pursuit_contract(contract: dict[str, Any]) -> dict[str, Any]:
    six_w_ids = [
        str(item.get("id"))
        for item in contract.get("six_w_fields", [])
        if isinstance(item, dict) and item.get("id")
    ]
    research_policy = contract.get("research_policy", {}) if isinstance(contract.get("research_policy"), dict) else {}
    execution_policy = contract.get("execution_policy", {}) if isinstance(contract.get("execution_policy"), dict) else {}
    learning_policy = contract.get("learning_policy", {}) if isinstance(contract.get("learning_policy"), dict) else {}
    privacy = contract.get("privacy", {}) if isinstance(contract.get("privacy"), dict) else {}
    checks = {
        "schema": contract.get("schema") == TASK_PURSUIT_CONTRACT_SCHEMA,
        "six_w_fields_complete": six_w_ids == SIX_W_FIELDS,
        "loop_complete": contract.get("loop") == TASK_PURSUIT_LOOP,
        "broad_search_not_primary": research_policy.get("broad_exhaustive_search_is_primary_method") is False,
        "local_context_first_gate_present": any(
            isinstance(item, dict) and item.get("id") == "local_context_first"
            for item in research_policy.get("necessary_research_gates", [])
        ),
        "work_until_completed_or_blocked": execution_policy.get("work_until_completed_or_blocked") is True,
        "registered_tools_are_authority": execution_policy.get("registered_tools_remain_execution_authority") is True,
        "automatic_memory_promotion_blocked": learning_policy.get("automatic_memory_promotion_allowed") is False,
        "private_reasoning_not_stored": privacy.get("private_reasoning_trace") == "do_not_store",
        "stop_conditions_complete": contract.get("stop_conditions") == STOP_CONDITIONS,
    }
    failed = [check_id for check_id, passed in checks.items() if not passed]
    return {
        "schema": TASK_PURSUIT_VALIDATION_SCHEMA,
        "target_schema": TASK_PURSUIT_CONTRACT_SCHEMA,
        "status": "passed" if not failed else "failed",
        "passed": not failed,
        "checks": checks,
        "failed_checks": failed,
    }


def validate_task_pursuit_plan(
    plan: dict[str, Any],
    *,
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    six_w = plan.get("six_w_frame", {}) if isinstance(plan.get("six_w_frame"), dict) else {}
    research_plan = (
        plan.get("necessary_research_plan", {})
        if isinstance(plan.get("necessary_research_plan"), dict)
        else {}
    )
    iteration = plan.get("iteration_policy", {}) if isinstance(plan.get("iteration_policy"), dict) else {}
    private_reasoning = (
        plan.get("private_reasoning_policy", {})
        if isinstance(plan.get("private_reasoning_policy"), dict)
        else {}
    )
    contract_validation = validate_task_pursuit_contract(contract) if contract is not None else None
    checks = {
        "schema": plan.get("schema") == TASK_PURSUIT_PLAN_SCHEMA,
        "objective_present": bool(plan.get("objective")),
        "six_w_frame_complete": list(six_w.keys()) == SIX_W_FIELDS,
        "success_criteria_present": bool(plan.get("success_criteria")),
        "local_context_first": research_plan.get("local_context_first") is True,
        "external_search_not_default": research_plan.get("external_search_default") == "only_if_needed",
        "work_queue_present": bool(plan.get("work_queue")),
        "continue_until_completion_or_stop": iteration.get("continue_until") == "objective_completed_or_stop_condition",
        "same_blocker_threshold_three": iteration.get("same_blocker_threshold") == 3,
        "hidden_chain_of_thought_not_stored": private_reasoning.get("hidden_chain_of_thought_stored") is False,
        "contract_valid": contract_validation is None or contract_validation.get("passed") is True,
    }
    failed = [check_id for check_id, passed in checks.items() if not passed]
    return {
        "schema": TASK_PURSUIT_VALIDATION_SCHEMA,
        "target_schema": TASK_PURSUIT_PLAN_SCHEMA,
        "status": "passed" if not failed else "failed",
        "passed": not failed,
        "checks": checks,
        "failed_checks": failed,
        "contract_validation": contract_validation,
    }
