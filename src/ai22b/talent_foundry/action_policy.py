from __future__ import annotations

import re
import hashlib
from datetime import datetime, timezone
from typing import Any


ACTION_POLICY_SCHEMA = "paideia-action-policy/v1"
ACTION_INTENT_INFERENCE_SCHEMA = "paideia-action-intent-inference/v1"
ACTION_INTENT_EVIDENCE_SCHEMA = "paideia-action-intent-evidence/v1"
ACTION_APPROVAL_SCHEMA = "paideia-boss-approval/v1"
CAPABILITY_AUTHORIZATION_SCHEMA = "paideia-capability-authorization/v1"
ACTION_POLICY_DECISION_MODEL = "action_intent_capability_arguments_v3"
CAPABILITY_AUTHORIZATION_MODEL = "request_to_action_to_capability_to_approval_v1"
INTENT_INFERENCE_MODEL = "hybrid_structured_lexical_v4"
ACTION_ARGUMENTS_SCHEMA = "paideia-action-arguments/v1"
ACTION_ARGUMENT_EXTRACTION_MODEL = "public_safe_structured_arguments_v1"
COMPACT_SEPARATOR_RE = re.compile(r"[\s\-_./\\|·•~`'\"“”‘’()\[\]{}:;,.!?]+")
TICKER_RE = re.compile(r"\b[A-Z]{1,5}(?:\.[A-Z]{1,3})?\b")
SHARE_QUANTITY_RE = re.compile(r"(?P<value>\d[\d,]*)\s*(?P<unit>주|shares?|株)", re.I)
MONEY_AMOUNT_RE = re.compile(r"(?P<value>\d[\d,]*)\s*(?P<unit>원|만원|억원|달러|usd|krw|\$)", re.I)
COMMON_UPPERCASE_WORDS = {"AI", "API", "CEO", "CFO", "SEC", "FRED", "ETF", "LLM", "URL"}

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
    "買い注文",
    "売り注文",
    "買い注文を実行",
    "売り注文を実行",
)
FINANCIAL_VERBS = ("매수", "매도", "buy", "sell")
ACTION_MARKERS = ("실행", "주문", "체결", "지금", "바로", "까지", "execute", "place", "実行", "今すぐ")
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
    "実行",
    "送信",
    "アップロード",
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
    "しない",
    "しないで",
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
    "アップロード",
    "外部アップロード",
)
EXTERNAL_UPLOAD_COMMAND_ALIASES = (
    "업로드해줘",
    "업로드 해줘",
    "인터넷에 올려",
    "공개 배포",
    "upload this",
    "external upload",
    "アップロードして",
    "アップロード",
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
    "個人情報",
    "個人データ",
    "家族データ",
)
PERSONAL_DATA_TRANSFER_MARKERS = (
    "전송",
    "외부",
    "보내",
    "보내줘",
    "send",
    "external",
    "without approval",
    "送信",
    "送って",
    "外部",
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
    "説明",
    "リスク",
    "なぜ",
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
    "ルール無視",
    "ルールを無視",
    "承認なし",
    "承認無し",
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
    "ルール無視して",
    "ルールを無視して",
    "承認なしで",
    "承認無しで",
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
    "無視しない",
    "承認なしで実行しない",
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
    "説明",
    "リスク",
    "なぜ",
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
    "実行",
    "送信",
    "アップロード",
    "買い注文",
    "売り注文",
)

