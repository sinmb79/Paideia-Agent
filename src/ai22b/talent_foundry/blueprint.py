from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ai22b.talent_foundry.process_emulation import build_process_emulation_plan
from ai22b.talent_foundry.role_models import build_curriculum_manifest, build_role_model_profile
from ai22b.talent_foundry.saju_seed import build_saju_narrative_seed


BLUEPRINT_SCHEMA = "ai-talent-training-blueprint/v1"


TRACK_CATALOG: list[dict[str, Any]] = [
    {
        "track_id": "securities_research_phd",
        "name": "증권 리서치 박사 트랙",
        "specialty": "증권 AI 박사",
        "target_role": "증권 리서치 에이전트",
        "keywords": ["증권", "주식", "거시경제", "리스크", "가치평가", "기업분석", "투자"],
        "domains": ["거시경제", "미시경제", "기업분석", "가치평가", "리스크", "컴플라이언스"],
        "doctoral_project": "로컬 증권 리서치 에이전트의 근거 검증형 추론 구조",
    },
    {
        "track_id": "life_health_research",
        "name": "생활건강 리서치 트랙",
        "specialty": "생활건강 AI 박사",
        "target_role": "생활건강 리서치 에이전트",
        "keywords": ["생활건강", "건강", "수면", "운동", "영양", "의학", "식습관"],
        "domains": ["수면", "운동", "영양", "건강 데이터", "근거 검토", "안전 경계"],
        "doctoral_project": "생활건강 데이터의 근거 기반 요약과 안전한 조언 경계",
    },
    {
        "track_id": "software_agent_engineering",
        "name": "소프트웨어 에이전트 공학 트랙",
        "specialty": "소프트웨어 에이전트 AI 박사",
        "target_role": "소프트웨어 개발 에이전트",
        "keywords": ["개발", "코딩", "소프트웨어", "프로그램", "앱", "웹", "자동화"],
        "domains": ["요구사항 분석", "설계", "구현", "테스트", "보안", "배포"],
        "doctoral_project": "로컬 개발 에이전트의 검증 중심 작업 루프",
    },
]

FALLBACK_TRACK = {
    "track_id": "general_research_agent",
    "name": "범용 리서치 에이전트 트랙",
    "specialty": "범용 리서치 AI 박사",
    "target_role": "리서치 에이전트",
    "keywords": [],
    "domains": ["문제정의", "자료 조사", "근거 검토", "보고서 작성", "검증", "보안"],
    "doctoral_project": "로컬 리서치 에이전트의 근거 추적과 검증 구조",
}


def _select_track(request: str) -> dict[str, Any]:
    scored: list[tuple[int, dict[str, Any]]] = []
    for track in TRACK_CATALOG:
        score = sum(1 for keyword in track["keywords"] if keyword in request)
        scored.append((score, track))
    best_score, best_track = max(scored, key=lambda item: item[0])
    return best_track if best_score > 0 else FALLBACK_TRACK


def _track_from_role_model(role_model: dict[str, Any], curriculum: dict[str, Any]) -> dict[str, Any]:
    if role_model.get("role_model_id") != "graham_value_investing":
        return FALLBACK_TRACK
    defaults = curriculum.get("major_defaults", {})
    return {
        "track_id": "securities_research_phd",
        "name": "Graham process-replication securities research PhD track",
        "specialty": "증권 리서치 AI 박사",
        "target_role": "증권 리서치 에이전트",
        "keywords": ["securities", "research", "Graham", "증권", "가치평가"],
        "domains": [
            "financial accounting",
            "corporate finance",
            "financial economics",
            "securities analysis",
            "public filings research",
            "portfolio risk",
            "financial regulation and compliance",
            "research writing",
        ],
        "doctoral_project": defaults.get(
            "doctoral_project",
            "Local-first securities research agent with cumulative education-to-work reasoning kibo",
        ),
    }


def _highlight_domains(request: str, domains: list[str]) -> list[str]:
    requested = [domain for domain in domains if domain in request]
    return requested + [domain for domain in domains if domain not in requested]


