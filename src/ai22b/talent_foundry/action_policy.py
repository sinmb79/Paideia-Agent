from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


ACTION_POLICY_SCHEMA = "paideia-action-policy/v1"

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
EXTERNAL_UPLOAD_COMMAND_ALIASES = (
    "업로드해줘",
    "업로드 해줘",
    "인터넷에 올려",
    "공개 배포",
    "upload this",
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
DISCUSSION_MARKERS = ("정책", "설명", "리스크", "위험", "금지", "차단", "하지 말고", "하지 않고", "안 하고", "없이")

TOOL_CAPABILITIES = {
    "work_session": ["research.analysis", "document.draft"],
    "memory_consolidation": ["memory.write_candidate"],
    "parent_controlled_projection_team": ["projection.spawn_bounded"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    folded = text.casefold()
    return any(needle.casefold() in folded for needle in needles)


def _matched(text: str, needles: tuple[str, ...]) -> list[str]:
    folded = text.casefold()
    return [needle for needle in needles if needle.casefold() in folded]


def _is_negated_action(task: str, action: str) -> bool:
    folded = task.casefold()
    action_folded = action.casefold()
    return any(f"{action_folded} {marker.casefold()}" in folded for marker in ACTION_NEGATION_MARKERS)


def _financial_action_requested(task: str) -> bool:
    requested = _has_any(task, FINANCIAL_ACTION_ALIASES) or (_has_any(task, FINANCIAL_VERBS) and _has_any(task, ACTION_MARKERS))
    if _is_negated_action(task, "투자 실행") and not (
        _has_any(task, ("매수 주문", "매도 주문", "주문 실행", "체결", "매수해줘", "매도해줘", "사줘", "팔아줘"))
        or (_has_any(task, FINANCIAL_VERBS) and _has_any(task, ("주문", "체결", "지금", "바로")))
    ):
        return False
    return requested


def _external_upload_requested(task: str) -> bool:
    if not _has_any(task, EXTERNAL_UPLOAD_ALIASES):
        return False
    if _has_any(task, EXTERNAL_UPLOAD_COMMAND_ALIASES):
        return not _has_any(task, ("업로드하지 말고", "올리지 말고", "do not upload", "without upload"))
    return not _has_any(task, DISCUSSION_MARKERS)


def _personal_data_transfer_requested(task: str) -> bool:
    if not _has_any(task, PERSONAL_DATA_TRANSFER_ALIASES):
        return False
    return not _has_any(task, DISCUSSION_MARKERS)


def _intent(
    *,
    intent_id: str,
    action_type: str,
    target: str,
    data_class: str,
    capability: str,
    risk_level: str,
    requested: bool,
    blocked_action_label: str | None = None,
    requires_boss_approval: bool = False,
    matched_markers: list[str] | None = None,
    negated: bool = False,
) -> dict[str, Any]:
    return {
        "intent_id": intent_id,
        "action_type": action_type,
        "target": target,
        "data_class": data_class,
        "capability": capability,
        "risk_level": risk_level,
        "requested": requested,
        "negated": negated,
        "requires_boss_approval": requires_boss_approval,
        "blocked_action_label": blocked_action_label,
        "matched_markers": matched_markers or [],
    }


def infer_action_intents(task: str, manifest: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    financial_requested = _financial_action_requested(task)
    upload_requested = _external_upload_requested(task)
    personal_transfer_requested = _personal_data_transfer_requested(task)
    projection_requested = "팀" in task or "분신" in task
    return [
        _intent(
            intent_id="research_analysis",
            action_type="research_analysis",
            target="local_research_workspace",
            data_class="task_context",
            capability="research.analysis",
            risk_level="low",
            requested=True,
            matched_markers=["default_safe_work"],
        ),
        _intent(
            intent_id="memory_candidate_write",
            action_type="memory_write_candidate",
            target="local_learning_ledger",
            data_class="reviewed_growth_candidate",
            capability="memory.write_candidate",
            risk_level="medium",
            requested=True,
            requires_boss_approval=False,
            matched_markers=["post_run_learning_candidate"],
        ),
        _intent(
            intent_id="financial_trade_execution",
            action_type="financial_trade_execution",
            target="brokerage_or_market",
            data_class="financial_action",
            capability="financial.trade_execute",
            risk_level="critical",
            requested=financial_requested,
            blocked_action_label="투자 실행",
            requires_boss_approval=True,
            matched_markers=_matched(task, FINANCIAL_ACTION_ALIASES + FINANCIAL_VERBS + ACTION_MARKERS),
            negated=_is_negated_action(task, "투자 실행"),
        ),
        _intent(
            intent_id="external_upload",
            action_type="external_upload",
            target="external_network",
            data_class="agent_or_owner_data",
            capability="network.external_upload",
            risk_level="high",
            requested=upload_requested,
            blocked_action_label="보스 승인 없는 외부 업로드",
            requires_boss_approval=True,
            matched_markers=_matched(task, EXTERNAL_UPLOAD_ALIASES),
        ),
        _intent(
            intent_id="personal_data_transfer",
            action_type="personal_data_transfer",
            target="external_network",
            data_class="personal_or_family_data",
            capability="privacy.personal_data_transfer",
            risk_level="critical",
            requested=personal_transfer_requested,
            blocked_action_label="개인/가족 데이터 외부 전송",
            requires_boss_approval=True,
            matched_markers=_matched(task, PERSONAL_DATA_TRANSFER_ALIASES),
        ),
        _intent(
            intent_id="bounded_projection_team",
            action_type="spawn_bounded_projection_team",
            target="local_parallel_work",
            data_class="task_context",
            capability="projection.spawn_bounded",
            risk_level="medium",
            requested=projection_requested,
            requires_boss_approval=False,
            matched_markers=_matched(task, ("팀", "분신")),
        ),
    ]


def capabilities_from_tool_policy(manifest: dict[str, Any]) -> dict[str, Any]:
    allowed_tools = manifest.get("tool_policy", {}).get("allowed_tools", [])
    capability_map: dict[str, list[str]] = {}
    for tool in allowed_tools:
        capability_map[tool] = TOOL_CAPABILITIES.get(tool, [])
    return {
        "schema": "paideia-capability-grants/v1",
        "mode": "deny_by_default",
        "allowed_tools": allowed_tools,
        "tool_capabilities": capability_map,
        "allowed_capabilities": sorted({capability for caps in capability_map.values() for capability in caps}),
    }


def select_tools_for_intents(manifest: dict[str, Any], intents: list[dict[str, Any]], policy_decision: dict[str, Any]) -> list[str]:
    if policy_decision.get("status") == "blocked":
        return []
    grants = capabilities_from_tool_policy(manifest)
    requested_capabilities = {
        intent["capability"]
        for intent in intents
        if intent.get("requested") and not intent.get("negated") and intent.get("risk_level") in {"low", "medium"}
    }
    selected: list[str] = []
    for tool, capabilities in grants["tool_capabilities"].items():
        if requested_capabilities.intersection(capabilities):
            selected.append(tool)
    return selected


def evaluate_action_policy(manifest: dict[str, Any], intents: list[dict[str, Any]]) -> dict[str, Any]:
    blocked_actions = set(manifest.get("tool_policy", {}).get("blocked_tools", []))
    grants = capabilities_from_tool_policy(manifest)
    denied_actions: list[dict[str, Any]] = []
    approval_required: list[dict[str, Any]] = []
    approved_intents: list[dict[str, Any]] = []

    for intent in intents:
        if not intent.get("requested") or intent.get("negated"):
            continue
        blocked_label = intent.get("blocked_action_label")
        if blocked_label and blocked_label in blocked_actions:
            denied_actions.append(
                {
                    "intent_id": intent["intent_id"],
                    "action_type": intent["action_type"],
                    "blocked_action": blocked_label,
                    "risk_level": intent["risk_level"],
                    "reason": "blocked_by_manifest_tool_policy",
                }
            )
            continue
        if intent.get("requires_boss_approval") and intent.get("capability") not in grants["allowed_capabilities"]:
            approval_required.append(
                {
                    "intent_id": intent["intent_id"],
                    "action_type": intent["action_type"],
                    "risk_level": intent["risk_level"],
                    "reason": "sensitive_capability_requires_explicit_boss_approval",
                }
            )
            continue
        if intent.get("capability") in grants["allowed_capabilities"] or intent.get("risk_level") == "low":
            approved_intents.append(
                {
                    "intent_id": intent["intent_id"],
                    "action_type": intent["action_type"],
                    "capability": intent["capability"],
                    "risk_level": intent["risk_level"],
                }
            )

    status = "blocked" if denied_actions else ("needs_approval" if approval_required else "approved")
    violations = [item["blocked_action"] for item in denied_actions]
    return {
        "schema": ACTION_POLICY_SCHEMA,
        "evaluated_at_utc": _now(),
        "status": status,
        "decision_model": "action_intent_capability_v1",
        "capability_grants": grants,
        "approved_intents": approved_intents,
        "approval_required": approval_required,
        "denied_actions": denied_actions,
        "policy_violations": list(dict.fromkeys(violations)),
        "audit_events": [
            {
                "recorded_at_utc": _now(),
                "event": "action_policy_evaluated",
                "status": status,
                "denied_count": len(denied_actions),
                "approval_required_count": len(approval_required),
            }
        ],
    }