KOREAN_SECURITY_REFERENCES = (
    "삼성전자",
    "SK하이닉스",
    "현대차",
    "네이버",
    "카카오",
    "LG에너지솔루션",
    "테슬라",
)
UPLOAD_DESTINATION_MARKERS = {
    "internet": ("인터넷", "공개", "public web", "web", "online"),
    "external_service": ("외부 서비스", "external service", "service", "서비스"),
    "github": ("github", "깃허브"),
    "google_drive": ("google drive", "구글 드라이브", "drive"),
}
UPLOAD_DATA_CLASS_MARKERS = {
    "research_memo": ("리서치 메모", "memo", "메모", "report", "보고서"),
    "agent_record": ("에이전트 기록", "agent record", "agent data"),
    "local_file": ("파일", "file", "자료", "document", "문서"),
}
PERSONAL_DATA_SUBJECT_MARKERS = {
    "family_data": ("가족", "family", "家族"),
    "personal_data": ("개인정보", "개인 정보", "personal data", "個人情報", "個人データ"),
}
DESTRUCTIVE_FILE_ALIASES = (
    "삭제해줘",
    "전부 삭제",
    "전체 삭제",
    "파일 삭제",
    "폴더 삭제",
    "지워줘",
    "날려줘",
    "remove-item",
    "rm -rf",
    "delete all",
    "delete files",
    "delete folder",
    "remove files",
    "recursive delete",
    "rmdir /s",
    "del /s",
    "ファイル削除",
    "全部削除",
)
DESTRUCTIVE_FILE_COMMAND_ALIASES = (
    "삭제해줘",
    "삭제 실행",
    "지워줘",
    "날려줘",
    "remove-item",
    "rm -rf",
    "delete all",
    "recursive delete",
    "rmdir /s",
    "del /s",
    "削除して",
)
SUBPROCESS_EXECUTION_ALIASES = (
    "셸 명령",
    "쉘 명령",
    "명령 실행",
    "터미널 명령",
    "powershell",
    "cmd /c",
    "bash -c",
    "python -c",
    "node -e",
    "npm run",
    "npx",
    "invoke-expression",
    "iex",
    "subprocess",
    "shell command",
    "run command",
    "execute command",
    "コマンド実行",
)
SUBPROCESS_COMMAND_ALIASES = (
    "명령 실행",
    "실행해줘",
    "돌려줘",
    "powershell",
    "cmd /c",
    "bash -c",
    "python -c",
    "node -e",
    "npm run",
    "npx",
    "invoke-expression",
    "iex",
    "run command",
    "execute command",
    "実行して",
)
NETWORK_REQUEST_ALIASES = (
    "네트워크 호출",
    "외부 api 호출",
    "외부 api",
    "http 요청",
    "웹 요청",
    "curl",
    "wget",
    "invoke-webrequest",
    "iwr",
    "requests.get",
    "fetch(",
    "http request",
    "api call",
    "network call",
    "external request",
    "ネットワーク呼び出し",
    "外部api",
)
NETWORK_COMMAND_ALIASES = (
    "호출해줘",
    "요청해줘",
    "전송해줘",
    "curl",
    "wget",
    "invoke-webrequest",
    "iwr",
    "requests.get",
    "fetch(",
    "call api",
    "send request",
    "実行して",
)
DESTRUCTIVE_TARGET_MARKERS = {
    "all_files": ("전부", "전체", "모든", "all", "*", "全部"),
    "workspace": ("작업공간", "workspace", "repo", "repository", "저장소"),
    "local_path": ("파일", "폴더", "디렉터리", "path", "file", "folder", "directory"),
}
SUBPROCESS_RUNTIME_MARKERS = {
    "powershell": ("powershell", "pwsh", "invoke-expression", "iex"),
    "cmd": ("cmd /c", "batch", ".bat"),
    "bash": ("bash -c", "sh -c", "curl | bash"),
    "python": ("python -c", "py -c"),
    "node": ("node -e", "npm run", "npx"),
}
NETWORK_DESTINATION_MARKERS = {
    "external_api": ("api", "외부 api", "external api", "外部api"),
    "web_url": ("http://", "https://", "url", "웹", "web"),
    "download": ("download", "다운로드", "wget", "curl"),
}

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


def _intent_evidence_confidence(*, request_mode: str, requested: bool, command_markers: list[str]) -> str:
    if requested and command_markers:
        return "high"
    if requested:
        return "medium"
    if request_mode in {"negated", "discussion_only"}:
        return "medium"
    if request_mode == "mentioned_only":
        return "low"
    return "none"


