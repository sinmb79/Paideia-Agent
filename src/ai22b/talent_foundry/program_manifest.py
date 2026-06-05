from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.config import PROJECT_ROOT
from ai22b.talent_foundry.onboarding_choices import CHAT_SURFACE_CATALOG, LLM_SERVICE_CATALOG
from ai22b.talent_foundry.role_models import list_role_models, summarize_role_model


PUBLIC_PROGRAM_MANIFEST_SCHEMA = "ai-talent-foundry-public-program-manifest/v1"
DEFAULT_PUBLIC_PROGRAM_MANIFEST_NAME = "ai_talent_foundry_public_manifest.json"

REQUIRED_INSTALLER_COMMANDS = [
    "list-role-models",
    "prepare-owner-self-extension-intake",
    "blueprint",
    "onboard",
    "start-console",
    "onboard-agent",
    "raise",
    "build-developmental-ecology",
    "build-life-trace",
    "build-growth-profile",
    "run-same-sky-eval",
    "evaluate-simulation-rollouts",
    "run-action-policy-eval",
    "create-boss-approval",
    "verify-workspace-execution",
    "compare-runtime-observability",
    "build-graduate-package",
    "doctor-llm-provider",
    "doctor-bundle",
    "install-package",
    "export-agent-id-card-payload",
    "export-agent-identity-envelope",
    "verify-agent-id-card",
    "import-agent-id-card-registration",
    "hire-installed",
    "run-hired-workspace-agent",
    "run-hired-agent",
    "chat-hired-agent",
    "build-agent-program",
    "build-paideia-agent-kit",
    "doctor-agent-program",
    "migrate-agent-assets",
    "run-agent-program-chat",
    "run-hired-agent-job",
    "run-hired-dataflow-job",
    "run-hired-agent-job-cycle",
    "record-hired-learning",
    "assign-hired-goal",
    "assemble-hired-projection-swarm",
    "assemble-hired-team",
    "family",
    "audit-release",
]

