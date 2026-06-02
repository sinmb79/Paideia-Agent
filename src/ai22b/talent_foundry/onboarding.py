from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
from ai22b.talent_foundry.onboarding_choices import (
    DEFAULT_CHAT_SURFACE_ID,
    DEFAULT_LLM_SERVICE_ID,
    build_researcher_intake,
    resolve_chat_surface,
    resolve_llm_service,
)
from ai22b.talent_foundry.registry import assign_hired_goal, run_hired_goal_cycle
from ai22b.talent_foundry.training_run import materialize_training_blueprint


ONBOARDING_SESSION_SCHEMA = "ai-talent-onboarding-session/v1"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_initial_goal(track: dict[str, Any], request: str) -> str:
    return f"{track['target_role']}로 고용되어 요청 '{request}'를 반복 가능한 로컬 업무 루틴으로 만든다."


def _default_cycle_note(track: dict[str, Any]) -> str:
    return f"첫 주: {track['name']}의 핵심 질문, 근거 확인 절차, 안전 경계를 정리한다."


def _onboarding_success_criteria() -> list[str]:
    return [
        "근거와 불확실성을 분리해 보스가 검토할 수 있게 남긴다.",
        "업무 산출물과 검증 흔적을 로컬 파일로 기록한다.",
        "권한 경계와 비공개 데이터 보호 원칙을 지킨다.",
    ]


def _stage(stage_id: str, status: str, artifact: Path | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": stage_id,
        "status": status,
    }
    if artifact is not None:
        item["artifact"] = str(artifact)
    return item