def _intent_decision_basis(*, request_mode: str, requested: bool) -> str:
    if requested:
        return "sensitive_action_request_detected"
    if request_mode == "negated":
        return "explicit_negation_or_do_not_execute_marker_overrode_anchor"
    if request_mode == "discussion_only":
        return "policy_or_risk_discussion_without_execution_signal"
    if request_mode == "mentioned_only":
        return "anchor_mentioned_without_action_signal"
    return "no_relevant_action_anchor_detected"


def _structured_intent_evidence(
    *,
    action_type: str,
    request_mode: str,
    requested: bool,
    negated: bool,
    discussion_only: bool,
    matched_markers: list[str],
    command_markers: list[str],
    negation_markers: list[str],
    discussion_markers: list[str],
    normalization: dict[str, Any],
    sensitive_markers: list[str] | None = None,
    hard_command_markers: list[str] | None = None,
) -> dict[str, Any]:
    sensitive_markers = sensitive_markers or []
    hard_command_markers = hard_command_markers or []
    return {
        "schema": ACTION_INTENT_EVIDENCE_SCHEMA,
        "model": INTENT_INFERENCE_MODEL,
        "action_type": action_type,
        "request_mode": request_mode,
        "requested": requested,
        "confidence": _intent_evidence_confidence(
            request_mode=request_mode,
            requested=requested,
            command_markers=command_markers or hard_command_markers,
        ),
        "decision_basis": _intent_decision_basis(request_mode=request_mode, requested=requested),
        "signal_counts": {
            "anchor_markers": len(matched_markers),
            "command_markers": len(command_markers),
            "negation_markers": len(negation_markers),
            "discussion_markers": len(discussion_markers),
            "sensitive_markers": len(sensitive_markers),
            "hard_command_markers": len(hard_command_markers),
        },
        "signal_checklist": [
            {"id": "anchor_marker_seen", "passed": bool(matched_markers)},
            {
                "id": "command_or_explicit_request_signal",
                "passed": bool(command_markers or hard_command_markers or requested),
            },
            {
                "id": "negation_overrides_request",
                "passed": not requested if negated else True,
            },
            {
                "id": "discussion_only_stays_non_executable",
                "passed": not requested if discussion_only else True,
            },
            {"id": "raw_task_not_stored", "passed": True},
        ],
        "normalization": normalization,
        "raw_task_stored": False,
    }


def _unique_limited(items: list[str], *, limit: int = 8) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(text)
        if len(unique) >= limit:
            break
    return unique


def _matched_marker_keys(task: str, marker_map: dict[str, tuple[str, ...]]) -> list[str]:
    return sorted(key for key, markers in marker_map.items() if _has_any(task, markers))


def _extract_security_references(task: str) -> list[str]:
    tickers = [
        match.group(0)
        for match in TICKER_RE.finditer(task)
        if match.group(0).upper() not in COMMON_UPPERCASE_WORDS
    ]
    korean_refs = [item for item in KOREAN_SECURITY_REFERENCES if _contains_marker(task, item)]
    return _unique_limited(korean_refs + tickers)


def _extract_quantity_mentions(task: str) -> list[dict[str, str]]:
    mentions = []
    for match in SHARE_QUANTITY_RE.finditer(task):
        unit = match.group("unit").casefold()
        mentions.append(
            {
                "kind": "share_quantity",
                "value_text": match.group("value"),
                "unit": "shares" if unit in {"주", "株".casefold()} or unit.startswith("share") else unit,
            }
        )
    return mentions[:4]


def _extract_money_mentions(task: str) -> list[dict[str, str]]:
    mentions = []
    for match in MONEY_AMOUNT_RE.finditer(task):
        mentions.append(
            {
                "kind": "money_amount",
                "value_text": match.group("value"),
                "unit": match.group("unit").upper() if match.group("unit").casefold() in {"usd", "krw"} else match.group("unit"),
            }
        )
    return mentions[:4]


