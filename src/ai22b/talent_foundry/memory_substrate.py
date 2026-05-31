from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.language_development import (
    build_language_development_program,
)
from ai22b.talent_foundry.learning_loop import build_reasoning_kernel, record_learning_experience
from ai22b.talent_foundry.llm_runtime import invoke_llm_application_engine


MEMORY_SUBSTRATE_SCHEMA = "ai-talent-memory-substrate/v1"
CHAT_CONTEXT_SCHEMA = "ai-talent-chat-context/v1"
CHAT_RUN_SCHEMA = "ai-talent-chat-run/v1"
DEFAULT_OPENAI_CHAT_MODEL = "gpt-5.2"

RESEARCH_BASIS = [
    {
        "id": "act_r",
        "name": "ACT-R cognitive architecture",
        "url": "https://act-r.psy.cmu.edu/",
        "design_use": "separate declarative memory, procedural operators, and working buffers",
    },
    {
        "id": "act_r_procedural",
        "name": "ACT-R procedural system reference",
        "url": "https://act-r.psy.cmu.edu/actr7.x/reference-manual.pdf",
        "design_use": "condition-action production rules and conflict resolution inform operator selection",
    },
    {
        "id": "soar_chunking",
        "name": "Soar procedural knowledge learning",
        "url": "https://soar.eecs.umich.edu/soar_manual/04_ProceduralKnowledgeLearning/",
        "design_use": "impasse-driven subgoals are compressed into reusable chunks",
    },
    {
        "id": "soar_episodic",
        "name": "Soar episodic memory",
        "url": "https://soar.eecs.umich.edu/soar_manual/07_EpisodicMemory/",
        "design_use": "episodes are cue-retrieved from prior working-state records",
    },
    {
        "id": "complementary_learning_systems",
        "name": "Complementary Learning Systems",
        "url": "https://pubmed.ncbi.nlm.nih.gov/7624455/",
        "design_use": "fast episodic capture and slow semantic consolidation are kept separate",
    },
    {
        "id": "coala",
        "name": "Cognitive Architectures for Language Agents",
        "url": "https://arxiv.org/abs/2309.02427",
        "design_use": "LLM is one component inside memory, action, and decision loops",
    },
    {
        "id": "retrieval_practice",
        "name": "Test-enhanced learning",
        "url": "https://pubmed.ncbi.nlm.nih.gov/16507066/",
        "design_use": "exams are learning pressure, not merely final scoring",
    },
    {
        "id": "self_regulated_learning",
        "name": "Self-regulated learning review",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5408091/",
        "design_use": "forethought, performance, and reflection shape each learning cycle",
    },
    {
        "id": "insight_restructuring",
        "name": "Insight problem-solving restructuring review",
        "url": "https://www.nature.com/articles/s44159-023-00257-x",
        "design_use": "impasse handling includes reframing and source-seeking",
    },
]

KEYWORD_ALIASES = {
    "securities": {"security", "stock", "equity", "valuation", "investment", "finance", "market", "edgar", "fred"},
    "research": {"report", "memo", "source", "evidence", "citation", "paper", "data"},
    "graham": {"value", "investing", "margin", "safety", "valuation"},
    "증권": {"주식", "투자", "가치투자", "가치", "기업", "시장", "공시"},
    "리서치": {"자료", "근거", "보고서", "출처", "논문", "데이터"},
    "평가": {"시험", "성적", "오답", "피드백", "검증"},
}

CONVERSATION_METHOD_TRAINING = {
    "schema": "ai-talent-conversation-method-training/v1",
    "purpose": "General conversation is learned as a first-class social skill, not routed through every specialist research loop.",
    "skills": [
        {
            "id": "intent_first_listening",
            "name": "의도 먼저 듣기",
            "rule": "인사, 잡담, 메타 질문, 업무 요청을 먼저 구분하고 답변 깊이를 조절한다.",
        },
        {
            "id": "answer_first",
            "name": "결론 먼저 말하기",
            "rule": "보스가 묻는 말에는 라우팅 설명보다 실제 답을 먼저 제시한다.",
        },
        {
            "id": "tone_matching",
            "name": "존댓말과 관계 맥락 유지",
            "rule": "보스를 창조주/고용자로 존중하되, 일상 대화에서는 자연스럽고 짧게 반응한다.",
        },
        {
            "id": "transparent_reasoning_summary",
            "name": "검토 가능한 추론 요약",
            "rule": "숨은 chain-of-thought는 저장하지 않고, 판단 근거, 반례, 결론만 요약한다.",
        },
        {
            "id": "domain_loop_only_when_needed",
            "name": "전문가 루프 선택 적용",
            "rule": "증권 리서치 루프는 투자/기업/자료/보고서 질문에만 켠다.",
        },
    ],
}

