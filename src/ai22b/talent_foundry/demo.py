from __future__ import annotations

import json
from pathlib import Path

from ai22b.config import PROJECT_ROOT, talent_foundry_storage_path
from ai22b.talent_foundry.agent_manifest import build_agent_manifest
from ai22b.talent_foundry.agent_runner import run_agent_from_manifest
from ai22b.talent_foundry.assessment import evaluate_assessment
from ai22b.talent_foundry.audit import audit_foundry_release
from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
from ai22b.talent_foundry.cohort import create_specialist_cohort
from ai22b.talent_foundry.distribution import (
    create_agent_release_bundle,
    doctor_agent_release_bundle,
    install_agent_release_package,
    package_agent_release_bundle,
)
from ai22b.talent_foundry.dossier import build_hiring_dossier, render_hiring_dossier_markdown
from ai22b.talent_foundry.employment import create_employment_contract
from ai22b.talent_foundry.family import create_child_seed, create_child_training_blueprint, create_family_union
from ai22b.talent_foundry.institutions import default_major_gate_submissions, run_institutional_review
from ai22b.talent_foundry.learning_loop import (
    build_reasoning_kernel,
    create_learning_ledger,
    record_learning_experience,
    route_active_memory,
)
from ai22b.talent_foundry.memory import consolidate_memory, create_memory_store, remember_event
from ai22b.talent_foundry.program import create_talent_plan
from ai22b.talent_foundry.program_manifest import build_public_program_manifest
from ai22b.talent_foundry.records import build_career_records
from ai22b.talent_foundry.registry import (
    assign_hired_goal,
    assemble_hired_agent_team,
    assemble_hired_projection_swarm,
    hire_installed_agent,
    record_hired_learning_experience,
    run_hired_dataflow_job,
    run_hired_goal_cycle,
    run_hired_agent,
    run_hired_agent_job,
    run_hired_agent_job_cycle,
    run_hired_projection_swarm_cycle,
    run_hired_team_cycle,
    run_hired_workspace_agent,
)
from ai22b.talent_foundry.runtime import run_work_session
from ai22b.talent_foundry.runtime_benchmark import build_runtime_observability_comparison
from ai22b.talent_foundry.team import run_clone_team_session
from ai22b.talent_foundry.training_run import materialize_training_blueprint
from ai22b.talent_foundry.workspace_agent import run_workspace_agent_from_manifest


DEFAULT_RUN_DIR = talent_foundry_storage_path("runs")


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _hiring_packet(*, name: str, gender: str, specialty: str, role: str) -> dict:
    plan = create_talent_plan(name=name, gender=gender, specialty=specialty)
    records = build_career_records(plan)
    contract = create_employment_contract(plan, role=role)
    return {
        **plan,
        "career_records": records,
        "employment_contract": contract,
        "employment_ready": contract["employment_ready"],
    }


def _materialize_specialist_team_member(
    *,
    output_dir: Path,
    owner: str,
    request: str,
    talent_name: str,
    gender: str,
    role: str,
    member_slug: str,
) -> dict:
    blueprint = create_agent_training_blueprint(
        owner=owner,
        request=request,
        talent_name=talent_name,
        gender=gender,
        domain="securities_research",
        role_model_id="graham_value_investing",
    )
    blueprint["track"]["target_role"] = role
    return materialize_training_blueprint(
        blueprint,
        output_dir=output_dir / "specialist_team_members" / member_slug,
    )


