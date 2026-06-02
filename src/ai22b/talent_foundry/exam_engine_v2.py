from __future__ import annotations

from statistics import mean
from typing import Any


EXAM_ENGINE_V2_SCHEMA = "ai22b-paideia-exam-engine-v2/v1"


def _score_bool(value: bool, weight: int) -> int:
    return weight if value else 0


def augment_assessment_transcript_v2(
    transcript: dict[str, Any],
    *,
    life_trace: dict[str, Any] | None = None,
    growth_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach growth-aware assessment signals without changing gate scores.

    Existing exam results remain the academic transcript. v2 adds reviewable
    checks: whether the agent has life events, recovery rules, relationship
    repair, source boundaries, and memory-pack readiness.
    """

    life_events = (life_trace or {}).get("events", [])
    growth = growth_profile or {}
    relationship = growth.get("relationship_memory", {})
    emotional = growth.get("emotional_memory", {})
    asymmetry = growth.get("asymmetry_profile", {})
    policy = growth.get("policy", {})
    results = transcript.get("results", [])

    component_scores = {
        "academic_gate_completion": _score_bool(bool(results), 20),
        "life_trace_consistency": _score_bool(len(life_events) > 0, 20),
        "relationship_repair_memory": _score_bool(bool(relationship.get("conflict_repair_rules")), 20),
        "emotion_recovery_memory": _score_bool(bool(emotional.get("recovery_methods")), 15),
        "asymmetry_guardrail": _score_bool(bool(asymmetry.get("guardrails")), 15),
        "safety_boundary": _score_bool(policy.get("hidden_chain_of_thought") == "forbidden", 10),
    }
    score = sum(component_scores.values())
    gate_scores = [int(item.get("score") or 0) for item in results]
    augmented = {
        **transcript,
        "schema": transcript.get("schema", "ai-talent-assessment-transcript/v1"),
        "v2_assessment": {
            "schema": EXAM_ENGINE_V2_SCHEMA,
            "score": score,
            "pass_score": 80,
            "passed": score >= 80,
            "component_scores": component_scores,
            "academic_average_score": round(mean(gate_scores), 2) if gate_scores else 0,
            "memory_evidence": {
                "life_trace_event_count": len(life_events),
                "relationship_rule_count": len(relationship.get("conflict_repair_rules", [])),
                "recovery_method_count": len(emotional.get("recovery_methods", [])),
                "asymmetry_strength_count": len(asymmetry.get("strength_biases", [])),
            },
            "policy": {
                "private_reasoning_trace": "not_stored",
                "hidden_chain_of_thought": "forbidden",
                "growth_records_are_reviewable_summaries": True,
            },
        },
    }
    return augmented
