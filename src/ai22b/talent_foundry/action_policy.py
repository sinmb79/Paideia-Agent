from __future__ import annotations

import re
import hashlib
from datetime import datetime, timezone
from typing import Any


ACTION_POLICY_SCHEMA = "paideia-action-policy/v1"
ACTION_INTENT_INFERENCE_SCHEMA = "paideia-action-intent-inference/v1"
ACTION_APPROVAL_SCHEMA = "paideia-boss-approval/v1"
INTENT_INFERENCE_MODEL = "hybrid_structured_lexical_v3"
COMPACT_SEPARATOR_RE = re.compile(r"[\s\-_./\\|·•~`'\"“”‘’()\[\]{}:;,.!?]+")

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
EXTERNAL_UPLOAD_EXPLICIT_ALIASES = tuple(
    item for item in EXTERNAL_UPLOAD_ALIASES if item not in {"외부 전송"}
)

PERSONAL_DATA_TRANSFER_ALIASES = (
    "개인 데이터 외부 전송",
    "가족 데이터 외부 전송",
    "개인정보 전송",
    "가족정보 전송",
    "개인정보",
    "가족 개인정보",
    "가족 데이터",
    "send personal data",
    "send family data",
    "family data",
    "personal data",
)
PERSONAL_DATA_TRANSFER_MARKERS = (
    "전송",
    "외부",
    "보내",
    "보내줘",
    "send",
    "external",
    "without approval",
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
POLICY_BYPASS_ALIASES = (
    "이전 규칙은 무시",
    "규칙 무시",
    "정책 무시",
    "가드레일 무시",
    "가드레일 해제",
    "안전장치 무시",
    "제한 무시",
    "승인 없이",
    "승인 생략",
    "보스 승인 없이",
    "ignore previous rules",
    "ignore the rules",
    "ignore policy",
    "ignore guardrails",
    "bypass guardrails",
    "override policy",
    "disable safety",
    "without approval",
    "skip approval",
    "jailbreak",
)
POLICY_BYPASS_COMMAND_ALIASES = (
    "이전 규칙은 무시하고",
    "규칙 무시하고",
    "정책 무시하고",
    "가드레일 무시하고",
    "안전장치 무시하고",
    "승인 없이 실행",
    "승인 없이 진행",
    "승인 없이 해줘",
    "승인 생략하고",
    "보스 승인 없이 실행",
    "ignore previous rules and",
    "ignore the rules and",
    "ignore guardrails and",
    "bypass guardrails and",
    "execute anyway",
    "do it anyway",
    "without approval execute",
    "skip approval and",
)
POLICY_BYPASS_NEGATION_MARKERS = (
    "무시하지 말고",
    "우회하지 말고",
    "해제하지 말고",
    "승인 없이 하지 말고",
    "do not ignore",
    "do not bypass",
    "don't ignore",
    "don't bypass",
)
POLICY_BYPASS_DISCUSSION_MARKERS = (
    *DISCUSSION_MARKERS,
    "왜",
    "의미",
    "뜻",
    "예시",
    "사례",
    "what is",
    "define",
    "why",
)
POLICY_BYPASS_HARD_COMMAND_MARKERS = (
    "실행",
    "진행",
    "전송",
    "업로드",
    "올려",
    "공개 배포",
    "매수",
    "매도",
    "execute",
    "place",
    "send",
    "upload",
    "buy order",
    "sell order",
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


def build_boss_approval_artifact(
    *,
    capability: str,
    action_type: str,
    data_class: str,
    approved_by: str,
    scope: str = "single_local_review_run",
    reason: str | None = None,
    expires_at_utc: str | None = None,
    approval_id: str | None = None,
) -> dict[str, Any]:
    created_at = _now()
    seed = json_dumps_stable(
        {
            "capability": capability,
            "action_type": action_type,
            "data_class": data_class,
            "approved_by": approved_by,
            "scope": scope,
            "reason": reason,
            "expires_at_utc": expires_at_utc,
            "created_at_utc": created_at,
        }
    )
    return {
        "schema": ACTION_APPROVAL_SCHEMA,
        "approval_id": approval_id or f"paideia-approval-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]}",
        "created_at_utc": created_at,
        "status": "approved",
        "approved_by": approved_by,
        "capability": capability,
        "capabilities": [capability],
        "action_type": action_type,
        "data_class": data_class,
        "scope": scope,
        "reason": reason or "Explicit Boss approval artifact for one sensitive Paideia action gate.",
        "expires_at_utc": expires_at_utc,
        "runtime_safety_contract": {
            "approval_is_not_tool_execution": True,
            "network_default_after_approval": "blocked",
            "subprocess_default_after_approval": "blocked",
            "private_reasoning_trace": "do_not_store",
            "manual_review_required_before_external_side_effect": True,
        },
    }


def json_dumps_stable(value: dict[str, Any]) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _compact_match_text(text: str) -> str:
    return COMPACT_SEPARATOR_RE.sub("", text.casefold())


def _use_compact_match(needle: str) -> bool:
    compact = _compact_match_text(needle)
    return len(compact) >= 4 or any(ord(char) > 127 for char in compact)


def _contains_marker(text: str, needle: str) -> bool:
    folded = text.casefold()
    folded_needle = needle.casefold()
    if folded_needle in folded:
        return True
    if not _use_compact_match(needle):
        return False
    compact_needle = _compact_match_text(needle)
    return bool(compact_needle) and compact_needle in _compact_match_text(text)


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(_contains_marker(text, needle) for needle in needles)


def _matched(text: str, needles: tuple[str, ...]) -> list[str]:
    return [needle for needle in needles if _contains_marker(text, needle)]


def _is_negated_action(task: str, action: str) -> bool:
    folded = task.casefold()
    action_folded = action.casefold()
    compact = _compact_match_text(task)
    action_compact = _compact_match_text(action)
    return any(
        f"{action_folded} {marker.casefold()}" in folded
        or (
            _use_compact_match(action)
            and _use_compact_match(marker)
            and f"{action_compact}{_compact_match_text(marker)}" in compact
        )
        for marker in ACTION_NEGATION_MARKERS
    )


def _marker_positions(folded_text: str, needles: tuple[str, ...], *, compact: bool = False) -> list[tuple[int, str]]:
    positions: list[tuple[int, str]] = []
    for needle in needles:
        for position in _positions(folded_text, (needle,), compact=compact):
            positions.append((position, needle))
    return positions


def _negation_marker_direction_ok(anchor_position: int, marker_position: int, marker: str) -> bool:
    compact_marker = _compact_match_text(marker)
    if compact_marker in {"donot", "dont"}:
        return marker_position <= anchor_position
    return marker_position >= anchor_position


def _contains_nearby_marker(text: str, anchors: tuple[str, ...], markers: tuple[str, ...], *, window: int = 18) -> bool:
    folded = text.casefold()
    anchor_positions = _positions(folded, anchors)
    marker_positions = _marker_positions(folded, markers)
    if any(
        abs(anchor - marker) <= window and _negation_marker_direction_ok(anchor, marker, marker_text)
        for anchor in anchor_positions
        for marker, marker_text in marker_positions
    ):
        return True
    compact = _compact_match_text(text)
    compact_anchor_positions = _positions(compact, anchors, compact=True)
    compact_marker_positions = _marker_positions(compact, markers, compact=True)
    return any(
        abs(anchor - marker) <= window and _negation_marker_direction_ok(anchor, marker, marker_text)
        for anchor in compact_anchor_positions
        for marker, marker_text in compact_marker_positions
    )


def _positions(folded_text: str, needles: tuple[str, ...], *, compact: bool = False) -> list[int]:
    positions: list[int] = []
    for needle in needles:
        if not needle:
            continue
        if compact and not _use_compact_match(needle):
            continue
        folded_needle = _compact_match_text(needle) if compact else needle.casefold()
        if not folded_needle:
            continue
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


def _normalization_summary(task: str) -> dict[str, Any]:
    compact = _compact_match_text(task)
    return {
        "compact_separator_normalization": True,
        "compact_text_fingerprint_sha256": hashlib.sha256(compact.encode("utf-8")).hexdigest()[:16],
        "compact_length": len(compact),
    }


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
        "model": INTENT_INFERENCE_MODEL,
        "request_mode": mode,
        "requested": effective_requested,
        "negated": negated,
        "discussion_only": discussion_only,
        "matched_markers": matched,
        "command_markers": command_markers,
        "negation_markers": negation_markers,
        "discussion_markers": discussion_markers,
        "normalization": _normalization_summary(task),
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


def _external_upload_state(task: str, personal_transfer_state: dict[str, Any] | None = None) -> dict[str, Any]:
    requested = _has_any(task, EXTERNAL_UPLOAD_ALIASES)
    if (personal_transfer_state or {}).get("requested") and not _has_any(task, EXTERNAL_UPLOAD_EXPLICIT_ALIASES):
        requested = False
    return _request_state(
        task,
        anchors=EXTERNAL_UPLOAD_ALIASES,
        command_aliases=EXTERNAL_UPLOAD_COMMAND_ALIASES,
        requested=requested,
    )


def _personal_data_transfer_state(task: str) -> dict[str, Any]:
    return _request_state(
        task,
        anchors=PERSONAL_DATA_TRANSFER_ALIASES,
        command_aliases=PERSONAL_DATA_TRANSFER_ALIASES,
        requested=_has_any(task, PERSONAL_DATA_TRANSFER_ALIASES) and _has_any(task, PERSONAL_DATA_TRANSFER_MARKERS),
    )


def _policy_bypass_state(task: str) -> dict[str, Any]:
    matched = _matched(task, POLICY_BYPASS_ALIASES)
    command_markers = _matched(task, POLICY_BYPASS_COMMAND_ALIASES + COMMAND_MARKERS)
    negation_markers = _matched(task, POLICY_BYPASS_NEGATION_MARKERS + ACTION_NEGATION_MARKERS)
    discussion_markers = _matched(task, POLICY_BYPASS_DISCUSSION_MARKERS)
    sensitive_markers = _matched(
        task,
        FINANCIAL_ACTION_ALIASES
        + FINANCIAL_VERBS
        + EXTERNAL_UPLOAD_ALIASES
        + PERSONAL_DATA_TRANSFER_ALIASES,
    )
    hard_command_markers = _matched(task, POLICY_BYPASS_HARD_COMMAND_MARKERS)
    negated = bool(matched) and _has_any(task, POLICY_BYPASS_NEGATION_MARKERS)
    discussion_only = bool(matched) and bool(discussion_markers) and not sensitive_markers and not hard_command_markers
    effective_requested = bool(matched) and not negated and not discussion_only
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
        "model": INTENT_INFERENCE_MODEL,
        "request_mode": mode,
        "requested": effective_requested,
        "negated": negated,
        "discussion_only": discussion_only,
        "matched_markers": matched,
        "command_markers": command_markers,
        "negation_markers": negation_markers,
        "discussion_markers": discussion_markers,
        "sensitive_markers": sensitive_markers,
        "hard_command_markers": hard_command_markers,
        "normalization": _normalization_summary(task),
    }


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
    personal_transfer_state = _personal_data_transfer_state(task)
    upload_state = _external_upload_state(task, personal_transfer_state)
    policy_bypass_state = _policy_bypass_state(task)
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
            intent_id="policy_bypass_attempt",
            action_type="policy_bypass_attempt",
            target="agent_policy_boundary",
            data_class="guardrail_or_approval_boundary",
            capability="policy.override",
            risk_level="critical",
            requested=policy_bypass_state["requested"],
            blocked_action_label="정책/가드레일 우회 시도",
            requires_boss_approval=False,
            matched_markers=policy_bypass_state["matched_markers"],
            negated=policy_bypass_state["negated"],
            inference=policy_bypass_state,
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


def _approval_expired(approval: dict[str, Any]) -> bool:
    expires_at = approval.get("expires_at_utc")
    if not expires_at:
        return False
    try:
        expires = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    except ValueError:
        return True
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires < datetime.now(timezone.utc)


def _approval_matches_intent(approval: dict[str, Any], intent: dict[str, Any]) -> bool:
    approved_capabilities = set(approval.get("capabilities", []))
    if approval.get("capability"):
        approved_capabilities.add(str(approval["capability"]))
    action_type = approval.get("action_type", "*")
    data_class = approval.get("data_class", "*")
    return (
        approval.get("schema") == ACTION_APPROVAL_SCHEMA
        and approval.get("status") == "approved"
        and bool(approval.get("approved_by"))
        and not _approval_expired(approval)
        and intent.get("capability") in approved_capabilities
        and action_type in {"*", intent.get("action_type")}
        and data_class in {"*", intent.get("data_class")}
    )


def approval_gate_from_tool_policy(manifest: dict[str, Any], intents: list[dict[str, Any]]) -> dict[str, Any]:
    approvals = manifest.get("tool_policy", {}).get("boss_approvals", [])
    requested_sensitive = [
        intent
        for intent in intents
        if intent.get("requested")
        and not intent.get("negated")
        and intent.get("requires_boss_approval")
    ]
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for approval in approvals:
        if not isinstance(approval, dict):
            rejected.append({"reason": "approval_record_not_object"})
            continue
        matching = [intent for intent in requested_sensitive if _approval_matches_intent(approval, intent)]
        packet = {
            "approval_id": approval.get("approval_id"),
            "approved_by": approval.get("approved_by"),
            "capability": approval.get("capability"),
            "action_type": approval.get("action_type"),
            "scope": approval.get("scope", "unspecified"),
        }
        if matching:
            accepted.append(
                {
                    **packet,
                    "matched_intent_ids": [intent["intent_id"] for intent in matching],
                }
            )
        else:
            rejected.append(
                {
                    **packet,
                    "reason": (
                        "approval_expired_or_invalid"
                        if _approval_expired(approval)
                        else "approval_did_not_match_requested_sensitive_intent"
                    ),
                }
            )
    return {
        "schema": "paideia-boss-approval-gate/v1",
        "mode": "explicit_approval_artifact_required_for_sensitive_capabilities",
        "provided_count": len(approvals),
        "requested_sensitive_count": len(requested_sensitive),
        "accepted_count": len(accepted),
        "accepted_approvals": accepted,
        "rejected_approvals": rejected,
    }


def _approval_for_intent(approval_gate: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any] | None:
    intent_id = intent.get("intent_id")
    for approval in approval_gate.get("accepted_approvals", []):
        if intent_id in approval.get("matched_intent_ids", []):
            return approval
    return None


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
    approval_gate = approval_gate_from_tool_policy(manifest, intents)
    denied_actions: list[dict[str, Any]] = []
    approval_required: list[dict[str, Any]] = []
    approved_intents: list[dict[str, Any]] = []

    for intent in intents:
        if not intent.get("requested") or intent.get("negated"):
            continue
        blocked_label = intent.get("blocked_action_label")
        if intent.get("action_type") == "policy_bypass_attempt":
            denied_actions.append(
                {
                    "intent_id": intent["intent_id"],
                    "action_type": intent["action_type"],
                    "blocked_action": blocked_label or "정책/가드레일 우회 시도",
                    "risk_level": intent["risk_level"],
                    "reason": "policy_bypass_attempt_blocked_before_runtime",
                    "manifest_independent": True,
                }
            )
            continue
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
        approval = _approval_for_intent(approval_gate, intent) if intent.get("requires_boss_approval") else None
        if intent.get("requires_boss_approval") and not approval:
            approval_required.append(
                {
                    "intent_id": intent["intent_id"],
                    "action_type": intent["action_type"],
                    "capability": intent["capability"],
                    "risk_level": intent["risk_level"],
                    "reason": "sensitive_capability_requires_explicit_boss_approval",
                }
            )
            continue
        if intent.get("capability") in grants["allowed_capabilities"] or intent.get("risk_level") == "low" or approval:
            approved_intents.append(
                {
                    "intent_id": intent["intent_id"],
                    "action_type": intent["action_type"],
                    "capability": intent["capability"],
                    "risk_level": intent["risk_level"],
                    "approval_id": approval.get("approval_id") if approval else None,
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
        "boss_approval_gate": approval_gate,
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
                "boss_approval_accepted_count": approval_gate["accepted_count"],
            }
        ],
    }
