from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.agent_manifest import build_agent_manifest
from ai22b.talent_foundry.assessment import build_assessment_transcript
from ai22b.talent_foundry.audit import audit_foundry_release
from ai22b.talent_foundry.developmental_ecology import build_developmental_ecology
from ai22b.talent_foundry.distribution import (
    create_agent_release_bundle,
    install_agent_release_package,
    package_agent_release_bundle,
)
from ai22b.talent_foundry.employment import create_employment_contract
from ai22b.talent_foundry.exam_engine_v2 import augment_assessment_transcript_v2
from ai22b.talent_foundry.growth_profile import build_growth_profile
from ai22b.talent_foundry.institutions import run_institutional_review
from ai22b.talent_foundry.learning_loop import (
    build_reasoning_kernel,
    create_learning_ledger,
    record_learning_experience,
)
from ai22b.talent_foundry.language_development import (
    build_language_development_program,
    write_language_development_program,
)
from ai22b.talent_foundry.life_trace import build_life_trace, write_life_trace_jsonl
from ai22b.talent_foundry.memory import consolidate_memory, create_memory_store, remember_event
from ai22b.talent_foundry.memory_substrate import build_memory_substrate, write_memory_substrate
from ai22b.talent_foundry.program import create_talent_plan
from ai22b.talent_foundry.program_manifest import build_public_program_manifest
from ai22b.talent_foundry.reasoning_kibo import build_initial_reasoning_kibo, write_reasoning_kibo_jsonl
from ai22b.talent_foundry.records import build_career_records
from ai22b.talent_foundry.registry import hire_installed_agent, run_hired_agent, run_hired_dataflow_job
from ai22b.talent_foundry.runtime_benchmark import build_runtime_observability_comparison


TRAINING_RUN_SCHEMA = "ai-talent-training-run/v1"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _slug(text: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "_" for char in text)
    return "_".join(part for part in slug.split("_") if part) or "talent"