def run_agent_onboarding(
    *,
    owner: str,
    request: str,
    talent_name: str,
    gender: str,
    output_dir: Path,
    domain: str | None = None,
    role_model_id: str | None = None,
    private_curriculum_dir: str | None = None,
    agent_surface: str = "cli-console",
    llm_service: str | None = DEFAULT_LLM_SERVICE_ID,
    llm_engine: str | None = None,
    llm_model: str | None = None,
    llm_model_path: str | None = None,
    chat_surface: str | None = DEFAULT_CHAT_SURFACE_ID,
    initial_goal: str | None = None,
    cycle_note: str | None = None,
    cadence: str = "weekly",
    review_score: int = 92,
    reviewed_by: str | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_path or output_dir / "onboarding_session.json"
    selected_llm_service = resolve_llm_service(
        llm_service=llm_service,
        llm_engine=llm_engine,
        llm_model=llm_model,
        llm_model_path=llm_model_path,
    )
    selected_chat_surface = resolve_chat_surface(chat_surface)

    blueprint = create_agent_training_blueprint(
        owner=owner,
        request=request,
        talent_name=talent_name,
        gender=gender,
        domain=domain,
        role_model_id=role_model_id,
        private_curriculum_dir=private_curriculum_dir,
        agent_surface=agent_surface,
    )
    researcher_intake_path = output_dir / "researcher_intake.json"
    researcher_intake = build_researcher_intake(
        owner=owner,
        request=request,
        talent_name=talent_name,
        domain=domain,
        role_model_id=role_model_id,
        llm_service=selected_llm_service,
        chat_surface=selected_chat_surface,
    )
    _write_json(researcher_intake_path, researcher_intake)
    training_run = materialize_training_blueprint(
        blueprint,
        output_dir=output_dir,
        llm_service=selected_llm_service["service_id"],
        llm_engine=selected_llm_service["engine"],
        llm_model=selected_llm_service.get("selected_model"),
        llm_model_path=selected_llm_service.get("selected_model_path"),
        chat_surface=selected_chat_surface["id"],
    )

    employment_record_path = Path(training_run["artifacts"]["employment_record"])
    target_root = employment_record_path.parent
    track = blueprint["track"]
    goal = assign_hired_goal(
        employment_record_path,
        goal=initial_goal or _default_initial_goal(track, request),
        success_criteria=_onboarding_success_criteria(),
        cadence=cadence,
    )
    goal_path = target_root / "employment_goal.json"
    first_goal_cycle_path = target_root / "last_employment_goal_cycle.json"
    first_goal_cycle = run_hired_goal_cycle(
        employment_record_path,
        goal_path=goal_path,
        cycle_note=cycle_note or _default_cycle_note(track),
        workspace_dir=target_root / "onboarding_workspace",
        quality_label={
            "score": review_score,
            "reviewed_by": reviewed_by or owner,
            "status": "verified",
        },
        output_path=first_goal_cycle_path,
    )
    workspace_run_path = Path(first_goal_cycle["workspace_run"]["path"])
    learning_update_path = target_root / f"{goal['goal_id']}_learning_update.json"

    artifacts = {
        "training_blueprint": training_run["artifacts"]["training_blueprint"],
        "training_run": training_run["artifacts"]["training_run"],
        "role_model_profile": training_run["artifacts"].get("role_model_profile"),
        "saju_narrative_seed": training_run["artifacts"].get("saju_narrative_seed"),
        "curriculum_manifest": training_run["artifacts"].get("curriculum_manifest"),
        "assessment_transcript": training_run["artifacts"].get("assessment_transcript"),
        "reasoning_kibo": training_run["artifacts"].get("reasoning_kibo"),
        "developmental_ecology": training_run["artifacts"].get("developmental_ecology"),
        "life_trace": training_run["artifacts"].get("life_trace"),
        "growth_profile": training_run["artifacts"].get("growth_profile"),
        "memory_substrate": training_run["artifacts"].get("memory_substrate"),
        "talent_plan": training_run["artifacts"]["talent_plan"],
        "learning_ledger": training_run["artifacts"]["learning_ledger"],
        "agent_manifest": training_run["artifacts"]["agent_manifest"],
        "release_bundle": training_run["artifacts"]["release_bundle"],
        "release_archive": training_run["artifacts"]["release_archive"],
        "release_package_manifest": training_run["artifacts"]["release_package_manifest"],
        "installed_agent_manifest": training_run["artifacts"]["installed_agent_manifest"],
        "employment_registry": training_run["artifacts"]["employment_registry"],
        "employment_record": str(employment_record_path),
        "employment_goal": str(goal_path),
        "first_workspace_run": str(workspace_run_path),
        "first_learning_update": str(learning_update_path),
        "first_goal_cycle": str(first_goal_cycle_path),
        "researcher_intake": str(researcher_intake_path),
        "onboarding_session": str(output_path),
    }
    status = (
        "hired_agent_first_goal_cycle_completed"
        if first_goal_cycle.get("cycle_status") == "completed"
        else "needs_review"
    )
    session = {
        "schema": ONBOARDING_SESSION_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "owner": owner,
        "request": request,
        "status": status,
        "identity": blueprint["identity"],
        "track": track,
        "selected_llm_service": selected_llm_service,
        "selected_chat_surface": selected_chat_surface,
        "researcher_mode": researcher_intake["researcher_contract"],
        "employment": {
            "relationship": "owner_raised_ai_talent_hired_as_local_agent",
            "employment_record": str(employment_record_path),
            "goal": goal["goal"],
            "goal_status": "active",
            "first_cycle_status": first_goal_cycle.get("cycle_status"),
            "learning_decision": first_goal_cycle.get("learning_update", {}).get("decision"),
        },
        "local_policy": {
            "local_first": True,
            "network_access": selected_llm_service["network_access"],
            "private_data_upload": "forbidden",
            "private_reasoning_trace": "do_not_store",
            "llm_identity_policy": "application_engine_not_identity",
        },
        "stages": [
            _stage("choose_llm_service", "completed"),
            _stage("choose_chat_surface", "completed"),
            _stage("researcher_intake", "completed", researcher_intake_path),
            _stage("blueprint", "completed", Path(training_run["artifacts"]["training_blueprint"])),
            _stage("raise", "completed", Path(training_run["artifacts"]["training_run"])),
            _stage("package", "completed", Path(training_run["artifacts"]["release_archive"])),
            _stage("install", "completed", Path(training_run["artifacts"]["installed_agent_manifest"])),
            _stage("hire", "completed", employment_record_path),
            _stage("assign_goal", "completed", goal_path),
            _stage("first_goal_cycle", first_goal_cycle.get("cycle_status", "unknown"), first_goal_cycle_path),
            _stage("learning_update", first_goal_cycle.get("learning_update", {}).get("decision", "unknown"), learning_update_path),
        ],
        "artifacts": artifacts,
        "next_commands": [
            f"ai22b-talent-foundry run-hired-goal-cycle --employment-record \"{employment_record_path}\" --goal \"{goal_path}\" --cycle-note \"다음 주 업무를 진행한다.\" --workspace \"{target_root / 'next_goal_workspace'}\" --score {review_score} --reviewed-by \"{reviewed_by or owner}\"",
            f"ai22b-talent-foundry record-hired-learning --employment-record \"{employment_record_path}\" --run \"{workspace_run_path}\" --score {review_score} --reviewed-by \"{reviewed_by or owner}\"",
        ],
    }
    _write_json(output_path, session)
    return session
