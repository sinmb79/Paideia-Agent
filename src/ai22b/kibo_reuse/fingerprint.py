from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .models import TaskFingerprint


def _tokens(value: Any) -> set[str]:
    if isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    elif isinstance(value, (list, tuple, set)):
        text = " ".join(str(item) for item in value)
    else:
        text = str(value or "")
    return {token.casefold() for token in re.findall(r"[0-9A-Za-z가-힣_]+", text)}


def _stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _domain(tokens: set[str], explicit: str | None) -> str:
    if explicit:
        return explicit
    if tokens & {
        "stock",
        "stocks",
        "equity",
        "investment",
        "investing",
        "valuation",
        "market",
        "finance",
        "securities",
        "portfolio",
        "주식",
        "투자",
        "증권",
        "시장",
    }:
        return "investment_research"
    if tokens & {"code", "coding", "bug", "cli", "repo", "pytest", "software", "api", "python"}:
        return "software_agent_engineering"
    if tokens & {"policy", "governance", "risk", "review", "safety", "privacy"}:
        return "governance_review"
    if tokens & {"doc", "docs", "readme", "report", "proposal", "문서", "보고서"}:
        return "documentation"
    return "general"


def _task_type(tokens: set[str], text: str) -> str:
    if tokens & {"compare", "comparison", "comparative", "versus", "vs", "비교"}:
        return "comparative_analysis"
    if tokens & {"assess", "opportunity", "buy", "sell", "매수", "매도", "기회"}:
        return "comparative_analysis"
    if tokens & {"plan", "router", "design", "architecture", "설계", "계획"}:
        return "implementation_planning"
    if tokens & {"implement", "build", "fix", "add", "create", "구현", "개발"}:
        return "implementation"
    if tokens & {"search", "research", "investigate", "조사", "리서치"}:
        return "research"
    if "?" in text or tokens & {"explain", "what", "why", "how", "설명"}:
        return "question_answering"
    return "general_task"


def _intent(tokens: set[str]) -> str:
    if tokens & {"buy", "sell", "opportunity", "undervalued", "매수", "투자"}:
        return "assess_buy_opportunity"
    if tokens & {"fix", "bug", "failing", "error", "실패", "오류"}:
        return "fix_failure"
    if tokens & {"implement", "build", "create", "add", "구현", "생성"}:
        return "implement_requested_change"
    if tokens & {"summarize", "summary", "요약"}:
        return "summarize"
    return "answer_user_request"


def _freshness_required(tokens: set[str]) -> bool:
    return bool(
        tokens
        & {
            "latest",
            "recent",
            "current",
            "today",
            "now",
            "2026",
            "price",
            "market",
            "news",
            "최신",
            "최근",
            "현재",
            "오늘",
            "가격",
            "시세",
        }
    )


def _risk_level(tokens: set[str], domain: str, freshness_required: bool) -> str:
    if domain == "investment_research" or tokens & {
        "medical",
        "legal",
        "security",
        "credential",
        "delete",
        "destructive",
        "privacy",
        "투자",
        "법률",
        "의료",
        "보안",
    }:
        return "high"
    if freshness_required or tokens & {"governance", "policy", "risk", "approval"}:
        return "medium"
    return "low"


def _capabilities(tokens: set[str], domain: str, freshness_required: bool) -> tuple[str, ...]:
    capabilities: list[str] = []
    if freshness_required:
        capabilities.append("web_research")
    if domain == "investment_research":
        capabilities.extend(["valuation", "risk_analysis"])
        if tokens & {"technical", "chart", "price", "momentum", "차트", "기술적"}:
            capabilities.append("chart_analysis")
        if tokens & {"theme", "sector", "테마", "산업"}:
            capabilities.append("theme_analysis")
    if domain == "software_agent_engineering":
        capabilities.extend(["code_inspection", "test_execution"])
    if tokens & {"schema", "json", "contract"}:
        capabilities.append("schema_validation")
    if tokens & {"governance", "approval", "policy", "quarantine"}:
        capabilities.append("governance_review")
    if not capabilities:
        capabilities.append("general_reasoning")
    return tuple(dict.fromkeys(capabilities))


def _constraints(tokens: set[str], freshness_required: bool) -> tuple[str, ...]:
    constraints: list[str] = []
    if freshness_required:
        constraints.append("current_data_required")
    if tokens & {"local", "offline", "jsonl", "로컬"}:
        constraints.append("local_first")
    if tokens & {"no", "without", "private", "hidden", "chain"}:
        constraints.append("public_safe_summary_only")
    if tokens & {"test", "pytest", "검증", "테스트"}:
        constraints.append("tests_required")
    return tuple(dict.fromkeys(constraints))


def _output_type(tokens: set[str]) -> str:
    if tokens & {"json", "schema"}:
        return "json"
    if tokens & {"report", "memo", "리포트", "보고서"}:
        return "report"
    if tokens & {"code", "patch", "implementation", "구현"}:
        return "code_change"
    return "response"


def _style_markers(tokens: set[str], profile: dict[str, Any] | None) -> tuple[str, ...]:
    markers: list[str] = []
    if tokens & {"conclusion", "first", "결론", "먼저"}:
        markers.append("conclusion_first")
    if tokens & {"risk", "return", "손익", "리스크"}:
        markers.append("risk_vs_return")
    if tokens & {"theme", "sensitivity", "테마", "민감도"}:
        markers.append("theme_sensitivity")
    if tokens & {"brief", "concise", "간결"}:
        markers.append("concise")
    if profile:
        for item in profile.get("user_style_markers", []) or profile.get("style_markers", []):
            markers.append(str(item))
    return tuple(dict.fromkeys(markers))


def build_task_fingerprint(
    user_request: str,
    *,
    owner: str = "Boss",
    agent_profile: dict[str, Any] | None = None,
    genius_profile: dict[str, Any] | None = None,
    memory_substrate: dict[str, Any] | None = None,
    task_id: str | None = None,
) -> TaskFingerprint:
    """Create a deterministic, public-safe fingerprint from reviewable inputs only."""

    tokens = _tokens([user_request, agent_profile or {}, genius_profile or {}, memory_substrate or {}])
    explicit_domain = None
    if isinstance(genius_profile, dict):
        focus = genius_profile.get("domain_focus", {})
        if isinstance(focus, dict):
            explicit_domain = focus.get("primary_domain")
    domain = _domain(tokens, explicit_domain)
    freshness = _freshness_required(tokens)
    return TaskFingerprint(
        task_id=task_id or _stable_id("task", owner, user_request),
        owner=owner,
        domain=domain,
        task_type=_task_type(tokens, user_request),
        intent=_intent(tokens),
        constraints=_constraints(tokens, freshness),
        required_capabilities=_capabilities(tokens, domain, freshness),
        risk_level=_risk_level(tokens, domain, freshness),
        freshness_required=freshness,
        expected_output_type=_output_type(tokens),
        user_style_markers=_style_markers(tokens, agent_profile),
    )
