from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LIFE_TRACE_SCHEMA = "ai22b-paideia-life-trace/v1"
LIFE_TRACE_EVENT_SCHEMA = "ai22b-paideia-life-trace-event/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _stage_for_age(age_year: int) -> str:
    if age_year == 0:
        return "infancy_attachment_and_sensory_rhythm"
    if age_year <= 2:
        return "toddler_language_and_boundary_practice"
    if age_year <= 5:
        return "early_childhood_play_and_emotion_naming"
    if age_year <= 8:
        return "lower_elementary_basic_school_and_friendship"
    if age_year <= 11:
        return "upper_elementary_rules_clubs_and_first_exams"
    if age_year <= 14:
        return "middle_school_identity_peer_stress_and_study_habits"
    if age_year <= 17:
        return "high_school_exam_pressure_and_domain_discovery"
    if age_year <= 20:
        return "university_foundation_major_projects_and_work_identity"
    return "post_hire_growth"


def _domain_cycle() -> list[str]:
    return [
        "family_interaction",
        "peer_world",
        "school_challenge",
        "aesthetic_exposure",
        "emotional_recovery",
        "environment_observation",
        "meaning_reflection",
        "domain_obsession",
    ]


def _setting_for(domain: str, ecology: dict[str, Any], age_year: int) -> str:
    residential = ecology.get("residential_environment", {})
    if domain == "family_interaction":
        return "home dining table and evening review"
    if domain == "peer_world":
        return "playground, classroom, club room, or group chat"
    if domain == "school_challenge":
        return "school desk, academy room, or online course"
    if domain == "aesthetic_exposure":
        return "music, drawing, book, travel photo, or note design"
    if domain == "emotional_recovery":
        return "quiet room, short walk, or feedback conversation"
    if domain == "environment_observation":
        return str(residential.get("environment_type") or "ordinary local neighborhood")
    if domain == "meaning_reflection":
        return "family talk, diary, history trip, or public event"
    if age_year >= 18:
        return "university library, public filings desk, or project notebook"
    return "personal notebook and supervised study block"


def _actors_for(domain: str, ecology: dict[str, Any], age_year: int) -> list[str]:
    family = ecology.get("family_climate", {})
    caregivers = [str(item) for item in family.get("caregivers", [])][:2] or ["caregiver"]
    if domain == "family_interaction":
        return caregivers
    if domain == "peer_world":
        return ["friend", "classmate"] if age_year >= 3 else caregivers + ["nearby child"]
    if domain == "school_challenge":
        return ["teacher", "classmate", "self"]
    if domain == "emotional_recovery":
        return ["self", caregivers[0]]
    if domain == "domain_obsession":
        return ["self", "mentor", "source material"]
    return ["self"]


