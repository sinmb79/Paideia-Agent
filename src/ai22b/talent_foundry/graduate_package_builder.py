from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.life_trace import read_life_trace_jsonl


GRADUATE_PACKAGE_SCHEMA = "ai22b-paideia-graduate-package/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _artifact_path(training_run: dict[str, Any], key: str) -> Path | None:
    value = training_run.get("artifacts", {}).get(key)
    return Path(value) if value else None


def _agent_resume(
    agent_manifest: dict[str, Any],
    dossier: dict[str, Any],
    growth_profile: dict[str, Any],
    genius_profile: dict[str, Any],
) -> str:
    agent = agent_manifest.get("agent", {})
    candidate = dossier.get("candidate", {})
    assessment = dossier.get("assessment_summary", {})
    growth = growth_profile.get("asymmetry_profile", {})
    genius = genius_profile.get("domain_focus", {})
    kibo_targets = genius_profile.get("cognitive_kibo_targets", {})
    unevenness = genius_profile.get("unevenness_profile", {})
    strengths = ", ".join(str(item) for item in growth.get("strength_biases", [])) or "reviewable evidence routing"
    costs = ", ".join(str(item) for item in growth.get("growth_costs", [])) or "requires owner-reviewed learning promotion"
    return "\n".join(
        [
            f"# Agent Resume: {agent.get('name') or candidate.get('name') or 'Paideia Talent'}",
            "",
            f"- Role: {agent.get('role') or candidate.get('target_role')}",
            f"- Major goal: {agent.get('major_goal') or candidate.get('major_goal')}",
            f"- Birth record: {agent.get('birth', {}).get('datetime')}",
            f"- Academic gates: {len(assessment.get('major_gates', []))}",
            f"- Graduation ready: {assessment.get('graduation_ready')}",
            f"- Strength biases: {strengths}",
            f"- Growth costs: {costs}",
            f"- Domain genius profile: {genius.get('primary_domain') or 'not generated'}",
            f"- Pattern chunk candidates: {len(kibo_targets.get('pattern_chunks', []))}",
            f"- Weakness guardrails: {len(unevenness.get('weakness_guardrails', []))}",
            "",
            "## Hiring Boundary",
            "- The connected LLM is an application engine, not the agent identity.",
            "- The agent must use local learning data, memory pack, and reviewable summaries.",
            "- Hidden chain-of-thought and public-figure impersonation remain forbidden.",
        ]
    )


def _semantic_memory(growth_profile: dict[str, Any], memory_substrate: dict[str, Any]) -> dict[str, Any]:
    concepts = []
    for node in memory_substrate.get("nodes", []):
        if node.get("layer") in {"semantic_slow_store", "source_map"}:
            concepts.append(
                {
                    "id": node.get("id"),
                    "source": node.get("source"),
                    "title": node.get("title"),
                    "summary": node.get("summary"),
                    "tags": node.get("tags", []),
                }
            )
        if len(concepts) >= 120:
            break
    return {
        "schema": "ai22b-paideia-semantic-memory-pack/v1",
        "source": "memory_substrate_and_growth_profile",
        "concepts": concepts,
        "meaning_memory": growth_profile.get("meaning_memory", {}),
        "aesthetic_memory": growth_profile.get("aesthetic_memory", {}),
    }


def _procedural_memory(
    growth_profile: dict[str, Any],
    memory_substrate: dict[str, Any],
    genius_profile: dict[str, Any],
) -> dict[str, Any]:
    operators = []
    for node in memory_substrate.get("nodes", []):
        if node.get("layer") == "procedural_operator_store":
            operators.append(
                {
                    "id": node.get("id"),
                    "source": node.get("source"),
                    "title": node.get("title"),
                    "summary": node.get("summary"),
                    "stage": node.get("stage"),
                }
            )
        if len(operators) >= 80:
            break
    return {
        "schema": "ai22b-paideia-procedural-memory-pack/v1",
        "operators": operators,
        "relationship_repair_rules": growth_profile.get("relationship_memory", {}).get("conflict_repair_rules", []),
        "emotion_recovery_rules": growth_profile.get("emotional_memory", {}).get("regulation_rules", []),
        "genius_derivation": {
            "schema": genius_profile.get("schema"),
            "profile_id": genius_profile.get("profile_id"),
            "practice_cycle": genius_profile.get("deliberate_practice_program", {}).get("cycle", []),
            "compression_rules": genius_profile.get("cognitive_kibo_targets", {}).get("compression_rules", []),
            "weakness_guardrails": genius_profile.get("unevenness_profile", {}).get("weakness_guardrails", []),
        },
        "policy": {"private_reasoning_trace": "not_stored"},
    }


def _relationship_memory(growth_profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "ai22b-paideia-relationship-memory-pack/v1",
        "relationship_memory": growth_profile.get("relationship_memory", {}),
        "emotional_memory": growth_profile.get("emotional_memory", {}),
        "policy": {
            "contains_private_family_biography": False,
            "synthetic_or_redacted_relationship_records": True,
        },
    }


