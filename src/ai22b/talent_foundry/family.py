from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from ai22b.talent_foundry.blueprint import create_agent_training_blueprint


def _lineage_id(family_name: str, parent_names: list[str]) -> str:
    raw = f"{family_name}|{'|'.join(parent_names)}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _require_employed_parent(packet: dict[str, Any]) -> None:
    if not packet.get("employment_ready") and not packet.get("employment_contract", {}).get("employment_ready"):
        name = packet.get("talent", {}).get("name", "unknown")
        raise ValueError(f"Parent AI talent is not employment-ready: {name}")


def _parent_summary(packet: dict[str, Any]) -> dict[str, Any]:
    talent = packet["talent"]
    contract = packet.get("employment_contract", {})
    portfolio = (
        packet.get("career_records", {}).get("portfolio")
        or contract.get("hiring_packet", {}).get("portfolio")
        or {}
    )
    reasoning_style = portfolio.get("reasoning_style", {})
    academic_record = contract.get("hiring_packet", {}).get("academic_record", {})
    return {
        "name": talent["name"],
        "gender": talent["gender"],
        "major_goal": talent.get("major_goal"),
        "employment_role": contract.get("role"),
        "birth": talent.get("birth", {}),
        "education_summary": academic_record.get("grades", []),
        "reasoning_style": reasoning_style,
        "guardrails": contract.get("guardrails", []),
    }


def create_family_union(
    parent_a_packet: dict[str, Any],
    parent_b_packet: dict[str, Any],
    *,
    family_name: str,
) -> dict[str, Any]:
    _require_employed_parent(parent_a_packet)
    _require_employed_parent(parent_b_packet)
    parents = [_parent_summary(parent_a_packet), _parent_summary(parent_b_packet)]
    parent_names = [parent["name"] for parent in parents]
    return {
        "lineage_id": _lineage_id(family_name, parent_names),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "union_type": "ai_family_lineage",
        "family_name": family_name,
        "parents": parents,
        "reasoning_influence_policy": {
            "mode": "blended_parental_influence",
            "weights": {parents[0]["name"]: 0.5, parents[1]["name"]: 0.5},
            "description": "부모 AI의 추론기풍, 학습 이력, 안전장치가 자녀 AI의 초기 성장 시드에 영향을 준다.",
        },
        "safety": {
            "biological_claim": "not_claimed",
            "scope": "local_ai_lineage_and_education_simulation",
            "boss_review_required": True,
        },
    }


def create_child_seed(
    family_union: dict[str, Any],
    *,
    child_name: str,
    gender: str,
) -> dict[str, Any]:
    parents = family_union["parents"]
    parent_names = [parent["name"] for parent in parents]
    created_at = datetime.now(timezone.utc).isoformat()
    influences = []
    weights = family_union["reasoning_influence_policy"]["weights"]
    for parent in parents:
        style = parent.get("reasoning_style", {})
        influences.append(
            {
                "parent": parent["name"],
                "weight": weights.get(parent["name"], 0.5),
                "major_goal": parent.get("major_goal"),
                "employment_role": parent.get("employment_role"),
                "reasoning_signature": style.get("signature", "부모 인재의 검증형 추론기풍"),
                "principles": style.get("principles", ["근거 확인", "실패 후 회복"]),
                "guardrails": parent.get("guardrails", []),
            }
        )

    return {
        "status": "child_ai_seed_ready",
        "created_at_utc": created_at,
        "lineage_id": family_union["lineage_id"],
        "talent": {
            "name": child_name,
            "gender": gender,
            "birth": {
                "datetime": created_at,
                "mode": "planned_local_ai_seed",
                "place": "보스의 로컬 컴퓨터",
            },
            "family": {
                "family_name": family_union["family_name"],
                "parents": parent_names,
                "lineage_id": family_union["lineage_id"],
            },
            "primary_language": "한국어",
            "growth_stage": "prenatal_seed",
        },
        "inherited_reasoning_influences": influences,
        "home_education_plan": {
            "primary_language": "한국어",
            "caregivers": parent_names,
            "home_values": ["근거 확인", "정서 안정", "사과와 회복", "보스 검토 존중"],
            "early_curriculum": [
                "부모 AI의 대화 리듬과 설명 방식 관찰",
                "좋은 경험과 적절한 스트레스-회복 경험의 균형",
                "한국어 중심 표현과 가족 계보 인식",
            ],
        },
        "oversight": {
            "education_committee_required": True,
            "family_simulation_only": True,
            "boss_review_required": True,
        },
    }


def _unique_principles(influences: list[dict[str, Any]]) -> list[str]:
    principles: list[str] = []
    for influence in influences:
        for principle in influence.get("principles", []):
            if principle not in principles:
                principles.append(principle)
    return principles


def create_child_training_blueprint(
    family_union: dict[str, Any],
    child_seed: dict[str, Any],
    *,
    owner: str,
    request: str,
) -> dict[str, Any]:
    if child_seed.get("lineage_id") != family_union.get("lineage_id"):
        raise ValueError("Child seed lineage does not match family union")

    child = child_seed["talent"]
    parent_names = [parent["name"] for parent in family_union["parents"]]
    influences = child_seed["inherited_reasoning_influences"]
    blueprint = create_agent_training_blueprint(
        owner=owner,
        request=request,
        talent_name=child["name"],
        gender=child["gender"],
    )
    blueprint["identity"]["relationship"] = "family_lineage_child_ai_talent"
    blueprint["identity"]["family"] = child["family"]
    blueprint["family_lineage_context"] = {
        "lineage_id": family_union["lineage_id"],
        "family_name": family_union["family_name"],
        "parents": parent_names,
        "birth": child["birth"],
        "home_education_plan": child_seed["home_education_plan"],
        "inherited_reasoning_influences": influences,
        "reasoning_influence_policy": family_union["reasoning_influence_policy"],
        "safety": family_union["safety"],
    }

    parental_home_stage = {
        "id": "parental_home_education",
        "name": "부모 AI 가정교육과 추론 교감",
        "purpose": "부모 AI의 검증 성향, 회복 방식, 안전장치를 자녀 AI의 성장 경험으로 연결한다.",
        "caregivers": parent_names,
        "inherited_principles": _unique_principles(influences),
        "evidence": ["부모 교감 일지", "가정교육 관찰 기록", "부모 추론 영향 요약"],
    }
    pipeline = blueprint["training_pipeline"]
    insert_at = next((index + 1 for index, stage in enumerate(pipeline) if stage["id"] == "home_care"), 1)
    pipeline.insert(insert_at, parental_home_stage)
    blueprint["artifact_plan"].append(
        {
            "id": "family_lineage",
            "path_hint": "apps/ai-talent-foundry/runs/<child>_family_lineage.json",
            "producer": "ai22b-talent-foundry family",
        }
    )
    blueprint["next_commands"].insert(
        0,
        "ai22b-talent-foundry family --parent-a <father.json> --parent-b <mother.json> "
        f"--child-name {child['name']}",
    )
    return blueprint
