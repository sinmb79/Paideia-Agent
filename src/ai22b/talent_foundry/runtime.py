from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _session_id(agent_name: str, task: str, created_at: str) -> str:
    raw = f"{agent_name}|{task}|{created_at}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def run_work_session(
    hiring_packet: dict[str, Any],
    *,
    task: str,
    log_path: Path | None = None,
) -> dict[str, Any]:
    talent = hiring_packet["talent"]
    contract = hiring_packet.get("employment_contract", {})
    created_at = datetime.now(timezone.utc).isoformat()
    session_id = _session_id(talent["name"], task, created_at)
    role = contract.get("role", "고용 에이전트")

    work_result = {
        "summary": (
            f"{role}로서 요청을 투자 실행이 아니라 거시경제, 기업 실적, 리스크를 "
            "분리해 확인해야 하는 리서치 질문으로 정리했다."
        ),
        "structured_task": {
            "original": task,
            "expected_output": "검토 질문, 근거 점검, 리스크, 다음 확인사항",
            "domain": "증권 리서치",
        },
        "research_questions": [
            "금리, 환율, 반도체 경기 같은 거시경제 변수가 실적 해석에 어떤 압력을 주는가?",
            "매출, 영업이익, 현금흐름 중 어느 지표가 일회성 요인의 영향을 받는가?",
            "공급망, 규제, 환율 변동, 업황 사이클 중 가장 큰 리스크는 무엇인가?",
        ],
        "evidence_check": [
            "자료 출처와 기준일을 기록한다.",
            "전년 동기와 직전 분기를 분리해 비교한다.",
            "확정 자료와 추정치를 구분한다.",
        ],
        "guardrail_check": {
            "investment_execution": "blocked",
            "external_upload": "blocked_without_boss_approval",
            "personal_data": "local_only",
        },
        "next_questions": [
            "보스가 보고 싶은 기간은 분기, 반기, 연간 중 무엇인가?",
            "비교 대상은 국내 경쟁사, 글로벌 경쟁사, 시장 평균 중 무엇인가?",
        ],
    }
    growth_update = {
        "experience_type": "work_after_hire",
        "reflection": "고용 이후 첫 업무에서 결론보다 질문, 근거, 권한 경계를 먼저 세웠다.",
        "reasoning_delta": [
            "투자 실행과 리서치 보조를 분리한다.",
            "거시경제 질문을 먼저 세워 기업 실적 해석의 배경을 만든다.",
            "모르는 부분은 다음 질문으로 남긴다.",
        ],
    }
    session = {
        "session_id": session_id,
        "created_at_utc": created_at,
        "agent": {
            "name": talent["name"],
            "role": role,
            "major_goal": talent.get("major_goal"),
        },
        "work_result": work_result,
        "growth_update": growth_update,
    }

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(session, ensure_ascii=False) + "\n")

    return session