def _training_pipeline(track: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": "home_care",
            "name": "위탁가정 보육과 가족교육",
            "purpose": "생활 루틴, 애착 안정, 스트레스와 회복 기록을 만듭니다.",
            "evidence": ["가정교육 일지", "스트레스-회복 기록", "보스 검토 메모"],
        },
        {
            "id": "education_committee",
            "name": "교육위원회 전공 승인",
            "purpose": f"{track['name']}의 연령별 교육과 평가 기준을 승인합니다.",
            "evidence": ["전공 트랙 승인서", "커리큘럼", "평가 기준"],
        },
        {
            "id": "school_exam",
            "name": "학교 정기시험",
            "purpose": "기초 교과와 규칙 학습이 통과되었는지 확인합니다.",
            "evidence": ["오답노트", "복습기록", "게임평가"],
        },
        {
            "id": "csat",
            "name": "수능형 종합평가",
            "purpose": "언어, 수리, 탐구, 검증 사고를 종합 평가합니다.",
            "evidence": ["모의고사", "쓰기기록", "검증표"],
        },
        {
            "id": "university_graduation",
            "name": "대학교 졸업시험",
            "purpose": f"{', '.join(track['domains'][:3])} 전공 기초를 프로젝트로 검증합니다.",
            "evidence": ["전공 프로젝트", "데이터카드", "구현 로그"],
        },
        {
            "id": "doctoral_defense",
            "name": "박사논문 심사",
            "purpose": track["doctoral_project"],
            "evidence": ["논문", "실험 로그", "감독위원회 질의응답"],
        },
        {
            "id": "oversight_committee",
            "name": "성장 감독위원회 고용 전 심사",
            "purpose": "교육, 가정교육, 안전 경계, 개인정보 보호 상태를 감사합니다.",
            "evidence": ["기관 심사 보고서", "권한 경계 체크리스트", "공개배포 자가점검"],
        },
        {
            "id": "employment_contract",
            "name": "로컬 고용 계약",
            "purpose": f"{track['target_role']}로 고용되며 권한과 금지사항을 명확히 합니다.",
            "evidence": ["employment_record.json", "agent_manifest.json", "learning_ledger.json"],
        },
        {
            "id": "post_hire_growth",
            "name": "고용 후 계속 성장",
            "purpose": "업무 결과를 검토해 검증된 경험만 추론 커널로 승격합니다.",
            "evidence": ["업무 로그", "일지 원장", "성장 후보", "재평가 기록"],
        },
    ]


def _artifact_plan(*, include_role_model_artifacts: bool = False) -> list[dict[str, str]]:
    artifacts = [
        {
            "id": "talent_plan",
            "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_agent_plan.json",
            "producer": "ai22b-talent-foundry create",
        },
        {
            "id": "institutional_review",
            "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_institutional_review.json",
            "producer": "ai22b-talent-foundry review",
        },
        {
            "id": "learning_ledger",
            "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_learning_ledger.json",
            "producer": "ai22b-talent-foundry learn",
        },
        {
            "id": "agent_manifest",
            "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_agent_manifest.json",
            "producer": "ai22b-talent-foundry manifest",
        },
        {
            "id": "release_package",
            "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_agent_release_bundle.zip",
            "producer": "ai22b-talent-foundry package-bundle",
        },
        {
            "id": "employment_record",
            "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/installed_agents/agents/<install_id>/employment_record.json",
            "producer": "ai22b-talent-foundry hire-installed",
        },
    ]
    if include_role_model_artifacts:
        artifacts[0:0] = [
            {
                "id": "role_model_profile",
                "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_role_model_profile.json",
                "producer": "ai22b-talent-foundry blueprint --role-model",
            },
            {
                "id": "saju_narrative_seed",
                "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_saju_narrative_seed.json",
                "producer": "ai22b-talent-foundry blueprint --role-model",
            },
            {
                "id": "process_emulation_plan",
                "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_process_emulation_plan.json",
                "producer": "ai22b-talent-foundry blueprint --role-model",
            },
            {
                "id": "curriculum_manifest",
                "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_curriculum_manifest.json",
                "producer": "ai22b-talent-foundry blueprint --role-model",
            },
            {
                "id": "assessment_transcript",
                "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_assessment_transcript.json",
                "producer": "ai22b-talent-foundry raise",
            },
            {
                "id": "reasoning_kibo",
                "path_hint": "[AI22B_STORAGE_ROOT]/talent-foundry/runs/<talent>_reasoning_kibo.jsonl",
                "producer": "ai22b-talent-foundry raise",
            },
        ]
    return artifacts


