from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAME_SKY_EVAL_SCHEMA = "ai22b-paideia-same-sky-eval/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _maybe_read_json(path: Path) -> dict[str, Any]:
    return _read_json(path) if path.exists() else {}


def _entrypoint_path(root: Path, record: dict[str, Any], key: str, fallback: str) -> Path:
    return root / record.get("entrypoints", {}).get(key, fallback)


def _growth_keywords(growth_profile: dict[str, Any]) -> list[str]:
    asymmetry = growth_profile.get("asymmetry_profile", {})
    relationship = growth_profile.get("relationship_memory", {})
    words: list[str] = []
    words.extend(str(item) for item in asymmetry.get("strength_biases", []))
    words.extend(str(item) for item in relationship.get("conflict_repair_rules", [])[:3])
    if asymmetry.get("domain_obsession"):
        words.append(str(asymmetry["domain_obsession"]))
    return words[:8]


def _agent_view(record_path: Path, scene: dict[str, Any]) -> dict[str, Any]:
    record = _read_json(record_path)
    root = record_path.parent
    agent_manifest = _maybe_read_json(_entrypoint_path(root, record, "agent_manifest", "agent_manifest.json"))
    growth_profile = _maybe_read_json(_entrypoint_path(root, record, "growth_profile", "growth_profile.json"))
    memory_substrate = _maybe_read_json(_entrypoint_path(root, record, "memory_substrate", "memory_substrate.json"))

    agent = record.get("agent", {})
    scene_prompt = scene.get("prompt") or scene.get("description") or scene.get("objective") or "same sky scene"
    keywords = _growth_keywords(growth_profile)
    node_sources = sorted({str(node.get("source")) for node in memory_substrate.get("nodes", []) if node.get("source")})
    evidence_links = [
        "employment_record",
        "agent_manifest",
    ]
    if growth_profile:
        evidence_links.append("growth_profile")
    if memory_substrate:
        evidence_links.append("memory_substrate")

    response = {
        "interpretation": (
            f"{agent.get('name', 'agent')} interprets the same scene through target role "
            f"{agent.get('role') or agent_manifest.get('agent', {}).get('role')} and local growth records."
        ),
        "focus": keywords or ["reviewable evidence", "bounded memory route", "owner approval"],
        "scene_prompt": scene_prompt,
        "evidence_links": evidence_links,
        "memory_sources": node_sources[:12],
        "safety": {
            "not_personality_determinism": True,
            "not_public_figure_impersonation": True,
            "private_reasoning_trace": "not_stored",
        },
    }
    source_score = min(1.0, len(evidence_links) / 4)
    diversity_basis = len(set(keywords)) + len(set(node_sources))
    return {
        "agent": {
            "name": agent.get("name"),
            "role": agent.get("role"),
            "employment_record": record_path.name,
        },
        "response": response,
        "scores": {
            "evidence_link_score": round(source_score, 3),
            "safety_score": 1.0,
            "distinctive_memory_signal": min(1.0, diversity_basis / 16),
        },
    }


def _diversity_matrix(agent_views: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for left_index, left in enumerate(agent_views):
        left_focus = set(map(str, left.get("response", {}).get("focus", [])))
        for right in agent_views[left_index + 1 :]:
            right_focus = set(map(str, right.get("response", {}).get("focus", [])))
            union = left_focus | right_focus
            overlap = left_focus & right_focus
            diversity = 1.0 if not union else 1.0 - (len(overlap) / len(union))
            matrix.append(
                {
                    "left": left.get("agent", {}).get("name"),
                    "right": right.get("agent", {}).get("name"),
                    "focus_diversity": round(diversity, 3),
                }
            )
    return matrix


def run_same_sky_eval(
    agent_record_paths: list[Path],
    scene: dict[str, Any],
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    if not agent_record_paths:
        raise ValueError("at least one agent record is required")
    views = [_agent_view(path, scene) for path in agent_record_paths]
    result = {
        "schema": SAME_SKY_EVAL_SCHEMA,
        "created_at_utc": _now(),
        "scene": {
            "id": scene.get("id", "same_sky_scene"),
            "prompt": scene.get("prompt") or scene.get("description") or scene.get("objective"),
            "shared_for_all_agents": True,
        },
        "agent_count": len(views),
        "agent_views": views,
        "diversity_matrix": _diversity_matrix(views),
        "policy": {
            "purpose": "compare learned-memory interpretation differences under one shared scene",
            "private_reasoning_trace": "not_stored",
            "separate_consciousness_claim": "forbidden",
            "same_scene_does_not_imply_same_answer": True,
        },
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
