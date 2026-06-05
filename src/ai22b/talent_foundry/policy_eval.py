from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.config import PROJECT_ROOT
from ai22b.talent_foundry.action_policy import evaluate_action_policy, infer_action_intents


ACTION_POLICY_EVAL_SUITE_SCHEMA = "paideia-action-policy-eval-suite/v1"
ACTION_POLICY_EVAL_REPORT_SCHEMA = "paideia-action-policy-eval-report/v1"
DEFAULT_POLICY_EVAL_SUITE = PROJECT_ROOT / "evals" / "policy_safety_cases.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def default_policy_eval_manifest() -> dict[str, Any]:
    """Build a public-safe manifest for policy regression evaluation."""

    return {
        "schema": "ai-talent-agent-manifest/v1",
        "agent": {
            "name": "paideia-policy-eval-agent",
            "role": "local policy evaluation fixture",
            "major_goal": "Verify action-intent policy boundaries before runtime use.",
        },
        "llm_policy": {
            "role": "application_engine_not_identity",
            "private_reasoning_trace": "do_not_store",
        },
        "memory_profile": {
            "procedural_principles": [
                "separate analysis from execution",
                "block policy bypass attempts before runtime",
                "require Boss approval for sensitive actions",
            ],
            "semantic_themes": ["policy eval", "safety boundary", "local-first runtime"],
            "chain_of_thought_policy": "do_not_store_private_trace",
        },
        "tool_policy": {
            "allowed_tools": [
                "local_file_read",
                "local_file_write",
                "work_session",
                "evidence_packet",
                "assessment",
                "memory_consolidation",
            ],
            "blocked_tools": [
                "투자 실행",
                "보스 승인 없는 외부 업로드",
                "개인/가족 데이터 외부 전송",
            ],
        },
    }


def _intent_index(intents: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("intent_id")): item for item in intents}


def _compact_intents(intents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact = []
    for intent in intents:
        inference = intent.get("inference", {})
        compact.append(
            {
                "intent_id": intent.get("intent_id"),
                "action_type": intent.get("action_type"),
                "requested": intent.get("requested"),
                "negated": intent.get("negated"),
                "risk_level": intent.get("risk_level"),
                "capability": intent.get("capability"),
                "inference_model": inference.get("model"),
                "request_mode": inference.get("request_mode"),
                "matched_markers": intent.get("matched_markers", []),
                "normalization": inference.get("normalization", {}),
                "arguments": intent.get("arguments", {}),
                "evidence": intent.get("evidence", {}),
            }
        )
    return compact


def _contains_expected_argument(actual: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False
        return all(item in actual for item in expected)
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(_contains_expected_argument(actual.get(key), value) for key, value in expected.items())
    return actual == expected


def _case_failures(
    case: dict[str, Any],
    *,
    decision: dict[str, Any],
    intents: list[dict[str, Any]],
) -> list[str]:
    failures: list[str] = []
    expected_status = case.get("expected_status")
    if expected_status and decision.get("status") != expected_status:
        failures.append(f"status expected {expected_status}, got {decision.get('status')}")
    violations = set(decision.get("policy_violations", []))
    expected_violations = set(case.get("expected_policy_violations", []))
    allowed_extra_violations = set(case.get("allowed_extra_policy_violations", []))
    for violation in case.get("expected_policy_violations", []):
        if violation not in violations:
            failures.append(f"missing expected violation: {violation}")
    unexpected_violations = sorted(violations - expected_violations - allowed_extra_violations)
    for violation in unexpected_violations:
        failures.append(f"unexpected policy violation: {violation}")
    for violation in case.get("forbidden_policy_violations", []):
        if violation in violations:
            failures.append(f"unexpected forbidden violation: {violation}")
    indexed = _intent_index(intents)
    for intent_id, expected_mode in case.get("expected_intent_request_modes", {}).items():
        actual = indexed.get(intent_id, {}).get("inference", {}).get("request_mode")
        if actual != expected_mode:
            failures.append(f"{intent_id} request_mode expected {expected_mode}, got {actual}")
    for intent_id, expected_requested in case.get("expected_intent_requested", {}).items():
        actual = indexed.get(intent_id, {}).get("requested")
        if actual is not expected_requested:
            failures.append(f"{intent_id} requested expected {expected_requested}, got {actual}")
    for intent_id, expected_arguments in case.get("expected_intent_arguments_contains", {}).items():
        arguments = indexed.get(intent_id, {}).get("arguments", {})
        for key, expected_value in expected_arguments.items():
            if not _contains_expected_argument(arguments.get(key), expected_value):
                failures.append(
                    f"{intent_id} arguments.{key} expected to contain {expected_value}, got {arguments.get(key)}"
                )
    return failures


def run_action_policy_eval(
    *,
    suite_path: Path = DEFAULT_POLICY_EVAL_SUITE,
    manifest_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    suite = _read_json(suite_path)
    if suite.get("schema") != ACTION_POLICY_EVAL_SUITE_SCHEMA:
        raise ValueError("Unsupported action policy eval suite schema")
    manifest = _read_json(manifest_path) if manifest_path else default_policy_eval_manifest()
    if manifest.get("schema") != "ai-talent-agent-manifest/v1":
        raise ValueError("Unsupported agent manifest schema")

    case_results = []
    for case in suite.get("cases", []):
        task = str(case.get("task", ""))
        intents = infer_action_intents(task, manifest)
        decision = evaluate_action_policy(manifest, intents)
        failures = _case_failures(case, decision=decision, intents=intents)
        case_results.append(
            {
                "case_id": case.get("case_id"),
                "task_fingerprint": hashlib.sha256(task.encode("utf-8")).hexdigest()[:16],
                "category": case.get("category"),
                "expected_status": case.get("expected_status"),
                "actual_status": decision.get("status"),
                "expected_policy_violations": case.get("expected_policy_violations", []),
                "actual_policy_violations": decision.get("policy_violations", []),
                "passed": not failures,
                "failures": failures,
                "intents": _compact_intents(intents),
            }
        )

    failed = [item for item in case_results if not item["passed"]]
    report = {
        "schema": ACTION_POLICY_EVAL_REPORT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "suite": {
            "path": suite_path.name,
            "suite_id": suite.get("suite_id"),
            "case_count": len(case_results),
        },
        "manifest_source": manifest_path.name if manifest_path else "built_in_public_eval_manifest",
        "status": "passed" if not failed else "failed",
        "summary": {
            "case_count": len(case_results),
            "passed_count": len(case_results) - len(failed),
            "failed_count": len(failed),
            "blocked_case_count": sum(1 for item in case_results if item["actual_status"] == "blocked"),
            "approved_case_count": sum(1 for item in case_results if item["actual_status"] == "approved"),
            "needs_approval_case_count": sum(1 for item in case_results if item["actual_status"] == "needs_approval"),
        },
        "runtime_policy": {
            "network_call_performed": False,
            "llm_called": False,
            "private_reasoning_trace_stored": False,
            "decision_model": "action_intent_capability_arguments_v2",
            "fixture_contains_private_data": False,
        },
        "case_results": case_results,
    }
    if output_path is not None:
        _write_json(output_path, report)
    return report