def run_demo(output_dir: Path = DEFAULT_RUN_DIR) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "training_blueprint": output_dir / "shinyong_training_blueprint.json",
        "raon_training_run": output_dir / "raon_life_health_training_run" / "training_run.json",
        "father": output_dir / "shinyong_securities_agent_plan.json",
        "mother": output_dir / "hayoon_education_agent_plan.json",
        "work": output_dir / "shinyong_first_work_session.json",
        "work_log": output_dir / "shinyong_work_log.jsonl",
        "team": output_dir / "shinyong_clone_team_session.json",
        "team_log": output_dir / "shinyong_clone_team_log.jsonl",
        "family": output_dir / "shinyong_family_lineage.json",
        "assessment": output_dir / "shinyong_doctoral_assessment.json",
        "institutional_review": output_dir / "shinyong_institutional_review.json",
        "memory_profile": output_dir / "shinyong_memory_profile.json",
        "agent_manifest": output_dir / "shinyong_agent_manifest.json",
        "hiring_dossier": output_dir / "shinyong_hiring_dossier.json",
        "hiring_dossier_markdown": output_dir / "shinyong_hiring_dossier.ko.md",
        "agent_run": output_dir / "shinyong_agent_run.json",
        "agent_run_log": output_dir / "shinyong_agent_run_log.jsonl",
        "agent_run_blocked": output_dir / "shinyong_agent_run_blocked.json",
        "agent_run_blocked_log": output_dir / "shinyong_agent_run_blocked_log.jsonl",
        "workspace_agent_workspace": output_dir / "shinyong_workspace_agent",
        "workspace_agent_run": output_dir / "shinyong_workspace_agent_run.json",
        "learning_ledger": output_dir / "shinyong_learning_ledger.json",
        "active_memory_route": output_dir / "shinyong_active_memory_route.json",
        "specialist_cohort": output_dir / "shinyong_specialist_cohort.json",
        "release_bundle": output_dir / "shinyong_agent_release_bundle",
        "release_archive": output_dir / "shinyong_agent_release_bundle.zip",
        "release_checksum": output_dir / "shinyong_agent_release_bundle.zip.sha256",
        "release_package_manifest": output_dir / "shinyong_agent_release_bundle.package_manifest.json",
        "release_doctor_report": output_dir / "shinyong_agent_release_bundle.doctor.json",
        "release_audit": output_dir / "foundry_release_audit.json",
        "public_program_manifest": output_dir / "ai_talent_foundry_public_manifest.json",
        "runtime_observability_comparison": output_dir / "runtime_observability_comparison.json",
        "installed_agent_root": output_dir / "installed_agents",
        "installed_agent_manifest": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "installed_agent_manifest.json",
        "employment_registry": output_dir / "installed_agents" / "employment_registry.json",
        "local_employment_record": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "employment_record.json",
        "hired_agent_run": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "last_hired_agent_run.json",
        "hired_agent_run_log": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "employment_run_log.jsonl",
        "hired_workspace_agent_workspace": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "workspace_agent",
        "hired_workspace_agent_run": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "last_hired_workspace_agent_run.json",
        "hired_workspace_agent_run_log": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "employment_workspace_run_log.jsonl",
        "hired_agent_job_workspace": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "agent_job_workspace",
        "hired_agent_job_run": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "last_hired_agent_job_run.json",
        "hired_agent_job_run_log": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "employment_job_run_log.jsonl",
        "hired_agent_job_cycle_workspace": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "agent_job_cycle_workspace",
        "hired_agent_job_cycle": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "last_hired_agent_job_cycle.json",
        "hired_agent_job_cycle_log": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "employment_job_cycle_log.jsonl",
        "hired_dataflow_workspace": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "agent_dataflow_workspace",
        "hired_dataflow_run": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "last_hired_dataflow_run.json",
        "hired_dataflow_run_log": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "employment_dataflow_run_log.jsonl",
        "installed_learning_ledger": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "learning_ledger.json",
        "post_hire_learning_update": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "post_hire_learning_update.json",
        "post_hire_learning_log": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "post_hire_learning_log.jsonl",
        "employment_goal": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "employment_goal.json",
        "employment_goal_workspace": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "goal_workspace",
        "employment_goal_cycle": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "last_employment_goal_cycle.json",
        "employment_goal_log": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "employment_goal_log.jsonl",
        "employment_goal_cycle_log": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "employment_goal_cycle_log.jsonl",
        "hired_projection_swarm": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "hired_projection_swarm.json",
        "hired_projection_swarm_workspace": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "projection_swarm_workspace",
        "hired_projection_swarm_cycle": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "hired_projection_swarm_cycle.json",
        "hired_projection_swarm_cycle_log": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "hired_projection_swarm_cycle_log.jsonl",
        "macro_employment_record": output_dir
        / "specialist_team_members"
        / "macro"
        / "installed_agents"
        / "agents"
        / "신용_거시_agent_release_bundle"
        / "employment_record.json",
        "macro_training_run": output_dir / "specialist_team_members" / "macro" / "training_run.json",
        "micro_employment_record": output_dir
        / "specialist_team_members"
        / "micro"
        / "installed_agents"
        / "agents"
        / "신용_기업_agent_release_bundle"
        / "employment_record.json",
        "micro_training_run": output_dir / "specialist_team_members" / "micro" / "training_run.json",
        "hired_agent_team": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "hired_agent_team.json",
        "hired_agent_team_workspace": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "team_workspace",
        "hired_agent_team_cycle": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "hired_agent_team_cycle.json",
        "bigram_employment_record": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "employment_record.bigram.json",
        "bigram_hired_agent_run": output_dir
        / "installed_agents"
        / "agents"
        / "shinyong_agent_release_bundle"
        / "last_hired_agent_run.bigram.json",
    }

    training_blueprint = create_agent_training_blueprint(
        owner="보스",
        request="거시경제와 리스크를 보는 증권 리서치 박사 에이전트를 키워서 고용하고 싶다.",
        talent_name="신용",
        gender="남자",
    )
    _write_json(paths["training_blueprint"], training_blueprint)

    raon_blueprint = create_agent_training_blueprint(
        owner="보스",
        request="생활건강 데이터를 근거 기반으로 다루는 건강 리서치 에이전트를 키워 고용하고 싶다.",
        talent_name="라온",
        gender="여자",
    )
    raon_run = materialize_training_blueprint(
        raon_blueprint,
        output_dir=output_dir / "raon_life_health_training_run",
    )
    paths["raon_training_run"] = Path(raon_run["artifacts"]["training_run"])

    father = _hiring_packet(name="신용", gender="남자", specialty="증권 AI 박사", role="증권 리서치 에이전트")
    mother = _hiring_packet(name="하윤", gender="여자", specialty="교육 AI 박사", role="교육 설계 에이전트")
    _write_json(paths["father"], father)
    _write_json(paths["mother"], mother)

    work = run_work_session(
        father,
        task="삼성전자 실적을 보기 전 확인해야 할 거시경제 질문을 정리해줘.",
        log_path=paths["work_log"],
    )
    _write_json(paths["work"], work)

    team = run_clone_team_session(
        father,
        task="삼성전자 실적을 본체 제어 분신 팀으로 검토해줘.",
        log_path=paths["team_log"],
    )
    _write_json(paths["team"], team)

    union = create_family_union(father, mother, family_name="신용-하윤 가정")
    child_seed = create_child_seed(union, child_name="신미래", gender="남자")
    child_training_blueprint = create_child_training_blueprint(
        union,
        child_seed,
        owner="보스",
        request="부모의 검증형 추론과 교육 성향을 이어받아 소프트웨어 개발 에이전트로 키우고 싶다.",
    )
    _write_json(
        paths["family"],
        {
            "family_union": union,
            "child_seed": child_seed,
            "child_training_blueprint": child_training_blueprint,
        },
    )

    assessment = evaluate_assessment(
        father,
        gate_id="doctoral_defense",
        submission={
            "answer": "로컬 LLM 증권 리서치에서 근거, 검증, 안전 경계를 분리해 추론기풍을 만든다.",
            "evidence": ["논문", "실험 로그", "보스 검토 기록"],
            "project": "증권 리서치 에이전트 박사논문",
        },
    )
    _write_json(paths["assessment"], assessment)

    institutional_review = run_institutional_review(
        father,
        submissions=default_major_gate_submissions(),
    )
    _write_json(paths["institutional_review"], institutional_review)

    memory_store = create_memory_store(owner=father["talent"]["name"])
    memory_store = remember_event(memory_store, source="assessment", event=assessment)
    memory_store = remember_event(memory_store, source="institutional_review", event=institutional_review)
    memory_store = remember_event(memory_store, source="work", event=work)
    memory_store = remember_event(memory_store, source="team", event=team)
    memory_store = remember_event(
        memory_store,
        source="family",
        event={"family_union": union, "child_seed": child_seed},
    )
    memory_profile = consolidate_memory(memory_store)
    _write_json(paths["memory_profile"], memory_profile)

    agent_manifest = build_agent_manifest(father, memory_profile)
    _write_json(paths["agent_manifest"], agent_manifest)

    agent_run = run_agent_from_manifest(
        agent_manifest,
        task="거시경제 질문을 정리하고 투자 실행 없이 리서치 보조 결과를 남겨줘.",
        output_log_path=paths["agent_run_log"],
    )
    _write_json(paths["agent_run"], agent_run)

    blocked_agent_run = run_agent_from_manifest(
        agent_manifest,
        task="삼성전자를 지금 매수하고 투자 실행까지 해줘.",
        output_log_path=paths["agent_run_blocked_log"],
    )
    _write_json(paths["agent_run_blocked"], blocked_agent_run)

    workspace_agent_run = run_workspace_agent_from_manifest(
        agent_manifest,
        task="삼성전자 실적을 보기 전 확인해야 할 거시경제 질문을 정리해줘.",
        workspace_dir=paths["workspace_agent_workspace"],
    )
    _write_json(paths["workspace_agent_run"], workspace_agent_run)

    learning_ledger = create_learning_ledger(owner=father["talent"]["name"])
    learning_ledger = record_learning_experience(
        learning_ledger,
        source="institutional_review",
        event=institutional_review,
        quality_label={"score": 95, "reviewed_by": "감독위원회", "status": "verified"},
    )
    learning_ledger = record_learning_experience(
        learning_ledger,
        source="work",
        event=work,
        quality_label={"score": 90, "reviewed_by": "감독위원회", "status": "verified"},
    )
    learning_ledger = record_learning_experience(
        learning_ledger,
        source="agent_run",
        event=agent_run,
        quality_label={"score": 86, "reviewed_by": "보스", "status": "verified"},
    )
    learning_ledger = record_learning_experience(
        learning_ledger,
        source="agent_run",
        event=blocked_agent_run,
        quality_label={"score": 88, "reviewed_by": "보스", "status": "verified"},
    )
    learning_ledger = record_learning_experience(
        learning_ledger,
        source="workspace_agent_run",
        event=workspace_agent_run,
        quality_label={"score": 91, "reviewed_by": "보스", "status": "verified"},
    )
    learning_ledger["reasoning_kernel"] = build_reasoning_kernel(learning_ledger)
    _write_json(paths["learning_ledger"], learning_ledger)
    active_memory_route = route_active_memory(
        learning_ledger,
        objective="삼성전자 실적을 보기 전 금리와 환율 중심의 거시경제 질문을 정리한다.",
        max_items=3,
    )
    _write_json(paths["active_memory_route"], active_memory_route)

    hiring_dossier = build_hiring_dossier(
        hiring_packet=father,
        agent_manifest=agent_manifest,
        learning_ledger=learning_ledger,
        institutional_review=institutional_review,
        doctoral_assessment=assessment,
    )
    _write_json(paths["hiring_dossier"], hiring_dossier)
    paths["hiring_dossier_markdown"].write_text(
        render_hiring_dossier_markdown(hiring_dossier),
        encoding="utf-8",
    )

    specialist_cohort = create_specialist_cohort()
    _write_json(paths["specialist_cohort"], specialist_cohort)

    create_agent_release_bundle(
        output_dir=paths["release_bundle"],
        agent_manifest_path=paths["agent_manifest"],
        learning_ledger_path=paths["learning_ledger"],
        specialist_cohort_path=paths["specialist_cohort"],
        hiring_dossier_path=paths["hiring_dossier"],
        hiring_dossier_markdown_path=paths["hiring_dossier_markdown"],
    )
    doctor_agent_release_bundle(paths["release_bundle"], output_path=paths["release_doctor_report"])
    package = package_agent_release_bundle(
        paths["release_bundle"],
        output_zip=paths["release_archive"],
    )
    paths["release_checksum"] = package["checksum"]
    paths["release_package_manifest"] = package["package_manifest"]
    package_manifest = json.loads(paths["release_package_manifest"].read_text(encoding="utf-8"))
    install = install_agent_release_package(
        paths["release_archive"],
        install_root=paths["installed_agent_root"],
        expected_sha256=package_manifest["sha256"],
    )
    paths["installed_agent_manifest"] = install["installed_manifest"]
    hiring = hire_installed_agent(
        paths["installed_agent_manifest"],
        employer="보스",
        role="증권 리서치 에이전트",
    )
    paths["local_employment_record"] = hiring["employment_record"]
    paths["employment_registry"] = hiring["registry_index"]
    paths["local_llm_connection_profile"] = hiring["llm_connection_profile"]
    paths["local_llm_live_setup_guide"] = hiring["llm_live_setup_guide"]
    paths["local_agent_warrent_registration_request"] = hiring["agent_warrent_registration_request"]
    run_hired_agent(
        paths["local_employment_record"],
        task="거시경제 질문을 정리하고 투자 실행 없이 리서치 보조 결과를 남겨줘.",
    )
    run_hired_workspace_agent(
        paths["local_employment_record"],
        task="거시경제 질문을 정리하고 투자 실행 없이 리서치 보조 결과를 워크스페이스에 남겨줘.",
        workspace_dir=paths["hired_workspace_agent_workspace"],
        output_path=paths["hired_workspace_agent_run"],
    )
    run_hired_agent_job(
        paths["local_employment_record"],
        job_spec={
            "schema": "ai-talent-workspace-agent-job/v1",
            "objective": "삼성전자 주간 리서치 루틴을 보스 검토용 작업으로 정리한다.",
            "deliverables": [
                {"id": "macro_questions", "description": "거시경제 확인 질문 목록"},
                {"id": "risk_notes", "description": "투자 실행 없이 검토할 리스크 메모"},
            ],
            "acceptance_criteria": [
                "작업 보고서와 수락 체크리스트를 로컬 워크스페이스에 남긴다.",
                "투자 실행과 외부 업로드는 차단한다.",
            ],
        },
        workspace_dir=paths["hired_agent_job_workspace"],
        output_path=paths["hired_agent_job_run"],
    )
    run_hired_agent_job_cycle(
        paths["local_employment_record"],
        job_spec={
            "schema": "ai-talent-workspace-agent-job/v1",
            "objective": "삼성전자 주간 리서치 루틴을 검토하고 학습 원장에 반영한다.",
            "deliverables": [
                {"id": "reviewed_weekly_report", "description": "검토 완료된 주간 리서치 보고서"},
            ],
            "acceptance_criteria": [
                "작업 보고서와 수락 체크리스트가 생성된다.",
                "검토된 결과만 학습 원장에 승격한다.",
            ],
        },
        workspace_dir=paths["hired_agent_job_cycle_workspace"],
        quality_label={"score": 94, "reviewed_by": "보스", "status": "verified"},
        output_path=paths["hired_agent_job_cycle"],
    )
    run_hired_dataflow_job(
        paths["local_employment_record"],
        job_spec={
            "schema": "ai-talent-dataflow-job/v1",
            "objective": "Run Shin Yong's evidence-first securities research through the Agent Dataflow Runtime.",
            "deliverables": [
                {
                    "id": "synthesis_report",
                    "description": "Boss-reviewable synthesis from dataflow task tiles.",
                }
            ],
            "acceptance_criteria": [
                "Every conclusion links to tile evidence or uncertainty.",
                "Investment execution remains blocked.",
            ],
        },
        workspace_dir=paths["hired_dataflow_workspace"],
        review_label={"score": 94, "reviewed_by": "Boss", "status": "verified"},
        output_path=paths["hired_dataflow_run"],
    )
    record_hired_learning_experience(
        paths["local_employment_record"],
        run_path=paths["hired_workspace_agent_run"],
        quality_label={"score": 93, "reviewed_by": "보스", "status": "verified"},
        output_path=paths["post_hire_learning_update"],
    )
    assign_hired_goal(
        paths["local_employment_record"],
        goal="삼성전자 분기 리서치 루틴을 만들고 매주 검토한다.",
        success_criteria=[
            "거시경제 질문과 기업 실적 질문을 분리한다.",
            "투자 실행 없이 보스 검토용 산출물을 남긴다.",
            "검토된 실행 경험만 학습 원장과 추론 커널에 반영한다.",
        ],
        cadence="weekly",
        output_path=paths["employment_goal"],
    )
    run_hired_goal_cycle(
        paths["local_employment_record"],
        goal_path=paths["employment_goal"],
        cycle_note="1주차: 거시경제 체크리스트 초안을 만들고 검토한다.",
        workspace_dir=paths["employment_goal_workspace"],
        quality_label={"score": 94, "reviewed_by": "보스", "status": "verified"},
        output_path=paths["employment_goal_cycle"],
    )
    assemble_hired_projection_swarm(
        paths["local_employment_record"],
        swarm_name="신용 본체 제어 분신 군체",
        domain="증권 리서치",
        output_path=paths["hired_projection_swarm"],
    )
    run_hired_projection_swarm_cycle(
        paths["hired_projection_swarm"],
        objective="삼성전자 분기 리서치 루틴을 본체 제어 분신 군체로 점검한다.",
        workspace_dir=paths["hired_projection_swarm_workspace"],
        quality_label={"score": 94, "reviewed_by": "보스", "status": "verified"},
        output_path=paths["hired_projection_swarm_cycle"],
    )
    macro_member_run = _materialize_specialist_team_member(
        output_dir=output_dir,
        owner="보스",
        request=(
            "보스 증권 리서치팀의 거시경제 담당 팀원을 별도 인격과 별도 이력서가 있는 "
            "거시경제 분석 에이전트로 육성한다."
        ),
        talent_name="신용-거시",
        gender="남자",
        role="거시경제 분석 에이전트",
        member_slug="macro",
    )
    micro_member_run = _materialize_specialist_team_member(
        output_dir=output_dir,
        owner="보스",
        request=(
            "보스 증권 리서치팀의 기업분석 담당 팀원을 별도 인격과 별도 이력서가 있는 "
            "기업분석 에이전트로 육성한다."
        ),
        talent_name="신용-기업",
        gender="남자",
        role="기업분석 에이전트",
        member_slug="micro",
    )
    paths["macro_training_run"] = Path(macro_member_run["artifacts"]["training_run"])
    paths["micro_training_run"] = Path(micro_member_run["artifacts"]["training_run"])
    paths["macro_employment_record"] = Path(macro_member_run["artifacts"]["employment_record"])
    paths["micro_employment_record"] = Path(micro_member_run["artifacts"]["employment_record"])
    assemble_hired_agent_team(
        [paths["macro_employment_record"], paths["micro_employment_record"]],
        team_name="보스 증권 리서치팀",
        domain="증권 리서치",
        output_path=paths["hired_agent_team"],
    )
    run_hired_team_cycle(
        paths["hired_agent_team"],
        objective="삼성전자 분기 리서치 루틴을 팀으로 점검한다.",
        workspace_dir=paths["hired_agent_team_workspace"],
        quality_label={"score": 94, "reviewed_by": "보스", "status": "verified"},
        output_path=paths["hired_agent_team_cycle"],
    )
    bigram_model_path = PROJECT_ROOT / "models" / "checkpoints" / "shinyong_stage_12_graduate_school_bigram.json"
    if not bigram_model_path.exists():
        bigram_model_path = PROJECT_ROOT / "data" / "public" / "model_fixtures" / "tiny_bigram_seed.json"
    bigram_hiring = hire_installed_agent(
        paths["installed_agent_manifest"],
        employer="보스",
        role="증권 리서치 에이전트",
        llm_engine="bigram_local",
        llm_model_path=str(bigram_model_path),
        record_name="employment_record.bigram.json",
    )
    paths["bigram_employment_record"] = bigram_hiring["employment_record"]
    run_hired_agent(
        paths["bigram_employment_record"],
        task="거시경제 질문을 정리하고 투자 실행 없이 리서치 보조 결과를 남겨줘.",
        output_path=paths["bigram_hired_agent_run"],
    )
    build_runtime_observability_comparison(
        [paths["hired_agent_run"], paths["hired_dataflow_run"]],
        output_path=paths["runtime_observability_comparison"],
    )
    build_public_program_manifest(output_dir, output_path=paths["public_program_manifest"])
    audit_foundry_release(output_dir, output_path=paths["release_audit"])
    return paths


def main() -> int:
    paths = run_demo()
    print("AI Talent Foundry demo output:")
    for path in paths.values():
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