def _event_text(domain: str, ecology: dict[str, Any], age_year: int, period_index: int) -> dict[str, str]:
    family = ecology.get("family_climate", {})
    peer = ecology.get("peer_world", {})
    aesthetic = ecology.get("aesthetic_profile", {})
    emotional = ecology.get("emotional_development", {})
    target_role = ecology.get("talent", {}).get("target_role") or "local specialist agent"
    sensory_cues = ecology.get("residential_environment", {}).get("sensory_cues", [])
    cue = sensory_cues[period_index % len(sensory_cues)] if sensory_cues else "ordinary sensory cue"
    support = (family.get("supports") or ["short supervised reset"])[period_index % len(family.get("supports") or [1])]
    recovery = (emotional.get("recovery_methods") or ["review and reset"])[
        period_index % len(emotional.get("recovery_methods") or [1])
    ]

    if domain == "family_interaction":
        return {
            "stimulus": f"Shared routine around {cue} and a caregiver's voice.",
            "challenge": "Notice the caregiver's intention before reacting.",
            "choice": "Pause, answer politely, and ask one clarifying question.",
            "outcome": "Attachment rhythm becomes linked to language, routine, and feedback.",
            "support": support,
            "recovery": recovery,
            "learning_delta": "conversation starts from listening to intent, not from rushing to a specialist answer",
        }
    if domain == "peer_world":
        pattern = (peer.get("conflict_patterns") or ["minor misunderstanding"])[period_index % len(peer.get("conflict_patterns") or [1])]
        return {
            "stimulus": f"Peer interaction produces {pattern}.",
            "challenge": "Keep belonging while handling disagreement.",
            "choice": "Summarize the other side, state one need, and offer a repair.",
            "outcome": "Social memory stores conflict as a recoverable process.",
            "support": "friendship repair practice",
            "recovery": "specific apology or rule adjustment",
            "learning_delta": "relationship repair becomes a reusable social operator",
        }
    if domain == "school_challenge":
        return {
            "stimulus": "Assignment, quiz, presentation, or long reading task.",
            "challenge": "Turn pressure into visible work product instead of self-judgment.",
            "choice": "Make a small answer, mark uncertainty, and revise after feedback.",
            "outcome": "Mistakes become exam-ready records rather than hidden failures.",
            "support": "teacher feedback and home review",
            "recovery": recovery,
            "learning_delta": "wrong answers feed the Reasoning Ledger through reviewable evidence",
        }
    if domain == "aesthetic_exposure":
        hobby = (aesthetic.get("hobbies") or ["note-taking"])[period_index % len(aesthetic.get("hobbies") or [1])]
        return {
            "stimulus": f"Aesthetic practice through {hobby}.",
            "challenge": "Connect feeling, perception, and expression without over-explaining.",
            "choice": "Keep a short journal note with one image, sound, or rhythm.",
            "outcome": "Memory gains sensory anchors for ordinary conversation.",
            "support": str(aesthetic.get("music") or "music and reading"),
            "recovery": "low-stakes creative reset",
            "learning_delta": "nontechnical experience improves tone, empathy, and metaphor control",
        }
    if domain == "emotional_recovery":
        stressor = (family.get("stressors") or ["bounded stress"])[period_index % len(family.get("stressors") or [1])]
        return {
            "stimulus": f"Stress event: {stressor}.",
            "challenge": "Recover without pretending the stress did not happen.",
            "choice": "Name the stress, choose one repair method, and retest later.",
            "outcome": "Recovery skill becomes more important than avoiding all stress.",
            "support": support,
            "recovery": recovery,
            "learning_delta": "stress is recorded with support, repair, and a next action",
        }
    if domain == "environment_observation":
        return {
            "stimulus": f"Observation walk in {cue}.",
            "challenge": "Notice how context changes behavior and attention.",
            "choice": "Record one local detail and one question it raises.",
            "outcome": "External environment becomes part of evidence seeking.",
            "support": "walk, weather, library, or family errand",
            "recovery": "slow attention reset",
            "learning_delta": "situational cues can change what evidence should be collected",
        }
    if domain == "meaning_reflection":
        return {
            "stimulus": "Cultural event, family value talk, biography, or public issue.",
            "challenge": "Make meaning without claiming superiority or fate.",
            "choice": "Compare two perspectives and keep one open question.",
            "outcome": "Worldview is practiced as inquiry, not injected as a fixed slogan.",
            "support": "nonsectarian meaning-making and respectful discussion",
            "recovery": "return to evidence and empathy",
            "learning_delta": "values guide questions but do not replace verification",
        }
    return {
        "stimulus": f"Domain curiosity toward {target_role}.",
        "challenge": "Avoid copying the role model's answers while following the learning path.",
        "choice": "Study source material, solve a task, and keep an error note.",
        "outcome": "Domain identity forms through repeated coursework and exams.",
        "support": "mentor, public source, and local practice notebook",
        "recovery": "counterexample review",
        "learning_delta": "specialist habits must emerge from work, not from personality prompt injection",
    }


def _stress_level(domain: str, age_year: int, sequence: int) -> int:
    base = {
        "family_interaction": 1,
        "peer_world": 2,
        "school_challenge": 3,
        "aesthetic_exposure": 1,
        "emotional_recovery": 4,
        "environment_observation": 1,
        "meaning_reflection": 2,
        "domain_obsession": 3,
    }[domain]
    if age_year in {14, 17, 20} and domain in {"school_challenge", "domain_obsession"}:
        base += 1
    if sequence % 29 == 0:
        base += 1
    return max(0, min(5, base))


