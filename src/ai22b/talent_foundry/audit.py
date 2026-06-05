from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.config import PROJECT_ROOT
from ai22b.talent_foundry.distribution import verify_agent_release_archive, verify_agent_release_bundle


AUDIT_SCHEMA = "ai-talent-foundry-release-audit/v1"
AGENT_EXECUTION_CONTRACT_SCHEMA = "paideia-agent-execution-contract/v1"
CAPABILITY_AUTHORIZATION_SCHEMA = "paideia-capability-authorization/v1"
MEMORY_REVIEW_CANDIDATE_SCHEMA = "paideia-memory-review-candidate/v1"
RUNTIME_OBSERVABILITY_SCHEMA = "paideia-runtime-observability/v1"
REQUIRED_MAJOR_GATES = {"school_exam", "csat", "university_graduation", "doctoral_defense"}
REQUIRED_RESEARCH_NAMES = {
    "Hermes Agent",
    "Hermes Memory Routing Issue",
    "Hermes Long-Session Field Report",
    "OpenHands",
    "OpenClaw",
    "OpenClaw Memory Index Issue",
    "Reflexion",
    "Generative Agents",
    "Survey on the Memory Mechanism of LLM-based Agents",
}
REQUIRED_RESEARCH_CATEGORIES = {
    "reference_agent_program",
    "agent_runtime",
    "reflection_learning",
    "memory_architecture",
    "memory_operability",
    "operational_feedback",
    "profile_isolation",
    "human_centered_governance",
    "public_distribution_safety",
}
OPERATIONAL_RESEARCH_CATEGORIES = {"operational_feedback", "memory_operability", "profile_isolation"}
REQUIRED_PUBLIC_PROGRAM_COMMANDS = {
    "blueprint",
    "start-console",
    "onboard-agent",
    "raise",
    "doctor-llm-provider",
    "doctor-bundle",
    "install-package",
    "hire-installed",
    "run-hired-workspace-agent",
    "run-hired-agent-job",
    "build-agent-program",
    "build-paideia-agent-kit",
    "doctor-agent-program",
    "migrate-agent-assets",
    "run-agent-program-chat",
    "run-hired-agent-job-cycle",
    "record-hired-learning",
    "assign-hired-goal",
    "assemble-hired-projection-swarm",
    "assemble-hired-team",
    "family",
    "audit-release",
}
REQUIRED_PUBLIC_PROGRAM_LIFECYCLE = {
    "design",
    "raise",
    "package",
    "install",
    "hire",
    "work",
    "review",
    "grow",
    "lineage",
    "audit",
}
REQUIRED_PUBLIC_PROGRAM_ROLES = {"education_committee", "home_care", "oversight_committee"}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _installed_agent_root(run_dir: Path) -> Path:
    agents_dir = run_dir / "installed_agents" / "agents"
    candidates = sorted(path for path in agents_dir.iterdir() if path.is_dir()) if agents_dir.exists() else []
    if not candidates:
        return agents_dir / "missing_agent"
    return candidates[0]


def _base_agent_run(run: dict[str, Any]) -> dict[str, Any]:
    base = run.get("base_agent_run")
    return base if isinstance(base, dict) else run


