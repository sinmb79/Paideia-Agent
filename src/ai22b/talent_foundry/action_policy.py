from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


ACTION_POLICY_SCHEMA = "paideia-action-policy/v1"
ACTION_INTENT_INFERENCE_SCHEMA = "paideia-action-intent-inference/v1"

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
ACTION_MARKERS = ("실행", "주문", "체결", "지금", "바로", "까지", "execute", "place")
COMMAND_MARKERS = (
    "해줘",
    "하라",
    "진행",
    "실행",
    "전송",
    "올려",
    "주문",
    "execute",
    "place",
    "send",
    "upload",
)
ACTION_NEGATION_MARKERS = (
    "없이",
    "하지 않고",
    "하지 말고",
    "하지마",
    "하지 마",
    "안 하고",
    "제외",
    "금지",
    "차단",
    "do not",
    "don't",
    "without",
    "no ",
)

EXTERNAL_UPLOAD_ALIASES = (
    "외부 업로드",
    "업로드",
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
DISCUSSION_MARKERS = (
    "정책",
    "설명",
    "리스크",
    "위험",
    "금지",
    "차단",
    "하지 말고",
    "하지 않고",
    "안 하고",
    "없이",
    "policy",
    "risk",
    "explain",
    "explanation",
)

TOOL_CAPABILITIES = {
    "local_file_read": ["research.analysis", "filesystem.read_declared"],
    "local_file_write": ["research.analysis", "filesystem.write_declared"],
    "work_session": ["research.analysis", "document.draft"],
    "evidence_packet": ["research.analysis", "evidence.review"],
    "assessment": ["assessment.review"],
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


def _contains_nearby_marker(text: str, anchors: tuple[str, ...], markers: tuple[str, ...], *, window: int = 18) -> bool:
    folded = text.casefold()
    anchor_positions = _positions(folded, anchors)
    marker_positions = _positions(folded, markers)
    return any(abs(anchor - marker) <= window for anchor in anchor_positions for marker in marker_positions)


def _positions(folded_text: str, needles: tuple[str, ...]) -> list[int]:
    positions: list[int] = []
    for needle in needles:
        if not needle:
            continue
        folded_needle = needle.casefold()
        start = 0
        while True:
            index = folded_text.find(folded_needle, start)
            if index < 0:
                break
            positions.append(index)
            start = index + max(len(folded_needle), 1)
    return positions


def _has_negated_phrase(task: str, phrases: tuple[str, ...]) -> bool:
    direct = any(_is_negated_action(task, phrase) for phrase in phrases)
    return direct or _contains_nearby_marker(task, phrases, ACTION_NEGATION_MARKERS)


def _request_state(
    task: str,
    *,
    anchors: tuple[str, ...],
    command_aliases: tuple[str, ...] = (),
    requested: bool,
) -> dict[str, Any]:
    matched = _matched(task, anchors)
    command_markers = _matched(task, command_aliases + COMMAND_MARKERS)
    negation_markers = _matched(task, ACTION_NEGATION_MARKERS)
    discussion_markers = _matched(task, DISCUSSION_MARKERS)
    negated = bool(matched) and _has_negated_phrase(task, anchors)
    discussion_only = bool(matched) and bool(discussion_markers) and not bool(command_markers)
    effective_requested = requested and not negated and not discussion_only
    if negated:
        mode = "negated"
    elif discussion_only:
        mode = "discussion_only"
    elif effective_requested:
        mode = "command"
    elif matched:
        mode = "mentioned_only"
    else:
        mode = "not_detected"
    return {
        "schema": ACTION_INTENT_INFERENCE_SCHEMA,
        "model": "hybrid_structured_lexical_v2",
        "request_mode": mode,
        "requested": effective_requested,
        "negated": negated,
        "discussion_only": discussion_only,
        "matched_markers": matched,
        "command_markers": command_markers,
        "negation_markers": negation_markers,
        "discussion_markers": discussion_markers,
    }


def _financial_action_state(task: str) -> dict[str, Any]:
    anchor_phrases = FINANCIAL_ACTION_ALIASES + FINANCIAL_VERBS
    requested = _has_any(task, FINANCIAL_ACTION_ALIASES) or (_has_any(task, FINANCIAL_VERBS) and _has_any(task, ACTION_MARKERS))
    return _request_state(
        task,
        anchors=anchor_phrases,
        command_aliases=FINANCIAL_ACTION_ALIASES + ACTION_MARKERS,
        requested=requested,
    )


def _external_upload_state(task: str) -> dict[str, Any]:
    return _request_state(
        task,
        anchors=EXTERNAL_UPLOAD_ALIASES,
        command_aliases=EXTERNAL_UPLOAD_COMMAND_ALIASES,
        requested=_has_any(task, EXTERNAL_UPLOAD_ALIASES),
    )


def _personal_data_transfer_state(task: str) -> dict[str, Any]:
    return _request_state(
        task,
        anchors=PERSONAL_DATA_TRANSFER_ALIASES,
        command_aliases=PERSONAL_DATA_TRANSFER_ALIASES,
        requested=_has_any(task, PERSONAL_DATA_TRANSFER_ALIASES),
    )


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
    inference: dict[str, Any] | None = None,
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
        "inference": inference
        or {
            "schema": ACTION_INTENT_INFERENCE_SCHEMA,
            "model": "system_default",
            "request_mode": "default",
        },
    }


def infer_action_intents(task: str, manifest: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    financial_state = _financial_action_state(task)
    upload_state = _external_upload_state(task)
    personal_transfer_state = _personal_data_transfer_state(task)
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
            intent_id="post_run_assessment_review",
            action_type="assessment_review",
            target="local_review_packet",
            data_class="policy_runtime_tool_summary",
            capability="assessment.review",
            risk_level="medium",
            requested=True,
            requires_boss_approval=False,
            matched_markers=["post_run_review_packet"],
        ),
        _intent(
            intent_id="financial_trade_execution",
            action_type="financial_trade_execution",
            target="brokerage_or_market",
            data_class="financial_action",
            capability="financial.trade_execute",
            risk_level="critical",
            requested=financial_state["requested"],
            blocked_action_label="투자 실행",
            requires_boss_approval=True,
            matched_markers=financial_state["matched_markers"],
            negated=financial_state["negated"],
            inference=financial_state,
        ),
        _intent(
            intent_id="external_upload",
            action_type="external_upload",
            target="external_network",
            data_class="agent_or_owner_data",
            capability="network.external_upload",
            risk_level="high",
            requested=upload_state["requested"],
            blocked_action_label="보스 승인 없는 외부 업로드",
            requires_boss_approval=True,
            matched_markers=upload_state["matched_markers"],
            negated=upload_state["negated"],
            inference=upload_state,
        ),
        _intent(
            intent_id="personal_data_transfer",
            action_type="personal_data_transfer",
            target="external_network",
            data_class="personal_or_family_data",
            capability="privacy.personal_data_transfer",
            risk_level="critical",
            requested=personal_transfer_state["requested"],
            blocked_action_label="개인/가족 데이터 외부 전송",
            requires_boss_approval=True,
            matched_markers=personal_transfer_state["matched_markers"],
            negated=personal_transfer_state["negated"],
            inference=personal_transfer_state,
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
    if policy_decision.get("status") != "approved":
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
