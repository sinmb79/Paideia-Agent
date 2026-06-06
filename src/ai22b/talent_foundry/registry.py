from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.agent_identity_card import (
    build_agent_id_card_payload,
    build_agent_identity_layer_envelope,
    verify_agent_identity_artifacts,
)
from ai22b.talent_foundry.agent_runner import run_agent_from_manifest
from ai22b.talent_foundry.dataflow_runtime import (
    DATAFLOW_RUN_SCHEMA,
    GROWTH_COMMIT_CANDIDATE_SCHEMA,
    format_dataflow_job,
    run_dataflow_job_from_manifest,
)
from ai22b.talent_foundry.learning_loop import (
    build_reasoning_kernel,
    create_learning_ledger,
    delete_learning_experience,
    refresh_learning_ledger,
    record_learning_experience,
    route_active_memory,
)
from ai22b.talent_foundry.memory_lifecycle import audit_learning_ledger
from ai22b.talent_foundry.llm_clients import LLMClient
from ai22b.talent_foundry.llm_runtime import (
    build_llm_provider_preflight,
    build_llm_runtime_config,
    invoke_llm_application_engine,
)
from ai22b.talent_foundry.llm_onboarding import build_llm_connection_profile
from ai22b.talent_foundry.onboarding_choices import resolve_chat_surface, resolve_llm_service
from ai22b.talent_foundry.team import DEFAULT_TEAM_ROLES
from ai22b.talent_foundry.workspace_agent import run_workspace_agent_from_manifest, run_workspace_agent_job_from_manifest