def build_life_trace(
    blueprint: dict[str, Any],
    ecology: dict[str, Any],
    *,
    density: str = "monthly",
) -> dict[str, Any]:
    if blueprint.get("schema") != "ai-talent-training-blueprint/v1":
        raise ValueError("Unsupported training blueprint schema")
    if ecology.get("schema") != "ai22b-paideia-developmental-ecology/v1":
        raise ValueError("Unsupported developmental ecology schema")
    if density == "monthly":
        periods_per_year = 12
        period_label = "month"
    elif density == "daily":
        periods_per_year = 365
        period_label = "day"
    else:
        raise ValueError("density must be one of: monthly, daily")

    identity = blueprint.get("identity", {})
    domains = _domain_cycle()
    trace_id = _stable_id(
        "life-trace",
        identity.get("name"),
        identity.get("gender"),
        blueprint.get("domain"),
        ecology.get("seed", {}).get("seed_id"),
        density,
    )
    events: list[dict[str, Any]] = []
    sequence = 0
    for age_year in range(0, 21):
        for period in range(1, periods_per_year + 1):
            sequence += 1
            domain = domains[(sequence - 1) % len(domains)]
            text = _event_text(domain, ecology, age_year, period)
            event = {
                "schema": LIFE_TRACE_EVENT_SCHEMA,
                "trace_id": trace_id,
                "event_id": _stable_id("event", trace_id, sequence),
                "sequence": sequence,
                "age_year": age_year,
                "period_type": period_label,
                "period_index": period,
                "stage_id": _stage_for_age(age_year),
                "domain": domain,
                "setting": _setting_for(domain, ecology, age_year),
                "actors": _actors_for(domain, ecology, age_year),
                "stimulus": text["stimulus"],
                "challenge": text["challenge"],
                "stress_level": _stress_level(domain, age_year, sequence),
                "support": text["support"],
                "choice": text["choice"],
                "outcome": text["outcome"],
                "recovery": text["recovery"],
                "learning_delta": text["learning_delta"],
                "memory_targets": [
                    "episodic_fast_store",
                    "semantic_slow_store" if sequence % 4 == 0 else "metacognitive_monitor",
                ],
                "assessment_tags": [
                    _stage_for_age(age_year),
                    domain,
                    "growth_experience",
                    "reviewable_summary_only",
                ],
                "safety": {
                    "private_reasoning_trace": "not_stored",
                    "synthetic_event": True,
                    "contains_real_private_location": False,
                    "bounded_stress": True,
                },
            }
            events.append(event)

    manifest = {
        "schema": LIFE_TRACE_SCHEMA,
        "created_at_utc": _now(),
        "trace_id": trace_id,
        "talent": {
            "name": identity.get("name"),
            "gender": identity.get("gender"),
            "primary_language": identity.get("language", "ko"),
        },
        "density": density,
        "age_span_years": [0, 20],
        "periods_per_year": periods_per_year,
        "event_count": len(events),
        "source_ecology_seed": ecology.get("seed", {}).get("seed_id"),
        "policy": {
            "records_are_synthetic_training_events": True,
            "used_for_memory_substrate": True,
            "hidden_chain_of_thought": "forbidden",
            "role_model_impersonation": "forbidden",
            "public_release_safe": True,
        },
    }
    return {"manifest": manifest, "events": events}


def write_life_trace_jsonl(path: Path, trace: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(trace["manifest"], ensure_ascii=False)]
    lines.extend(json.dumps(event, ensure_ascii=False) for event in trace.get("events", []))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_life_trace_jsonl(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"manifest": {}, "events": []}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        return {"manifest": {}, "events": []}
    manifest = rows[0] if rows[0].get("schema") == LIFE_TRACE_SCHEMA else {}
    events = [row for row in rows[1:] if row.get("schema") == LIFE_TRACE_EVENT_SCHEMA]
    if not manifest:
        events = [row for row in rows if row.get("schema") == LIFE_TRACE_EVENT_SCHEMA]
    return {"manifest": manifest, "events": events}