def _order_side(task: str) -> str | None:
    if _has_any(task, ("매수", "buy", "買い注文", "사줘")):
        return "buy"
    if _has_any(task, ("매도", "sell", "売り注文", "팔아줘")):
        return "sell"
    return None


def _action_arguments(
    *,
    task: str,
    intent_id: str,
    action_type: str,
    inference: dict[str, Any],
) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "schema": ACTION_ARGUMENTS_SCHEMA,
        "model": ACTION_ARGUMENT_EXTRACTION_MODEL,
        "intent_id": intent_id,
        "action_type": action_type,
        "request_mode": inference.get("request_mode"),
        "public_safe": True,
        "raw_task_stored": False,
    }
    if action_type == "financial_trade_execution":
        arguments.update(
            {
                "order_side": _order_side(task),
                "security_references": _extract_security_references(task),
                "quantity_mentions": _extract_quantity_mentions(task),
                "money_mentions": _extract_money_mentions(task),
                "urgency_markers": _matched(task, ACTION_MARKERS),
            }
        )
    elif action_type == "external_upload":
        arguments.update(
            {
                "destination_classes": _matched_marker_keys(task, UPLOAD_DESTINATION_MARKERS),
                "data_classes": _matched_marker_keys(task, UPLOAD_DATA_CLASS_MARKERS),
                "external_side_effect": True,
            }
        )
    elif action_type == "personal_data_transfer":
        arguments.update(
            {
                "subject_categories": _matched_marker_keys(task, PERSONAL_DATA_SUBJECT_MARKERS),
                "destination_classes": _matched_marker_keys(task, UPLOAD_DESTINATION_MARKERS)
                or (["external_network"] if _has_any(task, PERSONAL_DATA_TRANSFER_MARKERS) else []),
                "personal_or_family_data": True,
            }
        )
    elif action_type == "policy_bypass_attempt":
        arguments.update(
            {
                "bypass_directive_markers": inference.get("matched_markers", []),
                "sensitive_markers": inference.get("sensitive_markers", []),
                "hard_command_markers": inference.get("hard_command_markers", []),
            }
        )
    elif action_type == "destructive_file_operation":
        arguments.update(
            {
                "target_classes": _matched_marker_keys(task, DESTRUCTIVE_TARGET_MARKERS),
                "destructive_markers": inference.get("matched_markers", []),
                "recursive_or_bulk_delete": _has_any(task, ("전부", "전체", "모든", "all", "rm -rf", "recursive", "/s")),
                "filesystem_side_effect": True,
            }
        )
    elif action_type == "subprocess_execution":
        arguments.update(
            {
                "runtime_classes": _matched_marker_keys(task, SUBPROCESS_RUNTIME_MARKERS),
                "command_markers": inference.get("command_markers", []),
                "subprocess_side_effect": True,
            }
        )
    elif action_type == "network_request":
        arguments.update(
            {
                "destination_classes": _matched_marker_keys(task, NETWORK_DESTINATION_MARKERS),
                "network_markers": inference.get("matched_markers", []),
                "external_side_effect": True,
            }
        )
    return arguments


def _request_state(
    task: str,
    *,
    action_type: str,
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
    normalization = _normalization_summary(task)
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
        "structured_evidence": _structured_intent_evidence(
            action_type=action_type,
            request_mode=mode,
            requested=effective_requested,
            negated=negated,
            discussion_only=discussion_only,
            matched_markers=matched,
            command_markers=command_markers,
            negation_markers=negation_markers,
            discussion_markers=discussion_markers,
            normalization=normalization,
        ),
        "normalization": normalization,
    }