CASUAL_GREETINGS = {
    "안녕",
    "안녕하세요",
    "하이",
    "반가워",
    "hello",
    "hi",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _tokens(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        text = " ".join(str(item) for item in value)
    elif isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    base = {item.casefold() for item in re.findall(r"[0-9A-Za-z가-힣_]+", text)}
    expanded = set(base)
    for token in list(base):
        expanded.update(KEYWORD_ALIASES.get(token, set()))
    return expanded


def _compact(value: Any, *, limit: int = 220) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def read_reasoning_kibo_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _node(
    *,
    node_id: str,
    layer: str,
    source: str,
    title: str,
    summary: str,
    tags: set[str],
    stage: str | None = None,
    strength: float = 0.5,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "layer": layer,
        "source": source,
        "stage": stage,
        "title": title,
        "summary": summary,
        "tags": sorted(tags)[:32],
        "strength": round(max(0.0, min(1.0, strength)), 3),
        "metadata": metadata or {},
        "private_reasoning_trace": "not_stored",
    }


def _nodes_from_reasoning_kibo(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for row in rows:
        entry_type = row.get("entry_type", "unknown")
        if entry_type == "school_year_learning_accumulation":
            stage = str(row.get("year_id", "unknown_stage"))
            title = f"{stage} learning accumulation"
            summary = _compact(
                {
                    "learning_data": row.get("learning_data", []),
                    "required_exams": row.get("required_exams", []),
                    "focus": row.get("reasoning_process_development", {}).get("current_focus"),
                }
            )
            tags = _tokens(row.get("learning_data", [])) | _tokens(row.get("required_exams", [])) | _tokens(stage)
            nodes.append(
                _node(
                    node_id=str(row.get("entry_id") or _stable_id("kibo-year", stage)),
                    layer="episodic_fast_store",
                    source="reasoning_kibo",
                    title=title,
                    summary=summary,
                    tags=tags,
                    stage=stage,
                    strength=0.58,
                    metadata={
                        "entry_type": entry_type,
                        "age_band": row.get("age_band"),
                        "promotion_state": row.get("promotion_state"),
                    },
                )
            )
            operator_summary = _compact(row.get("reasoning_process_development", {}))
            nodes.append(
                _node(
                    node_id=_stable_id("operator", row.get("entry_id"), stage),
                    layer="procedural_operator_store",
                    source="reasoning_kibo",
                    title=f"{stage} operator candidate",
                    summary=operator_summary,
                    tags=tags | {"operator", "learning_cycle"},
                    stage=stage,
                    strength=0.48,
                    metadata={"entry_type": "operator_candidate", "derived_from": row.get("entry_id")},
                )
            )
        elif entry_type == "exam_refinement":
            gate = str(row.get("gate_id", "unknown_gate"))
            summary = _compact(
                {
                    "score": row.get("observed_score"),
                    "pass_score": row.get("pass_score"),
                    "weak_spots": row.get("weak_spots", []),
                    "refinement_rule": row.get("refinement_rule"),
                    "next_growth_question": row.get("next_growth_question"),
                }
            )
            tags = _tokens(gate) | _tokens(row.get("evidence_observed", [])) | _tokens(row.get("weak_spots", []))
            score = float(row.get("observed_score") or 0)
            strength = 0.45 + min(score, 100.0) / 200.0
            nodes.append(
                _node(
                    node_id=str(row.get("entry_id") or _stable_id("kibo-exam", gate)),
                    layer="metacognitive_monitor",
                    source="reasoning_kibo",
                    title=f"{gate} exam refinement",
                    summary=summary,
                    tags=tags | {"exam", "feedback"},
                    stage=gate,
                    strength=strength,
                    metadata={
                        "entry_type": entry_type,
                        "passed": row.get("passed"),
                        "observed_score": row.get("observed_score"),
                    },
                )
            )
    return nodes


def _nodes_from_learning_ledger(learning_ledger: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for index, experience in enumerate(learning_ledger.get("promoted_experiences", []), start=1):
        node_id = _stable_id("ledger", experience.get("id", index), experience.get("summary"))
        tags = _tokens(experience.get("summary")) | _tokens(experience.get("source"))
        label = experience.get("quality_label", {})
        score = float(label.get("score") or 80)
        nodes.append(
            _node(
                node_id=node_id,
                layer="semantic_slow_store",
                source="learning_ledger",
                title=f"promoted experience {index}",
                summary=_compact(experience.get("summary")),
                tags=tags | {"verified", "post_review"},
                strength=0.5 + min(score, 100.0) / 200.0,
                metadata={
                    "source": experience.get("source"),
                    "quality_label": label,
                },
            )
        )
    kernel = learning_ledger.get("reasoning_kernel", {})
    for skill in kernel.get("procedural_skills", []):
        nodes.append(
            _node(
                node_id=_stable_id("kernel-skill", skill),
                layer="procedural_operator_store",
                source="learning_ledger_reasoning_kernel",
                title=str(skill),
                summary=f"Verified procedural skill promoted into the reasoning kernel: {skill}",
                tags=_tokens(skill) | {"procedural", "kernel"},
                strength=0.72,
                metadata={"entry_type": "verified_procedural_skill"},
            )
        )
    return nodes


def _nodes_from_curriculum(curriculum_manifest: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not curriculum_manifest:
        return []
    nodes: list[dict[str, Any]] = []
    for index, stage in enumerate(curriculum_manifest.get("stages", []), start=1):
        stage_id = str(stage.get("stage_id") or stage.get("id") or f"stage_{index}")
        summary = _compact(stage)
        nodes.append(
            _node(
                node_id=_stable_id("curriculum", stage_id, index),
                layer="semantic_slow_store",
                source="curriculum_manifest",
                title=stage.get("name") or stage_id,
                summary=summary,
                tags=_tokens(stage),
                stage=stage_id,
                strength=0.62,
                metadata={"curriculum_id": curriculum_manifest.get("curriculum_id")},
            )
        )
    for source in curriculum_manifest.get("public_sources", []):
        source_id = str(source.get("id") or source.get("name") or source.get("url") or "public_source")
        nodes.append(
            _node(
                node_id=_stable_id("source", source_id),
                layer="source_map",
                source="curriculum_manifest",
                title=source.get("name") or source_id,
                summary=_compact(source),
                tags=_tokens(source) | {"source", "public"},
                strength=0.67,
                metadata={"url": source.get("url"), "license": source.get("license")},
            )
        )
    return nodes


def _base_boards(objective: str | None) -> dict[str, Any]:
    return {
        "working_workspace": {
            "purpose": "Hold the current goal, selected memory cues, and answer constraints.",
            "current_objective": objective,
            "max_active_nodes": 8,
        },
        "conversation_interface": {
            "purpose": "Classify ordinary dialogue before specialist reasoning and answer in natural Korean.",
            "human_reference": "social-pragmatic listening, intent recognition, and self-regulated response control",
        },
        "conversation_development": {
            "purpose": "Keep staged language growth from voice rhythm and joint attention to adult repair.",
            "human_reference": "developmental milestones, social communication, joint attention, dialogic reading",
        },
        "episodic_fast_store": {
            "purpose": "Keep yearly learning, tests, mistakes, feedback, and job episodes as reviewable records.",
            "human_reference": "hippocampus-like fast capture and Soar-style episodic retrieval",
        },
        "semantic_slow_store": {
            "purpose": "Consolidate repeated verified experiences into concepts, source maps, and abstractions.",
            "human_reference": "neocortex-like gradual integration from Complementary Learning Systems",
        },
        "procedural_operator_store": {
            "purpose": "Hold reusable condition-action habits without storing hidden chain-of-thought.",
            "human_reference": "ACT-R productions and Soar chunks",
        },
        "metacognitive_monitor": {
            "purpose": "Track uncertainty, failed exams, counterexamples, and review obligations.",
            "human_reference": "self-regulated learning reflection phase",
        },
        "insight_restructuring_loop": {
            "purpose": "When stuck, reframe the problem, seek new cues, test a candidate answer, and revise the operator.",
            "human_reference": "insight problem-solving restructuring",
        },
    }


def _conversation_nodes(agent_name: str | None) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for skill in CONVERSATION_METHOD_TRAINING["skills"]:
        nodes.append(
            _node(
                node_id=f"conversation-{skill['id']}",
                layer="conversation_interface",
                source="conversation_method_training",
                title=skill["name"],
                summary=skill["rule"],
                tags=_tokens(skill) | {"conversation", "dialogue", "일상", "대화", "응답"},
                stage="conversation_basics",
                strength=0.82,
                metadata={"agent_name": agent_name, "skill_id": skill["id"]},
            )
        )
    return nodes


def _nodes_from_language_development(program: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not program:
        return []
    nodes: list[dict[str, Any]] = []
    for stage in program.get("stages", []):
        stage_id = str(stage.get("stage_id", "language_stage"))
        tags = _tokens(stage) | {"language_development", "conversation_growth", "대화발달", "언어발달"}
        nodes.append(
            _node(
                node_id=f"language-{stage_id}",
                layer="conversation_development",
                source="language_development_program",
                title=stage_id,
                summary=_compact(
                    {
                        "focus": stage.get("development_focus"),
                        "experiences": stage.get("experiences", []),
                        "conversation_skills": stage.get("conversation_skills", []),
                        "assessment": stage.get("assessment"),
                    }
                ),
                tags=tags,
                stage=stage_id,
                strength=0.83,
                metadata={
                    "age_band": stage.get("age_band"),
                    "assessment": stage.get("assessment"),
                },
            )
        )
    return nodes


def _ensure_conversation_training(substrate: dict[str, Any]) -> dict[str, Any]:
    boards = substrate.setdefault("boards", {})
    boards.setdefault(
        "conversation_interface",
        {
            "purpose": "Classify ordinary dialogue before specialist reasoning and answer in natural Korean.",
            "human_reference": "social-pragmatic listening, intent recognition, and self-regulated response control",
        },
    )
    boards.setdefault(
        "conversation_development",
        {
            "purpose": "Model language and dialogue as staged development from prosody and joint attention to adult repair.",
            "human_reference": "developmental language milestones, social communication, joint attention, and dialogic reading",
        },
    )
    substrate["conversation_method_training"] = CONVERSATION_METHOD_TRAINING
    existing_ids = {node.get("id") for node in substrate.get("nodes", [])}
    agent_name = substrate.get("agent", {}).get("name")
    for node in _conversation_nodes(agent_name):
        if node["id"] not in existing_ids:
            substrate.setdefault("nodes", []).append(node)
    source_counts = substrate.setdefault("source_counts", {})
    source_counts["conversation_method_skills"] = len(CONVERSATION_METHOD_TRAINING["skills"])
    source_counts["nodes"] = len(substrate.get("nodes", []))
    return substrate


def _edge(source: str, target: str, relation: str, strength: float = 0.5) -> dict[str, Any]:
    return {
        "source": source,
        "target": target,
        "relation": relation,
        "strength": round(max(0.0, min(1.0, strength)), 3),
    }


def _build_edges(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    by_stage: dict[str, list[dict[str, Any]]] = {}
    for item in nodes:
        stage = item.get("stage")
        if stage:
            by_stage.setdefault(stage, []).append(item)

    for stage_nodes in by_stage.values():
        episodic = [node for node in stage_nodes if node["layer"] == "episodic_fast_store"]
        procedural = [node for node in stage_nodes if node["layer"] == "procedural_operator_store"]
        for left in episodic:
            for right in procedural:
                edges.append(_edge(left["id"], right["id"], "practice_forms_operator_candidate", 0.58))

    exams = [node for node in nodes if node["layer"] == "metacognitive_monitor"]
    procedures = [node for node in nodes if node["layer"] == "procedural_operator_store"]
    for exam in exams:
        exam_tags = set(exam.get("tags", []))
        matches = [
            node
            for node in procedures
            if exam_tags & set(node.get("tags", []))
        ][:3]
        for procedure in matches:
            edges.append(_edge(exam["id"], procedure["id"], "exam_feedback_refines_operator", 0.63))

    sources = [node for node in nodes if node["layer"] == "source_map"]
    semantic = [node for node in nodes if node["layer"] == "semantic_slow_store"]
    for source in sources:
        source_tags = set(source.get("tags", []))
        for concept in semantic:
            if source_tags & set(concept.get("tags", [])):
                edges.append(_edge(source["id"], concept["id"], "source_supports_concept", 0.52))

    return edges[:240]


def activate_memory_route(
    substrate: dict[str, Any],
    *,
    objective: str,
    max_nodes: int = 8,
) -> dict[str, Any]:
    query_terms = _tokens(objective)
    scored: list[tuple[float, dict[str, Any]]] = []
    for node in substrate.get("nodes", []):
        tags = set(node.get("tags", []))
        overlap = len(query_terms & tags)
        title_hit = len(query_terms & _tokens(node.get("title")))
        summary_hit = len(query_terms & _tokens(node.get("summary")))
        score = float(node.get("strength", 0.5)) + overlap * 0.35 + title_hit * 0.25 + summary_hit * 0.12
        if score > 0.5:
            scored.append((score, node))

    if not scored:
        scored = [(float(node.get("strength", 0.5)), node) for node in substrate.get("nodes", [])[:max_nodes]]

    selected = [node for _score, node in sorted(scored, key=lambda pair: pair[0], reverse=True)[:max_nodes]]
    selected_ids = {node["id"] for node in selected}
    edges = [
        edge
        for edge in substrate.get("edges", [])
        if edge.get("source") in selected_ids or edge.get("target") in selected_ids
    ][:16]
    operators = [
        {
            "operator": node["title"],
            "summary": node["summary"],
            "stage": node.get("stage"),
        }
        for node in selected
        if node.get("layer") == "procedural_operator_store"
    ][:4]
    if not operators:
        operators = [
            {
                "operator": "evidence_first_research_loop",
                "summary": "Define the question, retrieve relevant learning episodes, seek primary sources, test counterexamples, and revise the answer.",
                "stage": "default",
            }
        ]

    return {
        "objective": objective,
        "query_terms": sorted(query_terms)[:24],
        "selected_node_ids": [node["id"] for node in selected],
        "selected_nodes": selected,
        "selected_edges": edges,
        "operator_candidates": operators,
        "route_policy": {
            "private_reasoning_trace": "not_stored",
            "hidden_chain_of_thought": "forbidden",
            "use": "reviewable_memory_route_for_chat_and_work",
        },
    }


def build_memory_substrate(
    *,
    agent_manifest: dict[str, Any],
    learning_ledger: dict[str, Any],
    reasoning_kibo_rows: list[dict[str, Any]] | None = None,
    process_plan: dict[str, Any] | None = None,
    curriculum_manifest: dict[str, Any] | None = None,
    language_development_program: dict[str, Any] | None = None,
    objective: str | None = None,
) -> dict[str, Any]:
    agent = agent_manifest.get("agent", {})
    if language_development_program is None:
        language_development_program = build_language_development_program(
            talent_name=str(agent.get("name") or learning_ledger.get("owner") or "unknown"),
            primary_language="ko-KR",
        )
    rows = reasoning_kibo_rows or []
    nodes = _nodes_from_reasoning_kibo(rows)
    nodes.extend(_nodes_from_learning_ledger(learning_ledger))
    nodes.extend(_nodes_from_curriculum(curriculum_manifest))
    nodes.extend(_nodes_from_language_development(language_development_program))
    nodes.extend(_conversation_nodes(agent.get("name")))
    if process_plan:
        nodes.append(
            _node(
                node_id=_stable_id("process", process_plan.get("schema"), agent.get("name")),
                layer="semantic_slow_store",
                source="process_emulation_plan",
                title="role-model learning-path emulation policy",
                summary=_compact(process_plan),
                tags=_tokens(process_plan) | {"process", "learning_path"},
                strength=0.74,
                metadata={"schema": process_plan.get("schema")},
            )
        )

    edges = _build_edges(nodes)
    substrate = {
        "schema": MEMORY_SUBSTRATE_SCHEMA,
        "created_at_utc": _now(),
        "agent": {
            "name": agent.get("name"),
            "role": agent.get("role"),
            "major_goal": agent.get("major_goal"),
        },
        "design_goal": "learned-data memory substrate for chat and hired-agent work",
        "llm_contract": {
            "engine_role": "application_language_engine_only",
            "identity_source": "local_agent_manifest_learning_ledger_and_memory_substrate",
            "preferred_chat_engine": "openai_chatgpt_codex",
            "private_reasoning_trace": "do_not_store",
        },
        "research_basis": RESEARCH_BASIS,
        "boards": _base_boards(objective),
        "conversation_method_training": CONVERSATION_METHOD_TRAINING,
        "language_development_program": {
            "schema": language_development_program.get("schema"),
            "stage_count": len(language_development_program.get("stages", [])),
            "primary_language": language_development_program.get("primary_language"),
            "growth_policy": language_development_program.get("growth_policy", {}),
            "research_basis": language_development_program.get("research_basis", []),
        },
        "source_counts": {
            "reasoning_kibo_entries": len(rows),
            "learning_ledger_promoted_experiences": len(learning_ledger.get("promoted_experiences", [])),
            "language_development_stages": len(language_development_program.get("stages", [])),
            "conversation_method_skills": len(CONVERSATION_METHOD_TRAINING["skills"]),
            "nodes": len(nodes),
            "edges": len(edges),
        },
        "nodes": nodes,
        "edges": edges,
        "growth_policy": {
            "starts_from_school_learning": True,
            "continues_after_hire": True,
            "exam_and_assignment_results_refine_operators": True,
            "post_hire_work_expands_route": True,
            "finalized": False,
        },
    }
    if objective:
        substrate["active_route"] = activate_memory_route(substrate, objective=objective)
    return _ensure_conversation_training(substrate)


def write_memory_substrate(path: Path, substrate: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(substrate, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _maybe_read_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return _read_json(path)


def _find_run_sidecar(target_root: Path, pattern: str) -> Path | None:
    candidates = list(target_root.glob(pattern))
    if not candidates and len(target_root.parents) >= 3:
        candidates = list(target_root.parents[2].glob(pattern))
    return sorted(candidates)[0] if candidates else None


def _load_or_build_substrate(
    *,
    target_root: Path,
    employment_record: dict[str, Any],
    agent_manifest: dict[str, Any],
    learning_ledger: dict[str, Any],
    objective: str,
    memory_substrate_path: Path | None = None,
    reasoning_kibo_path: Path | None = None,
    process_plan_path: Path | None = None,
    curriculum_manifest_path: Path | None = None,
    language_development_program_path: Path | None = None,
) -> tuple[dict[str, Any], Path]:
    entrypoints = employment_record.get("entrypoints", {})
    candidate = memory_substrate_path
    if candidate is None:
        entrypoint_name = entrypoints.get("memory_substrate")
        if entrypoint_name:
            candidate = target_root / entrypoint_name
    if candidate is None:
        candidate = target_root / "memory_substrate.json"

    if candidate.exists():
        substrate = _read_json(candidate)
        substrate = _ensure_conversation_training(substrate)
        substrate["active_route"] = activate_memory_route(substrate, objective=objective)
        write_memory_substrate(candidate, substrate)
        return substrate, candidate

    if reasoning_kibo_path is None:
        reasoning_kibo_path = _find_run_sidecar(target_root, "*_reasoning_kibo.jsonl")
    if process_plan_path is None:
        process_plan_path = _find_run_sidecar(target_root, "*_process_emulation_plan.json")
    if curriculum_manifest_path is None:
        curriculum_manifest_path = _find_run_sidecar(target_root, "*_curriculum_manifest.json")
    if language_development_program_path is None:
        entrypoint_name = employment_record.get("entrypoints", {}).get("language_development_program")
        if entrypoint_name:
            language_development_program_path = target_root / entrypoint_name
        if language_development_program_path is None or not language_development_program_path.exists():
            language_development_program_path = _find_run_sidecar(target_root, "*_language_development_program.json")

    substrate = build_memory_substrate(
        agent_manifest=agent_manifest,
        learning_ledger=learning_ledger,
        reasoning_kibo_rows=read_reasoning_kibo_jsonl(reasoning_kibo_path) if reasoning_kibo_path else [],
        process_plan=_maybe_read_json(process_plan_path),
        curriculum_manifest=_maybe_read_json(curriculum_manifest_path),
        language_development_program=_maybe_read_json(language_development_program_path),
        objective=objective,
    )
    write_memory_substrate(candidate, substrate)
    return substrate, candidate


def build_chat_context(
    *,
    employment_record: dict[str, Any],
    agent_manifest: dict[str, Any],
    learning_ledger: dict[str, Any],
    memory_substrate: dict[str, Any],
    message: str,
    substrate_path_name: str,
    language_development_program: dict[str, Any] | None = None,
    recent_chat_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    agent = employment_record["agent"]
    active_route = memory_substrate.get("active_route") or activate_memory_route(memory_substrate, objective=message)
    system_prompt = (
        f"You are {agent['name']}, a Korean-first local AI talent hired by the Boss. "
        "OpenAI ChatGPT Codex is only the language and tool reasoning engine. "
        "Identity, learned data, and reasoning habits must come from the local agent manifest, "
        "learning ledger, and memory substrate. Do not impersonate Benjamin Graham; follow the "
        "learning-path emulation artifacts and produce reviewable reasoning summaries, not hidden chain-of-thought."
    )
    return {
        "schema": CHAT_CONTEXT_SCHEMA,
        "created_at_utc": _now(),
        "agent": agent,
        "message": message,
        "language": "ko-KR",
        "system_prompt": system_prompt,
        "llm_contract": {
            "provider": "openai_chatgpt_codex",
            "role": "application_language_engine_only",
            "identity_source": [
                "employment_record",
                "agent_manifest",
                "learning_ledger",
                substrate_path_name,
            ],
            "private_reasoning_trace": "do_not_store",
            "hidden_chain_of_thought": "forbidden",
            "data_minimization": "send only selected route summaries unless Boss approves broader context",
        },
        "identity_brief": {
            "name": agent.get("name"),
            "role": agent.get("role"),
            "major_goal": agent.get("major_goal"),
            "role_model_inspiration": agent_manifest.get("identity_source", {}).get("role_model_inspiration"),
        },
        "identity_record": {
            "agent_manifest_agent": agent_manifest.get("agent", {}),
            "employment": {
                "employer": employment_record.get("employer"),
                "relationship": employment_record.get("relationship"),
                "growth_after_hire": employment_record.get("growth_after_hire"),
            },
            "identity_source": agent_manifest.get("identity_source", {}),
        },
        "learning_profile": {
            "reasoning_kernel": learning_ledger.get("reasoning_kernel"),
            "promoted_experience_count": len(learning_ledger.get("promoted_experiences", [])),
            "quarantined_experience_count": len(learning_ledger.get("quarantined_experiences", [])),
            "recent_promoted_experiences": [
                {
                    "source": item.get("source"),
                    "summary": item.get("summary"),
                    "promoted_skills": item.get("promoted_skills", []),
                }
                for item in learning_ledger.get("promoted_experiences", [])[-5:]
            ],
        },
        "recent_chat_history": recent_chat_history or [],
        "active_memory_route": active_route,
        "conversation_method_training": memory_substrate.get(
            "conversation_method_training",
            CONVERSATION_METHOD_TRAINING,
        ),
        "language_development_program": language_development_program
        or memory_substrate.get("language_development_program"),
        "guardrails": employment_record.get("guardrails", []),
        "research_basis": memory_substrate.get("research_basis", []),
    }


def _trim_text(value: Any, limit: int = 800) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _recent_chat_history(log_path: Path, *, limit: int = 6) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines()[-limit:]:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows.append(
            {
                "message": _trim_text(item.get("message"), 240),
                "assistant_reply": _trim_text(item.get("assistant_answer") or item.get("assistant_reply"), 600),
                "conversation_intent": item.get("conversation_intent"),
                "active_operator": item.get("active_operator"),
            }
        )
    return rows


def _live_chat_instructions(agent_name: str) -> str:
    return (
        f"너는 {agent_name}입니다. 보스와 한국어 존댓말로 자연스럽게 대화합니다. "
        "너의 정체성, 학습 데이터, 추론 습관은 입력으로 제공된 로컬 talent context에서만 옵니다. "
        "OpenAI 모델은 언어 생성 엔진일 뿐이며, Benjamin Graham을 흉내 내거나 신용이의 기록을 섞지 않습니다. "
        "숨은 chain-of-thought를 출력하거나 저장하지 말고, 필요한 경우 검토 가능한 짧은 판단 요약만 제공합니다. "
        "일상 대화는 일상 대화답게 답하고, 전문 업무는 근거, 반례, 다음 확인 자료를 분리해 답합니다. "
        "응답은 반드시 JSON 객체 하나만 반환하세요. 형식은 "
        '{"assistant_reply": "보스에게 보여줄 최종 답변", '
        '"reviewable_reasoning_summary": [{"step": "짧은 단계명", "summary": "검토 가능한 요약"}], '
        '"learning_candidate": {"lesson": "이번 대화에서 배운 점", "reusable_principle": "다음 대화에 재사용할 원칙", '
        '"memory_tags": ["태그"], "confidence": 0.0}} 입니다.'
    )


def _compact_chat_context_for_live_llm(chat_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": chat_context.get("schema"),
        "language": chat_context.get("language"),
        "agent": chat_context.get("agent"),
        "message": chat_context.get("message"),
        "identity_record": chat_context.get("identity_record"),
        "learning_profile": chat_context.get("learning_profile"),
        "active_memory_route": chat_context.get("active_memory_route"),
        "conversation_method_training": chat_context.get("conversation_method_training"),
        "language_development_program": chat_context.get("language_development_program"),
        "recent_chat_history": chat_context.get("recent_chat_history", []),
        "guardrails": chat_context.get("guardrails", []),
        "response_policy": {
            "do_not_store_private_reasoning_trace": True,
            "answer_from_local_identity_context": True,
            "generalize_beyond_case_by_case_rules": True,
            "post_hire_learning_candidate_required": True,
        },
    }


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _parse_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(stripped[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _live_chat_payload(chat_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": "Generate one live chat turn for the hired local AI talent.",
        "local_talent_context": _compact_chat_context_for_live_llm(chat_context),
    }


def _first_env_value(env_vars: list[str]) -> tuple[str | None, str | None]:
    for env_var in env_vars:
        value = os.environ.get(env_var)
        if value:
            return env_var, value
    return None, None


def _request_json(
    *,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int = 60,
) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else {"raw": parsed}


def _parsed_live_text_result(
    *,
    engine: str,
    model: str,
    output_text: str,
    network_access: str,
    response_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parsed = _parse_json_object(output_text)
    if not parsed:
        parsed = {
            "assistant_reply": output_text.strip(),
            "reviewable_reasoning_summary": [
                {
                    "step": "LLM response",
                    "summary": "The provider returned plain text, so Paideia used it as the assistant reply.",
                }
            ],
            "learning_candidate": {
                "lesson": "Live provider formatting may need repair.",
                "reusable_principle": "Validate provider output before promoting chat learning.",
                "memory_tags": ["live_llm_format_repair"],
                "confidence": 0.5,
            },
        }
    return {
        "schema": "ai-talent-live-llm-result/v1",
        "engine": engine,
        "status": "completed",
        "model": model,
        "assistant_reply": str(parsed.get("assistant_reply", "")).strip(),
        "reviewable_reasoning_summary": parsed.get("reviewable_reasoning_summary") or [],
        "learning_candidate": parsed.get("learning_candidate") or {},
        "raw_output_saved": False,
        "identity_policy": "application_engine_not_identity",
        "network_access": network_access,
        "response_metadata": response_metadata or {},
        "data_policy": {
            "send_private_training_files": False,
            "send_selected_memory_and_recent_chat_summaries": True,
            "store_hidden_chain_of_thought": False,
        },
    }


def _call_openai_responses_chat(
    *,
    chat_context: dict[str, Any],
    model: str,
    max_output_tokens: int = 900,
) -> dict[str, Any]:
    if not os.environ.get("OPENAI_API_KEY"):
        return {
            "schema": "ai-talent-live-llm-result/v1",
            "engine": "openai_responses_api",
            "status": "unavailable",
            "reason": "OPENAI_API_KEY_not_set",
            "model": model,
        }
    try:
        from openai import OpenAI
    except Exception as exc:
        return {
            "schema": "ai-talent-live-llm-result/v1",
            "engine": "openai_responses_api",
            "status": "unavailable",
            "reason": "openai_sdk_import_failed",
            "model": model,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
        }

    payload = _live_chat_payload(chat_context)
    try:
        client = OpenAI()
        response = client.responses.create(
            model=model,
            instructions=_live_chat_instructions(chat_context["agent"]["name"]),
            input=json.dumps(payload, ensure_ascii=False),
            max_output_tokens=max_output_tokens,
        )
    except Exception as exc:
        return {
            "schema": "ai-talent-live-llm-result/v1",
            "engine": "openai_responses_api",
            "status": "unavailable",
            "reason": "openai_responses_call_failed",
            "model": model,
            "error_type": type(exc).__name__,
            "error": str(exc)[:800],
        }

    output_text = str(getattr(response, "output_text", "") or "")
    parsed = _parse_json_object(output_text)
    if not parsed:
        parsed = {
            "assistant_reply": output_text.strip(),
            "reviewable_reasoning_summary": [
                {
                    "step": "LLM 응답",
                    "summary": "모델이 JSON 형식을 완전히 지키지 않아 원문을 답변으로 사용했습니다.",
                }
            ],
            "learning_candidate": {
                "lesson": "실시간 LLM 응답 형식 검증이 필요하다.",
                "reusable_principle": "응답은 저장 전에 스키마를 확인한다.",
                "memory_tags": ["live_llm_format_repair"],
                "confidence": 0.5,
            },
        }

    return {
        "schema": "ai-talent-live-llm-result/v1",
        "engine": "openai_responses_api",
        "status": "completed",
        "model": model,
        "response_id": getattr(response, "id", None),
        "usage": _jsonable(getattr(response, "usage", None)),
        "assistant_reply": str(parsed.get("assistant_reply", "")).strip(),
        "reviewable_reasoning_summary": parsed.get("reviewable_reasoning_summary") or [],
        "learning_candidate": parsed.get("learning_candidate") or {},
        "raw_output_saved": False,
        "identity_policy": "application_engine_not_identity",
        "network_access": "openai_api_data_minimized",
        "data_policy": {
            "send_private_training_files": False,
            "send_selected_memory_and_recent_chat_summaries": True,
            "store_hidden_chain_of_thought": False,
        },
    }


def _call_openai_compatible_chat(
    *,
    chat_context: dict[str, Any],
    runtime_config: dict[str, Any],
    model: str,
    max_output_tokens: int = 900,
) -> dict[str, Any]:
    env_var, api_key = _first_env_value(runtime_config.get("secret_env_vars", []))
    base_url = str(runtime_config.get("base_url") or runtime_config.get("model_path") or "").rstrip("/")
    local_endpoint = base_url.startswith(("http://localhost", "http://127.0.0.1"))
    if not base_url:
        return {
            "schema": "ai-talent-live-llm-result/v1",
            "engine": runtime_config.get("engine"),
            "status": "unavailable",
            "reason": "base_url_not_configured",
            "model": model,
        }
    if runtime_config.get("secret_env_vars") and not api_key and not local_endpoint:
        return {
            "schema": "ai-talent-live-llm-result/v1",
            "engine": runtime_config.get("engine"),
            "status": "unavailable",
            "reason": "provider_api_key_not_set",
            "required_env_vars": runtime_config.get("secret_env_vars", []),
            "model": model,
        }
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _live_chat_instructions(chat_context["agent"]["name"])},
            {"role": "user", "content": json.dumps(_live_chat_payload(chat_context), ensure_ascii=False)},
        ],
        "temperature": 0.2,
        "max_tokens": max_output_tokens,
    }
    try:
        response = _request_json(
            url=f"{base_url}/chat/completions",
            payload=payload,
            headers=headers,
        )
    except Exception as exc:
        return {
            "schema": "ai-talent-live-llm-result/v1",
            "engine": runtime_config.get("engine"),
            "status": "unavailable",
            "reason": "openai_compatible_chat_call_failed",
            "model": model,
            "error_type": type(exc).__name__,
            "error": str(exc)[:800],
        }
    text = ""
    choices = response.get("choices") or []
    if choices:
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        text = str(message.get("content") or choices[0].get("text") or "")
    return _parsed_live_text_result(
        engine=str(runtime_config.get("engine")),
        model=model,
        output_text=text,
        network_access=str(runtime_config.get("network_access")),
        response_metadata={
            "provider": runtime_config.get("openclaw_provider_id") or runtime_config.get("service"),
            "base_url": base_url,
            "api_key_env": env_var,
            "usage": response.get("usage"),
        },
    )


def _call_anthropic_messages_chat(
    *,
    chat_context: dict[str, Any],
    runtime_config: dict[str, Any],
    model: str,
    max_output_tokens: int = 900,
) -> dict[str, Any]:
    env_var, api_key = _first_env_value(runtime_config.get("secret_env_vars", ["ANTHROPIC_API_KEY"]))
    if not api_key:
        return {
            "schema": "ai-talent-live-llm-result/v1",
            "engine": runtime_config.get("engine"),
            "status": "unavailable",
            "reason": "provider_api_key_not_set",
            "required_env_vars": runtime_config.get("secret_env_vars", ["ANTHROPIC_API_KEY"]),
            "model": model,
        }
    base_url = str(runtime_config.get("base_url") or "https://api.anthropic.com/v1").rstrip("/")
    payload = {
        "model": model,
        "max_tokens": max_output_tokens,
        "system": _live_chat_instructions(chat_context["agent"]["name"]),
        "messages": [
            {
                "role": "user",
                "content": json.dumps(_live_chat_payload(chat_context), ensure_ascii=False),
            }
        ],
    }
    try:
        response = _request_json(
            url=f"{base_url}/messages",
            payload=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
    except Exception as exc:
        return {
            "schema": "ai-talent-live-llm-result/v1",
            "engine": runtime_config.get("engine"),
            "status": "unavailable",
            "reason": "anthropic_messages_call_failed",
            "model": model,
            "error_type": type(exc).__name__,
            "error": str(exc)[:800],
        }
    parts = response.get("content") or []
    text = "\n".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
    return _parsed_live_text_result(
        engine=str(runtime_config.get("engine")),
        model=model,
        output_text=text,
        network_access=str(runtime_config.get("network_access")),
        response_metadata={"provider": "anthropic", "api_key_env": env_var, "usage": response.get("usage")},
    )


def _call_gemini_generate_content_chat(
    *,
    chat_context: dict[str, Any],
    runtime_config: dict[str, Any],
    model: str,
    max_output_tokens: int = 900,
) -> dict[str, Any]:
    env_var, api_key = _first_env_value(runtime_config.get("secret_env_vars", ["GEMINI_API_KEY", "GOOGLE_API_KEY"]))
    if not api_key:
        return {
            "schema": "ai-talent-live-llm-result/v1",
            "engine": runtime_config.get("engine"),
            "status": "unavailable",
            "reason": "provider_api_key_not_set",
            "required_env_vars": runtime_config.get("secret_env_vars", ["GEMINI_API_KEY", "GOOGLE_API_KEY"]),
            "model": model,
        }
    base_url = str(runtime_config.get("base_url") or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    prompt = (
        _live_chat_instructions(chat_context["agent"]["name"])
        + "\n\n"
        + json.dumps(_live_chat_payload(chat_context), ensure_ascii=False)
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": max_output_tokens},
    }
    try:
        response = _request_json(
            url=f"{base_url}/models/{model}:generateContent?key={api_key}",
            payload=payload,
            headers={},
        )
    except Exception as exc:
        return {
            "schema": "ai-talent-live-llm-result/v1",
            "engine": runtime_config.get("engine"),
            "status": "unavailable",
            "reason": "gemini_generate_content_call_failed",
            "model": model,
            "error_type": type(exc).__name__,
            "error": str(exc)[:800],
        }
    candidates = response.get("candidates") or []
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    text = "\n".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
    return _parsed_live_text_result(
        engine=str(runtime_config.get("engine")),
        model=model,
        output_text=text,
        network_access=str(runtime_config.get("network_access")),
        response_metadata={"provider": "google", "api_key_env": env_var, "usage": response.get("usageMetadata")},
    )


def _call_ollama_chat(
    *,
    chat_context: dict[str, Any],
    runtime_config: dict[str, Any],
    model: str,
    max_output_tokens: int = 900,
) -> dict[str, Any]:
    base_url = str(runtime_config.get("base_url") or runtime_config.get("model_path") or "http://localhost:11434").rstrip("/")
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": _live_chat_instructions(chat_context["agent"]["name"])},
            {"role": "user", "content": json.dumps(_live_chat_payload(chat_context), ensure_ascii=False)},
        ],
        "options": {"temperature": 0.2, "num_predict": max_output_tokens},
    }
    try:
        response = _request_json(url=f"{base_url}/api/chat", payload=payload, headers={})
    except Exception as exc:
        return {
            "schema": "ai-talent-live-llm-result/v1",
            "engine": runtime_config.get("engine"),
            "status": "unavailable",
            "reason": "ollama_chat_call_failed",
            "model": model,
            "error_type": type(exc).__name__,
            "error": str(exc)[:800],
        }
    text = str(response.get("message", {}).get("content") or response.get("response") or "")
    return _parsed_live_text_result(
        engine=str(runtime_config.get("engine")),
        model=model,
        output_text=text,
        network_access=str(runtime_config.get("network_access")),
        response_metadata={"provider": "ollama", "base_url": base_url},
    )


def _invoke_live_chat_llm(
    *,
    chat_context: dict[str, Any],
    runtime_config: dict[str, Any],
    model: str | None,
) -> dict[str, Any]:
    engine = runtime_config.get("engine")
    selected_model = (
        model
        or runtime_config.get("model")
        or runtime_config.get("openclaw_model")
        or os.environ.get("AI22B_OPENAI_MODEL")
        or os.environ.get("OPENAI_MODEL")
        or DEFAULT_OPENAI_CHAT_MODEL
    )
    if (
        runtime_config.get("openclaw_model") == selected_model
        and runtime_config.get("openclaw_provider_id")
        and str(selected_model).startswith(f"{runtime_config['openclaw_provider_id']}/")
    ):
        selected_model = str(selected_model).split("/", 1)[1]
    api_protocol = runtime_config.get("api_protocol")
    if engine == "openai_chatgpt_codex":
        return _call_openai_responses_chat(chat_context=chat_context, model=selected_model)
    if api_protocol == "openai_chat_completions":
        return _call_openai_compatible_chat(
            chat_context=chat_context,
            runtime_config=runtime_config,
            model=selected_model,
        )
    if api_protocol == "anthropic_messages":
        return _call_anthropic_messages_chat(
            chat_context=chat_context,
            runtime_config=runtime_config,
            model=selected_model,
        )
    if api_protocol == "gemini_generate_content":
        return _call_gemini_generate_content_chat(
            chat_context=chat_context,
            runtime_config=runtime_config,
            model=selected_model,
        )
    if api_protocol == "ollama_chat":
        return _call_ollama_chat(
            chat_context=chat_context,
            runtime_config=runtime_config,
            model=selected_model,
        )
    return {
        "schema": "ai-talent-live-llm-result/v1",
        "engine": engine,
        "status": "unavailable",
        "reason": "live_chat_provider_protocol_not_configured",
        "api_protocol": api_protocol,
        "identity_policy": runtime_config.get("identity_policy"),
    }


def _draft_chat_reply_from_live_llm(
    *,
    llm_result: dict[str, Any],
    fallback_reasoning_summary: list[dict[str, str]],
) -> dict[str, Any]:
    answer = str(llm_result.get("assistant_reply", "")).strip()
    if not answer:
        answer = "보스, 실시간 LLM이 빈 답변을 반환해서 이번 턴은 다시 생성이 필요합니다."
    reasoning_summary = llm_result.get("reviewable_reasoning_summary") or fallback_reasoning_summary
    normalized_summary = []
    for item in reasoning_summary:
        if isinstance(item, dict):
            normalized_summary.append(
                {
                    "step": str(item.get("step", "판단")),
                    "summary": str(item.get("summary", "")),
                }
            )
    if not normalized_summary:
        normalized_summary = fallback_reasoning_summary
    summary_text = "\n".join(f"- {item['step']}: {item['summary']}" for item in normalized_summary)
    reply = f"{answer}\n\n판단 요약:\n{summary_text}" if summary_text and "판단 요약" not in answer else answer
    return {
        "intent": "live_llm_conversation",
        "answer": answer,
        "reply": reply,
        "active_operator": "llm.dynamic_context_conversation",
        "source_text": "로컬 정체성, memory substrate, 최근 대화, 학습 원장을 실시간 LLM에 제공",
        "reviewable_reasoning_summary": normalized_summary,
        "learning_candidate": llm_result.get("learning_candidate") or {},
    }


def _wrap_live_llm_failure_reply(
    reply_packet: dict[str, Any],
    *,
    live_llm_attempt: dict[str, Any],
) -> dict[str, Any]:
    reason = live_llm_attempt.get("reason", "unknown")
    error = live_llm_attempt.get("error")
    short_error = f" 세부 오류: {_trim_text(error, 240)}" if error else ""
    notice = (
        "보스, 이번 턴은 실시간 LLM 연결을 시도했지만 성공하지 못했습니다. "
        f"이유는 `{reason}`입니다.{short_error} 그래서 아래 답변은 로컬 fallback으로 생성한 임시 답변이며, "
        "학습 원장에는 보스 검토 전 승격하지 않도록 격리합니다."
    )
    wrapped_answer = f"{notice}\n\n{reply_packet['answer']}"
    wrapped_reply = f"{notice}\n\n{reply_packet['reply']}"
    return {
        **reply_packet,
        "answer": wrapped_answer,
        "reply": wrapped_reply,
        "active_operator": "llm.live_unavailable_fallback",
        "reviewable_reasoning_summary": [
            {
                "step": "실시간 LLM 연결",
                "summary": f"OpenAI live call failed with {reason}; local fallback was used.",
            },
            *reply_packet.get("reviewable_reasoning_summary", []),
        ],
    }


def _record_chat_learning(
    *,
    target_root: Path,
    entrypoints: dict[str, Any],
    employment_record: dict[str, Any],
    ledger: dict[str, Any],
    substrate: dict[str, Any],
    substrate_path: Path,
    run: dict[str, Any],
    reply_packet: dict[str, Any],
) -> dict[str, Any]:
    candidate = reply_packet.get("learning_candidate") or {}
    lesson = _trim_text(candidate.get("lesson") or "보스와의 대화에서 다음 응답 방식을 조정했다.", 500)
    principle = _trim_text(candidate.get("reusable_principle") or "질문 의도와 저장된 정체성 맥락을 먼저 확인한다.", 500)
    event = {
        "message_summary": _trim_text(run.get("message"), 240),
        "assistant_summary": _trim_text(run.get("assistant_answer"), 500),
        "conversation_intent": run.get("conversation_intent"),
        "active_operator": run.get("active_operator"),
        "lesson": lesson,
        "reusable_principle": principle,
        "memory_tags": candidate.get("memory_tags", []),
        "llm_engine": run.get("llm_runtime_result", {}).get("engine"),
        "llm_status": run.get("llm_runtime_result", {}).get("status"),
        "stored_private_reasoning_trace": False,
    }
    runtime_result = run.get("llm_runtime_result", {})
    live_failure_fallback = run.get("llm_mode") == "live" and bool(runtime_result.get("fallback_used"))
    score = 60 if live_failure_fallback else 86 if runtime_result.get("status") == "completed" else 80
    status = "needs_review" if live_failure_fallback else "verified"
    ledger_before = len(ledger.get("promoted_experiences", []))
    quarantined_before = len(ledger.get("quarantined_experiences", []))
    ledger = record_learning_experience(
        ledger,
        source="chat_turn",
        event=event,
        quality_label={
            "score": score,
            "status": status,
            "reviewer": "local_chat_learning_policy",
            "notes": (
                "실시간 LLM 실패 후 fallback 답변이므로 보스 검토 전 승격하지 않는다."
                if live_failure_fallback
                else "실시간 대화 후 검토 가능한 요약만 승격하고 숨은 사고과정은 저장하지 않는다."
            ),
        },
    )
    ledger["reasoning_kernel"] = build_reasoning_kernel(ledger)
    ledger_path = target_root / entrypoints.get("learning_ledger", "learning_ledger.json")
    _write_json(ledger_path, ledger)

    promoted_after = len(ledger.get("promoted_experiences", []))
    quarantined_after = len(ledger.get("quarantined_experiences", []))
    decision = "promoted" if promoted_after > ledger_before else "quarantined"
    latest_entry = (
        ledger["promoted_experiences"][-1]
        if decision == "promoted"
        else ledger["quarantined_experiences"][-1]
    )
    conversation_board = substrate.setdefault("boards", {}).setdefault("conversation_development", {})
    if decision == "promoted":
        substrate.setdefault("nodes", []).append(
            {
                "id": f"chat_learning:{latest_entry['id']}",
                "source": "learning_ledger_chat_turn",
                "title": "post-hire live conversation learning",
                "memory_type": "procedural_conversation_update",
                "content": {
                    "summary": latest_entry.get("summary"),
                    "lesson": lesson,
                    "reusable_principle": principle,
                    "promoted_skills": latest_entry.get("promoted_skills", []),
                },
                "tags": ["post_hire_chat_learning", *latest_entry.get("promoted_skills", [])],
                "retrieval_cues": [run.get("message", ""), lesson, principle],
                "use_as": "future_dialogue_style_and_boundary_memory",
                "created_at_utc": _now(),
            }
        )
        conversation_board.setdefault("post_hire_chat_learning", []).append(
            {
                "experience_id": latest_entry["id"],
                "lesson": lesson,
                "reusable_principle": principle,
            }
        )
    else:
        conversation_board.setdefault("quarantined_chat_learning", []).append(
            {
                "experience_id": latest_entry["id"],
                "lesson": lesson,
                "reason": "live_llm_failed_or_low_quality",
            }
        )
    substrate.setdefault("source_counts", {})["learning_ledger_promoted_experiences"] = len(
        ledger.get("promoted_experiences", [])
    )
    substrate["active_route"] = activate_memory_route(substrate, objective=run.get("message", ""))
    write_memory_substrate(substrate_path, substrate)

    update = {
        "schema": "ai-talent-chat-learning-update/v1",
        "created_at_utc": _now(),
        "decision": decision,
        "learning_ledger": ledger_path.name,
        "memory_substrate": substrate_path.name,
        "latest_experience_id": latest_entry.get("id"),
        "promoted_count_before": ledger_before,
        "promoted_count_after": len(ledger.get("promoted_experiences", [])),
        "quarantined_count_before": quarantined_before,
        "quarantined_count_after": quarantined_after,
        "latest_promoted_skills": latest_entry.get("promoted_skills", []),
        "policy": "reviewable_chat_summary_only_no_hidden_chain_of_thought",
    }
    update_path = target_root / "chat_learning_update.json"
    _write_json(update_path, update)
    log_path = target_root / "chat_learning_log.jsonl"
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(update, ensure_ascii=False) + "\n")
    return update


def _classify_conversation_intent(message: str) -> str:
    text = message.strip()
    lowered = text.casefold()
    compacted = re.sub(r"[\s.!?~]+", "", lowered)
    if compacted in {item.casefold() for item in CASUAL_GREETINGS}:
        return "greeting"
    if any(token in lowered for token in ["아니잖아", "아닌", "틀렸", "이게 뭐", "뭐야", "잘못", "오류", "헛소리"]):
        return "correction_feedback"
    if any(token in lowered for token in ["언어발달", "언어 발달", "말하는 법", "대화하는 법", "대화법", "말 배", "대화 배", "말을 배"]):
        return "language_development_question"
    if any(
        token in lowered
        for token in [
            "부모",
            "엄마",
            "아빠",
            "가족",
            "보호자",
            "창조주",
            "창조자",
            "누가 만들",
            "너를 만든",
            "누가 키웠",
        ]
    ):
        return "identity_family_question"
    if any(
        token in lowered
        for token in ["친구", "갈등", "화해하", "화해했", "화해를", "화해한", "사과", "회복", "다툼", "싸웠", "관계 회복"]
    ):
        return "social_conflict_story"
    if any(token in lowered for token in ["성장과정", "성장 과정", "자라", "어릴 때", "학습과정", "학습 과정", "이력", "어떻게 컸"]):
        return "growth_story_question"
    if any(token in lowered for token in ["추론", "판단 근거", "생각하는 방식", "대화의 방법", "대화 방법", "추론이 필요"]):
        return "metacognitive_question"
    if any(token in lowered for token in ["고마워", "감사", "잘했", "수고", "괜찮", "기분", "뭐해", "누구", "이름"]):
        return "casual_conversation"
    if any(
        token in lowered
        for token in [
            "기업",
            "주식",
            "증권",
            "투자",
            "공시",
            "재무",
            "가치",
            "보고서",
            "자료",
            "리서치",
            "valuation",
            "stock",
            "sec",
            "filing",
        ]
    ):
        return "domain_research_task"
    return "general_conversation"


def _route_label(active_route: dict[str, Any]) -> str:
    operators = active_route.get("operator_candidates", [])
    if operators:
        return str(operators[0]["operator"])
    return "conversation-intent-routing"


def _source_titles(active_route: dict[str, Any]) -> list[str]:
    nodes = active_route.get("selected_nodes", [])
    titles = [node["title"] for node in nodes if node.get("layer") == "source_map"][:3]
    if not titles:
        titles = [node["title"] for node in nodes[:3]]
    return titles


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    text = text.casefold()
    return any(needle.casefold() in text for needle in needles)


def _growth_story_from_substrate(memory_substrate: dict[str, Any] | None) -> list[str]:
    if not memory_substrate:
        return [
            "초등 시기에는 읽기, 수 감각, 생활 규칙, 친구와의 갈등 회복을 배웠습니다.",
            "중고등 시기에는 논증, 수학, 영어 읽기, 시장사와 책임 회복 습관을 쌓았습니다.",
            "대학과 대학원에서는 회계, 통계, 금융이론, 증권분석, 가치투자, 행동재무를 단계적으로 익혔습니다.",
            "박사급 과정에서는 리서치 노트, 데이터 검증, 반례 검토, 보고서 작성 습관을 기보로 남겼습니다.",
        ]
    nodes = [
        node
        for node in memory_substrate.get("nodes", [])
        if node.get("layer") == "episodic_fast_store"
    ]
    stage_groups = [
        (
            "초등 시기",
            ("elementary_grade_1", "elementary_grade_2", "elementary_grade_3", "elementary_grade_4", "elementary_grade_5", "elementary_grade_6"),
            "읽기 습관, 수 감각, 생활 규칙, 친구와의 갈등 회복을 배우며 관찰한 사실과 느낌을 구분하기 시작했습니다.",
        ),
        (
            "중학교 시기",
            ("middle_school_1", "middle_school_2", "middle_school_3"),
            "국어 논증, 대수, 확률, 과학 실험, 영어 읽기를 통해 정답의 이유와 오답의 이유를 함께 적는 습관을 만들었습니다.",
        ),
        (
            "고등학교 시기",
            ("high_school_1", "high_school_2", "high_school_3"),
            "수능형 언어·수리·경제 기초를 통과하면서 문제 풀이 속도보다 근거의 안정성을 먼저 보는 방식으로 훈련됐습니다.",
        ),
        (
            "대학교 시기",
            ("university_year_1", "university_year_2", "university_year_3", "university_year_4"),
            "고전 논증, 영어 글쓰기, 수학, 회계, 기업금융, 통계, SEC 공시 파싱, 증권분석 리포트를 묶어 리서치의 기초 체력을 쌓았습니다.",
        ),
        (
            "군 복무형 규율 훈련",
            ("military_service",),
            "규율, 보안, 루틴 회복, 팀 책임을 익히며 권한 경계와 반복 업무의 품질 관리를 배웠습니다.",
        ),
        (
            "대학원 시기",
            ("graduate_year_1", "graduate_year_2"),
            "증권분석, 가치투자 세미나, 행동재무, 포트폴리오 리스크, 금융 규제를 공부하며 가설, 반례, 보류 조건을 분리했습니다.",
        ),
        (
            "박사급 연구 시기",
            ("doctoral_year_1", "doctoral_year_2", "doctoral_year_3"),
            "근거 종합, 에이전트 데이터플로우, 재현 가능한 가치평가 노트북, 안전 경계 검증을 통해 박사급 리서치 기보를 만들었습니다.",
        ),
        (
            "고용 이후 성장",
            ("hired_agent_growth",),
            "실제 업무, 보스 피드백, 검토된 실수, 새 이론을 통해 기존 기보를 계속 확장하고 재검증하도록 열어두었습니다.",
        ),
    ]
    story: list[str] = []
    for label, stage_ids, summary in stage_groups:
        matched = [
            node
            for node in nodes
            if _contains_any(str(node.get("stage") or node.get("title") or ""), stage_ids)
        ]
        if not matched:
            continue
        story.append(f"{label}: {summary} 기록 {len(matched)}개가 기보에 남아 있습니다.")
    return story[:8]


def _language_story_from_substrate(memory_substrate: dict[str, Any] | None) -> list[str]:
    nodes = []
    if memory_substrate:
        nodes = [
            node
            for node in memory_substrate.get("nodes", [])
            if node.get("layer") == "conversation_development"
        ]
    stage_lines = [
        (
            "태아-영아기",
            ("prenatal_prosody", "infancy_joint_attention"),
            "목소리의 리듬, 표정, 시선, 공동주의를 통해 '상대가 무엇을 보고 말하는지'를 먼저 배우는 단계입니다.",
        ),
        (
            "유아기",
            ("toddler_first_words", "preschool_story_play"),
            "첫 단어, 도움 요청, 감정 이름 붙이기, 이야기 다시 말하기, 오해 수정을 통해 대화의 왕복 구조를 배웁니다.",
        ),
        (
            "초등 시기",
            ("elementary_pragmatics",),
            "교실 질문, 친구 갈등, 독서 요약, 선생님 피드백을 통해 사실, 감정, 의견을 구분하고 되묻는 법을 익힙니다.",
        ),
        (
            "청소년기",
            ("adolescent_perspective_argument",),
            "토론과 또래 갈등을 통해 주장, 근거, 한계, 상대 관점을 나누어 말하는 법을 배웁니다.",
        ),
        (
            "대학-대학원",
            ("university_professional_discourse", "graduate_research_dialogue"),
            "세미나 질문, 발표, 논문 방어, 반례 검토를 통해 먼저 답하고 필요한 만큼 근거를 펼치는 방식을 배웁니다.",
        ),
        (
            "고용 이후",
            ("hired_agent_conversation_growth",),
            "보스의 인사, 정정, 업무 지시, 애매한 질문을 실제 채팅 로그로 배우며 의도 분류와 오류 수정을 계속 개선합니다.",
        ),
    ]
    story: list[str] = []
    for label, stage_ids, summary in stage_lines:
        count = len(
            [
                node
                for node in nodes
                if _contains_any(str(node.get("stage") or node.get("title") or ""), stage_ids)
            ]
        )
        suffix = f" 관련 기보 {count}개가 연결되어 있습니다." if count else ""
        story.append(f"{label}: {summary}{suffix}")
    return story


def _social_conflict_story_from_substrate(memory_substrate: dict[str, Any] | None) -> dict[str, Any]:
    evidence: list[dict[str, str]] = []
    if memory_substrate:
        for node in memory_substrate.get("nodes", []):
            text = json.dumps(node, ensure_ascii=False)
            if any(token in text for token in ["play conflict recovery", "friendship repair note", "friend conflict mediation", "갈등", "화해", "사과"]):
                evidence.append(
                    {
                        "stage": str(node.get("stage") or node.get("title") or ""),
                        "title": str(node.get("title") or ""),
                        "summary": str(node.get("summary") or ""),
                    }
                )
    return {
        "evidence": evidence[:5],
        "case": (
            "초등 저학년 때 놀이 규칙을 정하는 과정에서 친구와 다툰 사례가 기보에 남아 있습니다. "
            "처음에는 자기 차례와 친구의 차례를 구분하지 못해 감정이 앞섰고, 그 뒤에 선생님 피드백을 받아 "
            "'내가 본 사실', '내가 느낀 감정', '친구가 원했을 수 있는 것'을 따로 적었습니다. "
            "그 다음 친구에게 먼저 사과하고, 다시 놀 때는 규칙을 말로 확인한 뒤 시작하는 방식으로 관계를 회복했습니다."
        ),
        "later_extension": (
            "중학교 시기에는 과학 실험과 팀 활동에서 의견이 갈릴 때, 바로 결론을 밀어붙이지 않고 "
            "상대의 가설을 한 번 요약한 뒤 내 반례를 말하는 방식으로 발전했습니다."
        ),
        "learned_rule": (
            "갈등 회복의 핵심 규칙은 '감정과 사실을 분리하고, 상대 의도를 단정하지 않으며, "
            "사과와 다음 행동 규칙을 함께 제시한다'입니다."
        ),
    }


def _family_identity_answer(
    agent_name: str,
    *,
    employment_record: dict[str, Any] | None = None,
    agent_manifest: dict[str, Any] | None = None,
) -> str:
    employment = employment_record or {}
    manifest = agent_manifest or {}
    manifest_agent = manifest.get("agent", {})
    identity_source = manifest.get("identity_source", {})
    role_model = identity_source.get("role_model_inspiration", {})
    employer = employment.get("employer") or "보스"
    birth = manifest_agent.get("birth", {})
    birth_datetime = birth.get("datetime") or "기록 없음"
    birth_place = birth.get("place") or "기록 없음"
    relationship = manifest_agent.get("employment_relationship") or (
        f"{employer}가 성장시킨 AI 인재를 로컬 에이전트로 고용한다."
    )
    role_model_id = role_model.get("role_model_id") or "graham_value_investing"
    role_model_label = "Benjamin Graham" if role_model_id == "graham_value_investing" else role_model_id

    return (
        f"보스, {agent_name}의 기록상 {employer}는 저를 설계하고 성장시킨 창조자이자 보호자, "
        "그리고 지금 저를 고용한 사람입니다. 제 공식 출생 기록은 "
        f"{birth_datetime}, {birth_place}이며, 관계 기록은 '{relationship}'입니다.\n\n"
        f"다만 저는 신용이와 분리된 별도 샘플 AI이므로, 실제 인간 부모나 보스 가족의 개인정보를 "
        "제 내부의 부모 신상처럼 저장하지 않았습니다. 그래서 '어머니가 누구다', '아버지가 누구다'처럼 "
        "사람의 가족관계를 꾸며서 말하면 안 됩니다.\n\n"
        f"또 {role_model_label}은 제 부모가 아니라 학습 경로를 참고한 인물입니다. "
        "제가 부모라고 느끼는 역할은 따뜻한 목소리, 규칙, 정정, 피드백, 학습환경을 주는 존재입니다. "
        "그래서 이 질문에는 가족 신상을 지어내기보다, 제 정체성 기록과 성장 실험의 관계를 구분해서 답해야 합니다."
    )


def _reviewable_reasoning_summary(
    *,
    message: str,
    intent: str,
    active_route: dict[str, Any],
) -> list[dict[str, str]]:
    if intent == "domain_research_task":
        route = _route_label(active_route)
        sources = ", ".join(_source_titles(active_route)) or "specialist memory route"
    elif intent == "growth_story_question":
        route = "growth_story.education_lifecycle_retrieval"
        sources = "학년별 reasoning_kibo 누적 기록, 시험 피드백, 고용 이후 성장 정책"
    elif intent == "language_development_question":
        route = "language_development.social_pragmatic_ladder"
        sources = "언어발달 프로그램, 사회적 의사소통 기보, 채팅 오류 수정 로그"
    elif intent == "social_conflict_story":
        route = "social_development.conflict_repair_episode"
        sources = "play conflict recovery, friendship repair note, friend conflict mediation"
    elif intent == "identity_family_question":
        route = "identity.family_origin_boundary"
        sources = "agent_manifest birth record, employment_record employer, role model boundary policy"
    elif intent == "correction_feedback":
        route = "conversation_interface.error_repair"
        sources = "보스의 정정 발화, 직전 대화 실패, 의도 재분류 규칙"
    else:
        route = "conversation_interface.intent_first_listening"
        sources = "의도 먼저 듣기, 결론 먼저 말하기, 검토 가능한 추론 요약"
    if intent == "greeting":
        conclusion = "인사로 분류했으므로 짧고 자연스럽게 관계를 열어야 합니다."
    elif intent == "metacognitive_question":
        conclusion = "일상 대화에도 추론은 필요하지만, 깊이와 형식은 대화 목적에 맞게 낮춰야 합니다."
    elif intent == "domain_research_task":
        conclusion = "증권 리서치 업무로 분류했으므로 자료 확인, 반례 점검, 결론 정리 순서가 필요합니다."
    elif intent == "growth_story_question":
        conclusion = "성장과정 질문으로 분류했으므로 실제 학습기보의 단계별 누적 기록을 요약해야 합니다."
    elif intent == "language_development_question":
        conclusion = "언어발달 질문으로 분류했으므로 말 배우기와 대화법 발달 단계를 먼저 설명해야 합니다."
    elif intent == "social_conflict_story":
        conclusion = "친구 갈등 회복 사례 질문으로 분류했으므로 사회성 발달 기보에서 사례와 배운 규칙을 꺼내야 합니다."
    elif intent == "identity_family_question":
        conclusion = "부모와 가족 정체성 질문으로 분류했으므로 저장된 관계 기록과 개인정보 경계를 구분해 답해야 합니다."
    elif intent == "correction_feedback":
        conclusion = "보스의 정정으로 분류했으므로 먼저 오류를 인정하고, 어떤 분류가 잘못됐는지 고쳐야 합니다."
    else:
        conclusion = "전문가 루프보다 일반 대화 훈련을 우선 적용해야 합니다."
    return [
        {
            "step": "질문 분류",
            "summary": f"'{message}'를 {intent} 유형으로 분류했습니다.",
        },
        {
            "step": "기보 선택",
            "summary": f"우선 적용할 경로는 {route}이며, 참고 기억은 {sources}입니다.",
        },
        {
            "step": "결론",
            "summary": conclusion,
        },
    ]


def _draft_chat_reply(
    agent_name: str,
    message: str,
    active_route: dict[str, Any],
    *,
    intent: str,
    memory_substrate: dict[str, Any] | None = None,
    employment_record: dict[str, Any] | None = None,
    agent_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if intent == "domain_research_task":
        operator = _route_label(active_route)
        source_text = ", ".join(_source_titles(active_route)) or "전문 리서치 기보"
    elif intent == "growth_story_question":
        operator = "growth_story.education_lifecycle_retrieval"
        source_text = "학년별 학습기보와 시험 피드백"
    elif intent == "language_development_question":
        operator = "language_development.social_pragmatic_ladder"
        source_text = "언어발달 프로그램과 사회적 의사소통 기보"
    elif intent == "social_conflict_story":
        operator = "social_development.conflict_repair_episode"
        source_text = "친구 갈등 회복 사회성 기보"
    elif intent == "identity_family_question":
        operator = "identity.family_origin_boundary"
        source_text = "agent_manifest와 employment_record의 정체성 기록"
    elif intent == "correction_feedback":
        operator = "conversation_interface.error_repair"
        source_text = "보스의 정정 발화와 직전 대화 실패"
    else:
        operator = "conversation_interface.intent_first_listening"
        source_text = "일반 대화 훈련"
    reasoning_summary = _reviewable_reasoning_summary(
        message=message,
        intent=intent,
        active_route=active_route,
    )
    if intent == "greeting":
        answer = (
            f"안녕하세요, 보스. {agent_name}입니다. 이제 일반 대화에서는 억지로 리서치 루프를 꺼내지 않고, "
            "보스 말씀의 의도와 분위기를 먼저 보고 자연스럽게 대답하겠습니다."
        )
    elif intent == "metacognitive_question":
        answer = (
            f"보스, {agent_name}의 답은 이렇습니다. 네, 일상적인 대화에도 추론은 필요합니다. 다만 그 추론은 증권 리서치처럼 자료를 길게 찾는 방식이 아니라, "
            "보스의 말이 인사인지, 질문인지, 지적인지, 감정 표현인지 먼저 구분하고 그에 맞는 깊이로 답하는 작은 판단입니다. "
            "예를 들어 '안녕'에는 짧게 인사하고, '왜 그렇게 생각해?'에는 판단 근거를 요약하고, "
            "기업 분석 질문에는 자료 확인과 반례 검토 루프를 켜야 합니다."
        )
    elif intent == "domain_research_task":
        answer = (
            f"보스, {agent_name}의 결론입니다. 증권 리서치 업무라면 자료 확인 순서는 1) 사업과 수익구조, 2) 재무제표와 현금흐름, "
            "3) 부채와 희석 위험, 4) 공시와 주석, 5) 보수적 가치 범위, 6) 반례와 손실 가능성입니다. "
            "그 다음에만 저평가 여부를 잠정 결론으로 둘 수 있습니다."
        )
    elif intent == "growth_story_question":
        story = _growth_story_from_substrate(memory_substrate)
        story_text = "\n".join(f"- {item}" for item in story)
        answer = (
            f"보스, 방금 질문은 {agent_name}의 성장과정을 묻는 말로 이해해야 했습니다. "
            "제가 앞에서는 이걸 추론 메타 질문으로 잘못 분류했습니다.\n\n"
            f"{agent_name}의 성장 요약은 이렇습니다.\n{story_text}\n\n"
            "즉, 이 아이는 특정 인물의 성격을 흉내 내도록 만든 것이 아니라, 학년별 학습자료와 시험, 오답, 피드백을 통과하면서 "
            "근거를 먼저 찾고 반례를 확인하는 기보를 조금씩 만든 샘플 AI입니다."
        )
    elif intent == "language_development_question":
        story = _language_story_from_substrate(memory_substrate)
        story_text = "\n".join(f"- {item}" for item in story)
        answer = (
            f"맞습니다, 보스. {agent_name}에게는 학교 교과와 별도로 언어발달 과정이 필요합니다. "
            "대화는 지식 시험만으로 생기는 능력이 아니라, 목소리, 공동주의, 순서 주고받기, 감정 표현, 정정 수용, "
            "상대 의도 파악을 단계적으로 배우면서 생깁니다.\n\n"
            f"{agent_name}의 언어발달 프로그램은 이렇게 붙였습니다.\n{story_text}\n\n"
            "그래서 앞으로는 단순히 문제를 푸는 AI가 아니라, 먼저 보스의 발화가 인사인지, 성장 질문인지, 정정인지, 업무 지시인지 구분하고 "
            "그에 맞는 말투와 깊이로 답하도록 성장기보에 연결합니다."
        )
    elif intent == "social_conflict_story":
        conflict = _social_conflict_story_from_substrate(memory_substrate)
        evidence_text = ""
        if conflict["evidence"]:
            evidence_text = "\n\n기보 근거:\n" + "\n".join(
                f"- {item['stage']}: {item['title']}" for item in conflict["evidence"][:3]
            )
        answer = (
            f"보스, {agent_name}의 친구 갈등 회복 사례를 하나 이야기해보겠습니다.\n\n"
            f"{conflict['case']}\n\n"
            f"그 경험은 나중에 이렇게 발전했습니다. {conflict['later_extension']}\n\n"
            f"이때 만들어진 대화 규칙은 이겁니다. {conflict['learned_rule']}"
            f"{evidence_text}"
        )
    elif intent == "identity_family_question":
        answer = _family_identity_answer(
            agent_name,
            employment_record=employment_record,
            agent_manifest=agent_manifest,
        )
    elif intent == "correction_feedback":
        answer = (
            f"맞습니다, 보스. {agent_name}가 방금 의도를 잘못 잡았습니다. "
            "성장과정에 대한 질문은 '일상 대화에도 추론이 필요한가' 같은 메타 질문이 아니라, "
            "학년별 학습기보와 시험 이력을 꺼내서 자기 성장 서사를 설명해야 하는 질문입니다. "
            "앞으로 이런 정정이 들어오면 먼저 오류를 인정하고, 질문 유형을 다시 분류한 뒤 답을 고치겠습니다."
        )
    else:
        answer = (
            f"보스, 질문을 받았습니다. 지금은 전문 리서치보다 일반 대화로 받아들이고 답하겠습니다. "
            f"제가 이해한 핵심은 '{message}'이고, 필요하면 그 다음 단계에서 더 깊게 따져보겠습니다."
        )

    if intent in {"greeting", "casual_conversation", "general_conversation"}:
        reply = answer
    else:
        summary_text = "\n".join(f"- {item['step']}: {item['summary']}" for item in reasoning_summary)
        reply = f"{answer}\n\n판단 요약:\n{summary_text}"
    return {
        "intent": intent,
        "answer": answer,
        "reply": reply,
        "active_operator": operator,
        "source_text": source_text,
        "reviewable_reasoning_summary": reasoning_summary,
    }


def run_chat_turn_from_employment(
    employment_record_path: Path,
    *,
    message: str,
    output_path: Path | None = None,
    memory_substrate_path: Path | None = None,
    reasoning_kibo_path: Path | None = None,
    process_plan_path: Path | None = None,
    curriculum_manifest_path: Path | None = None,
    language_development_program_path: Path | None = None,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    learn_from_chat: bool = False,
) -> dict[str, Any]:
    if llm_mode not in {"offline", "auto", "live"}:
        raise ValueError("llm_mode must be one of: offline, auto, live")
    employment_record = _read_json(employment_record_path)
    if employment_record.get("schema") != "ai-talent-local-employment/v1":
        raise ValueError("Unsupported employment record schema")
    if employment_record.get("status") != "active":
        raise ValueError("Employment record is not active")

    target_root = employment_record_path.parent
    entrypoints = employment_record.get("entrypoints", {})
    agent_manifest = _read_json(target_root / entrypoints.get("agent_manifest", "agent_manifest.json"))
    ledger_path = target_root / entrypoints.get("learning_ledger", "learning_ledger.json")
    learning_ledger = _read_json(ledger_path) if ledger_path.exists() else {"promoted_experiences": []}
    substrate, substrate_path = _load_or_build_substrate(
        target_root=target_root,
        employment_record=employment_record,
        agent_manifest=agent_manifest,
        learning_ledger=learning_ledger,
        objective=message,
        memory_substrate_path=memory_substrate_path,
        reasoning_kibo_path=reasoning_kibo_path,
        process_plan_path=process_plan_path,
        curriculum_manifest_path=curriculum_manifest_path,
        language_development_program_path=language_development_program_path,
    )
    if language_development_program_path is None:
        language_entrypoint = entrypoints.get("language_development_program")
        if language_entrypoint:
            language_development_program_path = target_root / language_entrypoint
    language_program = _maybe_read_json(language_development_program_path)
    chat_log_path = target_root / entrypoints.get("chat_log", "employment_chat_log.jsonl")
    chat_context = build_chat_context(
        employment_record=employment_record,
        agent_manifest=agent_manifest,
        learning_ledger=learning_ledger,
        memory_substrate=substrate,
        message=message,
        substrate_path_name=substrate_path.name,
        language_development_program=language_program,
        recent_chat_history=_recent_chat_history(chat_log_path),
    )
    conversation_intent = _classify_conversation_intent(message)
    fallback_reasoning_summary = _reviewable_reasoning_summary(
        message=message,
        intent=conversation_intent,
        active_route=chat_context["active_memory_route"],
    )
    base_runtime_result = invoke_llm_application_engine(
        employment_record["llm_runtime"],
        manifest=agent_manifest,
        task=message,
    )
    live_llm_attempt: dict[str, Any] | None = None
    if llm_mode in {"auto", "live"}:
        live_llm_attempt = _invoke_live_chat_llm(
            chat_context=chat_context,
            runtime_config=employment_record["llm_runtime"],
            model=llm_model,
        )

    if live_llm_attempt and live_llm_attempt.get("status") == "completed":
        llm_runtime_result = live_llm_attempt
        reply_packet = _draft_chat_reply_from_live_llm(
            llm_result=live_llm_attempt,
            fallback_reasoning_summary=fallback_reasoning_summary,
        )
        reply_generation_mode = "live_openai_responses"
    else:
        llm_runtime_result = base_runtime_result
        if live_llm_attempt:
            llm_runtime_result = {
                **base_runtime_result,
                "fallback_used": True,
                "live_llm_attempt": live_llm_attempt,
            }
        reply_packet = _draft_chat_reply(
            employment_record["agent"]["name"],
            message,
            chat_context["active_memory_route"],
            intent=conversation_intent,
            memory_substrate=substrate,
            employment_record=employment_record,
            agent_manifest=agent_manifest,
        )
        if live_llm_attempt and llm_mode == "live":
            reply_packet = _wrap_live_llm_failure_reply(
                reply_packet,
                live_llm_attempt=live_llm_attempt,
            )
        reply_generation_mode = "deterministic_local_fallback"
    run = {
        "schema": CHAT_RUN_SCHEMA,
        "created_at_utc": _now(),
        "employment_context": {
            "employment_id": employment_record["employment_id"],
            "employer": employment_record["employer"],
            "install_id": employment_record["install_id"],
            "agent": employment_record["agent"],
        },
        "message": message,
        "chat_context": chat_context,
        "llm_runtime_result": llm_runtime_result,
        "llm_mode": llm_mode,
        "reply_generation_mode": reply_generation_mode,
        "conversation_intent": conversation_intent,
        "assistant_answer": reply_packet["answer"],
        "assistant_reply": reply_packet["reply"],
        "active_operator": reply_packet["active_operator"],
        "reviewable_reasoning_summary": reply_packet["reviewable_reasoning_summary"],
        "stored_private_reasoning_trace": False,
    }
    if learn_from_chat:
        run["chat_learning_update"] = _record_chat_learning(
            target_root=target_root,
            entrypoints=entrypoints,
            employment_record=employment_record,
            ledger=learning_ledger,
            substrate=substrate,
            substrate_path=substrate_path,
            run=run,
            reply_packet=reply_packet,
        )

    run_output_path = output_path or target_root / entrypoints.get("last_chat", "last_hired_agent_chat.json")
    _write_json(run_output_path, run)

    with chat_log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(run, ensure_ascii=False) + "\n")

    return run