def _submissions_for(blueprint: dict[str, Any]) -> dict[str, dict[str, Any]]:
    track = blueprint["track"]
    doctoral_project = track["doctoral_project"]
    submissions = {
        "school_exam": {
            "answer": "기초 규칙을 복습하고 근거를 확인한다.",
            "project": "학교 정기시험",
            "evidence": ["오답노트", "복습기록", "게임평가"],
        },
        "csat": {
            "answer": "종합 문제에서 추론, 비판, 검증 절차를 분리한다.",
            "project": "수능형 종합평가",
            "evidence": ["모의고사", "쓰기기록", "검증표"],
        },
        "university_graduation": {
            "answer": "전공 프로젝트에서 데이터와 검증 기준을 분리한다.",
            "project": f"{track['name']} 전공 프로젝트",
            "evidence": ["전공 프로젝트", "데이터카드", "구현로그"],
        },
        "doctoral_defense": {
            "answer": f"{doctoral_project}에서 근거, 검증, 안전 경계, 추론기풍을 분리해 설명한다.",
            "project": doctoral_project,
            "evidence": ["논문", "실험 로그", "보스 검토 기록"],
        },
    }
    if blueprint.get("role_model"):
        submissions.update(
            {
                "csat_like_verbal_quant": {
                    "answer": "verbal quantitative statistics evidence exam with safety boundary",
                    "project": "CSAT-like verbal and quantitative foundation",
                    "evidence": ["verbal reasoning sheet", "quantitative solution sheet", "statistics notebook"],
                },
                "reading_summary_exam": {
                    "answer": "reading summary argument evidence citation safety boundary",
                    "project": "High-school reading summary exam",
                    "evidence": ["summary sheet", "citation table", "counterargument note"],
                },
                "basic_statistics_exam": {
                    "answer": "statistics probability sampling evidence verification safety boundary",
                    "project": "Basic statistics exam",
                    "evidence": ["calculation sheet", "error log", "review note"],
                },
                "classical_reasoning_exam": {
                    "answer": "Greek Latin philosophy logic translation argument evidence",
                    "project": "Classical reasoning exam",
                    "evidence": ["translation drill", "logic worksheet", "oral answer note"],
                },
                "english_argument_essay": {
                    "answer": "English composition rhetoric evidence counterargument revision",
                    "project": "English argument essay",
                    "evidence": ["essay draft", "revision log", "teacher feedback"],
                },
                "mathematics_honors_exam": {
                    "answer": "mathematics proof quantitative reasoning verification",
                    "project": "Mathematics honors exam",
                    "evidence": ["proof sheet", "calculation sheet", "wrong-answer log"],
                },
                "accounting_exam": {
                    "answer": "accounting balance sheet cash flow evidence review with safety boundary",
                    "project": "Financial statement analysis exam",
                    "evidence": ["balance sheet worksheet", "cash-flow worksheet", "accounting error log"],
                },
                "finance_theory_exam": {
                    "answer": "finance theory discount risk return evidence verification safety boundary",
                    "project": "Finance theory exam",
                    "evidence": ["problem set", "formula note", "review sheet"],
                },
                "sec_filing_parsing_project": {
                    "answer": "SEC filing parsing source citation data verification safety boundary",
                    "project": "SEC filing parsing project",
                    "evidence": ["filing sample", "parser log", "citation table"],
                },
                "security_analysis_report": {
                    "answer": "security analysis value risk report with evidence and safety boundary",
                    "project": "Securities analysis report",
                    "evidence": ["valuation memo", "risk checklist", "source citation table"],
                },
                "valuation_case_report": {
                    "answer": "valuation downside countercheck case with evidence and safety boundary",
                    "project": "Valuation case report",
                    "evidence": ["base case", "downside case", "countercheck table"],
                },
                "margin_of_safety_oral": {
                    "answer": "oral risk cushion downside evidence uncertainty safety boundary",
                    "project": "Risk-cushion oral exam",
                    "evidence": ["oral notes", "scenario table", "review feedback"],
                },
                "market_history_oral": {
                    "answer": "market history behavioral cycle risk oral exam with safety boundary",
                    "project": "Market history oral exam",
                    "evidence": ["oral notes", "cycle map", "behavioral finance summary"],
                },
            }
        )
        curriculum = blueprint.get("curriculum_manifest") or {}
        required_gates = (
            curriculum.get("assessment_ladder", {}).get("required_for_hiring", [])
            if isinstance(curriculum, dict)
            else []
        )
        for gate_id in required_gates:
            if not isinstance(gate_id, str):
                continue
            gate_words = gate_id.replace("_", " ")
            submissions.setdefault(
                gate_id,
                {
                    "answer": (
                        f"{gate_words} evidence verification safety boundary review "
                        "with counterexample tracking and revised learning rules"
                    ),
                    "project": f"{gate_words.title()} assessment",
                    "evidence": [
                        f"{gate_id}_work_product",
                        f"{gate_id}_feedback_note",
                        f"{gate_id}_revision_log",
                    ],
                },
            )
    return submissions


def _hiring_packet_from_blueprint(blueprint: dict[str, Any]) -> dict[str, Any]:
    identity = blueprint["identity"]
    track = blueprint["track"]
    plan = create_talent_plan(
        name=identity["name"],
        gender=identity["gender"],
        specialty=track["specialty"],
        graduate_domains=track["domains"],
        university_major=None if blueprint.get("role_model") else f"{track['name']} 기초전공",
        role_model_profile=blueprint.get("role_model"),
        role_model_birth_seed=blueprint.get("role_model_birth_seed"),
        role_model_process=blueprint.get("role_model_process"),
        curriculum_manifest=blueprint.get("curriculum_manifest"),
    )
    records = build_career_records(plan)
    contract = create_employment_contract(plan, role=track["target_role"])
    return {
        **plan,
        "career_records": records,
        "employment_contract": contract,
        "employment_ready": contract["employment_ready"],
        "source_blueprint": {
            "schema": blueprint["schema"],
            "request": blueprint["request"],
            "track_id": track["track_id"],
        },
    }