def _runtime_manifest(
    *,
    training_run: dict[str, Any],
    agent_manifest: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    agent = agent_manifest.get("agent", {})
    return {
        "schema": "ai22b-paideia-graduate-runtime-manifest/v1",
        "agent": {
            "name": agent.get("name"),
            "role": agent.get("role"),
            "major_goal": agent.get("major_goal"),
        },
        "status": training_run.get("status"),
        "entrypoints": {
            "resume": "agent_resume.md",
            "transcript": "agent_transcript.json",
            "episodic_memory": "memory_pack/episodic_memory.jsonl",
            "semantic_memory": "memory_pack/semantic_memory.json",
            "procedural_memory": "memory_pack/procedural_memory.json",
            "relationship_memory": "memory_pack/relationship_memory.json",
            "genius_profile": "memory_pack/genius_profile.json",
            "onboarding_prompt": "onboarding_prompt.md",
        },
        "llm_contract": {
            "role": "application_engine_not_identity",
            "identity_source": "graduate_package_memory_pack",
            "private_reasoning_trace": "do_not_store",
        },
        "public_safety": {
            "contains_absolute_source_paths": False,
            "contains_private_runtime_chat_logs": False,
            "output_dir_name_only": output_dir.name,
        },
    }


def build_graduate_package(training_run_path: Path, output_dir: Path) -> dict[str, Any]:
    training_run = _read_json(training_run_path)
    if training_run.get("schema") != "ai-talent-training-run/v1":
        raise ValueError("Unsupported training run schema")

    output_dir.mkdir(parents=True, exist_ok=True)
    memory_pack_dir = output_dir / "memory_pack"
    memory_pack_dir.mkdir(parents=True, exist_ok=True)

    agent_manifest = _read_json(_artifact_path(training_run, "agent_manifest"))
    dossier = _read_json(_artifact_path(training_run, "release_bundle") / "hiring_dossier.json" if _artifact_path(training_run, "release_bundle") else None)
    transcript = _read_json(_artifact_path(training_run, "assessment_transcript"))
    growth_profile = _read_json(_artifact_path(training_run, "growth_profile"))
    genius_profile = _read_json(_artifact_path(training_run, "genius_profile"))
    memory_substrate = _read_json(_artifact_path(training_run, "memory_substrate"))
    life_trace_path = _artifact_path(training_run, "life_trace")
    life_trace = read_life_trace_jsonl(life_trace_path) if life_trace_path else {"events": []}

    resume_path = output_dir / "agent_resume.md"
    transcript_path = output_dir / "agent_transcript.json"
    runtime_path = output_dir / "runtime_manifest.json"
    onboarding_prompt_path = output_dir / "onboarding_prompt.md"
    episodic_path = memory_pack_dir / "episodic_memory.jsonl"
    semantic_path = memory_pack_dir / "semantic_memory.json"
    procedural_path = memory_pack_dir / "procedural_memory.json"
    relationship_path = memory_pack_dir / "relationship_memory.json"
    genius_profile_path = memory_pack_dir / "genius_profile.json"
    manifest_path = output_dir / "graduate_package_manifest.json"

    resume_path.write_text(_agent_resume(agent_manifest, dossier, growth_profile, genius_profile), encoding="utf-8")
    _write_json(transcript_path, transcript)
    episodic_lines = [json.dumps(event, ensure_ascii=False) for event in life_trace.get("events", [])]
    episodic_path.write_text("\n".join(episodic_lines) + ("\n" if episodic_lines else ""), encoding="utf-8")
    _write_json(semantic_path, _semantic_memory(growth_profile, memory_substrate))
    _write_json(procedural_path, _procedural_memory(growth_profile, memory_substrate, genius_profile))
    _write_json(relationship_path, _relationship_memory(growth_profile))
    _write_json(genius_profile_path, genius_profile or {"schema": "paideia-genius-derivation-profile/v1", "status": "not_generated"})
    _write_json(runtime_path, _runtime_manifest(training_run=training_run, agent_manifest=agent_manifest, output_dir=output_dir))
    onboarding_prompt_path.write_text(
        "\n".join(
            [
                "# Paideia Agent Onboarding Prompt",
                "",
                "Use this graduate package as the local identity and memory source.",
                "The LLM is only the application engine.",
                "Read runtime_manifest.json first, then the memory_pack files.",
                "Answer with reviewable reasoning summaries only; do not store hidden chain-of-thought.",
            ]
        ),
        encoding="utf-8",
    )

    genius_validation = (genius_profile or {}).get("validation", {})
    genius_ready = genius_validation.get("passed") is True
    readiness_checks = {
        "training_run_completed": training_run.get("status") == "employment_ready",
        "genius_profile_present": bool(genius_profile),
        "genius_profile_validation_passed": genius_ready,
        "resume_written": resume_path.exists(),
        "memory_pack_written": all(
            path.exists()
            for path in [episodic_path, semantic_path, procedural_path, relationship_path, genius_profile_path]
        ),
    }
    manifest_status = "ready" if all(readiness_checks.values()) else "review_required"
    manifest = {
        "schema": GRADUATE_PACKAGE_SCHEMA,
        "created_at_utc": _now(),
        "training_run_status": training_run.get("status"),
        "agent": agent_manifest.get("agent", {}),
        "files": {
            "agent_resume": resume_path.name,
            "agent_transcript": transcript_path.name,
            "episodic_memory": "memory_pack/episodic_memory.jsonl",
            "semantic_memory": "memory_pack/semantic_memory.json",
            "procedural_memory": "memory_pack/procedural_memory.json",
            "relationship_memory": "memory_pack/relationship_memory.json",
            "genius_profile": "memory_pack/genius_profile.json",
            "runtime_manifest": runtime_path.name,
            "onboarding_prompt": onboarding_prompt_path.name,
        },
        "policy": {
            "public_release_safe": True,
            "absolute_source_paths_exported": False,
            "private_reasoning_trace": "not_stored",
        },
        "readiness_checks": readiness_checks,
        "status": manifest_status,
    }
    _write_json(manifest_path, manifest)
    return {
        "manifest": manifest,
        "manifest_path": manifest_path,
        "output_dir": output_dir,
    }
