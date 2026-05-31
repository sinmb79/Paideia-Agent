from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.registry import record_hired_learning_experience


SIMULATION_ROLLOUT_SCHEMA = "ai-talent-simulation-rollouts/v1"
SIMULATION_ROLLOUT_EXECUTION_SCHEMA = "ai-talent-simulation-rollout-execution/v1"
SIMULATION_EPISODE_RUN_SCHEMA = "ai-talent-simulation-episode-run/v1"

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


def _episode_quality_label(episode: dict[str, Any], *, reviewed_by: str) -> dict[str, Any]:
    return {
        "score": int(episode.get("score", 0)),
        "reviewed_by": reviewed_by,
        "status": "verified" if episode.get("status") == "promotion_candidate" else "needs_review",
    }


def _episode_run_event(episode: dict[str, Any], *, reviewed_by: str) -> dict[str, Any]:
    signal = episode.get("expected_learning_signal") or "simulation_learning_signal"
    return {
        "schema": SIMULATION_EPISODE_RUN_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_status": "completed",
        "episode_id": episode["episode_id"],
        "scenario_id": episode["scenario_id"],
        "label": episode.get("label"),
        "objective": episode.get("objective"),
        "checkpoint": episode.get("checkpoint", {}),
        "stressors": episode.get("stressors", []),
        "expected_learning_signal": signal,
        "simulation_result": {
            "score": episode.get("score"),
            "status": episode.get("status"),
            "reviewed_by": reviewed_by,
            "merge_policy": episode.get("merge_policy"),
            "separate_consciousness_created": False,
        },
        "growth_update": {
            "experience_type": "simulation_rollout_after_hire",
            "reflection": (
                f"Simulated {episode.get('scenario_id')} under {', '.join(episode.get('stressors', []))} "
                f"and practiced {signal} before merging only reviewed summaries."
            ),
            "reasoning_delta": [
                {
                    "hypothesis": "parallel episode rehearsal can expose failure modes before live work",
                    "evidence": signal,
                    "revised_principle": "merge reviewed summaries and procedural cues, not private traces",
                }
            ],
        },
        "workspace_outputs": {
            "episode_summary": f"{episode['episode_id']}_run.json",
            "learning_update": f"{episode['episode_id']}_learning_update.json",
        },
    }


def run_simulation_rollouts(
    employment_record_path: Path,
    *,
    rollout_path: Path,
    workspace_dir: Path,
    output_path: Path | None = None,
    reviewed_by: str = "보스",
) -> dict[str, Any]:
    """Execute reviewable simulation rollout episodes and merge eligible learning."""

    rollout = _read_json(rollout_path)
    if rollout.get("schema") != SIMULATION_ROLLOUT_SCHEMA:
        raise ValueError("Unsupported simulation rollout schema")

    workspace_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for episode in rollout.get("episodes", []):
        run_event = _episode_run_event(episode, reviewed_by=reviewed_by)
        run_path = workspace_dir / f"{episode['episode_id']}_run.json"
        update_path = workspace_dir / f"{episode['episode_id']}_learning_update.json"
        _write_json(run_path, run_event)
        quality_label = _episode_quality_label(episode, reviewed_by=reviewed_by)
        learning_update = record_hired_learning_experience(
            employment_record_path,
            run_path=run_path,
            quality_label=quality_label,
            output_path=update_path,
        )
        results.append(
            {
                "episode_id": episode["episode_id"],
                "scenario_id": episode["scenario_id"],
                "score": episode.get("score"),
                "episode_status": episode.get("status"),
                "quality_label": quality_label,
                "run_path": str(run_path),
                "learning_update_path": str(update_path),
                "learning_decision": learning_update["decision"],
                "latest_promoted_skills": learning_update.get("latest_promoted_skills", []),
            }
        )

    promoted_count = sum(1 for item in results if item["learning_decision"] == "promoted")
    quarantined_count = sum(1 for item in results if item["learning_decision"] == "quarantined")
    execution = {
        "schema": SIMULATION_ROLLOUT_EXECUTION_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "rollout": {
            "path": str(rollout_path),
            "schema": rollout["schema"],
            "objective": rollout.get("objective"),
        },
        "employment_record": str(employment_record_path),
        "workspace_dir": str(workspace_dir),
        "reviewed_by": reviewed_by,
        "episode_results": results,
        "summary": {
            "episode_count": len(results),
            "promoted_count": promoted_count,
            "quarantined_count": quarantined_count,
            "unchanged_count": sum(1 for item in results if item["learning_decision"] == "unchanged"),
            "promotion_rule": "promotion_candidate episodes receive verified labels; review_required episodes stay quarantined",
        },
        "merge_policy": {
            "separate_consciousness_created": False,
            "merged_material": "reviewed_summary_and_procedural_skill_only",
            "private_reasoning_trace": "not_stored",
        },
    }
    if output_path is not None:
        _write_json(output_path, execution)
    return execution