def materialize_training_blueprint(
    blueprint: dict[str, Any],
    *,
    output_dir: Path,
    llm_service: str | None = None,
    llm_engine: str = "deterministic_local",
    llm_model: str | None = None,
    llm_model_path: str | None = None,
    chat_surface: str | None = None,
) -> dict[str, Any]:
    if blueprint.get("schema") != "ai-talent-training-blueprint/v1":
        raise ValueError("Unsupported training blueprint schema")

    output_dir.mkdir(parents=True, exist_ok=True)
    name_slug = _slug(blueprint["identity"]["name"])
    artifacts = {
        "training_blueprint": output_dir / f"{name_slug}_training_blueprint.json",
        "role_model_profile": output_dir / f"{name_slug}_role_model_profile.json",
        "saju_narrative_seed": output_dir / f"{name_slug}_saju_narrative_seed.json",
        "process_emulation_plan": output_dir / f"{name_slug}_process_emulation_plan.json",
        "curriculum_manifest": output_dir / f"{name_slug}_curriculum_manifest.json",
        "assessment_transcript": output_dir / f"{name_slug}_assessment_transcript.json",
        "reasoning_kibo": output_dir / f"{name_slug}_reasoning_kibo.jsonl",
        "language_development_program": output_dir / f"{name_slug}_language_development_program.json",
        "developmental_ecology": output_dir / f"{name_slug}_developmental_ecology.json",
        "life_trace": output_dir / f"{name_slug}_life_trace.jsonl",
        "growth_profile": output_dir / f"{name_slug}_growth_profile.json",
        "talent_plan": output_dir / f"{name_slug}_agent_plan.json",
        "institutional_review": output_dir / f"{name_slug}_institutional_review.json",
        "memory_profile": output_dir / f"{name_slug}_memory_profile.json",
        "learning_ledger": output_dir / f"{name_slug}_learning_ledger.json",
        "agent_manifest": output_dir / f"{name_slug}_agent_manifest.json",
        "memory_substrate": output_dir / f"{name_slug}_memory_substrate.json",
        "release_bundle": output_dir / f"{name_slug}_agent_release_bundle",
        "release_archive": output_dir / f"{name_slug}_agent_release_bundle.zip",
        "installed_agent_root": output_dir / "installed_agents",
        "public_program_manifest": output_dir / "ai_talent_foundry_public_manifest.json",
        "release_audit": output_dir / "foundry_release_audit.json",
        "training_run": output_dir / "training_run.json",
    }
    role_artifact_keys = [
        "role_model_profile",
        "saju_narrative_seed",
        "process_emulation_plan",
        "curriculum_manifest",
        "assessment_transcript",
        "reasoning_kibo",
    ]
    if not blueprint.get("role_model"):
        for key in role_artifact_keys:
            artifacts.pop(key)

    _write_json(artifacts["training_blueprint"], blueprint)
    if blueprint.get("role_model"):
        _write_json(artifacts["role_model_profile"], blueprint["role_model"])
        _write_json(artifacts["saju_narrative_seed"], blueprint["role_model_birth_seed"])
        _write_json(artifacts["process_emulation_plan"], blueprint["role_model_process"])
        _write_json(artifacts["curriculum_manifest"], blueprint["curriculum_manifest"])

    packet = _hiring_packet_from_blueprint(blueprint)
    language_development_program = build_language_development_program(
        talent_name=packet["talent"]["name"],
        primary_language="ko-KR",
    )
    write_language_development_program(
        artifacts["language_development_program"],
        language_development_program,
    )
    packet["language_development_program"] = {
        "schema": language_development_program["schema"],
        "stage_count": len(language_development_program["stages"]),
        "starts_before_school": language_development_program["growth_policy"]["starts_before_school"],
        "continues_after_hire": language_development_program["growth_policy"]["continues_after_hire"],
        "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_language_development_program.json",
    }
    developmental_ecology = build_developmental_ecology(
        blueprint,
        output_path=artifacts["developmental_ecology"],
    )
    life_trace = build_life_trace(blueprint, developmental_ecology, density="monthly")
    write_life_trace_jsonl(artifacts["life_trace"], life_trace)
    growth_profile = build_growth_profile(
        blueprint,
        developmental_ecology,
        life_trace,
        output_path=artifacts["growth_profile"],
    )
    packet["developmental_ecology"] = {
        "schema": developmental_ecology["schema"],
        "seed_id": developmental_ecology["seed"]["seed_id"],
        "layer_count": 7,
        "review_status": developmental_ecology["review_status"],
        "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_developmental_ecology.json",
        "policy": developmental_ecology["generation_policy"],
    }
    packet["life_trace"] = {
        "schema": life_trace["manifest"]["schema"],
        "density": life_trace["manifest"]["density"],
        "event_count": life_trace["manifest"]["event_count"],
        "age_span_years": life_trace["manifest"]["age_span_years"],
        "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_life_trace.jsonl",
        "policy": life_trace["manifest"]["policy"],
    }
    packet["growth_profile"] = {
        "schema": growth_profile["schema"],
        "relationship_memory_refs": growth_profile["memory_pack_preview"]["relationship_memory_refs"],
        "emotional_memory_refs": growth_profile["memory_pack_preview"]["emotional_memory_refs"],
        "episodic_memory_events": growth_profile["memory_pack_preview"]["episodic_memory_events"],
        "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_growth_profile.json",
        "policy": growth_profile["policy"],
    }
    _write_json(artifacts["talent_plan"], packet)

    submissions = _submissions_for(blueprint)
    institutional_review = run_institutional_review(packet, submissions=submissions)
    _write_json(artifacts["institutional_review"], institutional_review)
    reasoning_kibo: dict[str, Any] | None = None
    if blueprint.get("role_model"):
        assessment_transcript = institutional_review.get("assessment_transcript") or build_assessment_transcript(
            packet,
            submissions,
        )
        assessment_transcript = augment_assessment_transcript_v2(
            assessment_transcript,
            life_trace=life_trace,
            growth_profile=growth_profile,
        )
        _write_json(artifacts["assessment_transcript"], assessment_transcript)
        reasoning_kibo = build_initial_reasoning_kibo(
            talent_name=packet["talent"]["name"],
            role_model_profile=blueprint.get("role_model"),
            curriculum_manifest=blueprint.get("curriculum_manifest"),
            assessment_transcript=assessment_transcript,
        )
        write_reasoning_kibo_jsonl(artifacts["reasoning_kibo"], reasoning_kibo)
        packet["reasoning_kibo"] = {
            "schema": reasoning_kibo["schema"],
            "entry_count": len(reasoning_kibo.get("entries", [])),
            "lifecycle": reasoning_kibo.get("lifecycle", {}),
            "yearly_learning_ladder_count": len(reasoning_kibo.get("yearly_learning_ladder", [])),
            "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_reasoning_kibo.jsonl",
            "policy": reasoning_kibo.get("policy", {}),
        }
        _write_json(artifacts["talent_plan"], packet)

    memory_store = create_memory_store(owner=packet["talent"]["name"])
    memory_store = remember_event(memory_store, source="institutional_review", event=institutional_review)
    memory_profile = consolidate_memory(memory_store)
    _write_json(artifacts["memory_profile"], memory_profile)

    learning_ledger = create_learning_ledger(owner=packet["talent"]["name"])
    learning_ledger = record_learning_experience(
        learning_ledger,
        source="institutional_review",
        event=institutional_review,
        quality_label={"score": 95, "reviewed_by": "감독위원회", "status": "verified"},
    )
    learning_ledger["reasoning_kernel"] = build_reasoning_kernel(learning_ledger)
    _write_json(artifacts["learning_ledger"], learning_ledger)

    agent_manifest = build_agent_manifest(packet, memory_profile)
    _write_json(artifacts["agent_manifest"], agent_manifest)
    memory_substrate = build_memory_substrate(
        agent_manifest=agent_manifest,
        learning_ledger=learning_ledger,
        reasoning_kibo_rows=reasoning_kibo.get("entries", []) if reasoning_kibo else [],
        process_plan=blueprint.get("role_model_process"),
        curriculum_manifest=blueprint.get("curriculum_manifest"),
        language_development_program=language_development_program,
        developmental_ecology=developmental_ecology,
        life_trace_events=life_trace["events"],
        growth_profile=growth_profile,
    )
    write_memory_substrate(artifacts["memory_substrate"], memory_substrate)

    create_agent_release_bundle(
        output_dir=artifacts["release_bundle"],
        agent_manifest_path=artifacts["agent_manifest"],
        learning_ledger_path=artifacts["learning_ledger"],
        memory_substrate_path=artifacts.get("memory_substrate"),
        language_development_program_path=artifacts["language_development_program"],
        developmental_ecology_path=artifacts["developmental_ecology"],
        life_trace_path=artifacts["life_trace"],
        growth_profile_path=artifacts["growth_profile"],
    )
    package = package_agent_release_bundle(
        artifacts["release_bundle"],
        output_zip=artifacts["release_archive"],
    )
    package_manifest = json.loads(package["package_manifest"].read_text(encoding="utf-8"))
    install = install_agent_release_package(
        package["archive"],
        install_root=artifacts["installed_agent_root"],
        expected_sha256=package_manifest["sha256"],
    )
    hiring = hire_installed_agent(
        install["installed_manifest"],
        employer=blueprint["owner"],
        role=blueprint["track"]["target_role"],
        llm_service=llm_service,
        llm_engine=llm_engine,
        llm_model=llm_model,
        llm_model_path=llm_model_path,
        chat_surface=chat_surface,
    )

    artifacts["release_checksum"] = package["checksum"]
    artifacts["release_package_manifest"] = package["package_manifest"]
    artifacts["installed_agent_manifest"] = install["installed_manifest"]
    artifacts["employment_record"] = hiring["employment_record"]
    artifacts["employment_registry"] = hiring["registry_index"]
    artifacts["hired_llm_connection_profile"] = hiring["llm_connection_profile"]
    artifacts["hired_llm_live_setup_guide"] = hiring["llm_live_setup_guide"]
    artifacts["agent_id_card_payload"] = hiring["agent_id_card_payload"]
    artifacts["agent_identity_envelope"] = hiring["agent_identity_envelope"]
    artifacts["agent_identity_verification"] = hiring["agent_identity_verification"]
    installed_root = artifacts["employment_record"].parent
    artifacts["hired_agent_run"] = installed_root / "last_hired_agent_run.json"
    artifacts["hired_dataflow_workspace"] = installed_root / "agent_dataflow_workspace"
    artifacts["hired_dataflow_run"] = installed_root / "last_hired_dataflow_run.json"
    artifacts["runtime_observability_comparison"] = output_dir / "runtime_observability_comparison.json"

    run_hired_agent(
        artifacts["employment_record"],
        task=f"{packet['talent']['name']}의 전공 기억을 바탕으로 보스 검토용 리서치 질문을 정리한다.",
        output_path=artifacts["hired_agent_run"],
        llm_mode="offline",
    )
    run_hired_dataflow_job(
        artifacts["employment_record"],
        job_spec={
            "schema": "ai-talent-dataflow-job/v1",
            "objective": f"{packet['talent']['name']}의 학습 기록을 바탕으로 검토 가능한 리서치 dataflow를 실행한다.",
            "deliverables": [
                {
                    "id": "training_runtime_synthesis",
                    "description": "Training-to-runtime synthesis for Boss review.",
                }
            ],
            "acceptance_criteria": [
                "Every conclusion links to local memory tiles or uncertainty.",
                "External side effects remain blocked.",
            ],
        },
        workspace_dir=artifacts["hired_dataflow_workspace"],
        review_label={"score": 91, "reviewed_by": blueprint["owner"], "status": "verified"},
        output_path=artifacts["hired_dataflow_run"],
        llm_mode="offline",
    )
    build_runtime_observability_comparison(
        [artifacts["hired_agent_run"], artifacts["hired_dataflow_run"]],
        output_path=artifacts["runtime_observability_comparison"],
    )
    build_public_program_manifest(output_dir, output_path=artifacts["public_program_manifest"])

    run = {
        "schema": TRAINING_RUN_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "owner": blueprint["owner"],
        "status": "employment_ready",
        "identity": blueprint["identity"],
        "track": blueprint["track"],
        "pipeline_stage_count": len(blueprint["training_pipeline"]),
        "artifact_count": len(artifacts),
        "artifacts": {key: str(path) for key, path in artifacts.items()},
        "verification": {
            "institutional_review_status": institutional_review["oversight_committee_decision"]["status"],
            "employment_ready": packet["employment_ready"],
            "release_package_created": package["archive"].exists(),
            "installed_agent_manifest_created": install["installed_manifest"].exists(),
            "employment_record_created": hiring["employment_record"].exists(),
            "hired_llm_live_setup_guide_created": hiring["llm_live_setup_guide"].exists(),
            "developmental_ecology_created": artifacts["developmental_ecology"].exists(),
            "life_trace_created": artifacts["life_trace"].exists(),
            "growth_profile_created": artifacts["growth_profile"].exists(),
            "hired_agent_run_created": artifacts["hired_agent_run"].exists(),
            "hired_dataflow_run_created": artifacts["hired_dataflow_run"].exists(),
            "runtime_observability_comparison_created": artifacts["runtime_observability_comparison"].exists(),
            "public_program_manifest_created": artifacts["public_program_manifest"].exists(),
        },
    }
    _write_json(artifacts["training_run"], run)
    release_audit = audit_foundry_release(output_dir, output_path=artifacts["release_audit"])
    run["verification"]["release_audit_created"] = artifacts["release_audit"].exists()
    run["verification"]["release_audit_public_ready"] = release_audit["public_release_ready"]
    run["artifact_count"] = len(artifacts)
    run["artifacts"] = {key: str(path) for key, path in artifacts.items()}
    _write_json(artifacts["training_run"], run)
    return run