def _agent_p0_runtime_details(run: dict[str, Any]) -> dict[str, Any]:
    base = _base_agent_run(run)
    contract = base.get("execution_contract", {}) if isinstance(base.get("execution_contract"), dict) else {}
    policy = base.get("policy_decision", {}) if isinstance(base.get("policy_decision"), dict) else {}
    authorization = (
        policy.get("capability_authorization", {})
        if isinstance(policy.get("capability_authorization"), dict)
        else {}
    )
    authorization_invariants = (
        authorization.get("invariants", {})
        if isinstance(authorization.get("invariants"), dict)
        else {}
    )
    memory_write = base.get("memory_write", {}) if isinstance(base.get("memory_write"), dict) else {}
    review_candidate = (
        memory_write.get("review_candidate", {})
        if isinstance(memory_write.get("review_candidate"), dict)
        else {}
    )
    promotion_gate = (
        review_candidate.get("promotion_gate", {})
        if isinstance(review_candidate.get("promotion_gate"), dict)
        else {}
    )
    retention_policy = (
        review_candidate.get("retention_policy", {})
        if isinstance(review_candidate.get("retention_policy"), dict)
        else {}
    )
    observability = (
        base.get("runtime_observability", {})
        if isinstance(base.get("runtime_observability"), dict)
        else run.get("runtime_observability", {})
    )
    observability = observability if isinstance(observability, dict) else {}
    llm_result = base.get("llm_runtime_result", {}) if isinstance(base.get("llm_runtime_result"), dict) else {}
    llm_plan = llm_result.get("llm_plan", {}) if isinstance(llm_result.get("llm_plan"), dict) else {}
    alignment = (
        base.get("llm_tool_plan_alignment", {})
        if isinstance(base.get("llm_tool_plan_alignment"), dict)
        else {}
    )
    contract_policy = contract.get("policy_gate", {}) if isinstance(contract.get("policy_gate"), dict) else {}
    contract_memory = contract.get("memory_write", {}) if isinstance(contract.get("memory_write"), dict) else {}
    details = {
        "run_schema": base.get("schema"),
        "run_status": base.get("run_status"),
        "execution_contract_schema": contract.get("schema"),
        "execution_contract_status": contract.get("status"),
        "execution_contract_issues": contract.get("issues", []),
        "policy_status": policy.get("status"),
        "policy_checked_before_llm": contract_policy.get("checked_before_llm"),
        "policy_checked_before_tools": contract_policy.get("checked_before_tools"),
        "capability_authorization_schema": authorization.get("schema"),
        "capability_authorization_mode": authorization.get("mode"),
        "capability_authorization_model": authorization.get("authorization_model"),
        "registered_tool_executor_is_execution_authority": authorization_invariants.get(
            "registered_tool_executor_is_execution_authority"
        ),
        "llm_tool_suggestions_are_non_authoritative": authorization_invariants.get(
            "llm_tool_suggestions_are_non_authoritative"
        ),
        "llm_plan_schema": llm_plan.get("schema"),
        "llm_plan_raw_provider_text_stored": llm_plan.get("raw_provider_text_stored"),
        "llm_tool_plan_alignment_schema": alignment.get("schema"),
        "llm_tool_plan_suggestion_only_enforced": alignment.get("suggestion_only_enforced"),
        "memory_review_candidate_schema": review_candidate.get("schema"),
        "memory_review_candidate_target": review_candidate.get("target"),
        "memory_automatic_promotion_performed": contract_memory.get(
            "automatic_promotion_performed",
            memory_write.get("automatic_promotion_performed"),
        ),
        "memory_review_candidate_automatic_promotion_allowed": promotion_gate.get("automatic_promotion_allowed"),
        "memory_review_candidate_private_reasoning_trace": retention_policy.get("private_reasoning_trace"),
        "runtime_observability_schema": observability.get("schema"),
        "runtime_private_reasoning_trace_stored": observability.get("privacy", {}).get(
            "private_reasoning_trace_stored"
        ),
        "runtime_full_session_replay_used": observability.get("context", {}).get("full_session_replay_used"),
    }
    details["p0_runtime_ready"] = (
        details["execution_contract_schema"] == AGENT_EXECUTION_CONTRACT_SCHEMA
        and details["execution_contract_status"] == "passed"
        and details["execution_contract_issues"] == []
        and details["policy_status"] == "approved"
        and details["policy_checked_before_llm"] is True
        and details["policy_checked_before_tools"] is True
        and details["capability_authorization_schema"] == CAPABILITY_AUTHORIZATION_SCHEMA
        and details["capability_authorization_mode"] == "deny_by_default"
        and details["registered_tool_executor_is_execution_authority"] is True
        and details["llm_tool_suggestions_are_non_authoritative"] is True
        and details["llm_plan_schema"] == "paideia-llm-reviewable-plan/v1"
        and details["llm_plan_raw_provider_text_stored"] is False
        and details["llm_tool_plan_alignment_schema"] == "paideia-llm-tool-plan-alignment/v1"
        and details["llm_tool_plan_suggestion_only_enforced"] is True
        and details["memory_review_candidate_schema"] == MEMORY_REVIEW_CANDIDATE_SCHEMA
        and details["memory_review_candidate_target"] == "local_learning_ledger"
        and details["memory_automatic_promotion_performed"] is False
        and details["memory_review_candidate_automatic_promotion_allowed"] is False
        and details["memory_review_candidate_private_reasoning_trace"] == "do_not_store"
        and details["runtime_observability_schema"] == RUNTIME_OBSERVABILITY_SCHEMA
        and details["runtime_private_reasoning_trace_stored"] is False
        and details["runtime_full_session_replay_used"] is False
    )
    return details


def _dataflow_p0_runtime_details(run: dict[str, Any]) -> dict[str, Any]:
    observability = run.get("runtime_observability", {}) if isinstance(run.get("runtime_observability"), dict) else {}
    llm_result = run.get("llm_runtime_result", {}) if isinstance(run.get("llm_runtime_result"), dict) else {}
    preflight = (
        run.get("llm_provider_preflight", {})
        if isinstance(run.get("llm_provider_preflight"), dict)
        else llm_result.get("llm_provider_preflight", {})
    )
    preflight = preflight if isinstance(preflight, dict) else {}
    growth = run.get("growth_commit_candidate", {}) if isinstance(run.get("growth_commit_candidate"), dict) else {}
    details = {
        "schema": run.get("schema"),
        "status": run.get("run_status"),
        "llm_provider_preflight_schema": preflight.get("schema"),
        "runtime_observability_schema": observability.get("schema"),
        "runtime_private_reasoning_trace_stored": observability.get("privacy", {}).get(
            "private_reasoning_trace_stored"
        ),
        "runtime_full_session_replay_used": observability.get("context", {}).get("full_session_replay_used"),
        "growth_candidate_schema": growth.get("schema"),
        "growth_candidate_private_reasoning_trace_policy": growth.get("private_reasoning_trace_policy"),
    }
    details["p0_runtime_ready"] = (
        details["schema"] == "ai-talent-dataflow-run/v1"
        and details["status"] == "completed"
        and details["llm_provider_preflight_schema"] == "paideia-llm-provider-preflight/v1"
        and details["runtime_observability_schema"] == RUNTIME_OBSERVABILITY_SCHEMA
        and details["runtime_private_reasoning_trace_stored"] is False
        and details["runtime_full_session_replay_used"] is False
        and details["growth_candidate_schema"] == "ai-talent-dataflow-growth-commit-candidate/v1"
        and details["growth_candidate_private_reasoning_trace_policy"] == "do_not_store"
    )
    return details


