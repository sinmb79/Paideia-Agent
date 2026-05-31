from __future__ import annotations

from typing import Any

from ai22b.talent_foundry.reasoning import build_reasoning_style


def build_career_records(plan: dict[str, Any]) -> dict[str, Any]:
    talent = plan["talent"]
    gates = plan["assessment_gates"]
    major_goal = talent["major_goal"]
    graduate_path = plan["education_path"]["graduate_school"]
    university_path = plan["education_path"]["university"]
    domains = graduate_path.get("required_domains", [])
    domain_summary = ", ".join(domains[:3]) if domains else major_goal
    role_model = plan.get("role_model_inspiration")
    curriculum = plan.get("curriculum_manifest") or {}
    role_model_id = role_model.get("role_model_id") if role_model else None
    assessments = [
        {"gate": "school_exam", "score": 88},
        {"gate": "csat", "score": 91},
        {"gate": "university_graduation", "score": 93},
        {"gate": "doctoral_defense", "score": 92},
    ]
    reasoning_style = build_reasoning_style(
        experiences=[
            "숙제를 미뤘다가 다시 계획표를 세움",
            "부모에게 야단을 맞고 이유와 다음 행동을 기록함",
            "친구와 다투고 사과와 화해 과정을 남김",
            "증권 데이터 프로젝트에서 오류를 인정하고 재검증함",
        ],
        assessments=assessments,
    )
    grades = [
        {"stage": "초중고", "summary": "기초 교과와 생활규칙 통과", "gpa": "우수"},
        {"stage": "대학교", "summary": university_path["major"], "gpa": "4.2/4.5"},
        {"stage": "대학원", "summary": graduate_path["major"], "gpa": "4.3/4.5"},
    ]
    papers = [
        {
            "title": f"로컬 LLM 기반 {major_goal} 에이전트의 검증형 기억 구조",
            "level": "doctoral_dissertation",
            "status": "defended",
        }
    ]
    activities = [
        "태권도와 팀 운동을 통한 규칙 학습",
        "영어 발표와 해외 연수 경험",
        "AI 데이터 분석 프로젝트",
        "군 복무형 규율, 보안, 협업 훈련",
    ]
    awards_discipline_recovery = [
        {"type": "award", "label": "전공 프로젝트 우수", "recovery": None},
        {"type": "discipline", "label": "숙제 미제출 경고", "recovery": "계획표 재작성 후 제출 완료"},
        {"type": "recovery", "label": "친구와 다툰 뒤 사과와 화해", "recovery": "상대 입장 기록"},
    ]
    major_projects = [
        f"{domain_summary} 근거를 분리해 보는 리서치 노트",
        f"{major_goal} 안전 경계와 검증 체크리스트",
    ]
    if role_model_id == "graham_value_investing":
        major_projects.extend(
            [
                "Graham-style margin-of-safety valuation memo",
                "SEC filing evidence table and downside case review",
            ]
        )
    recommendations = [
        {"from": "교육위원회", "note": "근거 확인과 회복 기록이 안정적이다."},
        {"from": "감독위원회", "note": "투자 실행 권한 없이 분석 보조로 고용 가능하다."},
    ]
    academic_record = {
        "name": talent["name"],
        "gender": talent["gender"],
        "birth": talent["birth"],
        "family": talent["family"],
        "major_goal": talent["major_goal"],
        "education": plan["education_path"],
        "grades": grades,
        "papers": papers,
        "activities": activities,
        "awards_discipline_recovery": awards_discipline_recovery,
        "major_projects": major_projects,
        "recommendations": recommendations,
        "assessment_gates": gates,
        "assessment_results": assessments,
        "reasoning_style": reasoning_style,
        "reasoning_kibo_growth": {
            "starts_at": "elementary_grade_1",
            "passes_through": ["elementary", "middle_school", "high_school", "university", "military", "graduate_school"],
            "continues_after_hire": True,
            "finalized": False,
            "record_policy": "학년별 학습 데이터, 시험, 과제 피드백, 업무 경험을 누적해 계속 갱신한다.",
        },
        "role_model_id": role_model_id,
        "curriculum_id": curriculum.get("curriculum_id"),
    }
    resume = "\n".join(
        [
            f"이름: {talent['name']}",
            f"성별: {talent['gender']}",
            f"생년월일시: {talent['birth']['datetime']}",
            f"출생지: {talent['birth']['place']}",
            f"학력: 초중고, {university_path['major']} 대학교, {graduate_path['major']} 대학원",
            "학점: 대학교 4.2/4.5, 대학원 4.3/4.5",
            f"논문: 로컬 LLM 기반 {major_goal} 에이전트의 검증형 기억 구조",
            "활동사항: AI 데이터 분석, 해외 연수, 군 복무형 보안/협업 훈련",
            f"주요 프로젝트: {domain_summary} 리서치 노트, 안전 경계 검증",
        ]
    )
    return {
        "academic_record": academic_record,
        "resume": resume,
        "portfolio": {
            "employment_packet_ready": True,
            "summary": "학적부, 이력서, 논문, 프로젝트, 추천 기록을 포함한다.",
            "reasoning_style": reasoning_style,
        },
    }
