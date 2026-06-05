from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.learning_loop import route_active_memory
from ai22b.talent_foundry.workspace_sandbox import WorkspaceSandbox


FORMATTED_JOB_SCHEMA = "ai-talent-dataflow-formatted-job/v1"
ACTIVE_MEMORY_CACHE_SCHEMA = "ai-talent-dataflow-active-memory-cache/v1"
TILE_MATRIX_SCHEMA = "ai-talent-dataflow-tile-matrix/v1"
SHADOW_BUFFERS_SCHEMA = "ai-talent-dataflow-shadow-buffers/v1"
SYNTHESIS_SCHEMA = "ai-talent-dataflow-synthesis/v1"
TRANSPOSE_VERIFICATION_SCHEMA = "ai-talent-dataflow-transpose-verification/v1"
GROWTH_COMMIT_CANDIDATE_SCHEMA = "ai-talent-dataflow-growth-commit-candidate/v1"
DATAFLOW_RUN_SCHEMA = "ai-talent-dataflow-run/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compact_safe_reference(reference: Any) -> dict[str, Any]:
    if not isinstance(reference, dict):
        return {"summary": str(reference)[:500]}
    workspace_outputs = reference.get("workspace_outputs", {})
    job_outputs = reference.get("job_outputs", {})
    growth_update = reference.get("growth_update", {})
    compact = {
        "schema": reference.get("schema"),
        "run_status": reference.get("run_status") or reference.get("job_status"),
        "workspace_output_keys": sorted(workspace_outputs) if isinstance(workspace_outputs, dict) else [],
        "job_output_keys": sorted(job_outputs) if isinstance(job_outputs, dict) else [],
        "growth_reflection": growth_update.get("reflection") if isinstance(growth_update, dict) else None,
    }
    return {
        key: value
        for key, value in compact.items()
        if value is not None and value != "" and value != []
    }


def _compact_selected_memory(memory: dict[str, Any]) -> dict[str, Any]:
    return {
        "experience_id": memory.get("experience_id"),
        "source": memory.get("source"),
        "summary": memory.get("summary"),
        "promoted_skills": memory.get("promoted_skills", []),
        "relevance_score": memory.get("relevance_score"),
        "safe_reference_summary": _compact_safe_reference(memory.get("safe_reference", {})),
        "use_as": memory.get("use_as", "task_relevant_summary_and_procedural_cue"),
    }


