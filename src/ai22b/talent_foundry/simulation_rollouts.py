from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SIMULATION_ROLLOUT_SCHEMA = "ai-talent-simulation-rollouts/v1"

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
