from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import SkillEdge, SkillNode, TaskFingerprint


SKILL_GRAPH_REPORT_SCHEMA = "paideia-skill-gap-report/v1"


def load_skill_graph(path: Path | None) -> tuple[list[SkillNode], list[SkillEdge]]:
    if path is None or not path.exists():
        return ([], [])
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("skill graph file must contain a JSON object")
    nodes = [
        SkillNode.from_dict(item)
        for item in payload.get("nodes", [])
        if isinstance(item, dict)
    ]
    edges = [
        SkillEdge.from_dict(item)
        for item in payload.get("edges", [])
        if isinstance(item, dict)
    ]
    return nodes, edges


def infer_required_skills(task: TaskFingerprint) -> tuple[str, ...]:
    required = list(task.required_capabilities)
    if task.freshness_required and "fresh_external_data" not in required:
        required.append("fresh_external_data")
    if task.risk_level == "high" and "critical_review" not in required:
        required.append("critical_review")
    return tuple(dict.fromkeys(required))


def build_skill_gap_report(
    task: TaskFingerprint,
    nodes: list[SkillNode],
    *,
    mastery_threshold: float = 0.65,
) -> dict[str, Any]:
    required = infer_required_skills(task)
    by_id = {node.skill_id: node for node in nodes}
    by_name = {node.name.casefold(): node for node in nodes}
    missing: list[str] = []
    weak: list[str] = []
    covered: list[str] = []
    for skill in required:
        node = by_id.get(skill) or by_name.get(skill.casefold())
        if node is None:
            missing.append(skill)
        elif node.mastery_score < mastery_threshold:
            weak.append(skill)
        else:
            covered.append(skill)
    return {
        "schema": SKILL_GRAPH_REPORT_SCHEMA,
        "task_id": task.task_id,
        "required_skills": list(required),
        "covered_skills": covered,
        "missing_skills": missing,
        "weak_skills": weak,
        "mastery_threshold": mastery_threshold,
    }
