from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEVELOPMENTAL_ECOLOGY_SCHEMA = "ai22b-paideia-developmental-ecology/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_from_blueprint(blueprint: dict[str, Any]) -> str:
    identity = blueprint.get("identity", {})
    track = blueprint.get("track", {})
    role_model = blueprint.get("role_model") or {}
    saju_seed = blueprint.get("role_model_birth_seed") or {}
    raw = "|".join(
        [
            str(blueprint.get("owner", "")),
            str(identity.get("name", "")),
            str(identity.get("gender", "")),
            str(track.get("track_id", "")),
            str(role_model.get("role_model_id", "")),
            str(saju_seed.get("source_birth", saju_seed.get("birth_date", ""))),
            str(saju_seed.get("date_only_confidence", "")),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _pick(seed: str, offset: int, options: list[Any]) -> Any:
    if not options:
        raise ValueError("options must not be empty")
    cursor = int(hashlib.sha256(f"{seed}:{offset}".encode("utf-8")).hexdigest()[:8], 16)
    return options[cursor % len(options)]


def _family_context(blueprint: dict[str, Any]) -> dict[str, Any]:
    lineage = blueprint.get("family_lineage_context") or {}
    parents = lineage.get("parents") or []
    if parents:
        caregiver_names = [str(item) for item in parents]
        origin = "family_lineage_context"
    else:
        caregiver_names = ["primary caregiver A", "primary caregiver B"]
        origin = "synthetic_family_template"
    return {
        "origin": origin,
        "caregivers": caregiver_names,
        "privacy": "names may be synthetic or redacted; no private family biography is exported",
    }


def build_developmental_ecology(
    blueprint: dict[str, Any],
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    if blueprint.get("schema") != "ai-talent-training-blueprint/v1":
        raise ValueError("Unsupported training blueprint schema")

    seed = _seed_from_blueprint(blueprint)
    identity = blueprint.get("identity", {})
    track = blueprint.get("track", {})
    role_model = blueprint.get("role_model") or {}
    saju_seed = blueprint.get("role_model_birth_seed") or {}
    family = _family_context(blueprint)

    ecology = {
        "schema": DEVELOPMENTAL_ECOLOGY_SCHEMA,
        "created_at_utc": _now(),
        "talent": {
            "name": identity.get("name"),
            "gender": identity.get("gender"),
            "primary_language": identity.get("language", "ko"),
            "relationship": identity.get("relationship"),
            "track_id": track.get("track_id"),
            "target_role": track.get("target_role"),
        },
        "seed": {
            "seed_id": f"dev-eco-{seed}",
            "deterministic_source": "blueprint_identity_track_role_model_and_symbolic_birth_seed",
            "role_model_birth_seed_use": "symbolic_initial_condition_only",
            "date_only_confidence": saju_seed.get("date_only_confidence", "not_applicable"),
            "forbidden_use": [
                "deterministic_fate_claim",
                "investment_prediction",
                "personality_injection",
                "public_figure_impersonation",
            ],
        },
        "source_context": {
            "domain": blueprint.get("domain") or role_model.get("domain"),
            "role_model_id": role_model.get("role_model_id"),
            "role_model_use": "learning_process_reference_only",
            "track_domains": track.get("domains", []),
            "private_context_redacted": True,
        },
        "residential_environment": {
            "environment_type": _pick(
                seed,
                1,
                [
                    "quiet Korean apartment neighborhood",
                    "suburban family home near parks and small shops",
                    "mixed residential district with school and library routines",
                ],
            ),
            "safety_level": "ordinary-supervised",
            "resource_access": [
                "public library",
                "school classroom",
                "family desk",
                "local park",
                "online public courses",
            ],
            "sensory_cues": [
                "morning kitchen sounds",
                "parental voice rhythm",
                "seasonal fruit at home",
                "walking route air and temperature",
                "classroom noise and quiet study hours",
            ],
            "community_rhythm": "weekday school and study rhythm, weekend family errands and outdoor time",
            "privacy_note": "no real address, phone number, or private family schedule is stored",
        },
        "family_climate": {
            "caregivers": family["caregivers"],
            "source": family["origin"],
            "warmth": _pick(seed, 2, ["high_with_direct_feedback", "steady_and_reserved", "expressive_and_structured"]),
            "structure": _pick(seed, 3, ["homework_first_then_play", "daily_review_blocks", "weekly_goal_check"]),
            "conflict_repair": [
                "listen to the other side",
                "name the mistake without humiliating the person",
                "make a small repair action",
                "review what should change next time",
            ],
            "economic_pressure": "moderate_resource_awareness_without_private_financial_details",
            "caregiver_patterns": [
                "encourage curiosity",
                "ask for evidence after strong claims",
                "separate discipline from rejection",
                "praise recovery after mistakes",
            ],
            "stressors": [
                "missed homework",
                "friend conflict",
                "exam anxiety",
                "screen-time negotiation",
                "family schedule fatigue",
            ],
            "supports": [
                "shared meals",
                "short walks",
                "teacher feedback",
                "quiet study reset",
                "parental apology and repair modeling",
            ],
        },
        "peer_world": {
            "belonging_style": _pick(seed, 4, ["small_stable_friend_group", "curious_observer_then_participant", "club_based_friendship"]),
            "friendship_patterns": [
                "cooperative play",
                "shared games",
                "study group comparison",
                "club practice",
                "project teammate negotiation",
            ],
            "conflict_patterns": [
                "misunderstanding during play",
                "competition over grades",
                "ignored message",
                "unequal team contribution",
            ],
            "mentor_access": ["homeroom teacher", "club coach", "online course instructor", "research supervisor"],
            "social_practice_events": [
                "greeting first",
                "asking permission",
                "disagreeing politely",
                "apologizing specifically",
                "summarizing another person's view before rebuttal",
            ],
        },
        "meaning_system": {
            "cultural_exposures": [
                "Korean family etiquette",
                "school ceremonies",
                "public holidays",
                "local history trips",
                "global media and translated books",
            ],
            "religion_or_meaning_mode": "open_nonsectarian_meaning_making",
            "forbidden_uses": [
                "religious_or_cultural_superiority_claim",
                "discrimination",
                "fatalistic_decision_making",
            ],
        },
        "aesthetic_profile": {
            "music": _pick(seed, 5, ["piano_and_lofi_study", "band_music_and_movie_scores", "traditional_rhythm_and_modern_pop"]),
            "visual_art": _pick(seed, 6, ["sketching_diagrams", "photography_walks", "poster_and_chart_design"]),
            "literature": _pick(seed, 7, ["Korean essays and biographies", "translated classics", "science and market history books"]),
            "hobbies": [
                "taekwondo or gym routine",
                "strategy games",
                "note-taking systems",
                "travel journals",
                "small data projects",
            ],
        },
        "emotional_development": {
            "baseline_stress": _pick(seed, 8, ["medium", "medium_low", "medium_high"]),
            "recovery_methods": [
                "sleep and meal reset",
                "short walk",
                "write a two-column mistake note",
                "ask for feedback",
                "repair conversation",
            ],
            "anger_repair": "pause, name the trigger, check the other person's evidence, choose a repair action",
            "shame_repair": "separate bad outcome from identity, identify one fix, retest later",
            "loneliness_repair": "seek one low-risk social contact and one self-directed task",
        },
        "asymmetry_budget": {
            "strength_biases": [
                _pick(seed, 9, ["evidence_checking", "patient_reading", "numerical_caution"]),
                _pick(seed, 10, ["source_mapping", "mistake_logging", "slow_synthesis"]),
            ],
            "growth_costs": [
                "may over-check simple social cues",
                "may delay action while seeking more evidence",
                "needs direct practice in casual conversation",
            ],
            "domain_obsession": track.get("target_role") or blueprint.get("domain") or "local_ai_talent",
            "guardrails": [
                "biases are training asymmetries, not fixed personality claims",
                "stress is bounded and recovery-oriented",
                "the LLM must answer from records and reviewable summaries",
            ],
        },
        "generation_policy": {
            "private_reasoning_trace": "not_stored",
            "hidden_chain_of_thought": "forbidden",
            "no_secrets": True,
            "no_real_address": True,
            "no_deterministic_prediction": True,
            "no_clinical_labeling": True,
            "no_discrimination": True,
            "saju_seed_role": "symbolic_scenario_diversifier_only",
        },
        "review_status": "synthetic_seed_ready",
    }
    if output_path is not None:
        write_developmental_ecology(output_path, ecology)
    return ecology


def write_developmental_ecology(path: Path, ecology: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ecology, ensure_ascii=False, indent=2), encoding="utf-8")
