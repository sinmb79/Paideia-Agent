from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .fingerprint import build_task_fingerprint
from .models import TaskFingerprint
from .curriculum_loop import load_weakness_records
from .pattern_layer import (
    apply_pattern_layer_to_decision,
    load_critic_reports,
    load_failure_memories,
    load_patterns,
    load_user_decision_model,
)
from .planner import build_kibo_reuse_plan as build_plan_payload
from .retriever import search_kibo
from .scorer import make_reuse_decision
from .skill_graph import build_skill_gap_report, load_skill_graph


def _read_task(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("task file must contain a JSON object")
    return payload


def fingerprint_from_task_payload(payload: dict[str, Any]) -> TaskFingerprint:
    if payload.get("schema") == "paideia-task-fingerprint/v1":
        return TaskFingerprint.from_dict(payload)
    request = str(payload.get("request") or payload.get("task") or payload.get("objective") or "")
    if not request:
        raise ValueError("task payload requires request, task, or objective")
    return build_task_fingerprint(
        request,
        owner=str(payload.get("owner") or "Boss"),
        agent_profile=payload.get("agent_profile") if isinstance(payload.get("agent_profile"), dict) else None,
        genius_profile=payload.get("genius_profile") if isinstance(payload.get("genius_profile"), dict) else None,
        memory_substrate=payload.get("memory_substrate") if isinstance(payload.get("memory_substrate"), dict) else None,
        task_id=payload.get("task_id"),
    )


def route_task(
    task: dict[str, Any] | TaskFingerprint,
    *,
    repo_root: Path | None = None,
    kibo_paths: Iterable[Path] | None = None,
    sqlite_index_path: Path | None = None,
    pattern_paths: Iterable[Path] | None = None,
    failure_paths: Iterable[Path] | None = None,
    weakness_paths: Iterable[Path] | None = None,
    user_model_path: Path | None = None,
    critic_paths: Iterable[Path] | None = None,
    skill_graph_path: Path | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    fingerprint = task if isinstance(task, TaskFingerprint) else fingerprint_from_task_payload(task)
    failure_memories = load_failure_memories(failure_paths)
    scores = search_kibo(
        fingerprint,
        repo_root=repo_root,
        kibo_paths=kibo_paths,
        sqlite_index_path=sqlite_index_path,
        failure_memories=failure_memories,
        limit=limit,
    )
    decision = make_reuse_decision(fingerprint, scores)
    pattern_context: dict[str, Any] | None = None
    if pattern_paths or failure_paths or weakness_paths or user_model_path or critic_paths or skill_graph_path:
        skill_nodes, _skill_edges = load_skill_graph(skill_graph_path)
        skill_gap_report = build_skill_gap_report(fingerprint, skill_nodes) if skill_graph_path else None
        decision, pattern_context = apply_pattern_layer_to_decision(
            fingerprint,
            decision,
            patterns=load_patterns(pattern_paths),
            failures=failure_memories,
            weakness_records=load_weakness_records(weakness_paths),
            user_model=load_user_decision_model(user_model_path),
            critic_reports=load_critic_reports(critic_paths),
            skill_gap_report=skill_gap_report,
        )
    return build_plan_payload(fingerprint, scores, decision, pattern_context=pattern_context)


def build_kibo_reuse_plan_from_file(
    task_path: Path,
    *,
    repo_root: Path | None = None,
    kibo_paths: Iterable[Path] | None = None,
    sqlite_index_path: Path | None = None,
    pattern_paths: Iterable[Path] | None = None,
    failure_paths: Iterable[Path] | None = None,
    weakness_paths: Iterable[Path] | None = None,
    user_model_path: Path | None = None,
    critic_paths: Iterable[Path] | None = None,
    skill_graph_path: Path | None = None,
    limit: int = 5,
    output_path: Path | None = None,
) -> dict[str, Any]:
    plan = route_task(
        _read_task(task_path),
        repo_root=repo_root,
        kibo_paths=kibo_paths,
        sqlite_index_path=sqlite_index_path,
        pattern_paths=pattern_paths,
        failure_paths=failure_paths,
        weakness_paths=weakness_paths,
        user_model_path=user_model_path,
        critic_paths=critic_paths,
        skill_graph_path=skill_graph_path,
        limit=limit,
    )
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def build_kibo_reuse_plan(
    task: TaskFingerprint,
    *,
    repo_root: Path | None = None,
    kibo_paths: Iterable[Path] | None = None,
    sqlite_index_path: Path | None = None,
    pattern_paths: Iterable[Path] | None = None,
    failure_paths: Iterable[Path] | None = None,
    weakness_paths: Iterable[Path] | None = None,
    user_model_path: Path | None = None,
    critic_paths: Iterable[Path] | None = None,
    skill_graph_path: Path | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    return route_task(
        task,
        repo_root=repo_root,
        kibo_paths=kibo_paths,
        sqlite_index_path=sqlite_index_path,
        pattern_paths=pattern_paths,
        failure_paths=failure_paths,
        weakness_paths=weakness_paths,
        user_model_path=user_model_path,
        critic_paths=critic_paths,
        skill_graph_path=skill_graph_path,
        limit=limit,
    )