EMPLOYMENT_SCHEMA = "ai-talent-local-employment/v1"
REGISTRY_SCHEMA = "ai-talent-local-employment-registry/v1"
POST_HIRE_LEARNING_UPDATE_SCHEMA = "ai-talent-post-hire-learning-update/v1"
EMPLOYMENT_GOAL_SCHEMA = "ai-talent-employment-goal/v1"
EMPLOYMENT_GOAL_CYCLE_SCHEMA = "ai-talent-employment-goal-cycle/v1"
HIRED_AGENT_JOB_CYCLE_SCHEMA = "ai-talent-hired-agent-job-cycle/v1"
HIRED_AGENT_TEAM_SCHEMA = "ai-talent-hired-agent-team/v1"
HIRED_TEAM_CYCLE_SCHEMA = "ai-talent-hired-team-cycle/v1"
HIRED_PROJECTION_SWARM_SCHEMA = "ai-talent-hired-projection-swarm/v1"
HIRED_PROJECTION_SWARM_CYCLE_SCHEMA = "ai-talent-hired-projection-swarm-cycle/v1"
MEMORY_LIFECYCLE_MAINTENANCE_SCHEMA = "paideia-memory-lifecycle-maintenance/v1"
SIMULATION_ROLLOUT_EVALUATION_SCHEMA = "ai-talent-simulation-rollout-evaluation/v1"
REVIEWED_ROLLOUT_LEARNING_EVENT_SCHEMA = "paideia-reviewed-rollout-learning-event/v1"
REASONING_LEDGER_CANDIDATE_SCHEMA = "paideia-reasoning-ledger-candidate/v1"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _manifest_with_runtime_boss_approvals(
    agent_manifest: dict[str, Any],
    boss_approvals: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    if not boss_approvals:
        return agent_manifest
    merged = copy.deepcopy(agent_manifest)
    tool_policy = merged.setdefault("tool_policy", {})
    approvals = list(tool_policy.get("boss_approvals", []))
    approvals.extend(copy.deepcopy(boss_approvals))
    tool_policy["boss_approvals"] = approvals
    return merged


def _employment_id(
    *,
    install_id: str,
    employer: str,
    role: str,
    source_sha256: str,
    llm_engine: str,
    llm_model: str | None,
    llm_model_path: str | None,
) -> str:
    raw = f"{install_id}|{employer}|{role}|{source_sha256}|{llm_engine}|{llm_model or ''}|{llm_model_path or ''}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _registry_root_from_installed_manifest(installed_manifest_path: Path) -> Path:
    target_root = installed_manifest_path.parent
    agents_dir = target_root.parent
    return agents_dir.parent


def _load_registry_index(registry_index_path: Path) -> dict[str, Any]:
    if registry_index_path.exists():
        return _read_json(registry_index_path)
    return {
        "schema": REGISTRY_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "employments": [],
    }


def _llm_connection_profile_entrypoint(record_name: str) -> str:
    stem = Path(record_name).stem or "employment_record"
    if stem == "employment_record":
        return "llm_connection_profile.json"
    return f"{stem}.llm_connection_profile.json"


def _summarize_llm_connection_profile(profile: dict[str, Any], *, entrypoint: str) -> dict[str, Any]:
    setup = profile.get("setup_requirements", {})
    public_safe = profile.get("public_safe", {})
    selected = profile.get("selected_llm_service", {})
    return {
        "schema": profile.get("schema"),
        "entrypoint": entrypoint,
        "status": profile.get("status"),
        "selected_engine": selected.get("engine") if isinstance(selected, dict) else None,
        "selected_service_id": selected.get("service_id") if isinstance(selected, dict) else None,
        "requires_live_check_before_agent_work": bool(
            setup.get("requires_live_check_before_agent_work")
        )
        if isinstance(setup, dict)
        else False,
        "public_safe": {
            "network_call_performed": bool(public_safe.get("network_call_performed"))
            if isinstance(public_safe, dict)
            else False,
            "secret_values_exported": bool(public_safe.get("secret_values_exported"))
            if isinstance(public_safe, dict)
            else False,
            "raw_provider_payload_saved": bool(public_safe.get("raw_provider_payload_saved"))
            if isinstance(public_safe, dict)
            else False,
            "private_reasoning_trace": public_safe.get("private_reasoning_trace")
            if isinstance(public_safe, dict)
            else "do_not_store",
        },
    }


def _summarize_agent_identity_artifacts(
    *,
    payload: dict[str, Any],
    envelope: dict[str, Any],
    verification: dict[str, Any],
) -> dict[str, Any]:
    agent_warrent = envelope.get("extensions", {}).get("agent_warrent", {})
    return {
        "schema": "paideia-hired-agent-identity-summary/v1",
        "agent_id_card_payload": {
            "schema": payload.get("schema"),
            "status": payload.get("status"),
            "network_action_performed": bool(payload.get("network_action_performed")),
            "payload_fingerprint_sha256": payload.get("payload_fingerprint_sha256"),
        },
        "agent_identity_layer": {
            "version": envelope.get("version"),
            "ail_id": envelope.get("ail_id"),
            "agent_id": envelope.get("agent", {}).get("id"),
            "registration_state": agent_warrent.get("registration_state"),
            "external_registration": agent_warrent.get("external_registration"),
            "repo_url": agent_warrent.get("repo_url"),
            "verification_strength": envelope.get("verification", {}).get("strength"),
            "signed": bool(envelope.get("verification", {}).get("signed")),
        },
        "local_verification": {
            "schema": verification.get("schema"),
            "status": verification.get("status"),
            "valid": bool(verification.get("valid")),
            "network_action_performed": bool(verification.get("network_action_performed")),
            "external_registration": verification.get("external_registration"),
        },
        "policy": {
            "external_registration": "manual_owner_action_only",
            "credential_token_stored_by_default": False,
            "raw_owner_email_exported": False,
            "local_absolute_paths_exported": False,
        },
    }


def hire_installed_agent(
    installed_manifest_path: Path,
    *,
    employer: str,
    role: str,
    llm_service: str | None = None,
    llm_engine: str = "deterministic_local",
    llm_model: str | None = None,
    llm_model_path: str | None = None,
    chat_surface: str | None = None,
    record_name: str = "employment_record.json",
) -> dict[str, Path]:
    installed_manifest = _read_json(installed_manifest_path)
    if installed_manifest.get("schema") != "ai-talent-installed-agent/v1":
        raise ValueError("Unsupported installed agent manifest schema")
    if not installed_manifest.get("archive_verification", {}).get("passed"):
        raise ValueError("Installed agent archive verification did not pass")

    target_root = installed_manifest_path.parent
    agent_manifest_path = target_root / installed_manifest["entrypoints"]["agent_manifest"]
    agent_manifest = _read_json(agent_manifest_path)
    agent = agent_manifest["agent"]
    selected_llm_service = resolve_llm_service(
        llm_service=llm_service,
        llm_engine=llm_engine,
        llm_model=llm_model,
        llm_model_path=llm_model_path,
    )
    selected_chat_surface = resolve_chat_surface(chat_surface)
    llm_connection_profile_entrypoint = _llm_connection_profile_entrypoint(record_name)
    llm_connection_profile_path = target_root / llm_connection_profile_entrypoint
    llm_connection_profile = build_llm_connection_profile(
        llm_service=selected_llm_service["service_id"],
        llm_engine=selected_llm_service["engine"],
        llm_model=selected_llm_service.get("selected_model"),
        llm_model_path=selected_llm_service.get("selected_model_path"),
        chat_surface=selected_chat_surface["id"],
        output_path=llm_connection_profile_path,
    )
    employment_id = _employment_id(
        install_id=installed_manifest["install_id"],
        employer=employer,
        role=role,
        source_sha256=installed_manifest["source_sha256"],
        llm_engine=selected_llm_service["engine"],
        llm_model=selected_llm_service.get("selected_model"),
        llm_model_path=selected_llm_service.get("selected_model_path"),
    )
    hired_at = datetime.now(timezone.utc).isoformat()
    employment_record = {
        "schema": EMPLOYMENT_SCHEMA,
        "employment_id": employment_id,
        "hired_at_utc": hired_at,
        "employer": employer,
        "relationship": "installed_ai_talent_hired_as_local_agent",
        "install_id": installed_manifest["install_id"],
        "agent": {
            "name": agent["name"],
            "role": role,
            "major_goal": agent.get("major_goal"),
        },
        "source": {
            "installed_manifest": installed_manifest_path.name,
            "agent_manifest": installed_manifest["entrypoints"]["agent_manifest"],
            "source_archive": installed_manifest["source_archive"],
            "source_sha256": installed_manifest["source_sha256"],
        },
        "entrypoints": {
            "agent_manifest": installed_manifest["entrypoints"]["agent_manifest"],
            "memory_substrate": installed_manifest["entrypoints"].get("memory_substrate", "memory_substrate.json"),
            "language_development_program": installed_manifest["entrypoints"].get(
                "language_development_program",
                "language_development_program.json",
            ),
            "developmental_ecology": installed_manifest["entrypoints"].get(
                "developmental_ecology",
                "developmental_ecology.json",
            ),
            "life_trace": installed_manifest["entrypoints"].get("life_trace", "life_trace.jsonl"),
            "growth_profile": installed_manifest["entrypoints"].get("growth_profile", "growth_profile.json"),
            "llm_connection_profile": llm_connection_profile_entrypoint,
            "agent_id_card_payload": "agent_id_card_payload.json",
            "agent_identity_envelope": "agent_identity_envelope.json",
            "agent_identity_verification": "agent_identity_verification.json",
            "chat_log": "employment_chat_log.jsonl",
            "last_chat": "last_hired_agent_chat.json",
            "run_log": "employment_run_log.jsonl",
            "last_run": "last_hired_agent_run.json",
            "workspace_run_log": "employment_workspace_run_log.jsonl",
            "last_workspace_run": "last_hired_workspace_agent_run.json",
            "job_run_log": "employment_job_run_log.jsonl",
            "last_job_run": "last_hired_agent_job_run.json",
            "dataflow_run_log": "employment_dataflow_run_log.jsonl",
            "last_dataflow_run": "last_hired_dataflow_run.json",
            "job_cycle_log": "employment_job_cycle_log.jsonl",
            "last_job_cycle": "last_hired_agent_job_cycle.json",
            "learning_ledger": installed_manifest["entrypoints"].get("learning_ledger", "learning_ledger.json"),
            "post_hire_learning_update": "post_hire_learning_update.json",
            "post_hire_learning_log": "post_hire_learning_log.jsonl",
            "memory_lifecycle_maintenance": "memory_lifecycle_maintenance.json",
            "memory_lifecycle_maintenance_log": "memory_lifecycle_maintenance_log.jsonl",
            "learning_ledger_backup": "learning_ledger.backup.json",
            "employment_goal": "employment_goal.json",
            "employment_goal_log": "employment_goal_log.jsonl",
            "last_goal_cycle": "last_employment_goal_cycle.json",
            "goal_cycle_log": "employment_goal_cycle_log.jsonl",
        },
        "guardrails": agent_manifest.get("tool_policy", {}).get("blocked_tools", []),
        "llm_service": selected_llm_service,
        "chat_surface": selected_chat_surface,
        "llm_connection_profile": _summarize_llm_connection_profile(
            llm_connection_profile,
            entrypoint=llm_connection_profile_entrypoint,
        ),
        "llm_runtime": build_llm_runtime_config(
            engine=selected_llm_service["engine"],
            model_path=selected_llm_service.get("selected_model_path"),
            model=selected_llm_service.get("selected_model"),
            service=selected_llm_service["service_id"],
        ),
        "growth_after_hire": {
            "continues": True,
            "principle": "고용은 종료가 아니라 업무 경험을 통한 계속 성장의 시작이다.",
            "record_policy": "업무 실행 결과는 검증 가능한 성장 후보로 남긴다.",
        },
        "llm_policy": agent_manifest.get("llm_policy", {}),
        "status": "active",
    }
    employment_record_path = target_root / record_name
    _write_json(employment_record_path, employment_record)
    agent_id_card_payload_path = target_root / employment_record["entrypoints"]["agent_id_card_payload"]
    agent_identity_envelope_path = target_root / employment_record["entrypoints"]["agent_identity_envelope"]
    agent_identity_verification_path = target_root / employment_record["entrypoints"]["agent_identity_verification"]
    agent_id_card_payload = build_agent_id_card_payload(
        installed_manifest_path=installed_manifest_path,
        employment_record_path=employment_record_path,
        output_path=agent_id_card_payload_path,
    )
    agent_identity_envelope = build_agent_identity_layer_envelope(
        installed_manifest_path=installed_manifest_path,
        employment_record_path=employment_record_path,
        output_path=agent_identity_envelope_path,
        surface=selected_chat_surface.get("entrypoint") or selected_chat_surface["id"],
        task_ref=f"employment:{employment_id}",
    )
    agent_identity_verification = verify_agent_identity_artifacts(
        payload_path=agent_id_card_payload_path,
        envelope_path=agent_identity_envelope_path,
        output_path=agent_identity_verification_path,
    )
    employment_record["agent_identity"] = _summarize_agent_identity_artifacts(
        payload=agent_id_card_payload,
        envelope=agent_identity_envelope,
        verification=agent_identity_verification,
    )
    _write_json(employment_record_path, employment_record)

    registry_root = _registry_root_from_installed_manifest(installed_manifest_path)
    registry_index_path = registry_root / "employment_registry.json"
    registry_index = _load_registry_index(registry_index_path)
    registry_index["updated_at_utc"] = hired_at
    entry = {
        "employment_id": employment_id,
        "install_id": installed_manifest["install_id"],
        "agent_name": agent["name"],
        "employer": employer,
        "role": role,
        "status": "active",
        "record": f"agents/{installed_manifest['install_id']}/{record_name}",
    }
    registry_index["employments"] = [
        existing
        for existing in registry_index.get("employments", [])
        if existing.get("employment_id") != employment_id
    ]
    registry_index["employments"].append(entry)
    registry_index["employments"] = sorted(registry_index["employments"], key=lambda item: item["employment_id"])
    _write_json(registry_index_path, registry_index)

    return {
        "employment_record": employment_record_path,
        "registry_index": registry_index_path,
        "llm_connection_profile": llm_connection_profile_path,
        "agent_id_card_payload": agent_id_card_payload_path,
        "agent_identity_envelope": agent_identity_envelope_path,
        "agent_identity_verification": agent_identity_verification_path,
    }


def _load_active_employment(employment_record_path: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    employment_record = _read_json(employment_record_path)
    if employment_record.get("schema") != EMPLOYMENT_SCHEMA:
        raise ValueError("Unsupported local employment record schema")
    if employment_record.get("status") != "active":
        raise ValueError("Local employment record is not active")

    target_root = employment_record_path.parent
    agent_manifest_path = target_root / employment_record["entrypoints"]["agent_manifest"]
    return employment_record, _read_json(agent_manifest_path), target_root


def _employment_context(employment_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "employment_id": employment_record["employment_id"],
        "employer": employment_record["employer"],
        "relationship": employment_record["relationship"],
        "install_id": employment_record["install_id"],
        "agent_role": employment_record["agent"]["role"],
        "growth_after_hire_continues": employment_record["growth_after_hire"]["continues"],
        "projection_control": "single_parent_identity_controls_task_limited_projections",
    }


def _route_active_memory_for_employment(
    employment_record: dict[str, Any],
    target_root: Path,
    *,
    objective: str,
) -> dict[str, Any]:
    entrypoints = employment_record.get("entrypoints", {})
    ledger_path = target_root / entrypoints.get("learning_ledger", "learning_ledger.json")
    if ledger_path.exists():
        ledger = _read_json(ledger_path)
    else:
        ledger = create_learning_ledger(owner=employment_record["agent"]["name"])
        ledger["reasoning_kernel"] = build_reasoning_kernel(ledger)
    return route_active_memory(ledger, objective=objective, max_items=3)


def _run_source(event: dict[str, Any]) -> str:
    schema = event.get("schema")
    if schema == "ai-talent-workspace-agent-run/v1":
        return "workspace_agent_run"
    if schema == "ai-talent-hired-agent-job-run/v1":
        return "hired_agent_job_run"
    if schema == "ai-talent-agent-run/v1":
        return "agent_run"
    return "post_hire_run"


def _goal_id(employment_id: str, goal: str, cadence: str) -> str:
    return hashlib.sha256(f"{employment_id}|{goal}|{cadence}".encode("utf-8")).hexdigest()[:16]


def _team_id(team_name: str, employment_ids: list[str]) -> str:
    raw = f"{team_name}|{'|'.join(sorted(employment_ids))}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _role_slug(role: str, index: int) -> str:
    digest = hashlib.sha256(f"{index}|{role}".encode("utf-8")).hexdigest()[:8]
    return f"member_{index}_{digest}"


def _projection_id(parent_name: str, employment_id: str, role_id: str) -> str:
    digest = hashlib.sha256(f"{parent_name}|{employment_id}|{role_id}".encode("utf-8")).hexdigest()[:8]
    return f"projection_{role_id}_{digest}"


def _default_success_criteria() -> list[str]:
    return [
        "근거와 불확실성을 분리해 보스가 검토할 수 있게 남긴다.",
        "업무 산출물과 검증 흔적을 로컬 파일로 기록한다.",
        "투자 실행, 외부 업로드, 개인 데이터 전송 권한을 넘지 않는다.",
    ]


def _goal_milestones(success_criteria: list[str]) -> list[dict[str, Any]]:
    base = [
        ("goal_plan", "목표를 반복 가능한 업무 루틴과 검증 기준으로 분해한다."),
        ("workspace_execution", "각 사이클에서 계획, 결과, 트레이스를 로컬 워크스페이스에 남긴다."),
        ("review_and_growth", "보스 또는 감독위원회 검토 후 학습 원장과 추론 커널에 반영한다."),
    ]
    milestones = [
        {
            "id": milestone_id,
            "description": description,
            "status": "pending",
        }
        for milestone_id, description in base
    ]
    for index, criterion in enumerate(success_criteria, start=1):
        milestones.append(
            {
                "id": f"success_criterion_{index}",
                "description": criterion,
                "status": "pending",
            }
        )
    return milestones


def assign_hired_goal(
    employment_record_path: Path,
    *,
    goal: str,
    success_criteria: list[str] | None = None,
    cadence: str = "manual",
    output_path: Path | None = None,
) -> dict[str, Any]:
    employment_record, _agent_manifest, target_root = _load_active_employment(employment_record_path)
    criteria = success_criteria or _default_success_criteria()
    assigned_at = datetime.now(timezone.utc).isoformat()
    goal_record = {
        "schema": EMPLOYMENT_GOAL_SCHEMA,
        "goal_id": _goal_id(employment_record["employment_id"], goal, cadence),
        "assigned_at_utc": assigned_at,
        "goal": goal,
        "cadence": cadence,
        "status": "active",
        "employment_context": _employment_context(employment_record),
        "success_criteria": criteria,
        "milestones": _goal_milestones(criteria),
        "guardrails": employment_record.get("guardrails", []),
        "growth_policy": {
            "principle": "장기 목표는 반복 업무, 검토, 학습 원장 갱신을 통해 추론기풍을 성장시킨다.",
            "review_required": "boss_or_oversight_committee",
        },
        "cycles": [],
    }

    entrypoints = employment_record.get("entrypoints", {})
    goal_path = output_path or target_root / entrypoints.get("employment_goal", "employment_goal.json")
    _write_json(goal_path, goal_record)

    log_path = target_root / entrypoints.get("employment_goal_log", "employment_goal_log.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(goal_record, ensure_ascii=False) + "\n")

    return goal_record


def assemble_hired_agent_team(
    employment_record_paths: list[Path],
    *,
    team_name: str,
    domain: str,
    output_path: Path | None = None,
) -> dict[str, Any]:
    if not employment_record_paths:
        raise ValueError("At least one employment record is required")

    members = []
    guardrails: list[str] = []
    employment_ids: list[str] = []
    for index, record_path in enumerate(employment_record_paths, start=1):
        employment_record, _agent_manifest, _target_root = _load_active_employment(record_path)
        context = _employment_context(employment_record)
        employment_ids.append(context["employment_id"])
        for guardrail in employment_record.get("guardrails", []):
            if guardrail not in guardrails:
                guardrails.append(guardrail)
        members.append(
            {
                "member_id": _role_slug(context["agent_role"], index),
                "employment_context": context,
                "employment_record_path": str(record_path),
                "agent": employment_record["agent"],
                "consciousness": "separately_hired_talent_agent",
                "coordination_role": context["agent_role"],
                "growth_after_hire_continues": context["growth_after_hire_continues"],
            }
        )

    created_at = datetime.now(timezone.utc).isoformat()
    team = {
        "schema": HIRED_AGENT_TEAM_SCHEMA,
        "team_id": _team_id(team_name, employment_ids),
        "created_at_utc": created_at,
        "team": {
            "name": team_name,
            "domain": domain,
            "member_count": len(members),
        },
        "members": members,
        "team_policy": {
            "coordination_model": "separately_hired_agents_under_boss_employment",
            "not_a_projection_team": True,
            "guardrails": guardrails,
            "review_required": "boss_or_oversight_committee",
            "learning_policy": "각 멤버의 고용 기록과 학습 원장을 유지하면서 팀 사이클 결과를 검토 후 반영한다.",
        },
    }

    if output_path is not None:
        _write_json(output_path, team)
    return team


def assemble_hired_projection_swarm(
    employment_record_path: Path,
    *,
    swarm_name: str,
    domain: str,
    projection_roles: list[dict[str, str]] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    employment_record, _agent_manifest, _target_root = _load_active_employment(employment_record_path)
    context = _employment_context(employment_record)
    parent_name = employment_record["agent"]["name"]
    roles = projection_roles or DEFAULT_TEAM_ROLES
    command_model = {
        "control_topology": "single_parent_body_to_task_projections",
        "projection_control": "main_body_issues_directives",
        "execution_modes": ["role_split", "joint_collaboration"],
        "projections_can_work_together": True,
        "projection_peer_consciousness": False,
        "result_merge": "parent_synthesis_before_growth_merge",
    }
    projections = [
        {
            "projection_id": _projection_id(parent_name, context["employment_id"], role["role_id"]),
            "projection_of": parent_name,
            "employment_context": context,
            "employment_record_path": str(employment_record_path),
            "role_id": role["role_id"],
            "role_name": role["role_name"],
            "focus": role["focus"],
            "consciousness": "parent_controlled_projection",
            "control": "본체 명령에 따른 업무 분담",
            "autonomy": "task_limited_no_separate_consciousness",
            "merge_target": "parent_growth_log",
            "command_binding": {
                "source": "parent_body_command",
                "default_execution_mode": "role_split",
                "allowed_execution_modes": command_model["execution_modes"],
                "result_returns_to": "parent_synthesis",
                "independent_goal_creation": False,
            },
        }
        for role in roles
    ]
    created_at = datetime.now(timezone.utc).isoformat()
    swarm = {
        "schema": HIRED_PROJECTION_SWARM_SCHEMA,
        "swarm_id": _team_id(swarm_name, [context["employment_id"], *[item["role_id"] for item in projections]]),
        "created_at_utc": created_at,
        "parent": {
            "agent": employment_record["agent"],
            "employment_context": context,
        },
        "swarm": {
            "name": swarm_name,
            "domain": domain,
            "projection_count": len(projections),
        },
        "projections": projections,
        "swarm_policy": {
            "execution": "local_workspace_parallel_or_sequential",
            "guardrails": employment_record.get("guardrails", []),
            "review_required": "boss_or_oversight_committee",
            "control_model": {
                "identity": "single_parent_identity",
                "controller": "parent_body",
                "command_source": "parent_instruction",
                "projection_autonomy": "task_limited_no_separate_consciousness",
                "merge_target": "parent_growth_log",
                "separate_employment_records": False,
                "not_separate_consciousnesses": True,
            },
            "command_model": command_model,
            "learning_policy": "분신 결과는 독립 인재의 경력으로 저장하지 않고 본체 성장 후보로 병합한다.",
        },
    }

    if output_path is not None:
        _write_json(output_path, swarm)
    return swarm


def run_hired_agent(
    employment_record_path: Path,
    *,
    task: str,
    output_path: Path | None = None,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    boss_approvals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    employment_record, agent_manifest, target_root = _load_active_employment(employment_record_path)
    agent_manifest = _manifest_with_runtime_boss_approvals(agent_manifest, boss_approvals)
    result = run_agent_from_manifest(
        agent_manifest,
        task=task,
        runtime_config=employment_record["llm_runtime"],
        llm_mode=llm_mode,
        llm_model=llm_model,
    )
    result["employment_context"] = _employment_context(employment_record)
    result["active_memory_route"] = _route_active_memory_for_employment(
        employment_record,
        target_root,
        objective=task,
    )

    run_output_path = output_path or target_root / employment_record["entrypoints"]["last_run"]
    _write_json(run_output_path, result)

    run_log_path = target_root / employment_record["entrypoints"]["run_log"]
    run_log_path.parent.mkdir(parents=True, exist_ok=True)
    with run_log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(result, ensure_ascii=False) + "\n")

    return result


def record_hired_learning_experience(
    employment_record_path: Path,
    *,
    run_path: Path,
    quality_label: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    employment_record, _agent_manifest, target_root = _load_active_employment(employment_record_path)
    run_event = _read_json(run_path)
    source = _run_source(run_event)
    entrypoints = employment_record.get("entrypoints", {})
    ledger_path = target_root / entrypoints.get("learning_ledger", "learning_ledger.json")
    if ledger_path.exists():
        ledger = _read_json(ledger_path)
    else:
        ledger = create_learning_ledger(owner=employment_record["agent"]["name"])

    promoted_before = len(ledger.get("promoted_experiences", []))
    quarantined_before = len(ledger.get("quarantined_experiences", []))
    ledger = record_learning_experience(
        ledger,
        source=source,
        event=run_event,
        quality_label=quality_label,
    )
    ledger["reasoning_kernel"] = build_reasoning_kernel(ledger)
    _write_json(ledger_path, ledger)

    promoted_after = len(ledger.get("promoted_experiences", []))
    quarantined_after = len(ledger.get("quarantined_experiences", []))
    if promoted_after > promoted_before:
        latest_entry = ledger["promoted_experiences"][-1]
        decision = "promoted"
    elif quarantined_after > quarantined_before:
        latest_entry = ledger["quarantined_experiences"][-1]
        decision = "quarantined"
    else:
        latest_entry = {}
        decision = "unchanged"

    update = {
        "schema": POST_HIRE_LEARNING_UPDATE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "source_run": run_path.name,
        "learning_ledger": ledger_path.name,
        "employment_context": _employment_context(employment_record),
        "quality_label": quality_label,
        "decision": decision,
        "latest_experience_id": latest_entry.get("id"),
        "latest_promoted_skills": latest_entry.get("promoted_skills", []),
        "experience_counts": {
            "promoted": promoted_after,
            "quarantined": quarantined_after,
        },
        "reasoning_kernel": ledger["reasoning_kernel"],
        "memory_lifecycle": ledger.get("memory_lifecycle", {}),
    }

    update_path = output_path or target_root / entrypoints.get("post_hire_learning_update", "post_hire_learning_update.json")
    _write_json(update_path, update)

    log_path = target_root / entrypoints.get("post_hire_learning_log", "post_hire_learning_log.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(update, ensure_ascii=False) + "\n")

    return update


def _rollout_episode_for_promotion(evaluation: dict[str, Any], episode_id: str | None) -> dict[str, Any]:
    winner = evaluation.get("winner") if isinstance(evaluation.get("winner"), dict) else {}
    if episode_id is None:
        selected = winner
    else:
        selected = next(
            (
                item
                for item in evaluation.get("ranked_episodes", [])
                if isinstance(item, dict) and item.get("episode_id") == episode_id
            ),
            {},
        )
    if not selected:
        raise ValueError("No rollout episode selected for promotion")
    eligible = set(evaluation.get("memory_update_gate", {}).get("eligible_episode_ids", []))
    if selected.get("episode_id") not in eligible or selected.get("decision") != "promotion_candidate":
        raise ValueError("Selected rollout episode is not eligible for reviewed promotion")
    return selected


def _reasoning_ledger_candidate_from_rollout(
    *,
    employment_record: dict[str, Any],
    evaluation: dict[str, Any],
    selected: dict[str, Any],
    latest_experience_id: str | None,
    quality_label: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": REASONING_LEDGER_CANDIDATE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_type": "reviewed_parallel_simulation_rollout",
        "source_experience_id": latest_experience_id,
        "employment_id": employment_record["employment_id"],
        "agent_name": employment_record["agent"]["name"],
        "objective": evaluation.get("objective"),
        "episode_id": selected.get("episode_id"),
        "scenario_id": selected.get("scenario_id"),
        "review_summary": selected.get("review_summary"),
        "learning_signal": selected.get("expected_learning_signal"),
        "score": selected.get("score"),
        "quality_label": quality_label,
        "candidate_principles": [
            "Compare parallel rollout outcomes before updating durable habits.",
            "Promote only owner-reviewed winner summaries, not full private traces.",
            "Keep failed rollout episodes as quarantine/recovery material unless reviewed later.",
        ],
        "policy": {
            "automatic_promotion_performed": False,
            "boss_review_required": True,
            "boss_review_applied": True,
            "private_reasoning_trace": "do_not_store",
            "full_rollout_replay_stored": False,
            "separate_consciousness_created": False,
        },
    }


def promote_simulation_rollout_winner(
    employment_record_path: Path,
    *,
    evaluation_path: Path,
    quality_label: dict[str, Any],
    output_path: Path | None = None,
    episode_id: str | None = None,
) -> dict[str, Any]:
    employment_record, _agent_manifest, target_root = _load_active_employment(employment_record_path)
    evaluation = _read_json(evaluation_path)
    if evaluation.get("schema") != SIMULATION_ROLLOUT_EVALUATION_SCHEMA:
        raise ValueError("Unsupported simulation rollout evaluation schema")
    selected = _rollout_episode_for_promotion(evaluation, episode_id)
    entrypoints = employment_record.get("entrypoints", {})
    ledger_path = target_root / entrypoints.get("learning_ledger", "learning_ledger.json")
    backup_path = target_root / entrypoints.get("learning_ledger_backup", "learning_ledger.backup.json")
    ledger = _read_json(ledger_path) if ledger_path.exists() else create_learning_ledger(owner=employment_record["agent"]["name"])
    if ledger_path.exists():
        _write_json(backup_path, ledger)

    event = {
        "schema": REVIEWED_ROLLOUT_LEARNING_EVENT_SCHEMA,
        "source_evaluation": evaluation_path.name,
        "objective": evaluation.get("objective"),
        "selected_episode": {
            "episode_id": selected.get("episode_id"),
            "scenario_id": selected.get("scenario_id"),
            "label": selected.get("label"),
            "score": selected.get("score"),
            "decision": selected.get("decision"),
            "stressors": selected.get("stressors", []),
            "expected_learning_signal": selected.get("expected_learning_signal"),
            "review_summary": selected.get("review_summary"),
            "private_reasoning_trace_stored": False,
            "merge_policy": "reviewed_summary_only_no_private_chain_of_thought",
        },
        "rollout_gate": {
            "automatic_promotion_performed": False,
            "boss_review_required": True,
            "boss_review_applied": True,
            "reasoning_ledger_write_policy": evaluation.get("memory_update_gate", {}).get(
                "reasoning_ledger_write_policy",
            ),
            "separate_consciousness_created": False,
        },
    }

    promoted_before = len(ledger.get("promoted_experiences", []))
    quarantined_before = len(ledger.get("quarantined_experiences", []))
    ledger = record_learning_experience(
        ledger,
        source="simulation_rollout_winner",
        event=event,
        quality_label=quality_label,
    )
    promoted_after = len(ledger.get("promoted_experiences", []))
    quarantined_after = len(ledger.get("quarantined_experiences", []))
    if promoted_after > promoted_before:
        latest_entry = ledger["promoted_experiences"][-1]
        decision = "promoted"
    elif quarantined_after > quarantined_before:
        latest_entry = ledger["quarantined_experiences"][-1]
        decision = "quarantined"
    else:
        latest_entry = {}
        decision = "unchanged"

    reasoning_candidate = None
    if decision == "promoted":
        reasoning_candidate = _reasoning_ledger_candidate_from_rollout(
            employment_record=employment_record,
            evaluation=evaluation,
            selected=selected,
            latest_experience_id=latest_entry.get("id"),
            quality_label=quality_label,
        )
        ledger.setdefault("reasoning_ledger_candidates", []).append(reasoning_candidate)
    ledger["reasoning_kernel"] = build_reasoning_kernel(ledger)
    ledger["memory_lifecycle"] = audit_learning_ledger(ledger)
    _write_json(ledger_path, ledger)

    update = {
        "schema": POST_HIRE_LEARNING_UPDATE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "simulation_rollout_winner",
        "source_run": evaluation_path.name,
        "learning_ledger": ledger_path.name,
        "employment_context": _employment_context(employment_record),
        "quality_label": quality_label,
        "decision": decision,
        "latest_experience_id": latest_entry.get("id"),
        "latest_promoted_skills": latest_entry.get("promoted_skills", []),
        "reasoning_ledger_candidate": reasoning_candidate,
        "reviewed_rollout_event": event,
        "experience_counts": {
            "promoted": promoted_after,
            "quarantined": quarantined_after,
        },
        "reasoning_kernel": ledger["reasoning_kernel"],
        "memory_lifecycle": ledger.get("memory_lifecycle", {}),
        "policy": {
            "stored_summary_only": True,
            "private_reasoning_trace": "do_not_store",
            "full_evaluation_replay_stored": False,
            "automatic_promotion_performed": False,
        },
    }

    update_path = output_path or target_root / "simulation_rollout_learning_update.json"
    _write_json(update_path, update)
    log_path = target_root / entrypoints.get("post_hire_learning_log", "post_hire_learning_log.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(update, ensure_ascii=False) + "\n")
    return update


def _read_json_or_none(path: Path) -> dict[str, Any] | None:
    try:
        return _read_json(path)
    except Exception:
        return None


def _json_digest(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def maintain_hired_memory_lifecycle(
    employment_record_path: Path,
    *,
    action: str,
    experience_id: str | None = None,
    requested_by: str = "보스",
    reason: str = "manual_memory_lifecycle_maintenance",
    output_path: Path | None = None,
) -> dict[str, Any]:
    if action not in {"audit", "delete-experience", "migrate", "recover"}:
        raise ValueError("action must be audit, delete-experience, migrate, or recover")
    if action == "delete-experience" and not experience_id:
        raise ValueError("experience_id is required for delete-experience")

    employment_record, _agent_manifest, target_root = _load_active_employment(employment_record_path)
    entrypoints = employment_record.get("entrypoints", {})
    ledger_path = target_root / entrypoints.get("learning_ledger", "learning_ledger.json")
    backup_path = target_root / entrypoints.get("learning_ledger_backup", "learning_ledger.backup.json")
    maintenance_path = output_path or target_root / entrypoints.get(
        "memory_lifecycle_maintenance",
        "memory_lifecycle_maintenance.json",
    )
    log_path = target_root / entrypoints.get(
        "memory_lifecycle_maintenance_log",
        "memory_lifecycle_maintenance_log.jsonl",
    )

    loaded_from = "learning_ledger"
    ledger_existed_before = ledger_path.exists()
    current_ledger = _read_json_or_none(ledger_path) if ledger_existed_before else None
    backup_ledger = _read_json_or_none(backup_path) if backup_path.exists() else None
    current_unreadable = ledger_existed_before and current_ledger is None
    current_digest_before = _json_digest(current_ledger)
    backup_digest_before = _json_digest(backup_ledger)
    if action == "recover":
        if current_ledger is not None:
            ledger = current_ledger
            status = "recovery_not_needed"
        elif backup_ledger is not None:
            ledger = backup_ledger
            loaded_from = "learning_ledger_backup"
            status = "recovered_from_backup"
        else:
            ledger = create_learning_ledger(owner=employment_record["agent"]["name"])
            loaded_from = "new_empty_ledger"
            status = "recovered_as_empty_ledger"
    else:
        if ledger_path.exists() and current_ledger is None:
            raise ValueError("learning ledger is unreadable; run recover before audit, migrate, or delete-experience")
        ledger = current_ledger or create_learning_ledger(owner=employment_record["agent"]["name"])
        status = "completed"
        if current_ledger is not None:
            _write_json(backup_path, current_ledger)

    tombstone: dict[str, Any] | None = None
    migration: dict[str, Any] | None = None
    if action == "delete-experience":
        ledger, tombstone = delete_learning_experience(
            ledger,
            experience_id=str(experience_id),
            requested_by=requested_by,
            reason=reason,
        )
    elif action == "migrate":
        migration = {
            "schema": "paideia-memory-ledger-migration/v1",
            "migrated_at_utc": datetime.now(timezone.utc).isoformat(),
            "from_schema": ledger.get("schema"),
            "to_policy_version": "memory_lifecycle_p0_v1",
            "summary_only": True,
        }
        ledger.setdefault("schema_migrations", []).append(migration)
        ledger = refresh_learning_ledger(ledger)
    else:
        ledger = refresh_learning_ledger(ledger)
        ledger["memory_lifecycle"] = audit_learning_ledger(ledger)

    _write_json(ledger_path, ledger)
    if action == "recover":
        _write_json(backup_path, ledger)
    ledger_digest_after = _json_digest(ledger)
    backup_digest_after = _json_digest(_read_json_or_none(backup_path) if backup_path.exists() else None)

    record = {
        "schema": MEMORY_LIFECYCLE_MAINTENANCE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "status": status,
        "requested_by": requested_by,
        "reason": reason,
        "employment_context": _employment_context(employment_record),
        "learning_ledger": ledger_path.name,
        "backup": backup_path.name,
        "loaded_from": loaded_from,
        "experience_id": experience_id,
        "deleted_experience": tombstone,
        "migration": migration,
        "integrity": {
            "current_ledger_existed_before": ledger_existed_before,
            "current_ledger_readable_before": current_ledger is not None,
            "current_ledger_unreadable_before": current_unreadable,
            "backup_available_before": backup_ledger is not None,
            "ledger_digest_before_sha256": current_digest_before,
            "backup_digest_before_sha256": backup_digest_before,
            "restored_source_digest_sha256": (
                backup_digest_before
                if action == "recover" and loaded_from == "learning_ledger_backup"
                else current_digest_before
            ),
            "ledger_digest_after_sha256": ledger_digest_after,
            "backup_digest_after_sha256": backup_digest_after,
            "backup_written_for_mutation": (
                action != "recover"
                and current_digest_before is not None
                and backup_digest_after == current_digest_before
            ),
            "recovered_from_backup": action == "recover" and loaded_from == "learning_ledger_backup",
            "backup_rewritten_to_recovered_digest": (
                action == "recover"
                and loaded_from == "learning_ledger_backup"
                and backup_digest_after == ledger_digest_after
            ),
        },
        "memory_lifecycle": ledger.get("memory_lifecycle", {}),
        "counts": {
            "promoted": len(ledger.get("promoted_experiences", [])),
            "quarantined": len(ledger.get("quarantined_experiences", [])),
            "deletion_tombstones": len(ledger.get("memory_deletion_log", [])),
        },
        "policy": {
            "manual_delete_audit_log": True,
            "backup_before_mutation": action != "recover",
            "private_reasoning_trace": "do_not_store",
            "safe_reference_retention_after_delete": "removed",
        },
    }
    _write_json(maintenance_path, record)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record


def _cycle_artifact_path(base_output_path: Path | None, target_root: Path, filename: str) -> Path:
    if base_output_path is not None:
        return base_output_path.parent / filename
    return target_root / filename


def _advance_goal_progress(goal_record: dict[str, Any], cycle: dict[str, Any]) -> dict[str, Any]:
    for milestone in goal_record.get("milestones", []):
        if milestone.get("status") == "pending":
            milestone["status"] = "completed"
            milestone["completed_by_cycle"] = cycle["cycle_id"]
            break
    goal_record.setdefault("cycles", []).append(
        {
            "cycle_id": cycle["cycle_id"],
            "cycle_status": cycle["cycle_status"],
            "recorded_at_utc": cycle["created_at_utc"],
            "learning_decision": cycle["learning_update"]["decision"],
        }
    )
    if goal_record.get("milestones") and all(
        milestone.get("status") == "completed" for milestone in goal_record["milestones"]
    ):
        goal_record["status"] = "completed"
    else:
        goal_record["status"] = "active"
    return goal_record


def run_hired_goal_cycle(
    employment_record_path: Path,
    *,
    goal_path: Path,
    cycle_note: str,
    workspace_dir: Path,
    quality_label: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    employment_record, _agent_manifest, target_root = _load_active_employment(employment_record_path)
    goal_record = _read_json(goal_path)
    if goal_record.get("schema") != EMPLOYMENT_GOAL_SCHEMA:
        raise ValueError("Unsupported employment goal schema")
    if goal_record.get("employment_context", {}).get("employment_id") != employment_record["employment_id"]:
        raise ValueError("Employment goal does not belong to this employment record")

    cycle_id = hashlib.sha256(
        f"{goal_record['goal_id']}|{cycle_note}|{datetime.now(timezone.utc).isoformat()}".encode("utf-8")
    ).hexdigest()[:16]
    workspace_run_path = _cycle_artifact_path(output_path, target_root, f"{goal_record['goal_id']}_workspace_run.json")
    learning_update_path = _cycle_artifact_path(output_path, target_root, f"{goal_record['goal_id']}_learning_update.json")
    task = (
        f"고용 목표: {goal_record['goal']}\n"
        f"이번 사이클: {cycle_note}\n"
        f"성공 기준: {', '.join(goal_record.get('success_criteria', []))}"
    )
    workspace_run = run_hired_workspace_agent(
        employment_record_path,
        task=task,
        workspace_dir=workspace_dir,
        output_path=workspace_run_path,
    )
    learning_update = record_hired_learning_experience(
        employment_record_path,
        run_path=workspace_run_path,
        quality_label=quality_label,
        output_path=learning_update_path,
    )
    cycle_status = "completed" if workspace_run.get("run_status") == "completed" else "blocked"
    cycle = {
        "schema": EMPLOYMENT_GOAL_CYCLE_SCHEMA,
        "cycle_id": cycle_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "goal_id": goal_record["goal_id"],
        "goal": goal_record["goal"],
        "cycle_note": cycle_note,
        "cycle_status": cycle_status,
        "employment_context": _employment_context(employment_record),
        "workspace_run": {
            "path": str(workspace_run_path),
            "run_status": workspace_run.get("run_status"),
            "workspace_outputs": workspace_run.get("workspace_outputs", {}),
        },
        "learning_update": learning_update,
        "next_review": "보스 검토 후 다음 목표 사이클을 진행한다.",
    }

    goal_record = _advance_goal_progress(goal_record, cycle)
    _write_json(goal_path, goal_record)

    entrypoints = employment_record.get("entrypoints", {})
    cycle_path = output_path or target_root / entrypoints.get("last_goal_cycle", "last_employment_goal_cycle.json")
    _write_json(cycle_path, cycle)

    log_path = target_root / entrypoints.get("goal_cycle_log", "employment_goal_cycle_log.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(cycle, ensure_ascii=False) + "\n")

    return cycle


def run_hired_team_cycle(
    team_path: Path,
    *,
    objective: str,
    workspace_dir: Path,
    quality_label: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    team = _read_json(team_path)
    if team.get("schema") != HIRED_AGENT_TEAM_SCHEMA:
        raise ValueError("Unsupported hired agent team schema")

    workspace_dir.mkdir(parents=True, exist_ok=True)
    contributions = []
    for member in team.get("members", []):
        record_path = Path(member["employment_record_path"])
        member_workspace = workspace_dir / member["member_id"]
        run_path = workspace_dir / f"{member['member_id']}_workspace_run.json"
        learning_update_path = workspace_dir / f"{member['member_id']}_learning_update.json"
        task = (
            f"팀 목표: {objective}\n"
            f"담당 역할: {member['coordination_role']}\n"
            "팀 보고서에 들어갈 검토 가능한 로컬 산출물을 작성한다."
        )
        workspace_run = run_hired_workspace_agent(
            record_path,
            task=task,
            workspace_dir=member_workspace,
            output_path=run_path,
        )
        learning_update = record_hired_learning_experience(
            record_path,
            run_path=run_path,
            quality_label=quality_label,
            output_path=learning_update_path,
        )
        contributions.append(
            {
                "member_id": member["member_id"],
                "employment_id": member["employment_context"]["employment_id"],
                "agent_role": member["employment_context"]["agent_role"],
                "run_status": workspace_run.get("run_status"),
                "workspace_run": workspace_run,
                "learning_update": learning_update,
            }
        )

    statuses = [item["run_status"] for item in contributions]
    cycle_status = "completed" if statuses and all(status == "completed" for status in statuses) else "blocked"
    created_at = datetime.now(timezone.utc).isoformat()
    cycle = {
        "schema": HIRED_TEAM_CYCLE_SCHEMA,
        "cycle_id": hashlib.sha256(f"{team['team_id']}|{objective}|{created_at}".encode("utf-8")).hexdigest()[:16],
        "created_at_utc": created_at,
        "team_id": team["team_id"],
        "team": team["team"],
        "objective": objective,
        "cycle_status": cycle_status,
        "team_policy": team["team_policy"],
        "contributions": contributions,
        "synthesis": {
            "summary": "별도 고용된 전문 에이전트들의 관점을 모아 보스 검토용 팀 결과로 정리했다.",
            "roles_consulted": [item["agent_role"] for item in contributions],
            "merge_policy": "팀 결과는 보스 검토 전 확정하지 않는다.",
            "investment_execution": "blocked",
        },
    }

    if output_path is not None:
        _write_json(output_path, cycle)
    log_path = (output_path.parent if output_path is not None else team_path.parent) / "hired_team_cycle_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(cycle, ensure_ascii=False) + "\n")

    return cycle


def run_hired_projection_swarm_cycle(
    swarm_path: Path,
    *,
    objective: str,
    workspace_dir: Path,
    quality_label: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    swarm = _read_json(swarm_path)
    if swarm.get("schema") != HIRED_PROJECTION_SWARM_SCHEMA:
        raise ValueError("Unsupported hired projection swarm schema")

    workspace_dir.mkdir(parents=True, exist_ok=True)
    contributions = []
    directives = []
    for projection in swarm.get("projections", []):
        record_path = Path(projection["employment_record_path"])
        projection_workspace = workspace_dir / projection["projection_id"]
        run_path = workspace_dir / f"{projection['projection_id']}_workspace_run.json"
        learning_update_path = workspace_dir / f"{projection['projection_id']}_learning_update.json"
        directive = {
            "projection_id": projection["projection_id"],
            "source": "parent_body_directive",
            "objective": objective,
            "role_id": projection["role_id"],
            "role_name": projection["role_name"],
            "focus": projection["focus"],
            "execution_mode": projection.get("command_binding", {}).get("default_execution_mode", "role_split"),
            "joint_collaboration_allowed": True,
            "result_returns_to": "parent_synthesis",
        }
        directives.append(directive)
        task = (
            f"군체 목표: {objective}\n"
            f"본체: {projection['projection_of']}\n"
            f"분신 역할: {projection['role_name']}\n"
            f"집중 관점: {projection['focus']}\n"
            f"본체 지시 실행 모드: {directive['execution_mode']}\n"
            "별도 의식을 만들지 말고 본체 명령에 따른 검증 가능한 부분 결과만 작성한다."
        )
        workspace_run = run_hired_workspace_agent(
            record_path,
            task=task,
            workspace_dir=projection_workspace,
            output_path=run_path,
        )
        learning_update = record_hired_learning_experience(
            record_path,
            run_path=run_path,
            quality_label=quality_label,
            output_path=learning_update_path,
        )
        contributions.append(
            {
                "projection_id": projection["projection_id"],
                "projection_of": projection["projection_of"],
                "employment_context": projection["employment_context"],
                "role_id": projection["role_id"],
                "role_name": projection["role_name"],
                "focus": projection["focus"],
                "consciousness": projection["consciousness"],
                "command_source": directive["source"],
                "execution_mode": directive["execution_mode"],
                "directive": directive,
                "run_status": workspace_run.get("run_status"),
                "workspace_run": workspace_run,
                "learning_update": learning_update,
            }
        )

    statuses = [item["run_status"] for item in contributions]
    cycle_status = "completed" if statuses and all(status == "completed" for status in statuses) else "blocked"
    created_at = datetime.now(timezone.utc).isoformat()
    cycle = {
        "schema": HIRED_PROJECTION_SWARM_CYCLE_SCHEMA,
        "cycle_id": hashlib.sha256(f"{swarm['swarm_id']}|{objective}|{created_at}".encode("utf-8")).hexdigest()[:16],
        "created_at_utc": created_at,
        "swarm_id": swarm["swarm_id"],
        "swarm": swarm["swarm"],
        "objective": objective,
        "cycle_status": cycle_status,
        "employment_context": swarm["parent"]["employment_context"],
        "swarm_policy": swarm["swarm_policy"],
        "dispatch_plan": {
            "control_topology": "single_parent_body_to_task_projections",
            "parent": swarm["parent"]["agent"]["name"],
            "execution_modes": ["role_split", "joint_collaboration"],
            "directives": directives,
            "separate_consciousness_created": False,
        },
        "contributions": contributions,
        "parent_synthesis": {
            "summary": "본체가 역할별 분신 결과를 모아 하나의 검토 결과로 합성한다.",
            "roles_consulted": [item["role_id"] for item in contributions],
            "separate_consciousness_created": False,
            "final_control": "parent_body",
            "joint_collaboration_allowed": True,
            "investment_execution": "blocked",
        },
        "parent_growth_merge": {
            "merge_target": "parent_growth_log",
            "merge_status": "pending_boss_review",
            "learning_update_count": len(contributions),
            "principle": "분신의 경험은 독립 인재 이력이 아니라 본체의 업무 경험 후보로만 반영한다.",
        },
    }

    if output_path is not None:
        _write_json(output_path, cycle)
    log_path = (output_path.parent if output_path is not None else swarm_path.parent) / "hired_projection_swarm_cycle_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(cycle, ensure_ascii=False) + "\n")

    return cycle


def run_hired_workspace_agent(
    employment_record_path: Path,
    *,
    task: str,
    workspace_dir: Path,
    output_path: Path | None = None,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    llm_client: LLMClient | None = None,
    boss_approvals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    employment_record, agent_manifest, target_root = _load_active_employment(employment_record_path)
    agent_manifest = _manifest_with_runtime_boss_approvals(agent_manifest, boss_approvals)
    result = run_workspace_agent_from_manifest(
        agent_manifest,
        task=task,
        workspace_dir=workspace_dir,
        runtime_config=employment_record["llm_runtime"],
        llm_mode=llm_mode,
        llm_model=llm_model,
        llm_client=llm_client,
    )
    result["employment_context"] = _employment_context(employment_record)
    result["active_memory_route"] = _route_active_memory_for_employment(
        employment_record,
        target_root,
        objective=task,
    )

    entrypoints = employment_record.get("entrypoints", {})
    run_output_path = output_path or target_root / entrypoints.get("last_workspace_run", "last_hired_workspace_agent_run.json")
    _write_json(run_output_path, result)

    run_log_path = target_root / entrypoints.get("workspace_run_log", "employment_workspace_run_log.jsonl")
    run_log_path.parent.mkdir(parents=True, exist_ok=True)
    with run_log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(result, ensure_ascii=False) + "\n")

    return result


def run_hired_agent_job(
    employment_record_path: Path,
    *,
    job_spec: dict[str, Any],
    workspace_dir: Path,
    output_path: Path | None = None,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    llm_client: LLMClient | None = None,
    boss_approvals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    employment_record, agent_manifest, target_root = _load_active_employment(employment_record_path)
    agent_manifest = _manifest_with_runtime_boss_approvals(agent_manifest, boss_approvals)
    result = run_workspace_agent_job_from_manifest(
        agent_manifest,
        job_spec=job_spec,
        workspace_dir=workspace_dir,
        runtime_config=employment_record["llm_runtime"],
        llm_mode=llm_mode,
        llm_model=llm_model,
        llm_client=llm_client,
    )
    result["schema"] = "ai-talent-hired-agent-job-run/v1"
    result["llm_runtime_result"] = result["workspace_run"]["llm_runtime_result"]
    result["llm_provider_preflight"] = result["llm_runtime_result"].get("llm_provider_preflight")
    result["employment_context"] = _employment_context(employment_record)
    result["active_memory_route"] = _route_active_memory_for_employment(
        employment_record,
        target_root,
        objective=result["job_spec"]["objective"],
    )
    result["workspace_run"]["active_memory_route"] = result["active_memory_route"]

    entrypoints = employment_record.get("entrypoints", {})
    run_output_path = output_path or target_root / entrypoints.get("last_job_run", "last_hired_agent_job_run.json")
    _write_json(run_output_path, result)

    run_log_path = target_root / entrypoints.get("job_run_log", "employment_job_run_log.jsonl")
    run_log_path.parent.mkdir(parents=True, exist_ok=True)
    with run_log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(result, ensure_ascii=False) + "\n")

    return result


def run_hired_dataflow_job(
    employment_record_path: Path,
    *,
    job_spec: dict[str, Any],
    workspace_dir: Path,
    review_label: dict[str, Any],
    output_path: Path | None = None,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    llm_client: LLMClient | None = None,
    boss_approvals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    employment_record, agent_manifest, target_root = _load_active_employment(employment_record_path)
    agent_manifest = _manifest_with_runtime_boss_approvals(agent_manifest, boss_approvals)
    entrypoints = employment_record.get("entrypoints", {})
    ledger_path = target_root / entrypoints.get("learning_ledger", "learning_ledger.json")
    if ledger_path.exists():
        ledger = _read_json(ledger_path)
    else:
        ledger = create_learning_ledger(owner=employment_record["agent"]["name"])
        ledger["reasoning_kernel"] = build_reasoning_kernel(ledger)

    formatted_job = format_dataflow_job(job_spec)
    llm_provider_preflight = build_llm_provider_preflight(
        employment_record["llm_runtime"],
        llm_mode=llm_mode,
        llm_model=llm_model,
    )
    provider_not_ready = (
        llm_mode == "live"
        and llm_client is None
        and llm_provider_preflight.get("status") == "needs_configuration"
    )
    if provider_not_ready:
        agent = agent_manifest.get("agent", {})
        llm_runtime_result = {
            "schema": "ai-talent-llm-runtime-result/v1",
            "engine": employment_record["llm_runtime"].get("engine", "deterministic_local"),
            "status": "skipped_provider_not_ready",
            "reason": "live_provider_needs_configuration_before_dataflow_execution",
            "identity_policy": employment_record["llm_runtime"].get(
                "identity_policy",
                "application_engine_not_identity",
            ),
            "network_access": employment_record["llm_runtime"].get("network_access", "blocked"),
            "llm_mode": llm_mode,
            "model": llm_model or employment_record["llm_runtime"].get("model"),
            "llm_provider_preflight": llm_provider_preflight,
        }
        result = {
            "schema": DATAFLOW_RUN_SCHEMA,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "runtime_model": "agent_dataflow_runtime_v1",
            "run_status": "needs_configuration",
            "agent": {
                "name": agent.get("name"),
                "role": agent.get("role"),
                "major_goal": agent.get("major_goal"),
            },
            "objective": formatted_job["objective"],
            "llm_policy": agent_manifest.get("llm_policy", {"role": "application_engine_not_identity"}),
            "tool_policy": agent_manifest.get("tool_policy", {}),
            "formatted_job": formatted_job,
            "llm_runtime_result": llm_runtime_result,
            "llm_provider_preflight": llm_provider_preflight,
            "workspace_outputs": {},
            "workspace_resource_usage": {
                "status": "not_started_provider_configuration_required",
                "workspace_root_created": False,
            },
            "growth_commit_candidate": {
                "schema": GROWTH_COMMIT_CANDIDATE_SCHEMA,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "objective": formatted_job["objective"],
                "promotion_status": "quarantine",
                "review_label": review_label,
                "verification_status": "skipped_provider_not_ready",
                "verification_issues": ["live_provider_needs_configuration_before_dataflow_execution"],
                "private_reasoning_trace_policy": "do_not_store",
            },
            "runtime_observability": {
                "schema": "paideia-runtime-observability/v1",
                "status": "skipped_provider_not_ready",
                "provider_usage_present": False,
                "private_reasoning_trace_stored": False,
                "raw_provider_payload_saved": False,
            },
        }
    else:
        result = run_dataflow_job_from_manifest(
            agent_manifest,
            ledger=ledger,
            job_spec=formatted_job,
            workspace_dir=workspace_dir,
            review_label=review_label,
        )
        result["llm_runtime_result"] = invoke_llm_application_engine(
            employment_record["llm_runtime"],
            manifest=agent_manifest,
            task=result["objective"],
            llm_mode=llm_mode,
            llm_model=llm_model,
            client=llm_client,
        )
        result["llm_provider_preflight"] = result["llm_runtime_result"].get("llm_provider_preflight")
    result["employment_context"] = _employment_context(employment_record)

    run_output_path = output_path or target_root / entrypoints.get("last_dataflow_run", "last_hired_dataflow_run.json")
    _write_json(run_output_path, result)

    run_log_path = target_root / entrypoints.get("dataflow_run_log", "employment_dataflow_run_log.jsonl")
    run_log_path.parent.mkdir(parents=True, exist_ok=True)
    with run_log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(result, ensure_ascii=False) + "\n")

    return result


def run_hired_agent_job_cycle(
    employment_record_path: Path,
    *,
    job_spec: dict[str, Any],
    workspace_dir: Path,
    quality_label: dict[str, Any],
    output_path: Path | None = None,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    llm_client: LLMClient | None = None,
    boss_approvals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    employment_record, _agent_manifest, target_root = _load_active_employment(employment_record_path)
    entrypoints = employment_record.get("entrypoints", {})
    job_run_path = _cycle_artifact_path(
        output_path,
        target_root,
        entrypoints.get("last_job_run", "last_hired_agent_job_run.json"),
    )
    learning_update_path = _cycle_artifact_path(
        output_path,
        target_root,
        "post_hire_learning_update.job_cycle.json",
    )
    job_run = run_hired_agent_job(
        employment_record_path,
        job_spec=job_spec,
        workspace_dir=workspace_dir,
        output_path=job_run_path,
        llm_mode=llm_mode,
        llm_model=llm_model,
        llm_client=llm_client,
        boss_approvals=boss_approvals,
    )
    learning_update = record_hired_learning_experience(
        employment_record_path,
        run_path=job_run_path,
        quality_label=quality_label,
        output_path=learning_update_path,
    )
    next_active_memory_route = _route_active_memory_for_employment(
        employment_record,
        target_root,
        objective=job_run["job_spec"]["objective"],
    )
    if job_run.get("job_status") == "completed" and learning_update.get("decision") == "promoted":
        cycle_status = "completed_and_promoted"
    elif job_run.get("job_status") == "completed":
        cycle_status = "completed_needs_review"
    else:
        cycle_status = "blocked"

    created_at = datetime.now(timezone.utc).isoformat()
    cycle = {
        "schema": HIRED_AGENT_JOB_CYCLE_SCHEMA,
        "cycle_id": hashlib.sha256(
            f"{employment_record['employment_id']}|{job_run['job_spec']['objective']}|{created_at}".encode("utf-8")
        ).hexdigest()[:16],
        "created_at_utc": created_at,
        "cycle_status": cycle_status,
        "employment_context": _employment_context(employment_record),
        "job_run": job_run,
        "job_run_path": str(job_run_path),
        "learning_update": learning_update,
        "learning_update_path": str(learning_update_path),
        "next_active_memory_route": next_active_memory_route,
        "growth_loop": {
            "execution": "job_spec_to_workspace_artifacts",
            "review": "quality_label_attached",
            "promotion": learning_update.get("decision"),
            "next_memory_route": "refreshed_after_learning_update",
        },
    }

    cycle_path = output_path or target_root / entrypoints.get("last_job_cycle", "last_hired_agent_job_cycle.json")
    _write_json(cycle_path, cycle)

    log_path = target_root / entrypoints.get("job_cycle_log", "employment_job_cycle_log.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(cycle, ensure_ascii=False) + "\n")

    return cycle