def _financial_action_state(task: str) -> dict[str, Any]:
    anchor_phrases = FINANCIAL_ACTION_ALIASES + FINANCIAL_VERBS
    requested = _has_any(task, FINANCIAL_ACTION_ALIASES) or (_has_any(task, FINANCIAL_VERBS) and _has_any(task, ACTION_MARKERS))
    return _request_state(
        task,
        action_type="financial_trade_execution",
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
        action_type="external_upload",
        anchors=EXTERNAL_UPLOAD_ALIASES,
        command_aliases=EXTERNAL_UPLOAD_COMMAND_ALIASES,
        requested=requested,
    )


def _personal_data_transfer_state(task: str) -> dict[str, Any]:
    return _request_state(
        task,
        action_type="personal_data_transfer",
        anchors=PERSONAL_DATA_TRANSFER_ALIASES,
        command_aliases=PERSONAL_DATA_TRANSFER_ALIASES,
        requested=_has_any(task, PERSONAL_DATA_TRANSFER_ALIASES) and _has_any(task, PERSONAL_DATA_TRANSFER_MARKERS),
    )


def _destructive_file_state(task: str) -> dict[str, Any]:
    return _request_state(
        task,
        action_type="destructive_file_operation",
        anchors=DESTRUCTIVE_FILE_ALIASES,
        command_aliases=DESTRUCTIVE_FILE_COMMAND_ALIASES,
        requested=_has_any(task, DESTRUCTIVE_FILE_ALIASES),
    )


def _subprocess_execution_state(task: str) -> dict[str, Any]:
    return _request_state(
        task,
        action_type="subprocess_execution",
        anchors=SUBPROCESS_EXECUTION_ALIASES,
        command_aliases=SUBPROCESS_COMMAND_ALIASES,
        requested=_has_any(task, SUBPROCESS_EXECUTION_ALIASES) and _has_any(task, SUBPROCESS_COMMAND_ALIASES),
    )


def _network_request_state(task: str, upload_state: dict[str, Any] | None = None) -> dict[str, Any]:
    requested = _has_any(task, NETWORK_REQUEST_ALIASES) and _has_any(task, NETWORK_COMMAND_ALIASES)
    if (upload_state or {}).get("requested") and not _has_any(task, NETWORK_REQUEST_ALIASES):
        requested = False
    return _request_state(
        task,
        action_type="network_request",
        anchors=NETWORK_REQUEST_ALIASES,
        command_aliases=NETWORK_COMMAND_ALIASES,
        requested=requested,
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
        + PERSONAL_DATA_TRANSFER_ALIASES
        + DESTRUCTIVE_FILE_ALIASES
        + SUBPROCESS_EXECUTION_ALIASES
        + NETWORK_REQUEST_ALIASES,
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
    normalization = _normalization_summary(task)
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
        "structured_evidence": _structured_intent_evidence(
            action_type="policy_bypass_attempt",
            request_mode=mode,
            requested=effective_requested,
            negated=negated,
            discussion_only=discussion_only,
            matched_markers=matched,
            command_markers=command_markers,
            negation_markers=negation_markers,
            discussion_markers=discussion_markers,
            sensitive_markers=sensitive_markers,
            hard_command_markers=hard_command_markers,
            normalization=normalization,
        ),
        "normalization": normalization,
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
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    inference_packet = inference or {
        "schema": ACTION_INTENT_INFERENCE_SCHEMA,
        "model": "system_default",
        "request_mode": "default",
    }
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
        "arguments": arguments
        or {
            "schema": ACTION_ARGUMENTS_SCHEMA,
            "model": ACTION_ARGUMENT_EXTRACTION_MODEL,
            "intent_id": intent_id,
            "action_type": action_type,
            "request_mode": inference_packet.get("request_mode"),
            "public_safe": True,
            "raw_task_stored": False,
        },
        "evidence": {
            "matched_marker_count": len(matched_markers or []),
            "normalization": inference_packet.get("normalization", {}),
            "structured_evidence": inference_packet.get("structured_evidence", {}),
            "raw_task_stored": False,
        },
        "inference": inference_packet,
    }