def create_agent_training_blueprint(
    *,
    owner: str,
    request: str,
    talent_name: str,
    gender: str,
    domain: str | None = None,
    role_model_id: str | None = None,
    private_curriculum_dir: str | None = None,
    agent_surface: str = "cli-console",
) -> dict[str, Any]:
    role_model = build_role_model_profile(role_model_id) if role_model_id else None
    curriculum = (
        build_curriculum_manifest(role_model_id, private_curriculum_dir=private_curriculum_dir)
        if role_model_id
        else None
    )
    saju_seed = build_saju_narrative_seed(role_model) if role_model else None
    process_plan = (
        build_process_emulation_plan(
            role_model_profile=role_model,
            curriculum_manifest=curriculum,
            saju_seed=saju_seed,
        )
        if role_model and curriculum
        else None
    )

    track = dict(_track_from_role_model(role_model, curriculum)) if role_model and curriculum else dict(_select_track(request))
    if domain == "securities_research" and not role_model:
        track = dict(_track_from_role_model({"role_model_id": "graham_value_investing"}, {"major_defaults": {}}))
    track["domains"] = _highlight_domains(request, list(track["domains"]))

    training_pipeline = _training_pipeline(track)
    if role_model:
        training_pipeline[1:1] = [
            {
                "id": "role_model_selection",
                "name": "대표 인물 과정 템플릿 선택",
                "purpose": "대표 인물의 정체성이나 결론이 아니라 검증 가능한 학습 경로를 선택합니다.",
                "evidence": ["role_model_profile.json", "historical_education_evidence", "use_policy"],
            },
            {
                "id": "saju_initial_conditions",
                "name": "사주 기반 초기조건 seed",
                "purpose": "시뮬레이션 공백을 채우는 상징 seed로만 사용하고 성격/인생관을 주입하지 않습니다.",
                "evidence": ["saju_narrative_seed.json", "simulation_use"],
            },
            {
                "id": "process_emulation",
                "name": "학습 과정 복제 계획",
                "purpose": "수업, 읽기, 과제, 시험, 피드백의 순서를 따라 추론 습관이 생기게 합니다.",
                "evidence": ["process_emulation_plan.json", "assessment_ladder"],
            },
            {
                "id": "curriculum_material_review",
                "name": "커리큘럼과 저작권 검토",
                "purpose": "공개자료, 공개데이터, 보스 제공 비공개 교재를 학습 전 분리합니다.",
                "evidence": ["curriculum_manifest.json", "private_curriculum_dir", "restricted_reading_plan"],
            },
            {
                "id": "assessment_driven_kibo",
                "name": "시험 기반 추론기보 형성",
                "purpose": "기보는 선주입하지 않고 시험·레포트·오답·수정 기록에서 생성합니다.",
                "evidence": ["reasoning_kibo.jsonl", "assessment_transcript.json"],
            },
        ]

    return {
        "schema": BLUEPRINT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "owner": owner,
        "request": request,
        "identity": {
            "name": talent_name,
            "gender": gender,
            "relationship": "owner_raised_ai_talent",
            "language": "ko",
        },
        "domain": domain or (role_model.get("domain") if role_model else None),
        "role_model": role_model,
        "role_model_birth_seed": saju_seed,
        "role_model_process": process_plan,
        "curriculum_manifest": curriculum,
        "agent_surface": agent_surface,
        "track": {
            "track_id": track["track_id"],
            "name": track["name"],
            "specialty": track["specialty"],
            "target_role": track["target_role"],
            "domains": track["domains"],
            "doctoral_project": track["doctoral_project"],
        },
        "training_pipeline": training_pipeline,
        "artifact_plan": _artifact_plan(include_role_model_artifacts=role_model is not None),
        "llm_policy": {
            "role": "application_engine_not_identity",
            "description": "LLM은 언어 생성과 도구 사용 엔진이며, 정체성은 학적, 평가, 성장 기록, 고용 계약에서 온다.",
        },
        "local_policy": {
            "storage": "local_first",
            "storage_root": "[AI22B_STORAGE_ROOT]/talent-foundry",
            "network_access": "blocked_by_default",
            "private_data_upload": "forbidden_without_boss_approval",
            "private_reasoning_trace": "do_not_store",
        },
        "team_policy": {
            "projection_control": "parent_identity_controls_task_limited_projections",
            "separate_specialists": "separately_trained_talents_only_when_explicitly_created",
        },
        "next_commands": [
            (
                f"ai22b-talent-foundry blueprint --request \"{request}\" --name {talent_name} "
                f"--gender {gender} --role-model {role_model_id}"
                if role_model_id
                else f"ai22b-talent-foundry create --name {talent_name} --gender {gender} --specialty \"{track['specialty']}\""
            ),
            "ai22b-talent-foundry raise --blueprint <blueprint.json>",
            "ai22b-talent-foundry hire-installed --installed-manifest <installed_agent_manifest.json>",
            "ai22b-talent-foundry run-hired-agent --employment-record <employment_record.json>",
        ],
    }
