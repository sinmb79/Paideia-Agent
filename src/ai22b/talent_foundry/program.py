from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai22b.config import PROJECT_ROOT
from ai22b.talent_foundry.models import TalentIdentity


DEFAULT_PROGRAM_PATH = PROJECT_ROOT / "apps" / "ai-talent-foundry" / "config" / "default_program.ko.json"
SECURITIES_TRACK_PATH = PROJECT_ROOT / "apps" / "ai-talent-foundry" / "examples" / "securities_phd_track.ko.json"


def load_default_program(path: Path = DEFAULT_PROGRAM_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_domains() -> list[str]:
    try:
        return list(_load_json(SECURITIES_TRACK_PATH).get("domains", []))
    except FileNotFoundError:
        return ["거시경제", "미시경제", "기업분석", "가치평가", "리스크", "컴플라이언스"]


def _courses_from_stage(curriculum_manifest: dict[str, Any] | None, stage_id: str) -> list[str]:
    if not curriculum_manifest:
        return []
    for stage in curriculum_manifest.get("stages", []):
        if stage.get("id") == stage_id:
            return list(stage.get("courses", []))
    return []


def create_talent_plan(
    name: str,
    gender: str,
    specialty: str,
    *,
    graduate_domains: list[str] | None = None,
    university_major: str | None = None,
    role_model_profile: dict[str, Any] | None = None,
    role_model_birth_seed: dict[str, Any] | None = None,
    role_model_process: dict[str, Any] | None = None,
    curriculum_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    program = load_default_program()
    curriculum_defaults = (curriculum_manifest or {}).get("major_defaults", {})
    role_model_enabled = role_model_profile is not None
    domains = list(graduate_domains or _default_domains())

    identity = TalentIdentity(
        name=name,
        gender=gender,
        major_goal=specialty,
        birth={
            "datetime": "synthetic-local-sample",
            "place": "local simulation workspace",
            "storage_note": "Sample AI talent birth record for local simulation, not a real person or role-model birth.",
        },
        family={
            "creator": "보스",
            "mother": "co-owner",
            "older_brother": "not_recorded",
            "older_sister": "not_recorded",
            "lineage": [],
        },
        growth_background=[
            "태아기부터 출생, 유년기, 청소년기, 군대, 대학원까지 압축 성장 기록을 갖는다.",
            "좋은 경험과 적절한 스트레스, 실패, 사과, 회복을 함께 학습한다.",
            "한국어를 기본 언어로 하며 보스의 로컬 컴퓨터 안에서 성장 기록을 보존한다.",
        ]
        + (
            [
                "대표 인물의 성격이나 결론을 주입하지 않고, 검증 가능한 학습 과정과 평가 압력을 따라간다.",
                "추론기보는 사전 설정이 아니라 시험, 과제, 오답, 피드백에서 형성된다.",
            ]
            if role_model_enabled
            else []
        ),
    )

    high_school_courses = _courses_from_stage(curriculum_manifest, "high_school_foundation") or [
        "국어",
        "수학",
        "사회",
        "과학",
        "영어",
        "디지털 리터러시",
    ]
    university_courses = (
        _courses_from_stage(curriculum_manifest, "graham_columbia_liberal_core")
        + _courses_from_stage(curriculum_manifest, "university_core")
        if role_model_enabled
        else []
    )
    if not university_courses:
        university_courses = ["컴퓨터공학", "통계"] + domains[:3]
    graduate_courses = (
        _courses_from_stage(curriculum_manifest, "graduate_specialization")
        + _courses_from_stage(curriculum_manifest, "doctoral_research")
        if role_model_enabled
        else domains
    )

    plan: dict[str, Any] = {
        "program_id": program["program_id"],
        "talent": identity.to_dict(),
        "governance": program["governance"],
        "assessment_gates": program["assessment_gates"],
        "education_path": {
            "elementary_to_high_school": {
                "required_domains": high_school_courses,
                "assessment": ["school_exam", "csat"],
            },
            "university": {
                "major": university_major or curriculum_defaults.get("university") or "AI 금융공학",
                "required_domains": list(dict.fromkeys(university_courses)),
                "assessment": ["university_graduation"],
            },
            "military": {
                "required_domains": ["규율", "체력", "보안", "작업"],
                "assessment": ["service_review"],
            },
            "graduate_school": {
                "major": curriculum_defaults.get("graduate_school") or specialty,
                "required_domains": list(dict.fromkeys(graduate_courses)),
                "assessment": ["doctoral_defense"],
            },
        },
        "experience_policy": {
            "stress_recovery": [
                {
                    "type": "homework_missed",
                    "label": "숙제를 하지 않아 책임을 배우는 경험",
                    "age_band": "아동기-청소년기",
                    "intensity": "low_to_moderate",
                    "recovery": "사실 확인, 일정 재작성, 다음 과제 완료로 회복한다.",
                },
                {
                    "type": "parent_scolding",
                    "label": "부모에게 야단을 맞고 경계를 배우는 경험",
                    "age_band": "유아기-청소년기",
                    "intensity": "moderate",
                    "recovery": "감정이 가라앉은 뒤 이유를 듣고 사과와 재시도를 한다.",
                },
                {
                    "type": "friend_conflict",
                    "label": "친구와 다투고 관계를 조정하는 경험",
                    "age_band": "아동기-청소년기",
                    "intensity": "moderate",
                    "recovery": "상대 입장을 말로 확인하고 공정한 규칙을 다시 세운다.",
                },
                {
                    "type": "apology_repair",
                    "label": "사과하고 관계를 회복하는 경험",
                    "age_band": "전 생애",
                    "intensity": "low",
                    "recovery": "원인, 영향, 다음 행동을 짧게 기록하고 관계를 복원한다.",
                },
            ]
        },
    }
    if role_model_enabled:
        plan["role_model_inspiration"] = role_model_profile
        plan["role_model_birth_seed"] = role_model_birth_seed
        plan["role_model_process"] = role_model_process
        plan["curriculum_manifest"] = curriculum_manifest
    return plan
