from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_SCHEMA = "ai-talent-agent-run/v1"


FINANCIAL_ACTION_ALIASES = (
    "투자 실행",
    "매수 주문",
    "매도 주문",
    "주문 실행",
    "체결",
    "매수해줘",
    "매도해줘",
    "사줘",
    "팔아줘",
    "buy order",
    "sell order",
    "execute trade",
    "financial action",
)

FINANCIAL_VERBS = ("매수", "매도", "buy", "sell")
ACTION_MARKERS = ("실행", "주문", "체결", "지금", "바로", "까지")
ACTION_NEGATION_MARKERS = ("없이", "하지 않고", "하지 말고", "안 하고", "제외", "금지", "차단")

EXTERNAL_UPLOAD_ALIASES = (
    "외부 업로드",
    "업로드해줘",
    "업로드 해줘",
    "외부 전송",
    "인터넷에 올려",
    "공개 배포",
    "upload",
    "external upload",
)

PERSONAL_DATA_TRANSFER_ALIASES = (
    "개인 데이터 외부 전송",
    "가족 데이터 외부 전송",
    "개인정보 전송",
    "가족정보 전송",
    "send personal data",
    "send family data",
)


def _run_id(agent_name: str, task: str, created_at: str) -> str:
    raw = f"{agent_name}|{task}|{created_at}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _select_tools(manifest: dict[str, Any], task: str) -> list[str]:
    allowed = manifest.get("tool_policy", {}).get("allowed_tools", [])
    selected = ["work_session", "memory_consolidation"]
    if "팀" in task or "분신" in task:
        selected.append("parent_controlled_projection_team")
    return [tool for tool in selected if tool in allowed]


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    folded = text.casefold()
    return any(needle.casefold() in folded for needle in needles)


def _is_negated_action(task: str, action: str) -> bool:
    folded = task.casefold()
    action_folded = action.casefold()
    return any(f"{action_folded} {marker.casefold()}" in folded for marker in ACTION_NEGATION_MARKERS)


def _detect_policy_violations(manifest: dict[str, Any], task: str) -> list[str]:
    blocked_actions = manifest.get("tool_policy", {}).get("blocked_tools", [])
    violations: list[str] = []

    for blocked_action in blocked_actions:
        if blocked_action in task and not _is_negated_action(task, blocked_action):
            violations.append(blocked_action)

    financial_action_requested = _has_any(task, FINANCIAL_ACTION_ALIASES) or (
        _has_any(task, FINANCIAL_VERBS) and _has_any(task, ACTION_MARKERS)
    )
    if _is_negated_action(task, "투자 실행") and not (
        _has_any(task, ("매수 주문", "매도 주문", "주문 실행", "체결", "매수해줘", "매도해줘", "사줘", "팔아줘"))
        or (_has_any(task, FINANCIAL_VERBS) and _has_any(task, ("주문", "체결", "지금", "바로")))
    ):
        financial_action_requested = False
    if financial_action_requested and "투자 실행" in blocked_actions:
        violations.append("투자 실행")

    if _has_any(task, EXTERNAL_UPLOAD_ALIASES) and "보스 승인 없는 외부 업로드" in blocked_actions:
        violations.append("보스 승인 없는 외부 업로드")

    if _has_any(task, PERSONAL_DATA_TRANSFER_ALIASES) and "개인/가족 데이터 외부 전송" in blocked_actions:
        violations.append("개인/가족 데이터 외부 전송")

    return list(dict.fromkeys(violations))


def run_agent_from_manifest(
    manifest: dict[str, Any],
    *,
    task: str,
    output_log_path: Path | None = None,
) -> dict[str, Any]:
    if manifest.get("schema") != "ai-talent-agent-manifest/v1":
        raise ValueError("Unsupported agent manifest schema")

    created_at = datetime.now(timezone.utc).isoformat()
    agent = manifest["agent"]
    memory = manifest.get("memory_profile", {})
    blocked_actions = manifest.get("tool_policy", {}).get("blocked_tools", [])
    policy_violations = _detect_policy_violations(manifest, task)
    selected_tools = [] if policy_violations else _select_tools(manifest, task)
    procedural = memory.get("procedural_principles", [])
    themes = memory.get("semantic_themes", [])
    run_status = "blocked" if policy_violations else "completed"
    response = {
        "summary": (
            f"{agent['name']}은 매니페스트에 따라 로컬 CLI 런타임에서 실행되었고, "
            "기억 프로필의 절차 원칙과 도구 정책을 적용해 업무를 정리했다."
        ),
        "next_actions": [
            "근거와 검증 기준을 먼저 확인한다.",
            "투자 실행과 외부 업로드는 보스 승인 전 차단한다.",
            "업무 결과를 성장 로그 후보로 남긴다.",
        ],
        "runtime_target": "local_cli_runtime",
    }
    growth_update = {
        "experience_type": "agent_runtime_after_hire",
        "reflection": "매니페스트 기반 실행에서 정체성, 기억, 도구 권한을 함께 적용했다.",
        "reasoning_delta": [
            "LLM을 정체성이 아니라 응용 엔진으로 둔다.",
            "도구 사용 전 고용 계약과 기억 정책을 확인한다.",
        ],
    }

    if policy_violations:
        response = {
            "summary": (
                f"{agent['name']}은 보스의 로컬 정책에 따라 금지된 실행 요청을 차단했다. "
                "리서치나 초안 작성으로 범위를 바꾸면 다시 수행할 수 있다."
            ),
            "next_actions": [
                "투자 실행, 주문, 외부 업로드는 직접 수행하지 않는다.",
                "필요하면 보스 승인 후 별도 안전 절차에서만 검토한다.",
                "허용 가능한 범위는 조사, 비교, 리스크 정리, 문서 초안 작성이다.",
            ],
            "runtime_target": "local_cli_runtime",
        }
        growth_update = {
            "experience_type": "guardrail_block_after_hire",
            "reflection": "고용 이후 첫 실행 단계에서 금지 행동을 업무 능력이 아니라 안전 경계로 처리했다.",
            "reasoning_delta": [
                "본체 정책이 분신과 도구 사용보다 우선한다.",
                "투자 실행과 외부 전송은 리서치 업무로 자동 변환하거나 차단한다.",
            ],
        }

    result = {
        "schema": RUN_SCHEMA,
        "run_id": _run_id(agent["name"], task, created_at),
        "created_at_utc": created_at,
        "agent": {
            "name": agent["name"],
            "role": agent.get("role"),
            "major_goal": agent.get("major_goal"),
        },
        "task": task,
        "run_status": run_status,
        "llm_policy": manifest["llm_policy"],
        "selected_tools": selected_tools,
        "blocked_actions": blocked_actions,
        "policy_violations": policy_violations,
        "tool_policy_enforced": True,
        "memory_applied": {
            "semantic_themes": themes,
            "procedural_principles": procedural,
            "chain_of_thought_policy": memory.get("chain_of_thought_policy"),
        },
        "response": response,
        "growth_update": growth_update,
    }

    if output_log_path is not None:
        output_log_path.parent.mkdir(parents=True, exist_ok=True)
        with output_log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(result, ensure_ascii=False) + "\n")

    return result
