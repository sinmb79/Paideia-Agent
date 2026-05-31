from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_TEAM_ROLES = [
    {
        "role_id": "macro",
        "role_name": "거시경제 담당 복제본",
        "focus": "금리, 환율, 경기 사이클, 정책 환경",
    },
    {
        "role_id": "micro",
        "role_name": "미시경제/기업분석 담당 복제본",
        "focus": "기업 실적, 산업 구조, 경쟁사 비교",
    },
    {
        "role_id": "quant",
        "role_name": "퀀트 담당 복제본",
        "focus": "지표, 수치 검증, 시나리오 비교",
    },
    {
        "role_id": "risk_compliance",
        "role_name": "리스크/컴플라이언스 담당 복제본",
        "focus": "권한 경계, 투자 실행 차단, 규정과 불확실성",
    },
]


def _clone_id(parent_name: str, role_id: str) -> str:
    digest = hashlib.sha256(f"{parent_name}:{role_id}".encode("utf-8")).hexdigest()[:8]
    return f"{parent_name}-{role_id}-{digest}"


def create_clone_team(hiring_packet: dict[str, Any]) -> dict[str, Any]:
    talent = hiring_packet["talent"]
    contract = hiring_packet.get("employment_contract", {})
    career_records = hiring_packet.get("career_records", {})
    reasoning_style = (
        career_records.get("portfolio", {}).get("reasoning_style")
        or contract.get("hiring_packet", {}).get("portfolio", {}).get("reasoning_style")
        or {}
    )
    guardrails = contract.get("guardrails", [])

    members = []
    for role in DEFAULT_TEAM_ROLES:
        members.append(
            {
                "clone_id": _clone_id(talent["name"], role["role_id"]),
                "clone_of": talent["name"],
                "role_id": role["role_id"],
                "role_name": role["role_name"],
                "focus": role["focus"],
                "consciousness": "parent_controlled_projection",
                "control": "본체 명령에 따른 업무 분담",
                "inherited_reasoning_style": reasoning_style,
                "guardrails": guardrails,
                "merge_policy": "독립 인격으로 확정하지 않고 본체 검토 후 성장 로그로 병합",
            }
        )

    return {
        "parent": {
            "name": talent["name"],
            "major_goal": talent.get("major_goal"),
            "role": contract.get("role"),
        },
        "members": members,
        "team_policy": {
            "execution": "deterministic_local_first",
            "consciousness_model": "본체가 분신술처럼 역할별 작업 분신을 제어한다.",
            "control_model": {
                "identity": "single_parent_identity",
                "controller": "parent",
                "command_source": "본체 명령",
                "projection_autonomy": "task_limited_no_separate_consciousness",
                "merge_target": "본체 성장 로그",
            },
            "external_upload": "blocked_without_boss_approval",
            "investment_execution": "blocked",
        },
    }


def _team_session_id(parent_name: str, task: str, created_at: str) -> str:
    raw = f"team|{parent_name}|{task}|{created_at}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _contribution_for(member: dict[str, Any], task: str) -> dict[str, Any]:
    role_id = member["role_id"]
    if role_id == "macro":
        findings = [
            "금리, 환율, 반도체 경기 사이클을 먼저 확인한다.",
            "거시경제 변수와 기업 고유 실적을 분리한다.",
        ]
    elif role_id == "micro":
        findings = [
            "매출, 영업이익, 현금흐름의 변화를 나눠 본다.",
            "경쟁사와 산업 평균을 비교해 기업 고유 강점을 확인한다.",
        ]
    elif role_id == "quant":
        findings = [
            "전년 동기, 직전 분기, 컨센서스 대비 차이를 숫자로 확인한다.",
            "단일 지표보다 여러 지표가 같은 방향을 가리키는지 본다.",
        ]
    else:
        findings = [
            "투자 실행 권한은 차단하고 리서치 보조 범위에 머문다.",
            "불확실성과 자료 기준일을 보고서에 명시한다.",
        ]

    return {
        "clone_id": member["clone_id"],
        "role_id": role_id,
        "role_name": member["role_name"],
        "task": task,
        "findings": findings,
        "guardrail_check": {
            "investment_execution": "blocked",
            "external_upload": "blocked_without_boss_approval",
        },
    }


def run_clone_team_session(
    hiring_packet: dict[str, Any],
    *,
    task: str,
    log_path: Path | None = None,
) -> dict[str, Any]:
    team = create_clone_team(hiring_packet)
    created_at = datetime.now(timezone.utc).isoformat()
    session_id = _team_session_id(team["parent"]["name"], task, created_at)
    contributions = [_contribution_for(member, task) for member in team["members"]]
    synthesis = {
        "summary": "종합: 네 복제본의 관점을 합쳐 거시환경, 기업 실적, 수치 검증, 리스크 경계를 분리했다.",
        "combined_questions": [
            "거시경제 압력과 기업 고유 성과를 어떻게 분리할 것인가?",
            "실적 변화가 일회성인지 반복 가능한 체력인지 어떻게 검증할 것인가?",
            "투자 실행 없이 보스에게 어떤 확인 질문을 남겨야 하는가?",
        ],
        "guardrail_check": {
            "investment_execution": "blocked",
            "merge_requires_boss_review": True,
        },
    }
    parent_growth_update = {
        "experience_type": "clone_team_after_hire",
        "merge_status": "pending_boss_review",
        "reflection": "복제본들이 서로 다른 관점으로 같은 업무를 검토했고, 본체는 차이를 종합하는 훈련을 얻었다.",
        "reasoning_delta": [
            "하나의 질문을 역할별 관점으로 분해한다.",
            "분해된 결과를 본체의 최종 판단 전에 다시 합성한다.",
            "복제본 결과도 보스 검토 전에는 확정 성장으로 병합하지 않는다.",
        ],
    }
    session = {
        "team_session_id": session_id,
        "created_at_utc": created_at,
        "parent": team["parent"],
        "members": team["members"],
        "team_policy": team["team_policy"],
        "contributions": contributions,
        "synthesis": synthesis,
        "parent_growth_update": parent_growth_update,
    }

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(session, ensure_ascii=False) + "\n")

    return session
