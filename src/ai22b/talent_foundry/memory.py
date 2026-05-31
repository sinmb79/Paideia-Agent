from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CHAIN_OF_THOUGHT_POLICY = "store_summaries_not_private_traces"


def create_memory_store(*, owner: str) -> dict[str, Any]:
    return {
        "owner": owner,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "chain_of_thought": CHAIN_OF_THOUGHT_POLICY,
            "storage": "local_json_only",
        },
        "memory": {
            "episodic": [],
            "semantic": [],
            "procedural": [],
            "risk_notes": [],
        },
    }


def _event_id(owner: str, source: str, event: dict[str, Any]) -> str:
    raw = json.dumps({"owner": owner, "source": source, "event": event}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _summarize_event(source: str, event: dict[str, Any]) -> str:
    if source == "assessment":
        return f"평가 {event.get('gate_id')}에서 {event.get('score')}점을 받고 {event.get('feedback', '')}"
    if source == "work":
        growth = event.get("growth_update", event)
        return f"업무 후 성장 경험: {growth.get('reflection', growth.get('experience_type', 'work_after_hire'))}"
    if source == "team":
        growth = event.get("parent_growth_update", event)
        return f"본체 제어 분신 팀 경험: {growth.get('reflection', growth.get('experience_type', 'clone_team_after_hire'))}"
    if source == "family":
        child = event.get("child_seed", {}).get("talent", {}).get("name", "자녀 AI")
        return f"가족 계보와 {child} 성장 시드를 생성했다."
    if source == "institutional_review":
        education = event.get("education_committee_decision", {}).get("status", "unknown")
        oversight = event.get("oversight_committee_decision", {}).get("status", "unknown")
        graduation_ready = event.get("assessment_transcript", {}).get("graduation_ready")
        return (
            "교육위원회, 위탁가정, 감독위원회 기관 심사를 거쳐 "
            f"교육 상태 {education}, 감독 상태 {oversight}, 졸업 준비 {graduation_ready}를 기록했다."
        )
    return str(event)[:240]


def remember_event(store: dict[str, Any], *, source: str, event: dict[str, Any]) -> dict[str, Any]:
    owner = store["owner"]
    entry = {
        "id": _event_id(owner, source, event),
        "source": source,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": _summarize_event(source, event),
        "safe_reference": {
            key: value
            for key, value in event.items()
            if key not in {"chain_of_thought", "private_reasoning_trace"}
        },
    }
    store["memory"]["episodic"].append(entry)
    return store


def save_memory_store(store: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def load_memory_store(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def consolidate_memory(store: dict[str, Any]) -> dict[str, Any]:
    summaries = [entry["summary"] for entry in store["memory"]["episodic"]]
    joined = "\n".join(summaries)

    semantic_themes: list[str] = []
    if _contains_any(joined, ["거시경제", "금리", "환율"]):
        semantic_themes.append("거시경제")
    if _contains_any(joined, ["doctoral_defense", "박사", "논문", "평가"]):
        semantic_themes.append("평가와 학위 심사")
    if _contains_any(joined, ["가족", "자녀", "가정"]):
        semantic_themes.append("가족 계보와 가정교육")
    if _contains_any(joined, ["분신", "팀"]):
        semantic_themes.append("본체 제어 분신 팀")
    if _contains_any(joined, ["교육위원회", "감독위원회", "기관 심사"]):
        semantic_themes.append("기관 심사와 고용 감독")

    procedural_principles: list[str] = []
    if _contains_any(joined, ["검증", "근거", "평가"]):
        procedural_principles.append("검증")
        procedural_principles.append("근거 우선")
    if _contains_any(joined, ["투자 실행은 차단", "blocked", "안전"]):
        procedural_principles.append("권한 경계 우선")
    if _contains_any(joined, ["회복", "성장"]):
        procedural_principles.append("실패와 피드백을 성장 기록으로 전환")
    if _contains_any(joined, ["거시경제"]):
        procedural_principles.append("거시경제 질문을 먼저 세우기")
    if _contains_any(joined, ["major_track_passed", "employment_ready_with_guardrails", "기관 심사"]):
        procedural_principles.append("위원회 검증 통과 후 고용")

    if not semantic_themes:
        semantic_themes.append("일반 성장 경험")
    if not procedural_principles:
        procedural_principles.append("기록 후 검토")

    profile = {
        "owner": store["owner"],
        "source_event_count": len(store["memory"]["episodic"]),
        "semantic_themes": semantic_themes,
        "procedural_principles": list(dict.fromkeys(procedural_principles)),
        "episodic_summaries": summaries,
        "risk_notes": [
            "요약과 근거만 저장하고 비공개 사고원문은 저장하지 않는다.",
            "성장 반영은 보스 검토가 필요한 항목과 자동 반영 항목을 구분한다.",
        ],
        "chain_of_thought_policy": store["policy"]["chain_of_thought"],
    }
    store["memory"]["semantic"] = semantic_themes
    store["memory"]["procedural"] = profile["procedural_principles"]
    store["memory"]["risk_notes"] = profile["risk_notes"]
    return profile