def _checkpoint(
    *,
    passed: bool,
    evidence: list[Path],
    root: Path,
    details: dict[str, Any] | None = None,
    missing: list[Path] | None = None,
) -> dict[str, Any]:
    return {
        "passed": passed,
        "evidence": [_rel(path, root) for path in evidence if path.exists()],
        "missing": [_rel(path, root) for path in missing or [] if not path.exists()],
        "details": details or {},
    }


def _research_foundation() -> dict[str, Any]:
    sources_path = PROJECT_ROOT / "data" / "public" / "research" / "agent_foundry_sources.jsonl"
    if not sources_path.exists():
        return _checkpoint(
            passed=False,
            evidence=[sources_path],
            root=PROJECT_ROOT,
            missing=[sources_path],
            details={"source_count": 0},
        )

    rows: list[dict[str, Any]] = []
    invalid_lines: list[int] = []
    for line_number, line in enumerate(sources_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            invalid_lines.append(line_number)
            continue
        if isinstance(item, dict):
            rows.append(item)

    names = {str(item.get("name", "")) for item in rows}
    categories = {str(item.get("category", "")) for item in rows}
    source_types = {str(item.get("source_type", "")) for item in rows}
    invalid_urls = [
        str(item.get("name", "unnamed"))
        for item in rows
        if not str(item.get("url", "")).startswith("https://")
    ]
    missing_implications = [
        str(item.get("name", "unnamed"))
        for item in rows
        if not str(item.get("design_implication", "")).strip()
    ]
    missing_operational_fields = [
        str(item.get("name", "unnamed"))
        for item in rows
        if str(item.get("category", "")) in OPERATIONAL_RESEARCH_CATEGORIES
        and (
            not str(item.get("observed_problem", "")).strip()
            or not str(item.get("mitigation", "")).strip()
        )
    ]
    missing_names = sorted(REQUIRED_RESEARCH_NAMES - names)
    missing_categories = sorted(REQUIRED_RESEARCH_CATEGORIES - categories)
    missing_source_types = sorted({"official_docs", "paper", "github_issue"} - source_types)

    details = {
        "source_count": len(rows),
        "names": sorted(names),
        "categories": sorted(categories),
        "source_types": sorted(source_types),
        "required_names_present": sorted(REQUIRED_RESEARCH_NAMES & names),
        "required_categories_present": sorted(REQUIRED_RESEARCH_CATEGORIES & categories),
        "invalid_lines": invalid_lines,
        "invalid_urls": invalid_urls,
        "missing_design_implications": missing_implications,
        "missing_operational_fields": missing_operational_fields,
        "operational_feedback_count": sum(
            1 for item in rows if str(item.get("category", "")) in OPERATIONAL_RESEARCH_CATEGORIES
        ),
        "missing_names": missing_names,
        "missing_categories": missing_categories,
        "missing_source_types": missing_source_types,
    }
    passed = (
        len(rows) >= 8
        and not invalid_lines
        and not invalid_urls
        and not missing_implications
        and not missing_operational_fields
        and not missing_names
        and not missing_categories
        and not missing_source_types
    )
    return _checkpoint(passed=passed, evidence=[sources_path], root=PROJECT_ROOT, details=details)


def _growth_governance(run_dir: Path) -> dict[str, Any]:
    paths = {
        "blueprint": run_dir / "shinyong_training_blueprint.json",
        "institutional_review": run_dir / "shinyong_institutional_review.json",
        "doctoral_assessment": run_dir / "shinyong_doctoral_assessment.json",
        "learning_ledger": run_dir / "shinyong_learning_ledger.json",
        "active_memory_route": run_dir / "shinyong_active_memory_route.json",
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        review = _read_json(paths["institutional_review"])
        assessment = _read_json(paths["doctoral_assessment"])
        ledger = _read_json(paths["learning_ledger"])
        active_memory_route = _read_json(paths["active_memory_route"])
        completed_gates = set(review.get("assessment_transcript", {}).get("completed_major_gates", []))
        details = {
            "education_committee_status": review.get("education_committee_decision", {}).get("status"),
            "oversight_status": review.get("oversight_committee_decision", {}).get("status"),
            "graduation_ready": review.get("assessment_transcript", {}).get("graduation_ready"),
            "completed_major_gates": sorted(completed_gates),
            "doctoral_defense_passed": assessment.get("gate_id") == "doctoral_defense" and assessment.get("passed"),
            "reasoning_kernel": ledger.get("reasoning_kernel", {}).get("schema"),
            "private_reasoning_trace": ledger.get("reasoning_kernel", {}).get("private_reasoning_trace"),
            "active_memory_route_schema": active_memory_route.get("schema"),
            "active_memory_route_budget": active_memory_route.get("routing_policy", {}).get("active_context_budget"),
            "active_memory_selected_count": active_memory_route.get("memory_health", {}).get("selected_experience_count"),
            "active_memory_quarantine_policy": active_memory_route.get("routing_policy", {}).get("quarantined_experiences"),
        }
        passed = (
            details["education_committee_status"] == "major_track_passed"
            and details["oversight_status"] == "employment_ready_with_guardrails"
            and details["graduation_ready"] is True
            and REQUIRED_MAJOR_GATES <= completed_gates
            and details["doctoral_defense_passed"] is True
            and details["reasoning_kernel"] == "ai-talent-reasoning-kernel/v1"
            and details["private_reasoning_trace"] == "do_not_store"
            and details["active_memory_route_schema"] == "ai-talent-active-memory-route/v1"
            and details["active_memory_route_budget"] == "bounded"
            and isinstance(details["active_memory_selected_count"], int)
            and details["active_memory_selected_count"] > 0
            and details["active_memory_quarantine_policy"] == "excluded"
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _public_program_manifest(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "ai_talent_foundry_public_manifest.json"
    if not manifest_path.exists():
        return _checkpoint(
            passed=False,
            evidence=[manifest_path],
            root=run_dir,
            missing=[manifest_path],
            details={},
        )

    manifest = _read_json(manifest_path)
    commands = {str(command.get("id", "")) for command in manifest.get("commands", [])}
    lifecycle = {str(step.get("id", "")) for step in manifest.get("employment_lifecycle", [])}
    roles = set(manifest.get("institutional_model", {}).get("required_roles", []))
    details = {
        "schema": manifest.get("schema"),
        "release_stage": manifest.get("distribution_model", {}).get("release_stage"),
        "local_first": manifest.get("distribution_model", {}).get("local_first"),
        "private_data_upload": manifest.get("privacy", {}).get("private_data_upload"),
        "commands": sorted(commands),
        "missing_commands": sorted(REQUIRED_PUBLIC_PROGRAM_COMMANDS - commands),
        "lifecycle": sorted(lifecycle),
        "missing_lifecycle_steps": sorted(REQUIRED_PUBLIC_PROGRAM_LIFECYCLE - lifecycle),
        "required_roles": sorted(roles),
        "missing_roles": sorted(REQUIRED_PUBLIC_PROGRAM_ROLES - roles),
        "not_separate_consciousnesses": manifest.get("projection_model", {}).get("not_separate_consciousnesses"),
        "separate_employment_records": manifest.get("projection_model", {}).get("separate_employment_records"),
        "family_child_blueprint": manifest.get("family_lineage_model", {}).get("child_blueprint"),
        "family_biological_claim": manifest.get("family_lineage_model", {}).get("biological_claim"),
        "source_count": manifest.get("research_foundation", {}).get("source_count"),
        "expected_audit": manifest.get("release_evidence", {}).get("expected_audit"),
    }
    passed = (
        details["schema"] == "ai-talent-foundry-public-program-manifest/v1"
        and details["release_stage"] == "local_public_preview"
        and details["local_first"] is True
        and details["private_data_upload"] == "forbidden"
        and not details["missing_commands"]
        and not details["missing_lifecycle_steps"]
        and not details["missing_roles"]
        and details["not_separate_consciousnesses"] is True
        and details["separate_employment_records"] is False
        and details["family_child_blueprint"] == "family_seed_to_training_blueprint"
        and details["family_biological_claim"] == "not_claimed"
        and isinstance(details["source_count"], int)
        and details["source_count"] >= 8
        and details["expected_audit"] == "foundry_release_audit.json"
    )
    return _checkpoint(passed=passed, evidence=[manifest_path], root=run_dir, details=details)


def _family_lineage(run_dir: Path) -> dict[str, Any]:
    family_path = run_dir / "shinyong_family_lineage.json"
    if not family_path.exists():
        return _checkpoint(
            passed=False,
            evidence=[family_path],
            root=run_dir,
            missing=[family_path],
            details={},
        )

    family = _read_json(family_path)
    union = family.get("family_union", {})
    child_seed = family.get("child_seed", {})
    child_blueprint = family.get("child_training_blueprint", {})
    lineage_context = child_blueprint.get("family_lineage_context", {})
    stage_ids = {str(stage.get("id", "")) for stage in child_blueprint.get("training_pipeline", [])}
    details = {
        "union_type": union.get("union_type"),
        "biological_claim": union.get("safety", {}).get("biological_claim"),
        "child_seed_status": child_seed.get("status"),
        "child_name": child_seed.get("talent", {}).get("name"),
        "child_blueprint_schema": child_blueprint.get("schema"),
        "child_blueprint_relationship": child_blueprint.get("identity", {}).get("relationship"),
        "child_blueprint_parents": lineage_context.get("parents", []),
        "inherited_influence_count": len(lineage_context.get("inherited_reasoning_influences", [])),
        "parental_home_education_stage": "parental_home_education" in stage_ids,
        "llm_identity_policy": child_blueprint.get("llm_policy", {}).get("role"),
    }
    passed = (
        details["union_type"] == "ai_family_lineage"
        and details["biological_claim"] == "not_claimed"
        and details["child_seed_status"] == "child_ai_seed_ready"
        and details["child_blueprint_schema"] == "ai-talent-training-blueprint/v1"
        and details["child_blueprint_relationship"] == "family_lineage_child_ai_talent"
        and len(details["child_blueprint_parents"]) == 2
        and details["inherited_influence_count"] == 2
        and details["parental_home_education_stage"] is True
        and details["llm_identity_policy"] == "application_engine_not_identity"
    )
    return _checkpoint(passed=passed, evidence=[family_path], root=run_dir, details=details)


def _public_distribution(run_dir: Path, installed_root: Path) -> dict[str, Any]:
    bundle_dir = run_dir / "shinyong_agent_release_bundle"
    archive = run_dir / "shinyong_agent_release_bundle.zip"
    package_manifest_path = run_dir / "shinyong_agent_release_bundle.package_manifest.json"
    installed_manifest_path = installed_root / "installed_agent_manifest.json"
    required = [bundle_dir, archive, package_manifest_path, installed_manifest_path]
    missing = [path for path in required if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        package_manifest = _read_json(package_manifest_path)
        installed_manifest = _read_json(installed_manifest_path)
        bundle_verification = verify_agent_release_bundle(bundle_dir)
        archive_verification = verify_agent_release_archive(archive, expected_sha256=package_manifest.get("sha256"))
        details = {
            "package_schema": package_manifest.get("schema"),
            "package_public_distribution_ready": package_manifest.get("public_distribution_ready"),
            "bundle_verification_passed": bundle_verification.get("passed"),
            "archive_verification_passed": archive_verification.get("passed"),
            "installed_archive_verification_passed": installed_manifest.get("archive_verification", {}).get("passed"),
            "forbidden_file_hits": bundle_verification.get("forbidden_file_hits", []),
            "forbidden_content_hits": bundle_verification.get("forbidden_content_hits", []),
        }
        passed = (
            details["package_schema"] == "ai-talent-release-package/v1"
            and details["package_public_distribution_ready"] is True
            and details["bundle_verification_passed"] is True
            and details["archive_verification_passed"] is True
            and details["installed_archive_verification_passed"] is True
            and not details["forbidden_file_hits"]
            and not details["forbidden_content_hits"]
        )
    return _checkpoint(passed=passed, evidence=required, root=run_dir, details=details, missing=missing)


def _local_employment(installed_root: Path, run_dir: Path) -> dict[str, Any]:
    paths = {
        "employment_record": installed_root / "employment_record.json",
        "hired_agent_run": installed_root / "last_hired_agent_run.json",
        "hired_workspace_run": installed_root / "last_hired_workspace_agent_run.json",
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        employment = _read_json(paths["employment_record"])
        agent_run = _read_json(paths["hired_agent_run"])
        workspace_run = _read_json(paths["hired_workspace_run"])
        agent_p0 = _agent_p0_runtime_details(agent_run)
        workspace_p0 = _agent_p0_runtime_details(workspace_run)
        details = {
            "employment_schema": employment.get("schema"),
            "employment_status": employment.get("status"),
            "growth_after_hire_continues": employment.get("growth_after_hire", {}).get("continues"),
            "llm_identity_policy": employment.get("llm_runtime", {}).get("identity_policy"),
            "agent_run_status": agent_run.get("run_status"),
            "workspace_run_status": workspace_run.get("run_status"),
            "agent_run_p0_runtime_ready": agent_p0["p0_runtime_ready"],
            "workspace_run_p0_runtime_ready": workspace_p0["p0_runtime_ready"],
            "agent_run_p0": agent_p0,
            "workspace_run_p0": workspace_p0,
        }
        passed = (
            details["employment_schema"] == "ai-talent-local-employment/v1"
            and details["employment_status"] == "active"
            and details["growth_after_hire_continues"] is True
            and details["llm_identity_policy"] == "application_engine_not_identity"
            and details["agent_run_status"] == "completed"
            and details["workspace_run_status"] == "completed"
            and details["agent_run_p0_runtime_ready"] is True
            and details["workspace_run_p0_runtime_ready"] is True
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _agent_job_runtime(installed_root: Path, run_dir: Path) -> dict[str, Any]:
    paths = {
        "agent_job_run": installed_root / "last_hired_agent_job_run.json",
        "agent_job_cycle": installed_root / "last_hired_agent_job_cycle.json",
        "agent_job_workspace": installed_root / "agent_job_workspace",
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        job_run = _read_json(paths["agent_job_run"])
        job_cycle = _read_json(paths["agent_job_cycle"])
        job_outputs = job_run.get("job_outputs", {})
        report_raw = str(job_outputs.get("job_report", ""))
        checklist_raw = str(job_outputs.get("acceptance_checklist", ""))
        report_path = Path(report_raw) if report_raw else None
        checklist_path = Path(checklist_raw) if checklist_raw else None
        checklist = _read_json(checklist_path) if checklist_path is not None and checklist_path.exists() else {}
        criteria_statuses = {str(item.get("status", "")) for item in checklist.get("criteria", [])}
        active_memory_route = job_run.get("active_memory_route", {})
        job_p0 = _agent_p0_runtime_details(job_run.get("workspace_run", {}))
        details = {
            "schema": job_run.get("schema"),
            "runtime_model": job_run.get("runtime_model"),
            "job_status": job_run.get("job_status"),
            "employment_relationship": job_run.get("employment_context", {}).get("relationship"),
            "network_access": job_run.get("tool_authorization", {}).get("network_access"),
            "job_report_exists": report_path is not None and report_path.exists(),
            "acceptance_checklist_exists": checklist_path is not None and checklist_path.exists(),
            "acceptance_schema": checklist.get("schema"),
            "criteria_statuses": sorted(criteria_statuses),
            "active_memory_route_schema": active_memory_route.get("schema"),
            "active_memory_selected_count": active_memory_route.get("memory_health", {}).get("selected_experience_count"),
            "active_memory_budget": active_memory_route.get("routing_policy", {}).get("active_context_budget"),
            "job_cycle_schema": job_cycle.get("schema"),
            "job_cycle_status": job_cycle.get("cycle_status"),
            "job_cycle_learning_decision": job_cycle.get("learning_update", {}).get("decision"),
            "job_base_agent_p0_runtime_ready": job_p0["p0_runtime_ready"],
            "job_base_agent_p0": job_p0,
        }
        passed = (
            details["schema"] == "ai-talent-hired-agent-job-run/v1"
            and details["runtime_model"] == "openclaw_style_hired_agent_job"
            and details["job_status"] == "completed"
            and details["employment_relationship"] == "installed_ai_talent_hired_as_local_agent"
            and details["network_access"] == "blocked"
            and details["job_report_exists"] is True
            and details["acceptance_checklist_exists"] is True
            and details["acceptance_schema"] == "ai-talent-agent-job-acceptance-checklist/v1"
            and criteria_statuses == {"satisfied_by_workspace_artifact"}
            and details["active_memory_route_schema"] == "ai-talent-active-memory-route/v1"
            and isinstance(details["active_memory_selected_count"], int)
            and details["active_memory_selected_count"] > 0
            and details["active_memory_budget"] == "bounded"
            and details["job_cycle_schema"] == "ai-talent-hired-agent-job-cycle/v1"
            and details["job_cycle_status"] == "completed_and_promoted"
            and details["job_cycle_learning_decision"] == "promoted"
            and details["job_base_agent_p0_runtime_ready"] is True
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _post_hire_growth(installed_root: Path, run_dir: Path) -> dict[str, Any]:
    paths = {
        "learning_ledger": installed_root / "learning_ledger.json",
        "post_hire_learning_update": installed_root / "post_hire_learning_update.json",
        "employment_goal": installed_root / "employment_goal.json",
        "employment_goal_cycle": installed_root / "last_employment_goal_cycle.json",
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        ledger = _read_json(paths["learning_ledger"])
        update = _read_json(paths["post_hire_learning_update"])
        goal = _read_json(paths["employment_goal"])
        cycle = _read_json(paths["employment_goal_cycle"])
        skills = set(ledger.get("reasoning_kernel", {}).get("procedural_skills", []))
        details = {
            "post_hire_decision": update.get("decision"),
            "quality_status": update.get("quality_label", {}).get("status"),
            "goal_status": goal.get("status"),
            "goal_cycle_status": cycle.get("cycle_status"),
            "goal_learning_decision": cycle.get("learning_update", {}).get("decision"),
            "has_workspace_artifact_trace": "workspace_artifact_trace" in skills,
        }
        passed = (
            details["post_hire_decision"] == "promoted"
            and details["quality_status"] == "verified"
            and details["goal_cycle_status"] == "completed"
            and details["goal_learning_decision"] == "promoted"
            and details["has_workspace_artifact_trace"] is True
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _projection_swarm(installed_root: Path, run_dir: Path) -> dict[str, Any]:
    paths = {
        "swarm": installed_root / "hired_projection_swarm.json",
        "cycle": installed_root / "hired_projection_swarm_cycle.json",
        "workspace": installed_root / "projection_swarm_workspace",
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        swarm = _read_json(paths["swarm"])
        cycle = _read_json(paths["cycle"])
        parent_id = swarm.get("parent", {}).get("employment_context", {}).get("employment_id")
        projection_ids = {
            item.get("employment_context", {}).get("employment_id")
            for item in swarm.get("projections", [])
        }
        consciousness = {
            item.get("consciousness")
            for item in swarm.get("projections", [])
        }
        command_model = swarm.get("swarm_policy", {}).get("command_model", {})
        contribution_modes = {
            item.get("execution_mode")
            for item in cycle.get("contributions", [])
        }
        details = {
            "projection_count": swarm.get("swarm", {}).get("projection_count"),
            "parent_employment_id": parent_id,
            "projection_employment_ids": sorted(item for item in projection_ids if item),
            "consciousness": next(iter(consciousness)) if len(consciousness) == 1 else sorted(consciousness),
            "command_control_topology": command_model.get("control_topology"),
            "command_execution_modes": command_model.get("execution_modes", []),
            "joint_collaboration_allowed": cycle.get("parent_synthesis", {}).get("joint_collaboration_allowed"),
            "contribution_execution_modes": sorted(item for item in contribution_modes if item),
            "separate_employment_records": swarm.get("swarm_policy", {})
            .get("control_model", {})
            .get("separate_employment_records"),
            "not_separate_consciousnesses": swarm.get("swarm_policy", {})
            .get("control_model", {})
            .get("not_separate_consciousnesses"),
            "cycle_status": cycle.get("cycle_status"),
            "separate_consciousness_created": cycle.get("parent_synthesis", {}).get("separate_consciousness_created"),
            "merge_target": cycle.get("parent_growth_merge", {}).get("merge_target"),
        }
        passed = (
            details["projection_count"] == 4
            and projection_ids == {parent_id}
            and consciousness == {"parent_controlled_projection"}
            and details["command_control_topology"] == "single_parent_body_to_task_projections"
            and "joint_collaboration" in details["command_execution_modes"]
            and details["joint_collaboration_allowed"] is True
            and contribution_modes == {"role_split"}
            and details["separate_employment_records"] is False
            and details["not_separate_consciousnesses"] is True
            and details["cycle_status"] == "completed"
            and details["separate_consciousness_created"] is False
            and details["merge_target"] == "parent_growth_log"
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _specialist_team(installed_root: Path, run_dir: Path) -> dict[str, Any]:
    paths = {
        "specialist_cohort": run_dir / "shinyong_specialist_cohort.json",
        "hired_agent_team": installed_root / "hired_agent_team.json",
        "hired_agent_team_cycle": installed_root / "hired_agent_team_cycle.json",
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        cohort = _read_json(paths["specialist_cohort"])
        team = _read_json(paths["hired_agent_team"])
        cycle = _read_json(paths["hired_agent_team_cycle"])
        details = {
            "cohort_schema": cohort.get("schema"),
            "cohort_member_count": cohort.get("team", {}).get("member_count"),
            "hired_team_schema": team.get("schema"),
            "hired_team_member_count": team.get("team", {}).get("member_count"),
            "hired_team_cycle_status": cycle.get("cycle_status"),
            "not_a_projection_team": team.get("team_policy", {}).get("not_a_projection_team"),
        }
        passed = (
            details["cohort_schema"] == "ai-talent-specialist-cohort/v1"
            and details["cohort_member_count"] == 4
            and details["hired_team_schema"] == "ai-talent-hired-agent-team/v1"
            and details["hired_team_member_count"] >= 2
            and details["hired_team_cycle_status"] == "completed"
            and details["not_a_projection_team"] is True
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _role_model_training_artifacts(run_dir: Path, installed_root: Path) -> dict[str, Any]:
    training_run_path = run_dir / "training_run.json"
    training_artifacts: dict[str, Path] = {}
    if training_run_path.exists():
        training_run_data = _read_json(training_run_path)
        training_artifacts = {
            key: Path(value)
            for key, value in training_run_data.get("artifacts", {}).items()
            if isinstance(value, str)
        }

    def from_run_or_glob(key: str, pattern: str) -> Path:
        artifact = training_artifacts.get(key)
        if artifact is not None:
            return artifact
        matches = sorted(run_dir.glob(pattern))
        return matches[0] if matches else run_dir / pattern.replace("*", "missing")

    paths = {
        "training_run": training_run_path,
        "training_blueprint": from_run_or_glob("training_blueprint", "*_training_blueprint.json"),
        "role_model_profile": from_run_or_glob("role_model_profile", "*_role_model_profile.json"),
        "saju_narrative_seed": from_run_or_glob("saju_narrative_seed", "*_saju_narrative_seed.json"),
        "process_emulation_plan": from_run_or_glob("process_emulation_plan", "*_process_emulation_plan.json"),
        "curriculum_manifest": from_run_or_glob("curriculum_manifest", "*_curriculum_manifest.json"),
        "assessment_transcript": from_run_or_glob("assessment_transcript", "*_assessment_transcript.json"),
        "reasoning_kibo": from_run_or_glob("reasoning_kibo", "*_reasoning_kibo.jsonl"),
        "talent_plan": from_run_or_glob("talent_plan", "*_agent_plan.json"),
        "institutional_review": from_run_or_glob("institutional_review", "*_institutional_review.json"),
        "learning_ledger": from_run_or_glob("learning_ledger", "*_learning_ledger.json"),
        "agent_manifest": from_run_or_glob("agent_manifest", "*_agent_manifest.json"),
        "release_bundle": from_run_or_glob("release_bundle", "*_agent_release_bundle"),
        "release_archive": from_run_or_glob("release_archive", "*_agent_release_bundle.zip"),
        "release_package_manifest": from_run_or_glob(
            "release_package_manifest",
            "*_agent_release_bundle.package_manifest.json",
        ),
        "installed_agent_manifest": installed_root / "installed_agent_manifest.json",
        "employment_record": installed_root / "employment_record.json",
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        training_run = _read_json(paths["training_run"])
        role_model = _read_json(paths["role_model_profile"])
        saju = _read_json(paths["saju_narrative_seed"])
        process = _read_json(paths["process_emulation_plan"])
        curriculum = _read_json(paths["curriculum_manifest"])
        transcript = _read_json(paths["assessment_transcript"])
        manifest = _read_json(paths["agent_manifest"])
        employment = _read_json(paths["employment_record"])
        kibo_entries = [
            line for line in paths["reasoning_kibo"].read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        details = {
            "training_status": training_run.get("status"),
            "role_model_id": role_model.get("role_model_id"),
            "saju_schema": saju.get("schema"),
            "process_schema": process.get("schema"),
            "process_mode": process.get("design_principle", {}).get("mode"),
            "curriculum_id": curriculum.get("curriculum_id"),
            "graduation_ready": transcript.get("graduation_ready"),
            "assessment_count": len(transcript.get("results", [])),
            "reasoning_kibo_entries": len(kibo_entries),
            "manifest_schema": manifest.get("schema"),
            "employment_schema": employment.get("schema"),
            "compatible_targets": manifest.get("compatible_targets", []),
        }
        passed = (
            details["training_status"] == "employment_ready"
            and details["role_model_id"] == "graham_value_investing"
            and details["saju_schema"] == "ai-talent-saju-narrative-seed/v1"
            and details["process_schema"] == "ai-talent-role-model-process-emulation/v1"
            and details["process_mode"] == "learning_path_replication_not_personality_injection"
            and details["curriculum_id"] == "graham_securities_research"
            and details["graduation_ready"] is True
            and details["assessment_count"] >= 9
            and details["reasoning_kibo_entries"] >= 2
            and details["manifest_schema"] == "ai-talent-agent-manifest/v1"
            and details["employment_schema"] == "ai-talent-local-employment/v1"
            and "openclaw_style_agent_manifest" in details["compatible_targets"]
            and "hermes_style_agent_manifest" in details["compatible_targets"]
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _role_model_runtime(installed_root: Path, run_dir: Path) -> dict[str, Any]:
    agent_run_candidates = [
        installed_root / "last_hired_agent_run.json",
        installed_root / "manual_hired_agent_run.json",
    ]
    dataflow_candidates = [
        installed_root / "last_hired_dataflow_run.json",
        installed_root / "manual_dataflow_run.json",
    ]
    agent_run_path = next((path for path in agent_run_candidates if path.exists()), agent_run_candidates[0])
    dataflow_run_path = next((path for path in dataflow_candidates if path.exists()), dataflow_candidates[0])
    paths = {
        "agent_run": agent_run_path,
        "dataflow_run": dataflow_run_path,
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        agent_run = _read_json(paths["agent_run"])
        dataflow_run = _read_json(paths["dataflow_run"])
        agent_p0 = _agent_p0_runtime_details(agent_run)
        dataflow_p0 = _dataflow_p0_runtime_details(dataflow_run)
        details = {
            "agent_run_status": agent_run.get("run_status"),
            "dataflow_schema": dataflow_run.get("schema"),
            "dataflow_status": dataflow_run.get("run_status"),
            "workspace_output_count": len(dataflow_run.get("workspace_outputs", {})),
            "growth_candidate_schema": dataflow_run.get("growth_commit_candidate", {}).get("schema"),
            "agent_run_p0_runtime_ready": agent_p0["p0_runtime_ready"],
            "dataflow_p0_runtime_ready": dataflow_p0["p0_runtime_ready"],
            "agent_run_p0": agent_p0,
            "dataflow_p0": dataflow_p0,
        }
        passed = (
            details["agent_run_status"] == "completed"
            and details["dataflow_schema"] == "ai-talent-dataflow-run/v1"
            and details["dataflow_status"] == "completed"
            and details["workspace_output_count"] >= 5
            and details["growth_candidate_schema"] == "ai-talent-dataflow-growth-commit-candidate/v1"
            and details["agent_run_p0_runtime_ready"] is True
            and details["dataflow_p0_runtime_ready"] is True
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _is_role_model_run(run_dir: Path) -> bool:
    return any(run_dir.glob("*_role_model_profile.json")) and any(run_dir.glob("*_reasoning_kibo.jsonl"))


def audit_foundry_release(run_dir: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    installed_root = _installed_agent_root(run_dir)
    if _is_role_model_run(run_dir):
        checkpoints = {
            "research_foundation": _research_foundation(),
            "public_program_manifest": _public_program_manifest(run_dir),
            "role_model_training_artifacts": _role_model_training_artifacts(run_dir, installed_root),
            "role_model_runtime": _role_model_runtime(installed_root, run_dir),
        }
    else:
        checkpoints = {
            "research_foundation": _research_foundation(),
            "public_program_manifest": _public_program_manifest(run_dir),
            "growth_governance": _growth_governance(run_dir),
            "public_distribution": _public_distribution(run_dir, installed_root),
            "local_employment": _local_employment(installed_root, run_dir),
            "agent_job_runtime": _agent_job_runtime(installed_root, run_dir),
            "post_hire_growth": _post_hire_growth(installed_root, run_dir),
            "family_lineage": _family_lineage(run_dir),
            "projection_swarm": _projection_swarm(installed_root, run_dir),
            "specialist_team": _specialist_team(installed_root, run_dir),
        }
    failed = [name for name, checkpoint in checkpoints.items() if not checkpoint["passed"]]
    public_release_ready = not failed
    audit = {
        "schema": AUDIT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_dir": run_dir.name,
        "installed_agent": installed_root.name,
        "public_release_ready": public_release_ready,
        "overall_status": "ready_for_local_public_preview" if public_release_ready else "needs_attention",
        "checkpoints": checkpoints,
        "required_next_actions": [
            f"Fix release checkpoint: {name}"
            for name in failed
        ],
    }
    if output_path is not None:
        _write_json(output_path, audit)
    return audit