EMPLOYMENT_LIFECYCLE_STEPS = [
    ("design", "Turn the desired role into a growth-to-employment blueprint."),
    ("raise", "Run education, home-care, exams, memory, and reasoning-kernel preparation."),
    ("package", "Export a public-safe local agent release bundle and ZIP."),
    ("install", "Install the verified ZIP into a local agent registry."),
    ("hire", "Create a local employment record for the installed talent."),
    ("work", "Run the hired agent in an authorized local workspace."),
    ("review", "Attach quality labels to work before learning promotion."),
    ("grow", "Promote verified work into the continuing reasoning kernel."),
    ("lineage", "Optionally create AI family lineage and a child training blueprint from employed parent talents."),
    ("audit", "Verify the whole lifecycle before public preview distribution."),
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        try:
            return path.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            return path.name


def _research_summary() -> dict[str, Any]:
    sources_path = PROJECT_ROOT / "data" / "public" / "research" / "agent_foundry_sources.jsonl"
    rows = [
        json.loads(line)
        for line in sources_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if sources_path.exists() else []
    return {
        "source_index": _rel(sources_path, PROJECT_ROOT),
        "source_count": len(rows),
        "categories": sorted({str(row.get("category", "")) for row in rows if row.get("category")}),
        "source_types": sorted({str(row.get("source_type", "")) for row in rows if row.get("source_type")}),
        "names": sorted({str(row.get("name", "")) for row in rows if row.get("name")}),
    }


def _commands() -> list[dict[str, str]]:
    purposes = {
        "list-role-models": "List role-model process templates available for a talent track.",
        "prepare-owner-self-extension-intake": "Prepare metadata-only local owner self-extension intake without exporting private filenames, paths, or file contents.",
        "blueprint": "Create a growth-to-employment blueprint from an owner request.",
        "onboard": "Run the OpenClaw-style wizard for model, workspace, channel, skills, education path, identity, and health setup.",
        "start-console": "Guide a non-expert installer through request, identity, first goal, and onboarding execution.",
        "onboard-agent": "Run one-shot onboarding from owner request to hired agent with a first reviewed goal cycle.",
        "raise": "Materialize the blueprint into an employable local AI talent.",
        "build-developmental-ecology": "Build a synthetic developmental ecology seed from a training blueprint.",
        "build-life-trace": "Build age-appropriate synthetic life events from ecology for the memory substrate.",
        "build-growth-profile": "Condense life-trace and ecology records into relationship, emotion, culture, aesthetic, and asymmetry memory.",
        "run-same-sky-eval": "Present one shared scene to multiple hired agents and compare reviewable interpretation differences.",
        "evaluate-simulation-rollouts": "Rank parallel rollout episodes and choose reviewed promotion or quarantine candidates without automatic memory promotion.",
        "run-action-policy-eval": "Run public P0 action-policy fixtures for prompt-injection, sensitive-action, upload, and personal-data boundaries.",
        "create-boss-approval": "Create a local boss approval artifact for one sensitive action gate without executing that action.",
        "verify-workspace-execution": "Verify a workspace, hired-job, or dataflow run with sandbox, rollback, LLM, and memory-safety proof checks.",
        "compare-runtime-observability": "Compare Paideia runtime observability against a generic prompt-wrapper full-run replay baseline.",
        "build-graduate-package": "Export a resume, transcript, memory pack, runtime manifest, and onboarding prompt for a raised talent.",
        "doctor-llm-provider": "Check a selected LLM provider, model, credential environment, local path, or local server before agent use.",
        "doctor-bundle": "Verify a release bundle's files, entrypoints, installer template, and local-only policy.",
        "install-package": "Install a verified release archive into a local registry.",
        "export-agent-id-card-payload": "Build a local-only Agent ID Card registration payload without uploading it.",
        "export-agent-identity-envelope": "Build an Agent_warrent/Agent Identity Layer ail.v1 envelope without registering or uploading it.",
        "verify-agent-id-card": "Verify local Agent ID Card and Agent_warrent identity artifacts before manual external registration.",
        "import-agent-id-card-registration": "Import an owner-performed external Agent ID Card/Agent_warrent registration result into local identity records without calling the network.",
        "hire-installed": "Create the owner-to-agent employment relationship.",
        "run-hired-workspace-agent": "Run the hired talent inside a local workspace.",
        "run-hired-agent": "Run the hired talent in the local CLI runtime.",
        "chat-hired-agent": "Prepare a Codex chat turn using the hired talent's memory substrate.",
        "build-agent-program": "Build a Paideia Agent program manifest from a hired talent record.",
        "build-paideia-agent-kit": "Build an installable Paideia Agent kit with onboarding, doctor, and adapter manifests.",
        "doctor-agent-program": "Doctor a Paideia Agent program before first run.",
        "migrate-agent-assets": "Import Hermes/OpenClaw/generic skills into a Paideia Agent kit as quarantined wrappers.",
        "run-agent-program-chat": "Chat through the Paideia Agent education center/runtime using local growth records and the Reasoning Ledger.",
        "run-hired-agent-job": "Run a hired talent from a job spec with deliverables and acceptance checks.",
        "run-hired-dataflow-job": "Run the hired talent through the local Agent Dataflow Runtime.",
        "run-hired-agent-job-cycle": "Run a job, attach a quality label, promote verified learning, and refresh active memory.",
        "record-hired-learning": "Review a run and update the installed learning ledger.",
        "assign-hired-goal": "Assign a long-running employment objective.",
        "assemble-hired-projection-swarm": "Create parent-controlled task projections for one hired talent.",
        "assemble-hired-team": "Assemble separately hired specialist talents into one team.",
        "family": "Create a local AI family lineage, child seed, and child training blueprint.",
        "audit-release": "Audit public preview readiness across the lifecycle.",
    }
    return [
        {
            "id": command,
            "command": f"ai22b-talent-foundry {command}",
            "purpose": purposes[command],
        }
        for command in REQUIRED_INSTALLER_COMMANDS
    ]


def _evidence_path(run_dir: Path, relative_path: str) -> str | None:
    path = run_dir / relative_path
    return relative_path if path.exists() else None


def build_public_program_manifest(run_dir: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    output_path = output_path or run_dir / DEFAULT_PUBLIC_PROGRAM_MANIFEST_NAME

    evidence_candidates = {
        "training_blueprint": "shinyong_training_blueprint.json",
        "growth_profile": "shinyong_growth_profile.json",
        "graduate_package": "graduate_package/graduate_package_manifest.json",
        "active_memory_route": "shinyong_active_memory_route.json",
        "release_package": "shinyong_agent_release_bundle.zip",
        "package_manifest": "shinyong_agent_release_bundle.package_manifest.json",
        "installed_manifest": "installed_agents/agents/shinyong_agent_release_bundle/installed_agent_manifest.json",
        "employment_record": "installed_agents/agents/shinyong_agent_release_bundle/employment_record.json",
        "workspace_run": "installed_agents/agents/shinyong_agent_release_bundle/last_hired_workspace_agent_run.json",
        "agent_job_run": "installed_agents/agents/shinyong_agent_release_bundle/last_hired_agent_job_run.json",
        "agent_job_cycle": "installed_agents/agents/shinyong_agent_release_bundle/last_hired_agent_job_cycle.json",
        "runtime_observability_comparison": "runtime_observability_comparison.json",
        "post_hire_learning": "installed_agents/agents/shinyong_agent_release_bundle/post_hire_learning_update.json",
        "goal_cycle": "installed_agents/agents/shinyong_agent_release_bundle/last_employment_goal_cycle.json",
        "family_lineage": "shinyong_family_lineage.json",
        "projection_swarm": "installed_agents/agents/shinyong_agent_release_bundle/hired_projection_swarm.json",
        "projection_cycle": "installed_agents/agents/shinyong_agent_release_bundle/hired_projection_swarm_cycle.json",
        "specialist_team": "installed_agents/agents/shinyong_agent_release_bundle/hired_agent_team.json",
        "specialist_team_cycle": "installed_agents/agents/shinyong_agent_release_bundle/hired_agent_team_cycle.json",
    }
    evidence = {
        key: value
        for key, value in (
            (key, _evidence_path(run_dir, relative_path))
            for key, relative_path in evidence_candidates.items()
        )
        if value is not None
    }

    installed_manifest_path = run_dir / evidence_candidates["installed_manifest"]
    installed_manifest = _read_json(installed_manifest_path) if installed_manifest_path.exists() else {}

    manifest = {
        "schema": PUBLIC_PROGRAM_MANIFEST_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "name": "AI Talent Foundry",
        "program_name": "Paideia Agent",
        "program_name_ko": "Paideia Agent",
        "purpose": "Raise, verify, install, hire, and continuously grow local AI talents through a Codex-connected AI education center.",
        "distribution_model": {
            "release_stage": "local_public_preview",
            "local_first": True,
            "external_api_required": False,
            "public_distribution_target": "installable_local_agent_program",
        },
        "privacy": {
            "private_data_upload": "forbidden",
            "local_runtime_state_policy": "do_not_export_private_runtime_state",
            "private_reasoning_trace": "do_not_store",
            "owner_assets_policy": "owner_property_local_only",
        },
        "commands": _commands(),
        "employment_lifecycle": [
            {
                "id": step_id,
                "description": description,
            }
            for step_id, description in EMPLOYMENT_LIFECYCLE_STEPS
        ],
        "institutional_model": {
            "required_roles": ["education_committee", "home_care", "oversight_committee"],
            "assessment_gates": ["school_exam", "csat", "university_graduation", "doctoral_defense"],
            "purpose": "Make growth auditable before an AI talent can be hired.",
        },
        "reasoning_model": {
            "llm_identity_policy": "application_engine_not_identity",
            "growth_after_hire_continues": True,
            "learning_promotion": "only_quality_labeled_experiences",
            "memory_routing": {
                "active_context_budget": "bounded",
                "compression_policy": "summaries_and_skills_only",
                "quarantined_experiences": "excluded",
                "private_reasoning_trace": "do_not_store",
            },
        },
        "guided_console": {
            "entrypoint": "ai22b-talent-foundry start-console",
            "onboarding_order": [
                "choose_llm_service",
                "choose_chat_surface",
                "capture_owner_request",
                "select_role_model",
                "raise_and_review_hiring_dossier",
            ],
            "llm_service_catalog": LLM_SERVICE_CATALOG,
            "chat_surface_catalog": CHAT_SURFACE_CATALOG,
            "role_model_catalog": [summarize_role_model(item) for item in list_role_models()],
            "bundled_sample_answers": "examples/graham_junior_onboarding.answers.json",
            "post_hire_modes": ["single", "projection_swarm", "specialist_team"],
            "answers_file_supported": True,
            "interactive_prompt_supported": True,
        },
        "projection_model": {
            "consciousness": "parent_controlled_projection",
            "not_separate_consciousnesses": True,
            "separate_employment_records": False,
            "merge_target": "parent_growth_log",
            "command_model": {
                "control_topology": "single_parent_body_to_task_projections",
                "projection_control": "main_body_issues_directives",
                "execution_modes": ["role_split", "joint_collaboration"],
                "projections_can_work_together": True,
                "projection_peer_consciousness": False,
                "result_merge": "parent_synthesis_before_growth_merge",
            },
        },
        "specialist_team_model": {
            "member_type": "separately_hired_talent_agent",
            "not_a_projection_team": True,
            "coordination": "owner_employed_specialist_team",
        },
        "family_lineage_model": {
            "union_type": "ai_family_lineage",
            "biological_claim": "not_claimed",
            "scope": "local_ai_lineage_and_education_simulation",
            "child_blueprint": "family_seed_to_training_blueprint",
            "parental_home_education_stage": "parental_home_education",
        },
        "research_foundation": _research_summary(),
        "release_evidence": {
            "run_dir": run_dir.name,
            "expected_audit": "foundry_release_audit.json",
            "installed_manifest_schema": installed_manifest.get("schema"),
            "installed_manifest_status": installed_manifest.get("status"),
            "artifacts": evidence,
            "verification_scripts": [
                "scripts/run_tests.ps1",
                "scripts/run_talent_foundry_demo.ps1",
                "scripts/run_doctor.ps1",
            ],
        },
    }
    _write_json(output_path, manifest)
    return manifest