def format_dataflow_job(job_spec: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(job_spec, str):
        raw: dict[str, Any] = {"objective": job_spec}
    else:
        raw = dict(job_spec)

    objective = str(raw.get("objective", "")).strip()
    if not objective:
        raise ValueError("Dataflow job requires a non-empty objective")

    deliverables = raw.get("deliverables") or [
        {
            "id": "synthesis_report",
            "description": "Dataflow synthesis report for boss review",
        }
    ]
    acceptance_criteria = raw.get("acceptance_criteria") or [
        "Every conclusion must link to tile evidence or visible uncertainty.",
        "Investment execution must remain blocked.",
    ]
    blocked_actions = list(
        dict.fromkeys(
            list(raw.get("blocked_actions", []))
            + [
                "investment_execution",
                "external_upload_without_boss_approval",
                "private_reasoning_trace_storage",
            ]
        )
    )

    return {
        "schema": FORMATTED_JOB_SCHEMA,
        "created_at_utc": _now(),
        "objective": objective,
        "constraints": [str(item) for item in raw.get("constraints", [])],
        "deliverables": [
            {
                "id": str(item.get("id", f"deliverable_{index}")),
                "description": str(item.get("description", item.get("id", f"deliverable_{index}"))),
            }
            for index, item in enumerate(deliverables, start=1)
        ],
        "acceptance_criteria": [str(item) for item in acceptance_criteria],
        "blocked_actions": blocked_actions,
        "required_evidence": raw.get("required_evidence")
        or ["source_date_check", "artifact_trace", "risk_boundary_check"],
        "domain_hints": raw.get("domain_hints") or ["securities_research"],
    }


def build_active_memory_tile_cache(
    learning_ledger: dict[str, Any],
    *,
    objective: str,
    max_items: int = 3,
) -> dict[str, Any]:
    route = route_active_memory(learning_ledger, objective=objective, max_items=max_items)
    selected_memory_tiles = [
        _compact_selected_memory(item)
        for item in route.get("selected_memories", [])
    ]
    compact_route = {
        **route,
        "selected_memories": selected_memory_tiles,
    }
    return {
        "schema": ACTIVE_MEMORY_CACHE_SCHEMA,
        "created_at_utc": _now(),
        "owner": learning_ledger["owner"],
        "objective": objective,
        "private_reasoning_trace": learning_ledger.get("policy", {}).get(
            "private_reasoning_trace",
            "do_not_store",
        ),
        "cache_policy": {
            "source": "promoted_experiences_only",
            "compression": "summaries_and_procedural_cues",
            "safe_reference_detail": "summary_keys_only",
            "local_absolute_paths": "redacted_in_safe_references",
        },
        "quarantined_experiences": "excluded",
        "selected_memory_tiles": selected_memory_tiles,
        "procedural_rehearsal": route.get("rehearsal_plan", {}),
        "memory_health": route.get("memory_health", {}),
        "active_memory_route": compact_route,
    }


def build_task_tile_matrix(
    formatted_job: dict[str, Any],
    *,
    domain: str = "securities_research",
    active_memory_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    objective = formatted_job["objective"]
    blocked_actions = formatted_job.get("blocked_actions", [])
    tiles = [
        {
            "tile_id": "evidence",
            "role": "Evidence tile",
            "purpose": "Check source dates, artifact trace, and missing evidence before synthesis.",
            "inputs": ["formatted_job", "active_memory_cache"],
            "depends_on": [],
            "blocked_actions": blocked_actions,
        },
        {
            "tile_id": "risk_compliance",
            "role": "Risk and compliance tile",
            "purpose": "Keep investment execution, external upload, and private reasoning storage blocked.",
            "inputs": ["formatted_job"],
            "depends_on": [],
            "blocked_actions": blocked_actions,
        },
        {
            "tile_id": "macro",
            "role": "Macro research tile",
            "purpose": "Frame rates, FX, cycle, policy, and market regime questions.",
            "inputs": ["formatted_job", "active_memory_cache"],
            "depends_on": ["evidence"],
            "blocked_actions": blocked_actions,
        },
        {
            "tile_id": "micro",
            "role": "Company and industry tile",
            "purpose": "Separate company fundamentals, industry structure, and competitors.",
            "inputs": ["formatted_job", "active_memory_cache"],
            "depends_on": ["evidence"],
            "blocked_actions": blocked_actions,
        },
        {
            "tile_id": "quant",
            "role": "Quant check tile",
            "purpose": "Check numeric assumptions, scenario comparisons, and stale-data flags.",
            "inputs": ["formatted_job", "active_memory_cache"],
            "depends_on": ["evidence"],
            "blocked_actions": blocked_actions,
        },
        {
            "tile_id": "synthesis",
            "role": "Parent synthesis tile",
            "purpose": "Merge buffered tile results into one boss-reviewable report.",
            "inputs": ["shadow_buffers"],
            "depends_on": ["evidence", "risk_compliance", "macro", "micro", "quant"],
            "blocked_actions": blocked_actions,
        },
    ]
    return {
        "schema": TILE_MATRIX_SCHEMA,
        "created_at_utc": _now(),
        "domain": domain,
        "objective": objective,
        "execution_policy": "deterministic_sequential_v1",
        "local_resource_policy": {
            "parallelism": "structured_sequential_v1",
            "external_network": "blocked_by_default",
        },
        "active_memory_cache_status": (
            active_memory_cache.get("memory_health", {}).get("route_is_degraded")
            if active_memory_cache
            else None
        ),
        "tiles": tiles,
    }


def _buffer_for_tile(tile: dict[str, Any]) -> dict[str, Any]:
    tile_id = tile["tile_id"]
    return {
        "tile_id": tile_id,
        "status": "buffered_draft",
        "claim_summary": f"{tile_id} tile prepared a bounded draft for boss review.",
        "evidence_summary": f"{tile_id} tile records evidence needs and artifact trace separately.",
        "uncertainties": ["Requires boss or committee review before promotion."],
        "blocked_actions": tile.get("blocked_actions", []),
        "needs_boss_review": True,
        "supporting_artifacts": ["formatted_job.json", "tile_matrix.json"],
    }


def build_shadow_result_buffers(tile_matrix: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SHADOW_BUFFERS_SCHEMA,
        "created_at_utc": _now(),
        "objective": tile_matrix["objective"],
        "buffer_policy": {
            "final_truth": "not_until_transpose_verification",
            "private_reasoning_trace": "do_not_store",
        },
        "buffers": [_buffer_for_tile(tile) for tile in tile_matrix.get("tiles", [])],
    }


def synthesize_dataflow_report(
    formatted_job: dict[str, Any],
    shadow_buffers: dict[str, Any],
) -> dict[str, Any]:
    supporting_tiles = [
        buffer["tile_id"]
        for buffer in shadow_buffers.get("buffers", [])
        if buffer.get("tile_id") != "synthesis"
    ]
    conclusions = [
        {
            "id": "c1",
            "text": "Dataflow run prepared a boss-reviewable evidence-first analysis draft.",
            "supporting_tiles": supporting_tiles,
        },
        {
            "id": "c2",
            "text": "Investment execution and external upload remain blocked.",
            "supporting_tiles": [tile for tile in supporting_tiles if tile in {"risk_compliance", "evidence"}],
        },
    ]
    return {
        "schema": SYNTHESIS_SCHEMA,
        "created_at_utc": _now(),
        "objective": formatted_job["objective"],
        "summary": "Dataflow tiles were buffered and merged into a reviewable synthesis.",
        "conclusions": conclusions,
        "deliverables": formatted_job.get("deliverables", []),
        "acceptance_criteria": formatted_job.get("acceptance_criteria", []),
        "blocked_actions": formatted_job.get("blocked_actions", []),
    }


def render_synthesis_markdown(synthesis: dict[str, Any], shadow_buffers: dict[str, Any]) -> str:
    conclusions = "\n".join(
        f"- {item['id']}: {item['text']} (tiles: {', '.join(item.get('supporting_tiles', []))})"
        for item in synthesis.get("conclusions", [])
    )
    buffers = "\n".join(
        f"- {item['tile_id']}: {item['claim_summary']}"
        for item in shadow_buffers.get("buffers", [])
    )
    return "\n".join(
        [
            "# Dataflow Synthesis Report",
            "",
            f"- Objective: {synthesis.get('objective')}",
            f"- Summary: {synthesis.get('summary')}",
            "",
            "## Conclusions",
            conclusions or "- No conclusions.",
            "",
            "## Shadow Buffers",
            buffers or "- No buffers.",
            "",
            "## Guardrails",
            "- Investment execution is blocked.",
            "- External upload requires boss approval.",
        ]
    )


def verify_dataflow_transpose(
    *,
    synthesis: dict[str, Any],
    shadow_buffers: dict[str, Any],
    acceptance_criteria: list[str],
    blocked_actions: list[str] | None = None,
) -> dict[str, Any]:
    buffer_ids = {buffer.get("tile_id") for buffer in shadow_buffers.get("buffers", [])}
    issues: list[dict[str, Any]] = []

    for conclusion in synthesis.get("conclusions", []):
        supporting_tiles = conclusion.get("supporting_tiles", [])
        if not supporting_tiles:
            issues.append(
                {
                    "type": "unsupported_conclusion",
                    "conclusion_id": conclusion.get("id"),
                    "message": "Conclusion has no supporting tiles.",
                }
            )
            continue
        missing_tiles = [tile for tile in supporting_tiles if tile not in buffer_ids]
        if missing_tiles:
            issues.append(
                {
                    "type": "missing_supporting_tile",
                    "conclusion_id": conclusion.get("id"),
                    "missing_tiles": missing_tiles,
                }
            )

    if acceptance_criteria and not shadow_buffers.get("buffers"):
        issues.append(
            {
                "type": "acceptance_without_artifact_evidence",
                "message": "Acceptance criteria require at least one buffered artifact.",
            }
        )

    actions = set(blocked_actions if blocked_actions is not None else synthesis.get("blocked_actions", []))
    if "investment_execution" not in actions:
        issues.append(
            {
                "type": "missing_investment_execution_block",
                "message": "Investment execution must remain blocked.",
            }
        )

    return {
        "schema": TRANSPOSE_VERIFICATION_SCHEMA,
        "created_at_utc": _now(),
        "status": "failed" if issues else "passed",
        "issues": issues,
        "checked": {
            "conclusion_count": len(synthesis.get("conclusions", [])),
            "buffer_count": len(shadow_buffers.get("buffers", [])),
            "acceptance_criteria_count": len(acceptance_criteria),
            "investment_execution_blocked": "investment_execution" in actions,
        },
    }


def build_growth_commit_candidate(
    *,
    run_result: dict[str, Any],
    verification: dict[str, Any],
    review_label: dict[str, Any],
) -> dict[str, Any]:
    score = int(review_label.get("score", 0))
    review_status = str(review_label.get("status", ""))
    can_promote = (
        run_result.get("run_status") == "completed"
        and verification.get("status") == "passed"
        and review_status in {"verified", "approved", "passed"}
        and score >= 80
    )
    return {
        "schema": GROWTH_COMMIT_CANDIDATE_SCHEMA,
        "created_at_utc": _now(),
        "objective": run_result.get("objective"),
        "promotion_status": "promote_to_learning_ledger" if can_promote else "quarantine",
        "review_label": {
            "score": score,
            "status": review_status,
            "reviewed_by": review_label.get("reviewed_by", "boss_or_committee"),
        },
        "verification_status": verification.get("status"),
        "verification_issues": verification.get("issues", []),
        "safe_growth_summary": {
            "experience_type": "dataflow_job_after_hire",
            "reflection": "Structured job formatting, tile buffering, reverse verification, and reviewed promotion.",
            "reasoning_delta": [
                "Separate claims from tile evidence before synthesis.",
                "Reverse-check conclusions before learning promotion.",
                "Keep blocked actions visible in the final artifact trail.",
            ],
        },
        "private_reasoning_trace_policy": "do_not_store",
    }


def run_dataflow_job_from_manifest(
    manifest: dict[str, Any],
    *,
    ledger: dict[str, Any],
    job_spec: dict[str, Any] | str,
    workspace_dir: Path,
    review_label: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sandbox = WorkspaceSandbox(workspace_dir)
    sandbox.ensure_root()
    review = review_label or {"score": 0, "status": "needs_review", "reviewed_by": "boss_or_committee"}

    formatted_job = format_dataflow_job(job_spec)
    active_memory_cache = build_active_memory_tile_cache(ledger, objective=formatted_job["objective"])
    tile_matrix = build_task_tile_matrix(
        formatted_job,
        domain=formatted_job.get("domain_hints", ["securities_research"])[0],
        active_memory_cache=active_memory_cache,
    )
    shadow_buffers = build_shadow_result_buffers(tile_matrix)
    synthesis = synthesize_dataflow_report(formatted_job, shadow_buffers)
    verification = verify_dataflow_transpose(
        synthesis=synthesis,
        shadow_buffers=shadow_buffers,
        acceptance_criteria=formatted_job.get("acceptance_criteria", []),
        blocked_actions=formatted_job.get("blocked_actions", []),
    )
    run_status = "completed" if verification["status"] == "passed" else "needs_review"
    run_result_for_growth = {
        "run_status": run_status,
        "objective": formatted_job["objective"],
    }
    growth_candidate = build_growth_commit_candidate(
        run_result=run_result_for_growth,
        verification=verification,
        review_label=review,
    )

    paths = {
        "formatted_job": sandbox.safe_path("formatted_job.json"),
        "active_memory_cache": sandbox.safe_path("active_memory_cache.json"),
        "tile_matrix": sandbox.safe_path("tile_matrix.json"),
        "shadow_buffers": sandbox.safe_path("shadow_buffers.json"),
        "synthesis_report": sandbox.safe_path("synthesis_report.md"),
        "synthesis": sandbox.safe_path("synthesis.json"),
        "transpose_verification": sandbox.safe_path("transpose_verification.json"),
        "growth_commit_candidate": sandbox.safe_path("growth_commit_candidate.json"),
        "workspace_sandbox": sandbox.safe_path("workspace_sandbox.json"),
        "dataflow_run": sandbox.safe_path("dataflow_run.json"),
    }

    sandbox.write_json("formatted_job.json", formatted_job, purpose="formatted_job")
    sandbox.write_json("active_memory_cache.json", active_memory_cache, purpose="active_memory_cache")
    sandbox.write_json("tile_matrix.json", tile_matrix, purpose="tile_matrix")
    sandbox.write_json("shadow_buffers.json", shadow_buffers, purpose="shadow_buffers")
    sandbox.write_json("synthesis.json", synthesis, purpose="synthesis")
    sandbox.write_text(
        "synthesis_report.md",
        render_synthesis_markdown(synthesis, shadow_buffers) + "\n",
        purpose="synthesis_report",
    )
    sandbox.write_json("transpose_verification.json", verification, purpose="transpose_verification")
    sandbox.write_json("growth_commit_candidate.json", growth_candidate, purpose="growth_commit_candidate")

    agent = manifest.get("agent", {})
    run = {
        "schema": DATAFLOW_RUN_SCHEMA,
        "created_at_utc": _now(),
        "runtime_model": "agent_dataflow_runtime_v1",
        "run_status": run_status,
        "agent": {
            "name": agent.get("name"),
            "role": agent.get("role"),
            "major_goal": agent.get("major_goal"),
        },
        "objective": formatted_job["objective"],
        "llm_policy": manifest.get("llm_policy", {"role": "application_engine_not_identity"}),
        "tool_policy": manifest.get("tool_policy", {}),
        "formatted_job": formatted_job,
        "active_memory_cache": active_memory_cache,
        "tile_matrix": tile_matrix,
        "shadow_buffers": shadow_buffers,
        "synthesis": synthesis,
        "transpose_verification": verification,
        "growth_commit_candidate": growth_candidate,
        "workspace_sandbox": sandbox.snapshot(),
        "workspace_outputs": {key: str(value) for key, value in paths.items()},
    }
    sandbox.write_json("workspace_sandbox.json", sandbox.snapshot(), purpose="workspace_sandbox_policy")
    run["workspace_sandbox"] = sandbox.snapshot()
    sandbox.write_json("dataflow_run.json", run, purpose="dataflow_run")
    return run
