from __future__ import annotations

from datetime import date, datetime
from typing import Any


SAJU_SEED_SCHEMA = "ai-talent-saju-narrative-seed/v1"
HEAVENLY_STEMS = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
EARTHLY_BRANCHES = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _pillar(index: int) -> dict[str, str]:
    stem = HEAVENLY_STEMS[index % 10]
    branch = EARTHLY_BRANCHES[index % 12]
    return {"stem": stem, "branch": branch, "label": f"{stem}{branch}"}


def _year_pillar(day: date) -> dict[str, str]:
    return _pillar((day.year - 4) % 60)


def _day_pillar(day: date) -> dict[str, str]:
    # Narrative approximation only. It must not be used as deterministic fortune telling.
    base = date(2000, 1, 1)
    return _pillar((day - base).days % 60)


def build_saju_narrative_seed(role_model_profile: dict[str, Any]) -> dict[str, Any]:
    identity = role_model_profile.get("public_identity", {})
    birth_date = identity.get("birth_date")
    birth_time = identity.get("birth_time")
    if not birth_date:
        raise ValueError("role model birth_date is required for saju narrative seed")

    parsed = _parse_date(str(birth_date))
    return {
        "schema": SAJU_SEED_SCHEMA,
        "role_model_id": role_model_profile.get("role_model_id"),
        "source_birth": {
            "date": birth_date,
            "time": birth_time,
            "place": identity.get("birth_place"),
        },
        "confidence": {
            "birth_date": "public_source",
            "birth_time": "known" if birth_time else "unknown_birth_time",
            "saju_precision": "low_date_only_symbolic_seed" if birth_time is None else "medium_symbolic_seed",
        },
        "pillars": {
            "year": _year_pillar(parsed),
            "day_approximation": _day_pillar(parsed),
            "hour": None,
        },
        "simulation_use": {
            "purpose": "초기 시뮬레이션 조건을 고르는 보조 seed입니다. 성격, 투자관, 인생관을 미리 주입하지 않습니다.",
            "allowed": [
                "scenario_initial_condition_variety",
                "timeline_and_family_story_prompt",
                "stress_event_distribution_prompt",
                "uncertainty_label_for_unknown_birth_time",
            ],
            "forbidden": [
                "personality_trait_injection",
                "worldview_or_investment_philosophy_injection",
                "deterministic_life_prediction",
                "medical_claim",
                "financial_prediction",
                "claim_that_the_ai_is_the_role_model",
            ],
        },
        "note": (
            "사주는 캐릭터 설정 공백을 채우는 상징적 난수 seed로만 사용합니다. "
            "추론 방식과 인생관은 교육과정, 시험, 실패, 피드백 기록에서 사후 형성되어야 합니다."
        ),
    }
