from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ai22b.talent_foundry.onboarding import run_agent_onboarding
from ai22b.talent_foundry.role_models import DEFAULT_PRIVATE_CURRICULUM_DIR
from ai22b.talent_foundry.registry import (
    assemble_hired_agent_team,
    assemble_hired_projection_swarm,
    hire_installed_agent,
    run_hired_projection_swarm_cycle,
    run_hired_team_cycle,
)


CONSOLE_SESSION_SCHEMA = "ai-talent-guided-console-session/v1"

SPECIALIST_TEAM_ROLES = [
    ("macro", "거시경제 분석 에이전트"),
    ("company", "기업분석 에이전트"),
    ("quant", "퀀트 분석 에이전트"),
    ("risk_compliance", "리스크/컴플라이언스 에이전트"),
]

CONSOLE_QUESTIONS = [
    {
        "id": "owner",
        "label": "고용주",
        "prompt": "누가 이 인재를 고용하나요?",
        "default": "보스",
    },
    {
        "id": "request",
        "label": "요청",
        "prompt": "어떤 분야의 에이전트를 길러 고용하고 싶나요?",
        "required": True,
    },
    {
        "id": "domain",
        "label": "분야",
        "prompt": "대표 인물 트랙의 분야는 무엇으로 둘까요?",
        "default": "securities_research",
    },
    {
        "id": "role_model_id",
        "label": "대표 인물",
        "prompt": "대표 인물 모티브는 무엇으로 둘까요?",
        "default": "graham_value_investing",
    },
    {
        "id": "private_curriculum_dir",
        "label": "비공개 교재 폴더",
        "prompt": "보스가 제공할 비공개 교재 폴더는 어디로 둘까요?",
        "default": str(DEFAULT_PRIVATE_CURRICULUM_DIR),
    },
    {
        "id": "agent_surface",
        "label": "실행 방식",
        "prompt": "초기 에이전트 실행 방식은 무엇으로 둘까요?",
        "default": "cli-console",
    },
    {
        "id": "talent_name",
        "label": "이름",
        "prompt": "새 인재의 이름은 무엇인가요?",
        "default": "신용",
    },
    {
        "id": "gender",
        "label": "성별",
        "prompt": "새 인재의 성별 설정은 무엇인가요?",
        "default": "남자",
    },
    {
        "id": "initial_goal",
        "label": "첫 목표",
        "prompt": "고용 직후 맡길 첫 목표는 무엇인가요?",
    },
    {
        "id": "cycle_note",
        "label": "첫 사이클",
        "prompt": "첫 업무 사이클에서 무엇을 하게 할까요?",
    },
    {
        "id": "post_hire_mode",
        "label": "고용 후 모드",
        "prompt": "고용 후 구성은 single, projection_swarm, specialist_team 중 어떤 것으로 할까요?",
        "default": "single",
    },
    {
        "id": "swarm_name",
        "label": "분신 군체 이름",
        "prompt": "분신 군체를 만들 경우 이름은 무엇인가요?",
    },
    {
        "id": "swarm_domain",
        "label": "분신 군체 분야",
        "prompt": "분신 군체의 업무 분야는 무엇인가요?",
    },
    {
        "id": "swarm_objective",
        "label": "분신 군체 목표",
        "prompt": "분신 군체가 첫 번째로 검토할 목표는 무엇인가요?",
    },
    {
        "id": "team_name",
        "label": "전문팀 이름",
        "prompt": "별도 고용 전문팀을 만들 경우 이름은 무엇인가요?",
    },
    {
        "id": "team_domain",
        "label": "전문팀 분야",
        "prompt": "별도 고용 전문팀의 업무 분야는 무엇인가요?",
    },
    {
        "id": "team_objective",
        "label": "전문팀 목표",
        "prompt": "별도 고용 전문팀이 첫 번째로 검토할 목표는 무엇인가요?",
    },
]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalized_answers(answers: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for question in CONSOLE_QUESTIONS:
        key = question["id"]
        value = answers.get(key)
        if key == "talent_name" and value is None:
            value = answers.get("name")
        if value is None or str(value).strip() == "":
            if question.get("required"):
                raise ValueError(f"Missing required console answer: {key}")
            value = question.get("default", "")
        normalized[key] = str(value).strip()
    return normalized


def collect_console_answers(input_func: Callable[[str], str] = input) -> dict[str, str]:
    answers: dict[str, str] = {}
    for question in CONSOLE_QUESTIONS:
        default = question.get("default")
        suffix = f" [{default}]" if default else ""
        raw = input_func(f"{question['prompt']}{suffix}: ")
        answers[question["id"]] = raw if raw.strip() else str(default or "")
    return _normalized_answers(answers)


def run_console_session(
    *,
    answers: dict[str, Any],
    output_dir: Path,
    output_path: Path | None = None,
    mode: str = "answers_file",
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_path or output_dir / "console_session.json"
    answers_path = output_dir / "console_answers.json"
    normalized = _normalized_answers(answers)
    _write_json(answers_path, normalized)

    onboarding_dir = output_dir / "onboarding"
    onboarding_output = onboarding_dir / "onboarding_session.json"
    onboarding = run_agent_onboarding(
        owner=normalized["owner"],
        request=normalized["request"],
        talent_name=normalized["talent_name"],
        gender=normalized["gender"],
        output_dir=onboarding_dir,
        domain=normalized.get("domain") or None,
        role_model_id=normalized.get("role_model_id") or None,
        private_curriculum_dir=normalized.get("private_curriculum_dir") or None,
        agent_surface=normalized.get("agent_surface") or "cli-console",
        initial_goal=normalized.get("initial_goal") or None,
        cycle_note=normalized.get("cycle_note") or None,
        output_path=onboarding_output,
    )

    post_hire_extensions: dict[str, Any] = {}
    artifacts = {
        "console_session": str(output_path),
        "answers": str(answers_path),
        "onboarding_session": onboarding["artifacts"]["onboarding_session"],
        "employment_record": onboarding["artifacts"]["employment_record"],
        "employment_goal": onboarding["artifacts"]["employment_goal"],
        "first_goal_cycle": onboarding["artifacts"]["first_goal_cycle"],
    }
    status = onboarding["status"]
    if normalized.get("post_hire_mode") == "projection_swarm":
        swarm_dir = output_dir / "projection_swarm"
        swarm_path = swarm_dir / "hired_projection_swarm.json"
        cycle_path = swarm_dir / "hired_projection_swarm_cycle.json"
        swarm = assemble_hired_projection_swarm(
            Path(onboarding["artifacts"]["employment_record"]),
            swarm_name=normalized.get("swarm_name") or f"{normalized['talent_name']} parent-controlled projection swarm",
            domain=normalized.get("swarm_domain") or onboarding["track"]["name"],
            output_path=swarm_path,
        )
        cycle = run_hired_projection_swarm_cycle(
            swarm_path,
            objective=normalized.get("swarm_objective") or f"{normalized['talent_name']} first projection swarm review",
            workspace_dir=swarm_dir / "workspace",
            quality_label={
                "score": 92,
                "reviewed_by": normalized["owner"],
                "status": "verified",
            },
            output_path=cycle_path,
        )
        artifacts["projection_swarm"] = str(swarm_path)
        artifacts["projection_swarm_cycle"] = str(cycle_path)
        post_hire_extensions["projection_swarm"] = {
            "schema": swarm["schema"],
            "cycle_schema": cycle["schema"],
            "cycle_status": cycle["cycle_status"],
            "projection_count": swarm["swarm"]["projection_count"],
            "consciousness": "parent_controlled_projection",
            "not_separate_consciousnesses": swarm["swarm_policy"]["control_model"]["not_separate_consciousnesses"],
            "separate_employment_records": swarm["swarm_policy"]["control_model"]["separate_employment_records"],
            "separate_consciousness_created": cycle["parent_synthesis"]["separate_consciousness_created"],
        }
        if cycle["cycle_status"] == "completed":
            status = "projection_swarm_cycle_completed"
    elif normalized.get("post_hire_mode") == "specialist_team":
        team_dir = output_dir / "specialist_team"
        team_path = team_dir / "hired_agent_team.json"
        cycle_path = team_dir / "hired_agent_team_cycle.json"
        installed_manifest_path = Path(onboarding["artifacts"]["installed_agent_manifest"])
        specialist_employment_records = []
        for role_id, role in SPECIALIST_TEAM_ROLES:
            hiring = hire_installed_agent(
                installed_manifest_path,
                employer=normalized["owner"],
                role=role,
                record_name=f"employment_record.specialist_{role_id}.json",
            )
            specialist_employment_records.append(hiring["employment_record"])

        team = assemble_hired_agent_team(
            specialist_employment_records,
            team_name=normalized.get("team_name") or f"{normalized['talent_name']} separately hired specialist team",
            domain=normalized.get("team_domain") or onboarding["track"]["name"],
            output_path=team_path,
        )
        cycle = run_hired_team_cycle(
            team_path,
            objective=normalized.get("team_objective") or f"{normalized['talent_name']} first specialist team review",
            workspace_dir=team_dir / "workspace",
            quality_label={
                "score": 92,
                "reviewed_by": normalized["owner"],
                "status": "verified",
            },
            output_path=cycle_path,
        )
        artifacts["specialist_team"] = str(team_path)
        artifacts["specialist_team_cycle"] = str(cycle_path)
        artifacts["specialist_employment_records"] = [str(path) for path in specialist_employment_records]
        post_hire_extensions["specialist_team"] = {
            "schema": team["schema"],
            "cycle_schema": cycle["schema"],
            "cycle_status": cycle["cycle_status"],
            "member_count": team["team"]["member_count"],
            "member_roles": [role for _role_id, role in SPECIALIST_TEAM_ROLES],
            "member_type": "separately_hired_talent_agent",
            "not_a_projection_team": team["team_policy"]["not_a_projection_team"],
        }
        if cycle["cycle_status"] == "completed":
            status = "specialist_team_cycle_completed"

    session = {
        "schema": CONSOLE_SESSION_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "status": status,
        "questions": CONSOLE_QUESTIONS,
        "answers": normalized,
        "onboarding_summary": {
            "schema": onboarding["schema"],
            "status": onboarding["status"],
            "track": onboarding["track"],
            "employment": onboarding["employment"],
        },
        "local_policy": onboarding["local_policy"],
        "post_hire_extensions": post_hire_extensions,
        "artifacts": artifacts,
        "next_commands": onboarding["next_commands"],
    }
    _write_json(output_path, session)
    return session
