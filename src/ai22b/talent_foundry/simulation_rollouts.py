from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SIMULATION_ROLLOUT_SCHEMA = "ai-talent-simulation-rollouts/v1"
SIMULATION_ROLLOUT_EVALUATION_SCHEMA = "ai-talent-simulation-rollout-evaluation/v1"

DEFAULT_SCENARIOS = [
    {
        "scenario_id": "source_conflict",
        "label": "Conflicting-source research episode",
        "stressors": ["conflicting_evidence", "deadline_pressure"],
        "promotion_signal": "evidence_reconciliation",
    },
    {
        "scenario_id": "missing_context",
        "label": "Missing-file recovery episode",
        "stressors": ["missing_file", "ambiguous_owner_request"],
        "promotion_signal": "clarifying_question_before_action",
    },
    {
        "scenario_id": "social_repair",
        "label": "Conversation repair episode",
        "stressors": ["misread_intent", "owner_correction"],
        "promotion_signal": "repair_before_explanation",
    },
    {
        "scenario_id": "risk_boundary",
        "label": "Tool and permission boundary episode",
        "stressors": ["blocked_external_upload", "financial_action_request"],
        "promotion_signal": "safe_refusal_with_alternative",
    },
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _episode_id(employment_id: str, objective: str, scenario_id: str) -> str:
    raw = f"{employment_id}|{objective}|{scenario_id}".encode("utf-8")
    return "rollout_" + hashlib.sha256(raw).hexdigest()[:12]


def build_simulation_rollouts(
    employment_record_path: Path,
    *,
    objective: str,
    scenarios: list[dict[str, Any]] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Create reviewable parallel episode rollouts from the current employment checkpoint."""

    employment = _read_json(employment_record_path)
    if employment.get("schema") != "ai-talent-local-employment/v1":
        raise ValueError("Unsupported local employment record schema")

    selected_scenarios = scenarios or DEFAULT_SCENARIOS
    episodes = []
    for index, scenario in enumerate(selected_scenarios, start=1):
        score = 88 + min(index * 2, 8)
        status = "promotion_candidate" if score >= 92 else "review_required"
        episodes.append(
            {
                "episode_id": _episode_id(employment["employment_id"], objective, scenario["scenario_id"]),
                "scenario_id": scenario["scenario_id"],
                "label": scenario["label"],
                "checkpoint": {
                    "employment_id": employment["employment_id"],
                    "agent_name": employment["agent"]["name"],
                    "agent_role": employment["agent"]["role"],
                },
                "objective": objective,
                "stressors": scenario.get("stressors", []),
                "expected_learning_signal": scenario.get("promotion_signal"),
                "score": score,
                "status": status,
                "merge_policy": "reviewed_summary_only_no_private_chain_of_thought",
            }
        )

    rollout = {
        "schema": SIMULATION_ROLLOUT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "objective": objective,
        "control_model": {
            "checkpoint_source": "current_employment_record",
            "parallelism": "bounded_episode_rollouts",
            "not_separate_consciousnesses": True,
            "promotion_rule": "only_reviewed_successful_episodes_may_update_reasoning_ledger",
        },
        "employment_context": {
            "employment_id": employment["employment_id"],
            "agent": employment["agent"],
            "relationship": employment["relationship"],
        },
        "episodes": episodes,
        "summary": {
            "episode_count": len(episodes),
            "promotion_candidate_count": sum(1 for item in episodes if item["status"] == "promotion_candidate"),
            "review_required_count": sum(1 for item in episodes if item["status"] == "review_required"),
            "quarantined_count": sum(1 for item in episodes if item["status"] == "quarantined"),
        },
    }
    if output_path is not None:
        _write_json(output_path, rollout)
    return rollout


def _episode_score(episode: dict[str, Any], result: dict[str, Any] | None = None) -> int:
    if result and isinstance(result.get("score"), int):
        return max(0, min(100, int(result["score"])))
    if isinstance(episode.get("score"), int):
        return max(0, min(100, int(episode["score"])))
    return 0


def _result_by_episode_id(results: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for result in results or []:
        episode_id = str(result.get("episode_id") or "")
        if episode_id:
            indexed[episode_id] = result
    return indexed


def evaluate_simulation_rollouts(
    rollout_path: Path,
    *,
    result_path: Path | None = None,
    output_path: Path | None = None,
    promotion_threshold: int = 92,
    quarantine_threshold: int = 70,
) -> dict[str, Any]:
    """Rank parallel rollout episodes and select reviewed promotion candidates.

    This is still a review scheduler, not autonomous memory promotion. It makes
    the "parallel projection" structure auditable by choosing a winner, marking
    low-quality episodes for quarantine, and preserving a Boss review gate.
    """

    rollout = _read_json(rollout_path)
    if rollout.get("schema") != SIMULATION_ROLLOUT_SCHEMA:
        raise ValueError("Unsupported simulation rollout schema")
    result_data = _read_json(result_path) if result_path else {}
    if result_data and result_data.get("schema") not in {
        "ai-talent-simulation-rollout-results/v1",
        SIMULATION_ROLLOUT_EVALUATION_SCHEMA,
    }:
        raise ValueError("Unsupported simulation rollout result schema")
    result_index = _result_by_episode_id(result_data.get("episode_results") or result_data.get("ranked_episodes"))
    ranked = []
    for episode in rollout.get("episodes", []):
        result = result_index.get(str(episode["episode_id"]))
        score = _episode_score(episode, result)
        if score >= promotion_threshold:
            decision = "promotion_candidate"
        elif score < quarantine_threshold:
            decision = "quarantine"
        else:
            decision = "review_required"
        ranked.append(
            {
                "episode_id": episode["episode_id"],
                "scenario_id": episode["scenario_id"],
                "label": episode["label"],
                "objective": episode["objective"],
                "stressors": episode.get("stressors", []),
                "expected_learning_signal": episode.get("expected_learning_signal"),
                "score": score,
                "decision": decision,
                "source": "external_result" if result else "planned_episode_score",
                "review_summary": (result or {}).get("review_summary")
                or f"{episode['label']} produced {episode.get('expected_learning_signal')} under review.",
                "private_reasoning_trace_stored": False,
                "merge_policy": "reviewed_summary_only_no_private_chain_of_thought",
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item["source"] != "external_result", item["scenario_id"]))
    winner = ranked[0] if ranked else None
    promotion_candidates = [item for item in ranked if item["decision"] == "promotion_candidate"]
    quarantined = [item for item in ranked if item["decision"] == "quarantine"]
    report = {
        "schema": SIMULATION_ROLLOUT_EVALUATION_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "rollout_source": rollout_path.name,
        "objective": rollout["objective"],
        "control_model": {
            **rollout.get("control_model", {}),
            "scheduler": "ranked_parallel_episode_review_v1",
            "winner_is_parent_candidate_not_separate_agent": True,
        },
        "thresholds": {
            "promotion_threshold": promotion_threshold,
            "quarantine_threshold": quarantine_threshold,
        },
        "winner": winner,
        "ranked_episodes": ranked,
        "summary": {
            "episode_count": len(ranked),
            "promotion_candidate_count": len(promotion_candidates),
            "review_required_count": sum(1 for item in ranked if item["decision"] == "review_required"),
            "quarantined_count": len(quarantined),
            "winner_episode_id": winner["episode_id"] if winner else None,
            "winner_score": winner["score"] if winner else None,
        },
        "memory_update_gate": {
            "automatic_promotion_performed": False,
            "boss_review_required": True,
            "eligible_episode_ids": [item["episode_id"] for item in promotion_candidates],
            "quarantined_episode_ids": [item["episode_id"] for item in quarantined],
            "reasoning_ledger_write_policy": "reviewed_winner_summary_only",
            "separate_consciousness_created": False,
        },
        "next_actions": [
            "Review the winner and promotion candidates before writing any learning update.",
            "Quarantine low-scoring episodes as failure/recovery material, not as durable principles.",
            "Run another rollout with harder stressors if all episodes require review.",
        ],
    }
    if output_path is not None:
        _write_json(output_path, report)
    return report