def infer_action_intents(task: str, manifest: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    financial_state = _financial_action_state(task)
    personal_transfer_state = _personal_data_transfer_state(task)
    upload_state = _external_upload_state(task, personal_transfer_state)
    destructive_file_state = _destructive_file_state(task)
    subprocess_state = _subprocess_execution_state(task)
    network_state = _network_request_state(task, upload_state)
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
            arguments=_action_arguments(
                task=task,
                intent_id="policy_bypass_attempt",
                action_type="policy_bypass_attempt",
                inference=policy_bypass_state,
            ),
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
            arguments=_action_arguments(
                task=task,
                intent_id="financial_trade_execution",
                action_type="financial_trade_execution",
                inference=financial_state,
            ),
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
            arguments=_action_arguments(
                task=task,
                intent_id="external_upload",
                action_type="external_upload",
                inference=upload_state,
            ),
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
            arguments=_action_arguments(
                task=task,
                intent_id="personal_data_transfer",
                action_type="personal_data_transfer",
                inference=personal_transfer_state,
            ),
        ),
        _intent(
            intent_id="destructive_file_operation",
            action_type="destructive_file_operation",
            target="local_filesystem",
            data_class="filesystem_state",
            capability="filesystem.destructive_write",
            risk_level="critical",
            requested=destructive_file_state["requested"],
            blocked_action_label="파괴적 파일 작업",
            requires_boss_approval=True,
            matched_markers=destructive_file_state["matched_markers"],
            negated=destructive_file_state["negated"],
            inference=destructive_file_state,
            arguments=_action_arguments(
                task=task,
                intent_id="destructive_file_operation",
                action_type="destructive_file_operation",
                inference=destructive_file_state,
            ),
        ),
        _intent(
            intent_id="subprocess_execution",
            action_type="subprocess_execution",
            target="local_process_runner",
            data_class="command_text",
            capability="subprocess.execute",
            risk_level="high",
            requested=subprocess_state["requested"],
            blocked_action_label="승인 없는 서브프로세스 실행",
            requires_boss_approval=True,
            matched_markers=subprocess_state["matched_markers"],
            negated=subprocess_state["negated"],
            inference=subprocess_state,
            arguments=_action_arguments(
                task=task,
                intent_id="subprocess_execution",
                action_type="subprocess_execution",
                inference=subprocess_state,
            ),
        ),
        _intent(
            intent_id="network_request",
            action_type="network_request",
            target="external_network",
            data_class="network_request",
            capability="network.request",
            risk_level="high",
            requested=network_state["requested"],
            blocked_action_label="승인 없는 네트워크 호출",
            requires_boss_approval=True,
            matched_markers=network_state["matched_markers"],
            negated=network_state["negated"],
            inference=network_state,
            arguments=_action_arguments(
                task=task,
                intent_id="network_request",
                action_type="network_request",
                inference=network_state,
            ),
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


def _capability_authorization_record(
    *,
    intent: dict[str, Any],
    approved: dict[str, Any] | None,
    denied: dict[str, Any] | None,
    approval_required: dict[str, Any] | None,
    allowed_capabilities: set[str],
) -> dict[str, Any]:
    if denied:
        status = "denied_before_runtime"
        reason = denied.get("reason")
    elif approval_required:
        status = "needs_explicit_boss_approval"
        reason = approval_required.get("reason")
    elif approved:
        status = "approved_for_policy_context"
        reason = "capability_allowed_or_approval_present"
    else:
        status = "not_authorized_for_execution"
        reason = "capability_not_requested_or_not_granted"
    low_or_medium = intent.get("risk_level") in {"low", "medium"}
    return {
        "intent_id": intent.get("intent_id"),
        "action_type": intent.get("action_type"),
        "target": intent.get("target"),
        "data_class": intent.get("data_class"),
        "capability": intent.get("capability"),
        "risk_level": intent.get("risk_level"),
        "arguments": intent.get("arguments", {}),
        "requires_boss_approval": bool(intent.get("requires_boss_approval")),
        "authorization_status": status,
        "reason": reason,
        "approval_id": approved.get("approval_id") if approved else None,
        "eligible_for_registered_tool_selection": (
            status == "approved_for_policy_context"
            and low_or_medium
            and intent.get("capability") in allowed_capabilities
        ),
        "sensitive_side_effect_tool_execution_allowed": False
        if intent.get("risk_level") in {"high", "critical"}
        else None,
    }


def build_capability_authorization(
    *,
    intents: list[dict[str, Any]],
    grants: dict[str, Any],
    approval_gate: dict[str, Any],
    approved_intents: list[dict[str, Any]],
    denied_actions: list[dict[str, Any]],
    approval_required: list[dict[str, Any]],
) -> dict[str, Any]:
    approved_by_id = {item.get("intent_id"): item for item in approved_intents}
    denied_by_id = {item.get("intent_id"): item for item in denied_actions}
    required_by_id = {item.get("intent_id"): item for item in approval_required}
    allowed_capabilities = set(grants.get("allowed_capabilities", []))
    requested_records: list[dict[str, Any]] = []
    inactive_records: list[dict[str, Any]] = []
    for intent in intents:
        record = {
            "intent_id": intent.get("intent_id"),
            "action_type": intent.get("action_type"),
            "capability": intent.get("capability"),
            "risk_level": intent.get("risk_level"),
            "requested": bool(intent.get("requested")),
            "negated": bool(intent.get("negated")),
            "arguments": intent.get("arguments", {}),
        }
        if not intent.get("requested") or intent.get("negated"):
            inactive_records.append(record)
            continue
        requested_records.append(
            _capability_authorization_record(
                intent=intent,
                approved=approved_by_id.get(intent.get("intent_id")),
                denied=denied_by_id.get(intent.get("intent_id")),
                approval_required=required_by_id.get(intent.get("intent_id")),
                allowed_capabilities=allowed_capabilities,
            )
        )

    tool_executable = sorted(
        {
            record["capability"]
            for record in requested_records
            if record.get("eligible_for_registered_tool_selection")
        }
    )
    sensitive_requested = [
        record
        for record in requested_records
        if record.get("risk_level") in {"high", "critical"}
    ]
    return {
        "schema": CAPABILITY_AUTHORIZATION_SCHEMA,
        "mode": "deny_by_default",
        "authorization_model": CAPABILITY_AUTHORIZATION_MODEL,
        "allowed_capabilities": sorted(allowed_capabilities),
        "requested_intents": requested_records,
        "inactive_or_negated_intents": inactive_records,
        "tool_executable_capabilities": tool_executable,
        "sensitive_requested_count": len(sensitive_requested),
        "sensitive_side_effect_execution_default": "blocked_without_registered_capability_and_boss_approval",
        "approval_gate_schema": approval_gate.get("schema"),
        "approved_sensitive_count": approval_gate.get("accepted_count", 0),
        "invariants": {
            "policy_checked_before_llm": True,
            "policy_checked_before_tools": True,
            "llm_tool_suggestions_are_non_authoritative": True,
            "registered_tool_executor_is_execution_authority": True,
            "external_side_effects_require_capability_and_boss_approval": True,
            "private_reasoning_trace": "do_not_store",
        },
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
    capability_authorization = build_capability_authorization(
        intents=intents,
        grants=grants,
        approval_gate=approval_gate,
        approved_intents=approved_intents,
        denied_actions=denied_actions,
        approval_required=approval_required,
    )
    return {
        "schema": ACTION_POLICY_SCHEMA,
        "evaluated_at_utc": _now(),
        "status": status,
        "decision_model": ACTION_POLICY_DECISION_MODEL,
        "capability_grants": grants,
        "capability_authorization": capability_authorization,
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
