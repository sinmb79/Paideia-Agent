from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GROWTH_PROFILE_SCHEMA = "ai22b-paideia-growth-profile/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _top(counter: Counter[str], *, limit: int = 8) -> list[dict[str, Any]]:
    return [{"id": key, "count": count} for key, count in counter.most_common(limit)]


def _event_counts(events: list[dict[str, Any]]) -> dict[str, Any]:
    domains = Counter(str(event.get("domain") or "unknown") for event in events)
    stages = Counter(str(event.get("stage_id") or "unknown") for event in events)
    stress = Counter(str(event.get("stress_level", "unknown")) for event in events)
    return {
        "event_count": len(events),
        "domain_distribution": _top(domains),
        "stage_distribution": _top(stages, limit=12),
        "stress_distribution": _top(stress, limit=8),
    }


def _event_refs(events: list[dict[str, Any]], *, domain: str | None = None, min_stress: int | None = None) -> list[str]:
    refs: list[str] = []
    for event in events:
        if domain is not None and event.get("domain") != domain:
            continue
        if min_stress is not None and int(event.get("stress_level") or 0) < min_stress:
            continue
        event_id = event.get("event_id")
        if event_id:
            refs.append(str(event_id))
        if len(refs) >= 12:
            break
    return refs


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_growth_profile(
    blueprint: dict[str, Any],
    developmental_ecology: dict[str, Any],
    life_trace: dict[str, Any],
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Build a reviewable growth profile from ecology and life-trace records.

    This is a memory-pack scaffold, not a personality injection. It summarizes
    relationship, emotion, culture, aesthetic, and asymmetry signals that were
    already produced by the growth simulation.
    """

    if blueprint.get("schema") != "ai-talent-training-blueprint/v1":
        raise ValueError("Unsupported training blueprint schema")
    if developmental_ecology.get("schema") != "ai22b-paideia-developmental-ecology/v1":
        raise ValueError("Unsupported developmental ecology schema")

    events = _as_list(life_trace.get("events"))
    identity = _safe_dict(blueprint.get("identity"))
    track = _safe_dict(blueprint.get("track"))
    role_model = _safe_dict(blueprint.get("role_model"))
    family = _safe_dict(developmental_ecology.get("family_climate"))
    peer = _safe_dict(developmental_ecology.get("peer_world"))
    meaning = _safe_dict(developmental_ecology.get("meaning_system"))
    aesthetic = _safe_dict(developmental_ecology.get("aesthetic_profile"))
    emotional = _safe_dict(developmental_ecology.get("emotional_development"))
    asymmetry = _safe_dict(developmental_ecology.get("asymmetry_budget"))
    counts = _event_counts(events)

    growth_profile = {
        "schema": GROWTH_PROFILE_SCHEMA,
        "created_at_utc": _now(),
        "talent": {
            "name": identity.get("name"),
            "gender": identity.get("gender"),
            "primary_language": identity.get("language", "ko"),
            "target_role": track.get("target_role"),
            "track_id": track.get("track_id"),
        },
        "source_context": {
            "blueprint_schema": blueprint.get("schema"),
            "developmental_ecology_schema": developmental_ecology.get("schema"),
            "life_trace_schema": life_trace.get("manifest", {}).get("schema"),
            "life_trace_density": life_trace.get("manifest", {}).get("density"),
            "role_model_id": role_model.get("role_model_id"),
            "role_model_use": "learning_process_reference_only",
            "event_counts": counts,
        },
        "relationship_memory": {
            "family_pattern": {
                "warmth": family.get("warmth"),
                "structure": family.get("structure"),
                "caregiver_patterns": _as_list(family.get("caregiver_patterns")),
                "privacy": "caregiver details are synthetic or redacted; no private family biography is exported",
            },
            "peer_pattern": {
                "belonging_style": peer.get("belonging_style"),
                "friendship_patterns": _as_list(peer.get("friendship_patterns")),
                "conflict_patterns": _as_list(peer.get("conflict_patterns")),
            },
            "conflict_repair_rules": _as_list(family.get("conflict_repair"))
            + ["summarize the other side before rebuttal", "use repair action before self-justification"],
            "mentor_map": _as_list(peer.get("mentor_access")),
            "evidence_event_ids": _event_refs(events, domain="peer_world"),
        },
        "emotional_memory": {
            "baseline_stress": emotional.get("baseline_stress"),
            "stress_distribution": counts["stress_distribution"],
            "recovery_methods": _as_list(emotional.get("recovery_methods")),
            "anger_repair": emotional.get("anger_repair"),
            "shame_repair": emotional.get("shame_repair"),
            "loneliness_repair": emotional.get("loneliness_repair"),
            "high_stress_event_ids": _event_refs(events, min_stress=4),
            "regulation_rules": [
                "record stress with support and recovery, not as identity",
                "separate bad outcome from self-worth",
                "convert failure into a retestable next action",
            ],
        },
        "meaning_memory": {
            "cultural_exposures": _as_list(meaning.get("cultural_exposures")),
            "meaning_mode": meaning.get("religion_or_meaning_mode"),
            "forbidden_uses": _as_list(meaning.get("forbidden_uses")),
            "value_questions": [
                "What evidence would change this view?",
                "Who is affected by this decision?",
                "Which local context might change the right action?",
            ],
        },
        "aesthetic_memory": {
            "music": aesthetic.get("music"),
            "visual_art": aesthetic.get("visual_art"),
            "literature": aesthetic.get("literature"),
            "hobbies": _as_list(aesthetic.get("hobbies")),
            "sensory_anchors": _as_list(
                _safe_dict(developmental_ecology.get("residential_environment")).get("sensory_cues")
            ),
            "purpose": "ordinary conversation, metaphor control, tone, and empathy anchors",
        },
        "asymmetry_profile": {
            "strength_biases": _as_list(asymmetry.get("strength_biases")),
            "growth_costs": _as_list(asymmetry.get("growth_costs")),
            "domain_obsession": asymmetry.get("domain_obsession"),
            "guardrails": _as_list(asymmetry.get("guardrails")),
            "observed_event_bias": counts["domain_distribution"],
            "not_fixed_personality": True,
        },
        "memory_pack_preview": {
            "episodic_memory_events": len(events),
            "semantic_memory_topics": len(counts["domain_distribution"]),
            "procedural_memory_rules": 3
            + len(_as_list(family.get("conflict_repair")))
            + len(_as_list(emotional.get("recovery_methods"))),
            "relationship_memory_refs": len(_event_refs(events, domain="peer_world")),
            "emotional_memory_refs": len(_event_refs(events, min_stress=4)),
        },
        "policy": {
            "private_reasoning_trace": "not_stored",
            "hidden_chain_of_thought": "forbidden",
            "personality_injection": "forbidden",
            "saju_determinism": "forbidden",
            "public_figure_impersonation": "forbidden",
            "synthetic_growth_records_only": True,
        },
        "review_status": "growth_profile_ready",
    }
    if output_path is not None:
        write_growth_profile(output_path, growth_profile)
    return growth_profile


def write_growth_profile(path: Path, profile: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def read_growth_profile(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
