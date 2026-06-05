from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from ai22b.config import talent_foundry_storage_path
from ai22b.talent_foundry.agent_identity_card import (
    build_agent_id_card_payload,
    build_agent_identity_layer_envelope,
    import_agent_identity_registration,
    verify_agent_identity_artifacts,
)
from ai22b.talent_foundry.agent_manifest import build_agent_manifest
from ai22b.talent_foundry.agent_program import (
    build_agent_program,
    build_paideia_agent_install_kit,
    doctor_agent_program,
    run_agent_program_chat,
)
from ai22b.talent_foundry.agent_runner import run_agent_from_manifest
from ai22b.talent_foundry.assessment import evaluate_assessment
from ai22b.talent_foundry.audit import audit_foundry_release
from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
from ai22b.talent_foundry.cohort import create_specialist_cohort
from ai22b.talent_foundry.console import collect_console_answers, run_console_session
from ai22b.talent_foundry.developmental_ecology import build_developmental_ecology
from ai22b.talent_foundry.distribution import (
    create_agent_release_bundle,
    doctor_agent_release_bundle,
    install_agent_release_package,
    package_agent_release_bundle,
)
from ai22b.talent_foundry.dossier import build_hiring_dossier, render_hiring_dossier_markdown
from ai22b.talent_foundry.employment import create_employment_contract
from ai22b.talent_foundry.family import create_child_seed, create_child_training_blueprint, create_family_union
from ai22b.talent_foundry.graduate_package_builder import build_graduate_package
from ai22b.talent_foundry.growth_profile import build_growth_profile
from ai22b.talent_foundry.institutions import default_major_gate_submissions, run_institutional_review
from ai22b.talent_foundry.learning_loop import (
    build_reasoning_kernel,
    create_learning_ledger,
    record_learning_experience,
)
from ai22b.talent_foundry.life_trace import build_life_trace, read_life_trace_jsonl, write_life_trace_jsonl
from ai22b.talent_foundry.llm_runtime import build_llm_runtime_config, doctor_llm_provider
from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
from ai22b.talent_foundry.onboarding import run_agent_onboarding
from ai22b.talent_foundry.onboarding_choices import (
    DEFAULT_CHAT_SURFACE_ID,
    chat_surface_ids,
    llm_service_ids,
)
from ai22b.talent_foundry.owner_self_extension import build_owner_self_extension_intake
from ai22b.talent_foundry.program import create_talent_plan
from ai22b.talent_foundry.program_manifest import build_public_program_manifest
from ai22b.talent_foundry.records import build_career_records
from ai22b.talent_foundry.role_models import list_role_models, summarize_role_model
from ai22b.talent_foundry.same_sky_eval import run_same_sky_eval
from ai22b.talent_foundry.skill_migration import migrate_external_agent_assets
from ai22b.talent_foundry.registry import (
    assign_hired_goal,
    assemble_hired_agent_team,
    assemble_hired_projection_swarm,
    hire_installed_agent,
    maintain_hired_memory_lifecycle,
    record_hired_learning_experience,
    run_hired_dataflow_job,
    run_hired_goal_cycle,
    run_hired_agent,
    run_hired_agent_job,
    run_hired_agent_job_cycle,
    run_hired_projection_swarm_cycle,
    run_hired_team_cycle,
    run_hired_workspace_agent,
)
from ai22b.talent_foundry.runtime import run_work_session
from ai22b.talent_foundry.team import run_clone_team_session
from ai22b.talent_foundry.training_run import materialize_training_blueprint
from ai22b.talent_foundry.workspace_agent import run_workspace_agent_from_manifest


DEFAULT_RUN_DIR = talent_foundry_storage_path("runs")
DEFAULT_OUTPUT = DEFAULT_RUN_DIR / "shinyong_securities_agent_plan.json"
DEFAULT_BLUEPRINT_OUTPUT = DEFAULT_RUN_DIR / "agent_training_blueprint.json"
DEFAULT_WORK_OUTPUT = DEFAULT_RUN_DIR / "shinyong_first_work_session.json"
DEFAULT_WORK_LOG = DEFAULT_RUN_DIR / "shinyong_work_log.jsonl"
DEFAULT_TEAM_OUTPUT = DEFAULT_RUN_DIR / "shinyong_clone_team_session.json"
DEFAULT_TEAM_LOG = DEFAULT_RUN_DIR / "shinyong_clone_team_log.jsonl"
DEFAULT_FAMILY_OUTPUT = DEFAULT_RUN_DIR / "shinyong_family_lineage.json"
DEFAULT_ASSESSMENT_OUTPUT = DEFAULT_RUN_DIR / "shinyong_doctoral_assessment.json"
DEFAULT_INSTITUTIONAL_REVIEW_OUTPUT = (
    DEFAULT_RUN_DIR / "shinyong_institutional_review.json"
)
DEFAULT_LEARNING_LEDGER_OUTPUT = DEFAULT_RUN_DIR / "shinyong_learning_ledger.json"
DEFAULT_COHORT_OUTPUT = DEFAULT_RUN_DIR / "shinyong_specialist_cohort.json"
DEFAULT_BUNDLE_OUTPUT_DIR = DEFAULT_RUN_DIR / "shinyong_agent_release_bundle"
DEFAULT_MANIFEST_OUTPUT = DEFAULT_RUN_DIR / "shinyong_agent_manifest.json"
DEFAULT_AGENT_RUN_OUTPUT = DEFAULT_RUN_DIR / "shinyong_agent_run.json"
DEFAULT_AGENT_RUN_LOG = DEFAULT_RUN_DIR / "shinyong_agent_run_log.jsonl"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a local AI talent hiring packet.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_role_models_command = subparsers.add_parser(
        "list-role-models",
        help="List public role-model process templates for AI talent tracks.",
    )
    list_role_models_command.add_argument("--domain")
    list_role_models_command.add_argument("--output")

    owner_intake = subparsers.add_parser(
        "prepare-owner-self-extension-intake",
        help="Prepare a local-only metadata intake for owner self-extension materials without ingesting file contents.",
    )
    owner_intake.add_argument("--source-dir", required=True)
    owner_intake.add_argument("--owner", default="보스")
    owner_intake.add_argument("--output", required=True)
    owner_intake.add_argument("--repo-root")
    owner_intake.add_argument("--max-files", type=int, default=200)
    owner_intake.add_argument("--owner-consent", action="store_true")
    owner_intake.add_argument(
        "--copyright-attestation",
        default="metadata_only_pending_review",
        choices=[
            "owner_provided_or_authorized_for_local_use",
            "public_or_open_license_metadata_only",
            "metadata_only_pending_review",
        ],
    )

    create = subparsers.add_parser("create", help="Create an AI talent plan and hiring packet.")
    create.add_argument("--name", default="신용")
    create.add_argument("--gender", default="남자")
    create.add_argument("--specialty", default="증권 AI 박사")
    create.add_argument("--role", default="증권 리서치 에이전트")
    create.add_argument("--output", default=str(DEFAULT_OUTPUT))

    blueprint = subparsers.add_parser("blueprint", help="Turn a hiring goal into a growth-to-employment blueprint.")
    blueprint.add_argument("--request", required=True)
    blueprint.add_argument("--name", "--talent-name", dest="name", default="신용")
    blueprint.add_argument("--gender", default="남자")
    blueprint.add_argument("--owner", default="보스")
    blueprint.add_argument("--domain")
    blueprint.add_argument("--role-model", dest="role_model_id")
    blueprint.add_argument("--private-curriculum-dir")
    blueprint.add_argument("--agent-surface", default="cli-console")
    blueprint.add_argument("--output", default=str(DEFAULT_BLUEPRINT_OUTPUT))

    start_console = subparsers.add_parser(
        "start-console",
        help="Start the guided installer console for raising and hiring a new local AI talent.",
    )
    start_console.add_argument("--answers", help="JSON file with console answers for non-interactive runs.")
    start_console.add_argument("--output-dir", default=str(DEFAULT_RUN_DIR / "console_onboarding"))
    start_console.add_argument("--output")

    onboard_wizard = subparsers.add_parser(
        "onboard",
        help="Run the OpenClaw-style Paideia onboarding wizard.",
    )
    onboard_wizard.add_argument("--answers", help="JSON file with console answers for non-interactive runs.")
    onboard_wizard.add_argument("--output-dir", default=str(DEFAULT_RUN_DIR / "console_onboarding"))
    onboard_wizard.add_argument("--output")

    onboard = subparsers.add_parser(
        "onboard-agent",
        help="Run one-shot onboarding from request to hired local agent with first goal cycle.",
    )
    onboard.add_argument("--request", required=True)
    onboard.add_argument("--name", "--talent-name", dest="name", default="신용")
    onboard.add_argument("--gender", default="남자")
    onboard.add_argument("--owner", default="보스")
    onboard.add_argument("--domain")
    onboard.add_argument("--role-model", dest="role_model_id")
    onboard.add_argument("--private-curriculum-dir")
    onboard.add_argument("--agent-surface", default="cli-console")
    onboard.add_argument("--llm-service", choices=llm_service_ids())
    onboard.add_argument("--llm-engine")
    onboard.add_argument("--llm-model")
    onboard.add_argument("--llm-model-path")
    onboard.add_argument("--chat-surface", default=DEFAULT_CHAT_SURFACE_ID, choices=chat_surface_ids())
    onboard.add_argument("--initial-goal")
    onboard.add_argument("--cycle-note")
    onboard.add_argument("--cadence", default="weekly")
    onboard.add_argument("--score", type=int, default=92)
    onboard.add_argument("--reviewed-by")
    onboard.add_argument("--output-dir", default=str(DEFAULT_RUN_DIR / "onboarding"))
    onboard.add_argument("--output")

    raise_command = subparsers.add_parser("raise", help="Materialize a blueprint into employable local agent outputs.")
    raise_command.add_argument("--blueprint", required=True)
    raise_command.add_argument("--output-dir", default=str(DEFAULT_RUN_DIR / "training_run"))

    developmental_ecology = subparsers.add_parser(
        "build-developmental-ecology",
        help="Build a synthetic developmental ecology seed from a training blueprint.",
    )
    developmental_ecology.add_argument("--blueprint", required=True)
    developmental_ecology.add_argument("--output", required=True)

    life_trace = subparsers.add_parser(
        "build-life-trace",
        help="Build a synthetic age-by-age life trace from a blueprint and developmental ecology.",
    )
    life_trace.add_argument("--blueprint", required=True)
    life_trace.add_argument("--ecology", required=True)
    life_trace.add_argument("--density", choices=["monthly", "daily"], default="monthly")
    life_trace.add_argument("--output", required=True)

    growth_profile = subparsers.add_parser(
        "build-growth-profile",
        help="Build relationship, emotion, culture, aesthetic, and asymmetry memory from ecology and life trace.",
    )
    growth_profile.add_argument("--blueprint", required=True)
    growth_profile.add_argument("--ecology", required=True)
    growth_profile.add_argument("--life-trace", required=True)
    growth_profile.add_argument("--output", required=True)

    same_sky_eval = subparsers.add_parser(
        "run-same-sky-eval",
        help="Compare how one shared scene is interpreted by one or more hired Paideia agents.",
    )
    same_sky_eval.add_argument("--agent", action="append", required=True, help="Employment record path. Repeatable.")
    same_sky_eval.add_argument("--scene", required=True)
    same_sky_eval.add_argument("--output", required=True)

    graduate_package = subparsers.add_parser(
        "build-graduate-package",
        help="Build an agent resume, transcript, memory pack, runtime manifest, and onboarding prompt.",
    )
    graduate_package.add_argument("--training-run", required=True)
    graduate_package.add_argument("--output-dir", required=True)

    work = subparsers.add_parser("work", help="Run one local work session for a hired AI talent.")
    work.add_argument("--packet", default=str(DEFAULT_OUTPUT))
    work.add_argument("--task", required=True)
    work.add_argument("--output", default=str(DEFAULT_WORK_OUTPUT))
    work.add_argument("--log", default=str(DEFAULT_WORK_LOG))

    team = subparsers.add_parser("team", help="Run one parent-controlled projection team session.")
    team.add_argument("--packet", default=str(DEFAULT_OUTPUT))
    team.add_argument("--task", required=True)
    team.add_argument("--output", default=str(DEFAULT_TEAM_OUTPUT))
    team.add_argument("--log", default=str(DEFAULT_TEAM_LOG))

    family = subparsers.add_parser("family", help="Create a local AI family lineage and child seed.")
    family.add_argument("--parent-a", required=True)
    family.add_argument("--parent-b", required=True)
    family.add_argument("--family-name", default="신용-하윤 가정")
    family.add_argument("--child-name", default="신미래")
    family.add_argument("--child-gender", default="남자")
    family.add_argument(
        "--child-request",
        default="부모의 추론기풍과 가정교육을 이어받아 로컬 AI 인재로 성장한다.",
    )
    family.add_argument("--output", default=str(DEFAULT_FAMILY_OUTPUT))

    assess = subparsers.add_parser("assess", help="Score one assessment gate for a local AI talent.")
    assess.add_argument("--packet", required=True)
    assess.add_argument("--gate", required=True)
    assess.add_argument("--answer", required=True)
    assess.add_argument("--project", default="AI Talent Foundry 평가")
    assess.add_argument("--evidence", action="append", default=[])
    assess.add_argument("--output", default=str(DEFAULT_ASSESSMENT_OUTPUT))

    review = subparsers.add_parser("review", help="Run the education/home/oversight institutional review.")
    review.add_argument("--packet", required=True)
    review.add_argument("--output", default=str(DEFAULT_INSTITUTIONAL_REVIEW_OUTPUT))

    manifest = subparsers.add_parser("manifest", help="Build a neutral runtime manifest for a hired AI talent.")
    manifest.add_argument("--packet", required=True)
    manifest.add_argument("--memory", required=True)
    manifest.add_argument("--output", default=str(DEFAULT_MANIFEST_OUTPUT))

    dossier = subparsers.add_parser("dossier", help="Build a human-readable hiring dossier for an AI talent.")
    dossier.add_argument("--packet", required=True)
    dossier.add_argument("--manifest", required=True)
    dossier.add_argument("--learning-ledger", required=True)
    dossier.add_argument("--institutional-review")
    dossier.add_argument("--doctoral-assessment")
    dossier.add_argument("--output", required=True)
    dossier.add_argument("--markdown-output", required=True)

    run_agent = subparsers.add_parser("run-agent", help="Run a local AI talent agent from its manifest.")
    run_agent.add_argument("--manifest", required=True)
    run_agent.add_argument("--task", required=True)
    run_agent.add_argument("--output", default=str(DEFAULT_AGENT_RUN_OUTPUT))
    run_agent.add_argument("--log", default=str(DEFAULT_AGENT_RUN_LOG))
    run_agent.add_argument("--llm-engine", default="deterministic_local")
    run_agent.add_argument("--llm-model")
    run_agent.add_argument("--llm-model-path")
    run_agent.add_argument("--llm-mode", choices=["offline", "auto", "live"], default="offline")
    run_agent.add_argument("--live-llm", action="store_true", help="Shortcut for --llm-mode live.")

    doctor_llm = subparsers.add_parser(
        "doctor-llm-provider",
        help="Check one selected LLM provider before using it in a hired Paideia Agent.",
    )
    doctor_llm.add_argument("--llm-engine", required=True)
    doctor_llm.add_argument("--llm-service")
    doctor_llm.add_argument("--llm-model")
    doctor_llm.add_argument("--llm-model-path")
    doctor_llm.add_argument(
        "--live-check",
        action="store_true",
        help="Actually call the selected provider/local server. Without this, no network call is made.",
    )
    doctor_llm.add_argument("--output", required=True)

    run_workspace_agent = subparsers.add_parser(
        "run-workspace-agent",
        help="Run a local OpenHands-style workspace agent from a manifest.",
    )
    run_workspace_agent.add_argument("--manifest", required=True)
    run_workspace_agent.add_argument("--task", required=True)
    run_workspace_agent.add_argument("--workspace", required=True)
    run_workspace_agent.add_argument("--output", required=True)

    learn = subparsers.add_parser("learn", help="Build a verified learning ledger and reasoning kernel.")
    learn.add_argument("--owner", default="신용")
    learn.add_argument("--work", action="append", default=[])
    learn.add_argument("--review", action="append", default=[])
    learn.add_argument("--agent-run", action="append", default=[])
    learn.add_argument("--output", default=str(DEFAULT_LEARNING_LEDGER_OUTPUT))

    cohort = subparsers.add_parser("cohort", help="Create a separately trained specialist agent cohort.")
    cohort.add_argument("--team-name", default="신용 증권 리서치 박사팀")
    cohort.add_argument("--output", default=str(DEFAULT_COHORT_OUTPUT))

    bundle = subparsers.add_parser("bundle", help="Export a public-safe local agent release bundle.")
    bundle.add_argument("--manifest", required=True)
    bundle.add_argument("--learning-ledger", required=True)
    bundle.add_argument("--memory-substrate")
    bundle.add_argument("--language-development-program")
    bundle.add_argument("--developmental-ecology")
    bundle.add_argument("--life-trace")
    bundle.add_argument("--growth-profile")
    bundle.add_argument("--cohort")
    bundle.add_argument("--hiring-dossier")
    bundle.add_argument("--hiring-dossier-markdown")
    bundle.add_argument("--output-dir", default=str(DEFAULT_BUNDLE_OUTPUT_DIR))

    package_bundle = subparsers.add_parser("package-bundle", help="Package a release bundle as ZIP plus SHA256.")
    package_bundle.add_argument("--bundle-dir", required=True)
    package_bundle.add_argument("--output-zip", required=True)

    doctor_bundle = subparsers.add_parser("doctor-bundle", help="Verify a release bundle before installer use.")
    doctor_bundle.add_argument("--bundle-dir", required=True)
    doctor_bundle.add_argument("--output", required=True)

    install_package = subparsers.add_parser("install-package", help="Install a verified release ZIP into a local registry.")
    install_package.add_argument("--archive", required=True)
    install_package.add_argument("--install-root", required=True)
    install_package.add_argument("--expected-sha256")

    agent_id_card = subparsers.add_parser(
        "export-agent-id-card-payload",
        help="Build a local-only Agent ID Card registration payload from an installed/hired agent.",
    )
    agent_id_card.add_argument("--installed-manifest", required=True)
    agent_id_card.add_argument("--employment-record")
    agent_id_card.add_argument("--output", required=True)

    agent_identity_envelope = subparsers.add_parser(
        "export-agent-identity-envelope",
        help="Build an Agent_warrent/Agent Identity Layer v1 envelope without registering or uploading it.",
    )
    agent_identity_envelope.add_argument("--installed-manifest", required=True)
    agent_identity_envelope.add_argument("--employment-record")
    agent_identity_envelope.add_argument("--surface", default="paideia_cli")
    agent_identity_envelope.add_argument("--task-ref")
    agent_identity_envelope.add_argument("--output", required=True)

    verify_agent_id_card = subparsers.add_parser(
        "verify-agent-id-card",
        help="Verify local Agent ID Card payload and Agent_warrent envelope artifacts without registering or uploading them.",
    )
    verify_agent_id_card.add_argument("--payload")
    verify_agent_id_card.add_argument("--envelope")
    verify_agent_id_card.add_argument("--output", required=True)

    import_agent_id_card = subparsers.add_parser(
        "import-agent-id-card-registration",
        help="Import an owner-performed Agent ID Card/Agent_warrent registration result into local identity artifacts.",
    )
    import_agent_id_card.add_argument("--envelope", required=True)
    import_agent_id_card.add_argument("--registration-result", required=True)
    import_agent_id_card.add_argument("--output", required=True)
    import_agent_id_card.add_argument("--updated-envelope")
    import_agent_id_card.add_argument(
        "--include-credential-token",
        action="store_true",
        help="Store the raw returned credential token in the updated envelope. Off by default; prefer hash-only storage.",
    )

    hire_installed = subparsers.add_parser("hire-installed", help="Hire an installed AI talent as a local agent.")
    hire_installed.add_argument("--installed-manifest", required=True)
    hire_installed.add_argument("--employer", default="보스")
    hire_installed.add_argument("--role", required=True)
    hire_installed.add_argument("--llm-service", choices=llm_service_ids())
    hire_installed.add_argument("--llm-engine", default="deterministic_local")
    hire_installed.add_argument("--llm-model")
    hire_installed.add_argument("--llm-model-path")
    hire_installed.add_argument("--chat-surface", choices=chat_surface_ids())

    run_hired_agent_command = subparsers.add_parser(
        "run-hired-agent",
        help="Run a locally hired AI talent agent from its employment record.",
    )
    run_hired_agent_command.add_argument("--employment-record", required=True)
    run_hired_agent_command.add_argument("--task", required=True)
    run_hired_agent_command.add_argument("--output")
    run_hired_agent_command.add_argument(
        "--llm-mode",
        choices=["offline", "auto", "live"],
        default="offline",
        help="offline uses local deterministic/manifest mode; auto tries live then falls back; live requires a configured provider.",
    )
    run_hired_agent_command.add_argument("--live-llm", action="store_true", help="Shortcut for --llm-mode live.")
    run_hired_agent_command.add_argument("--llm-model", help="Override the employment LLM model for this run.")

    chat_hired_agent_command = subparsers.add_parser(
        "chat-hired-agent",
        help="Prepare a Codex chat turn from a hired agent's local memory substrate.",
    )
    chat_hired_agent_command.add_argument("--employment-record", required=True)
    chat_hired_agent_command.add_argument("--message", required=True)
    chat_hired_agent_command.add_argument("--memory-substrate")
    chat_hired_agent_command.add_argument("--reasoning-kibo")
    chat_hired_agent_command.add_argument("--process-emulation-plan")
    chat_hired_agent_command.add_argument("--curriculum-manifest")
    chat_hired_agent_command.add_argument("--language-development-program")
    chat_hired_agent_command.add_argument("--developmental-ecology")
    chat_hired_agent_command.add_argument("--life-trace")
    chat_hired_agent_command.add_argument("--growth-profile")
    chat_hired_agent_command.add_argument(
        "--llm-mode",
        choices=["offline", "auto", "live"],
        default="offline",
        help="offline keeps deterministic local fallback; live calls OpenAI Responses API; auto tries live when available.",
    )
    chat_hired_agent_command.add_argument(
        "--live-llm",
        action="store_true",
        help="Shortcut for --llm-mode live.",
    )
    chat_hired_agent_command.add_argument("--llm-model", help="OpenAI model for --live-llm/--llm-mode live.")
    chat_hired_agent_command.add_argument(
        "--learn-from-chat",
        action="store_true",
        help="Promote a reviewable chat-learning summary into the local learning ledger.",
    )
    chat_hired_agent_command.add_argument("--output")

    run_hired_workspace_agent_command = subparsers.add_parser(
        "run-hired-workspace-agent",
        help="Run a locally hired AI talent workspace agent from its employment record.",
    )
    run_hired_workspace_agent_command.add_argument("--employment-record", required=True)
    run_hired_workspace_agent_command.add_argument("--task", required=True)
    run_hired_workspace_agent_command.add_argument("--workspace", required=True)
    run_hired_workspace_agent_command.add_argument("--output")
    run_hired_workspace_agent_command.add_argument(
        "--llm-mode",
        choices=["offline", "auto", "live"],
        default="offline",
        help="offline uses local manifest mode; auto tries live then falls back; live requires configured provider.",
    )
    run_hired_workspace_agent_command.add_argument("--live-llm", action="store_true", help="Shortcut for --llm-mode live.")
    run_hired_workspace_agent_command.add_argument("--llm-model", help="Override the employment LLM model for this workspace run.")

    run_hired_agent_job_command = subparsers.add_parser(
        "run-hired-agent-job",
        help="Run a hired AI talent against a local job spec with deliverables and acceptance checks.",
    )
    run_hired_agent_job_command.add_argument("--employment-record", required=True)
    run_hired_agent_job_command.add_argument("--job-spec", required=True)
    run_hired_agent_job_command.add_argument("--workspace", required=True)
    run_hired_agent_job_command.add_argument("--output")
    run_hired_agent_job_command.add_argument(
        "--llm-mode",
        choices=["offline", "auto", "live"],
        default="offline",
        help="offline uses local manifest mode; auto tries live then falls back; live requires configured provider.",
    )
    run_hired_agent_job_command.add_argument("--live-llm", action="store_true", help="Shortcut for --llm-mode live.")
    run_hired_agent_job_command.add_argument("--llm-model", help="Override the employment LLM model for this job run.")

    run_hired_dataflow_job_command = subparsers.add_parser(
        "run-hired-dataflow-job",
        help="Run a hired AI talent through the Agent Dataflow Runtime.",
    )
    run_hired_dataflow_job_command.add_argument("--employment-record", required=True)
    run_hired_dataflow_job_command.add_argument("--job-spec", required=True)
    run_hired_dataflow_job_command.add_argument("--workspace", required=True)
    run_hired_dataflow_job_command.add_argument("--score", type=int, required=True)
    run_hired_dataflow_job_command.add_argument("--reviewed-by", default="보스")
    run_hired_dataflow_job_command.add_argument("--status", default="verified")
    run_hired_dataflow_job_command.add_argument("--output")
    run_hired_dataflow_job_command.add_argument(
        "--llm-mode",
        choices=["offline", "auto", "live"],
        default="offline",
        help="offline uses local manifest mode; auto tries live then falls back; live requires configured provider.",
    )
    run_hired_dataflow_job_command.add_argument("--live-llm", action="store_true", help="Shortcut for --llm-mode live.")
    run_hired_dataflow_job_command.add_argument("--llm-model", help="Override the employment LLM model for this dataflow run.")

    run_hired_agent_job_cycle_command = subparsers.add_parser(
        "run-hired-agent-job-cycle",
        help="Run a hired agent job, review it, and promote verified learning in one cycle.",
    )
    run_hired_agent_job_cycle_command.add_argument("--employment-record", required=True)
    run_hired_agent_job_cycle_command.add_argument("--job-spec", required=True)
    run_hired_agent_job_cycle_command.add_argument("--workspace", required=True)
    run_hired_agent_job_cycle_command.add_argument("--score", type=int, required=True)
    run_hired_agent_job_cycle_command.add_argument("--reviewed-by", default="보스")
    run_hired_agent_job_cycle_command.add_argument("--status", default="verified")
    run_hired_agent_job_cycle_command.add_argument("--output")
    run_hired_agent_job_cycle_command.add_argument(
        "--llm-mode",
        choices=["offline", "auto", "live"],
        default="offline",
        help="offline uses local manifest mode; auto tries live then falls back; live requires configured provider.",
    )
    run_hired_agent_job_cycle_command.add_argument("--live-llm", action="store_true", help="Shortcut for --llm-mode live.")
    run_hired_agent_job_cycle_command.add_argument("--llm-model", help="Override the employment LLM model for this job cycle.")

    record_hired_learning = subparsers.add_parser(
        "record-hired-learning",
        help="Review a hired-agent run and update the installed learning ledger.",
    )
    record_hired_learning.add_argument("--employment-record", required=True)
    record_hired_learning.add_argument("--run", required=True)
    record_hired_learning.add_argument("--score", type=int, required=True)
    record_hired_learning.add_argument("--reviewed-by", default="보스")
    record_hired_learning.add_argument("--status", default="verified")
    record_hired_learning.add_argument("--output")

    maintain_hired_memory = subparsers.add_parser(
        "maintain-hired-memory",
        help="Audit, delete, migrate, or recover a hired agent learning ledger with lifecycle logs.",
    )
    maintain_hired_memory.add_argument("--employment-record", required=True)
    maintain_hired_memory.add_argument(
        "--action",
        required=True,
        choices=["audit", "delete-experience", "migrate", "recover"],
    )
    maintain_hired_memory.add_argument("--experience-id")
    maintain_hired_memory.add_argument("--requested-by", default="보스")
    maintain_hired_memory.add_argument("--reason", default="manual_memory_lifecycle_maintenance")
    maintain_hired_memory.add_argument("--output")

    assign_hired_goal_command = subparsers.add_parser(
        "assign-hired-goal",
        help="Assign a long-running objective to a hired local AI talent.",
    )
    assign_hired_goal_command.add_argument("--employment-record", required=True)
    assign_hired_goal_command.add_argument("--goal", required=True)
    assign_hired_goal_command.add_argument("--success-criterion", action="append", default=[])
    assign_hired_goal_command.add_argument("--cadence", default="manual")
    assign_hired_goal_command.add_argument("--output")

    run_hired_goal_cycle_command = subparsers.add_parser(
        "run-hired-goal-cycle",
        help="Run one reviewed workspace cycle for a hired talent's assigned goal.",
    )
    run_hired_goal_cycle_command.add_argument("--employment-record", required=True)
    run_hired_goal_cycle_command.add_argument("--goal", required=True)
    run_hired_goal_cycle_command.add_argument("--cycle-note", required=True)
    run_hired_goal_cycle_command.add_argument("--workspace", required=True)
    run_hired_goal_cycle_command.add_argument("--score", type=int, required=True)
    run_hired_goal_cycle_command.add_argument("--reviewed-by", default="보스")
    run_hired_goal_cycle_command.add_argument("--status", default="verified")
    run_hired_goal_cycle_command.add_argument("--output")

    assemble_hired_team = subparsers.add_parser(
        "assemble-hired-team",
        help="Assemble separately hired AI talents into one local employment team.",
    )
    assemble_hired_team.add_argument("--team-name", required=True)
    assemble_hired_team.add_argument("--domain", required=True)
    assemble_hired_team.add_argument("--employment-record", action="append", required=True)
    assemble_hired_team.add_argument("--output", required=True)

    run_hired_team = subparsers.add_parser(
        "run-hired-team-cycle",
        help="Run one team cycle across separately hired AI talents.",
    )
    run_hired_team.add_argument("--team", required=True)
    run_hired_team.add_argument("--objective", required=True)
    run_hired_team.add_argument("--workspace", required=True)
    run_hired_team.add_argument("--score", type=int, required=True)
    run_hired_team.add_argument("--reviewed-by", default="보스")
    run_hired_team.add_argument("--status", default="verified")
    run_hired_team.add_argument("--output", required=True)

    assemble_projection_swarm = subparsers.add_parser(
        "assemble-hired-projection-swarm",
        help="Assemble one hired AI talent's parent-controlled task projections.",
    )
    assemble_projection_swarm.add_argument("--employment-record", required=True)
    assemble_projection_swarm.add_argument("--swarm-name", required=True)
    assemble_projection_swarm.add_argument("--domain", required=True)
    assemble_projection_swarm.add_argument("--output", required=True)

    run_projection_swarm = subparsers.add_parser(
        "run-hired-projection-swarm-cycle",
        help="Run one cycle for a hired talent's parent-controlled projection swarm.",
    )
    run_projection_swarm.add_argument("--swarm", required=True)
    run_projection_swarm.add_argument("--objective", required=True)
    run_projection_swarm.add_argument("--workspace", required=True)
    run_projection_swarm.add_argument("--score", type=int, required=True)
    run_projection_swarm.add_argument("--reviewed-by", default="보스")
    run_projection_swarm.add_argument("--status", default="verified")
    run_projection_swarm.add_argument("--output", required=True)

    audit_release = subparsers.add_parser(
        "audit-release",
        help="Audit a full Talent Foundry run for local public preview readiness.",
    )
    audit_release.add_argument("--run-dir", required=True)
    audit_release.add_argument("--output", required=True)

    public_program_manifest = subparsers.add_parser(
        "build-public-program-manifest",
        help="Write the installer-facing Talent Foundry public program manifest.",
    )
    public_program_manifest.add_argument("--run-dir", required=True)
    public_program_manifest.add_argument("--output", required=True)

    build_agent_program_command = subparsers.add_parser(
        "build-agent-program",
        help="Build the Paideia Agent program manifest from a hired employment record.",
    )
    build_agent_program_command.add_argument("--employment-record", required=True)
    build_agent_program_command.add_argument("--output")
    build_agent_program_command.add_argument("--name", default="Paideia Agent")
    build_agent_program_command.add_argument("--name-ko", default="Paideia Agent")

    build_paideia_agent_kit_command = subparsers.add_parser(
        "build-paideia-agent-kit",
        help="Build an installable Paideia Agent kit with onboarding, doctor, and adapter manifests.",
    )
    build_paideia_agent_kit_command.add_argument("--employment-record", required=True)
    build_paideia_agent_kit_command.add_argument("--output-dir", required=True)
    build_paideia_agent_kit_command.add_argument("--name", default="Paideia Agent")
    build_paideia_agent_kit_command.add_argument("--name-ko", default="Paideia Agent")

    doctor_agent_program_command = subparsers.add_parser(
        "doctor-agent-program",
        help="Doctor a Paideia Agent program before first run.",
    )
    doctor_agent_program_command.add_argument("--program", required=True)
    doctor_agent_program_command.add_argument("--output")

    migrate_agent_assets_command = subparsers.add_parser(
        "migrate-agent-assets",
        help="Import Hermes/OpenClaw/generic skills into a Paideia Agent kit as quarantined wrappers.",
    )
    migrate_agent_assets_command.add_argument("--source", required=True)
    migrate_agent_assets_command.add_argument("--paideia-kit", required=True)
    migrate_agent_assets_command.add_argument(
        "--source-runtime",
        choices=["hermes", "openclaw", "generic"],
        default="generic",
    )
    migrate_agent_assets_command.add_argument("--output")

    run_agent_program_chat_command = subparsers.add_parser(
        "run-agent-program-chat",
        help="Chat through the Paideia Agent program using local education records and the Reasoning Ledger.",
    )
    run_agent_program_chat_command.add_argument("--program", required=True)
    run_agent_program_chat_command.add_argument("--message", required=True)
    run_agent_program_chat_command.add_argument("--output")
    run_agent_program_chat_command.add_argument(
        "--llm-mode",
        choices=["offline", "auto", "live"],
        default="offline",
    )
    run_agent_program_chat_command.add_argument("--live-llm", action="store_true")
    run_agent_program_chat_command.add_argument("--llm-model")
    run_agent_program_chat_command.add_argument("--learn-from-chat", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "list-role-models":
        result = {
            "schema": "ai-talent-role-model-list/v1",
            "domain": args.domain,
            "role_models": [summarize_role_model(item) for item in list_role_models(args.domain)],
        }
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(str(output_path))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "prepare-owner-self-extension-intake":
        result = build_owner_self_extension_intake(
            source_dir=Path(args.source_dir),
            owner=args.owner,
            output_path=Path(args.output),
            owner_consent=args.owner_consent,
            copyright_attestation=args.copyright_attestation,
            repo_root=Path(args.repo_root) if args.repo_root else Path.cwd(),
            max_files=args.max_files,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 2

    if args.command == "create":
        plan = create_talent_plan(name=args.name, gender=args.gender, specialty=args.specialty)
        records = build_career_records(plan)
        contract = create_employment_contract(plan, role=args.role)
        result = {
            **plan,
            "career_records": records,
            "employment_contract": contract,
            "employment_ready": contract["employment_ready"],
        }
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0

    if args.command == "blueprint":
        result = create_agent_training_blueprint(
            owner=args.owner,
            request=args.request,
            talent_name=args.name,
            gender=args.gender,
            domain=args.domain,
            role_model_id=args.role_model_id,
            private_curriculum_dir=args.private_curriculum_dir,
            agent_surface=args.agent_surface,
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0

    if args.command in {"start-console", "onboard"}:
        output_dir = Path(args.output_dir)
        output_path = Path(args.output) if args.output else output_dir / "console_session.json"
        if args.answers:
            answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
            mode = "answers_file"
        else:
            answers = collect_console_answers()
            mode = "interactive_prompt"
        run_console_session(
            answers=answers,
            output_dir=output_dir,
            output_path=output_path,
            mode=mode,
        )
        print(str(output_path))
        return 0

    if args.command == "onboard-agent":
        output_dir = Path(args.output_dir)
        output_path = Path(args.output) if args.output else output_dir / "onboarding_session.json"
        run_agent_onboarding(
            owner=args.owner,
            request=args.request,
            talent_name=args.name,
            gender=args.gender,
            output_dir=output_dir,
            domain=args.domain,
            role_model_id=args.role_model_id,
            private_curriculum_dir=args.private_curriculum_dir,
            agent_surface=args.agent_surface,
            llm_service=args.llm_service,
            llm_engine=args.llm_engine,
            llm_model=args.llm_model,
            llm_model_path=args.llm_model_path,
            chat_surface=args.chat_surface,
            initial_goal=args.initial_goal,
            cycle_note=args.cycle_note,
            cadence=args.cadence,
            review_score=args.score,
            reviewed_by=args.reviewed_by,
            output_path=output_path,
        )
        print(str(output_path))
        return 0

    if args.command == "raise":
        blueprint_data = json.loads(Path(args.blueprint).read_text(encoding="utf-8"))
        run = materialize_training_blueprint(blueprint_data, output_dir=Path(args.output_dir))
        print(str(run["artifacts"]["training_run"]))
        return 0

    if args.command == "build-developmental-ecology":
        blueprint_data = json.loads(Path(args.blueprint).read_text(encoding="utf-8"))
        output_path = Path(args.output)
        build_developmental_ecology(blueprint_data, output_path=output_path)
        print(str(output_path))
        return 0

    if args.command == "build-life-trace":
        blueprint_data = json.loads(Path(args.blueprint).read_text(encoding="utf-8"))
        ecology = json.loads(Path(args.ecology).read_text(encoding="utf-8"))
        output_path = Path(args.output)
        trace = build_life_trace(blueprint_data, ecology, density=args.density)
        write_life_trace_jsonl(output_path, trace)
        print(str(output_path))
        return 0

    if args.command == "build-growth-profile":
        blueprint_data = json.loads(Path(args.blueprint).read_text(encoding="utf-8"))
        ecology = json.loads(Path(args.ecology).read_text(encoding="utf-8"))
        trace = read_life_trace_jsonl(Path(args.life_trace))
        output_path = Path(args.output)
        build_growth_profile(blueprint_data, ecology, trace, output_path=output_path)
        print(str(output_path))
        return 0

    if args.command == "run-same-sky-eval":
        scene = json.loads(Path(args.scene).read_text(encoding="utf-8"))
        output_path = Path(args.output)
        run_same_sky_eval([Path(path) for path in args.agent], scene, output_path=output_path)
        print(str(output_path))
        return 0

    if args.command == "build-graduate-package":
        result = build_graduate_package(Path(args.training_run), Path(args.output_dir))
        print(str(result["manifest_path"]))
        return 0

    if args.command == "work":
        packet_path = Path(args.packet)
        hiring_packet = json.loads(packet_path.read_text(encoding="utf-8"))
        output_path = Path(args.output)
        log_path = Path(args.log)
        session = run_work_session(hiring_packet, task=args.task, log_path=log_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0

    if args.command == "team":
        packet_path = Path(args.packet)
        hiring_packet = json.loads(packet_path.read_text(encoding="utf-8"))
        output_path = Path(args.output)
        log_path = Path(args.log)
        session = run_clone_team_session(hiring_packet, task=args.task, log_path=log_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0

    if args.command == "family":
        parent_a = json.loads(Path(args.parent_a).read_text(encoding="utf-8"))
        parent_b = json.loads(Path(args.parent_b).read_text(encoding="utf-8"))
        union = create_family_union(parent_a, parent_b, family_name=args.family_name)
        child_seed = create_child_seed(union, child_name=args.child_name, gender=args.child_gender)
        owner = parent_a.get("talent", {}).get("family", {}).get("creator", "보스")
        child_training_blueprint = create_child_training_blueprint(
            union,
            child_seed,
            owner=owner,
            request=args.child_request,
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "family_union": union,
                    "child_seed": child_seed,
                    "child_training_blueprint": child_training_blueprint,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(str(output_path))
        return 0

    if args.command == "assess":
        packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
        result = evaluate_assessment(
            packet,
            gate_id=args.gate,
            submission={
                "answer": args.answer,
                "project": args.project,
                "evidence": args.evidence or ["제출 답안"],
            },
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0

    if args.command == "review":
        packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
        result = run_institutional_review(packet, submissions=default_major_gate_submissions())
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0

    if args.command == "manifest":
        packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
        memory_profile = json.loads(Path(args.memory).read_text(encoding="utf-8"))
        result = build_agent_manifest(packet, memory_profile)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0

    if args.command == "dossier":
        packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        learning_ledger = json.loads(Path(args.learning_ledger).read_text(encoding="utf-8"))
        institutional_review = (
            json.loads(Path(args.institutional_review).read_text(encoding="utf-8"))
            if args.institutional_review
            else None
        )
        doctoral_assessment = (
            json.loads(Path(args.doctoral_assessment).read_text(encoding="utf-8"))
            if args.doctoral_assessment
            else None
        )
        result = build_hiring_dossier(
            hiring_packet=packet,
            agent_manifest=manifest,
            learning_ledger=learning_ledger,
            institutional_review=institutional_review,
            doctoral_assessment=doctoral_assessment,
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        markdown_path = Path(args.markdown_output)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_hiring_dossier_markdown(result), encoding="utf-8")
        print(str(output_path))
        return 0

    if args.command == "run-agent":
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        llm_mode = "live" if args.live_llm else args.llm_mode
        runtime_config = build_llm_runtime_config(
            engine=args.llm_engine,
            model=args.llm_model,
            model_path=args.llm_model_path,
        )
        result = run_agent_from_manifest(
            manifest,
            task=args.task,
            output_log_path=Path(args.log) if args.log else None,
            runtime_config=runtime_config,
            llm_mode=llm_mode,
            llm_model=args.llm_model,
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0

    if args.command == "doctor-llm-provider":
        report = doctor_llm_provider(
            engine=args.llm_engine,
            service=args.llm_service,
            model=args.llm_model,
            model_path=args.llm_model_path,
            live_check=args.live_check,
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0

    if args.command == "run-workspace-agent":
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        result = run_workspace_agent_from_manifest(
            manifest,
            task=args.task,
            workspace_dir=Path(args.workspace),
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0

    if args.command == "learn":
        ledger = create_learning_ledger(owner=args.owner)
        for work_path in args.work:
            event = json.loads(Path(work_path).read_text(encoding="utf-8"))
            ledger = record_learning_experience(
                ledger,
                source="work",
                event=event,
                quality_label={"score": 90, "reviewed_by": "감독위원회", "status": "verified"},
            )
        for review_path in args.review:
            event = json.loads(Path(review_path).read_text(encoding="utf-8"))
            ledger = record_learning_experience(
                ledger,
                source="institutional_review",
                event=event,
                quality_label={"score": 95, "reviewed_by": "감독위원회", "status": "verified"},
            )
        for agent_run_path in args.agent_run:
            event = json.loads(Path(agent_run_path).read_text(encoding="utf-8"))
            ledger = record_learning_experience(
                ledger,
                source="agent_run",
                event=event,
                quality_label={"score": 86, "reviewed_by": "보스", "status": "verified"},
            )
        ledger["reasoning_kernel"] = build_reasoning_kernel(ledger)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0

    if args.command == "cohort":
        cohort = create_specialist_cohort(team_name=args.team_name)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(cohort, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0

    if args.command == "bundle":
        paths = create_agent_release_bundle(
            output_dir=Path(args.output_dir),
            agent_manifest_path=Path(args.manifest),
            learning_ledger_path=Path(args.learning_ledger),
            memory_substrate_path=Path(args.memory_substrate) if args.memory_substrate else None,
            language_development_program_path=(
                Path(args.language_development_program) if args.language_development_program else None
            ),
            developmental_ecology_path=Path(args.developmental_ecology) if args.developmental_ecology else None,
            life_trace_path=Path(args.life_trace) if args.life_trace else None,
            growth_profile_path=Path(args.growth_profile) if args.growth_profile else None,
            specialist_cohort_path=Path(args.cohort) if args.cohort else None,
            hiring_dossier_path=Path(args.hiring_dossier) if args.hiring_dossier else None,
            hiring_dossier_markdown_path=Path(args.hiring_dossier_markdown)
            if args.hiring_dossier_markdown
            else None,
        )
        print(str(paths["bundle_manifest"]))
        return 0

    if args.command == "package-bundle":
        package = package_agent_release_bundle(
            Path(args.bundle_dir),
            output_zip=Path(args.output_zip),
        )
        print(str(package["package_manifest"]))
        return 0

    if args.command == "doctor-bundle":
        doctor_agent_release_bundle(
            Path(args.bundle_dir),
            output_path=Path(args.output),
        )
        print(str(Path(args.output)))
        return 0

    if args.command == "install-package":
        install = install_agent_release_package(
            Path(args.archive),
            install_root=Path(args.install_root),
            expected_sha256=args.expected_sha256,
        )
        print(str(install["installed_manifest"]))
        return 0

    if args.command == "export-agent-id-card-payload":
        payload = build_agent_id_card_payload(
            installed_manifest_path=Path(args.installed_manifest),
            employment_record_path=Path(args.employment_record) if args.employment_record else None,
            output_path=Path(args.output),
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "export-agent-identity-envelope":
        envelope = build_agent_identity_layer_envelope(
            installed_manifest_path=Path(args.installed_manifest),
            employment_record_path=Path(args.employment_record) if args.employment_record else None,
            surface=args.surface,
            task_ref=args.task_ref,
            output_path=Path(args.output),
        )
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
        return 0

    if args.command == "verify-agent-id-card":
        report = verify_agent_identity_artifacts(
            payload_path=Path(args.payload) if args.payload else None,
            envelope_path=Path(args.envelope) if args.envelope else None,
            output_path=Path(args.output),
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["valid"] else 2

    if args.command == "import-agent-id-card-registration":
        report = import_agent_identity_registration(
            envelope_path=Path(args.envelope),
            registration_result_path=Path(args.registration_result),
            output_path=Path(args.output),
            updated_envelope_path=Path(args.updated_envelope) if args.updated_envelope else None,
            include_credential_token=args.include_credential_token,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["valid"] else 2

    if args.command == "hire-installed":
        hiring = hire_installed_agent(
            Path(args.installed_manifest),
            employer=args.employer,
            role=args.role,
            llm_service=args.llm_service,
            llm_engine=args.llm_engine,
            llm_model=args.llm_model,
            llm_model_path=args.llm_model_path,
            chat_surface=args.chat_surface,
        )
        print(str(hiring["employment_record"]))
        return 0

    if args.command == "run-hired-agent":
        llm_mode = "live" if args.live_llm else args.llm_mode
        run = run_hired_agent(
            Path(args.employment_record),
            task=args.task,
            output_path=Path(args.output) if args.output else None,
            llm_mode=llm_mode,
            llm_model=args.llm_model,
        )
        output_path = Path(args.output) if args.output else Path(args.employment_record).parent / "last_hired_agent_run.json"
        print(str(output_path))
        return 0

    if args.command == "chat-hired-agent":
        llm_mode = "live" if args.live_llm else args.llm_mode
        run_chat_turn_from_employment(
            Path(args.employment_record),
            message=args.message,
            output_path=Path(args.output) if args.output else None,
            memory_substrate_path=Path(args.memory_substrate) if args.memory_substrate else None,
            reasoning_kibo_path=Path(args.reasoning_kibo) if args.reasoning_kibo else None,
            process_plan_path=Path(args.process_emulation_plan) if args.process_emulation_plan else None,
            curriculum_manifest_path=Path(args.curriculum_manifest) if args.curriculum_manifest else None,
            language_development_program_path=(
                Path(args.language_development_program) if args.language_development_program else None
            ),
            developmental_ecology_path=Path(args.developmental_ecology) if args.developmental_ecology else None,
            life_trace_path=Path(args.life_trace) if args.life_trace else None,
            growth_profile_path=Path(args.growth_profile) if args.growth_profile else None,
            llm_mode=llm_mode,
            llm_model=args.llm_model,
            learn_from_chat=args.learn_from_chat,
        )
        output_path = (
            Path(args.output)
            if args.output
            else Path(args.employment_record).parent / "last_hired_agent_chat.json"
        )
        print(str(output_path))
        return 0

    if args.command == "run-hired-workspace-agent":
        llm_mode = "live" if args.live_llm else args.llm_mode
        run_hired_workspace_agent(
            Path(args.employment_record),
            task=args.task,
            workspace_dir=Path(args.workspace),
            output_path=Path(args.output) if args.output else None,
            llm_mode=llm_mode,
            llm_model=args.llm_model,
        )
        output_path = (
            Path(args.output)
            if args.output
            else Path(args.employment_record).parent / "last_hired_workspace_agent_run.json"
        )
        print(str(output_path))
        return 0

    if args.command == "run-hired-agent-job":
        llm_mode = "live" if args.live_llm else args.llm_mode
        job_spec = json.loads(Path(args.job_spec).read_text(encoding="utf-8"))
        run_hired_agent_job(
            Path(args.employment_record),
            job_spec=job_spec,
            workspace_dir=Path(args.workspace),
            output_path=Path(args.output) if args.output else None,
            llm_mode=llm_mode,
            llm_model=args.llm_model,
        )
        output_path = (
            Path(args.output)
            if args.output
            else Path(args.employment_record).parent / "last_hired_agent_job_run.json"
        )
        print(str(output_path))
        return 0

    if args.command == "run-hired-dataflow-job":
        llm_mode = "live" if args.live_llm else args.llm_mode
        job_spec = json.loads(Path(args.job_spec).read_text(encoding="utf-8"))
        run_hired_dataflow_job(
            Path(args.employment_record),
            job_spec=job_spec,
            workspace_dir=Path(args.workspace),
            review_label={
                "score": args.score,
                "reviewed_by": args.reviewed_by,
                "status": args.status,
            },
            output_path=Path(args.output) if args.output else None,
            llm_mode=llm_mode,
            llm_model=args.llm_model,
        )
        output_path = (
            Path(args.output)
            if args.output
            else Path(args.employment_record).parent / "last_hired_dataflow_run.json"
        )
        print(str(output_path))
        return 0

    if args.command == "run-hired-agent-job-cycle":
        llm_mode = "live" if args.live_llm else args.llm_mode
        job_spec = json.loads(Path(args.job_spec).read_text(encoding="utf-8"))
        run_hired_agent_job_cycle(
            Path(args.employment_record),
            job_spec=job_spec,
            workspace_dir=Path(args.workspace),
            quality_label={
                "score": args.score,
                "reviewed_by": args.reviewed_by,
                "status": args.status,
            },
            output_path=Path(args.output) if args.output else None,
            llm_mode=llm_mode,
            llm_model=args.llm_model,
        )
        output_path = (
            Path(args.output)
            if args.output
            else Path(args.employment_record).parent / "last_hired_agent_job_cycle.json"
        )
        print(str(output_path))
        return 0

    if args.command == "record-hired-learning":
        record_hired_learning_experience(
            Path(args.employment_record),
            run_path=Path(args.run),
            quality_label={
                "score": args.score,
                "reviewed_by": args.reviewed_by,
                "status": args.status,
            },
            output_path=Path(args.output) if args.output else None,
        )
        output_path = (
            Path(args.output)
            if args.output
            else Path(args.employment_record).parent / "post_hire_learning_update.json"
        )
        print(str(output_path))
        return 0

    if args.command == "maintain-hired-memory":
        maintain_hired_memory_lifecycle(
            Path(args.employment_record),
            action=args.action,
            experience_id=args.experience_id,
            requested_by=args.requested_by,
            reason=args.reason,
            output_path=Path(args.output) if args.output else None,
        )
        output_path = (
            Path(args.output)
            if args.output
            else Path(args.employment_record).parent / "memory_lifecycle_maintenance.json"
        )
        print(str(output_path))
        return 0

    if args.command == "assign-hired-goal":
        assign_hired_goal(
            Path(args.employment_record),
            goal=args.goal,
            success_criteria=args.success_criterion or None,
            cadence=args.cadence,
            output_path=Path(args.output) if args.output else None,
        )
        output_path = (
            Path(args.output)
            if args.output
            else Path(args.employment_record).parent / "employment_goal.json"
        )
        print(str(output_path))
        return 0

    if args.command == "run-hired-goal-cycle":
        run_hired_goal_cycle(
            Path(args.employment_record),
            goal_path=Path(args.goal),
            cycle_note=args.cycle_note,
            workspace_dir=Path(args.workspace),
            quality_label={
                "score": args.score,
                "reviewed_by": args.reviewed_by,
                "status": args.status,
            },
            output_path=Path(args.output) if args.output else None,
        )
        output_path = (
            Path(args.output)
            if args.output
            else Path(args.employment_record).parent / "last_employment_goal_cycle.json"
        )
        print(str(output_path))
        return 0

    if args.command == "assemble-hired-team":
        assemble_hired_agent_team(
            [Path(path) for path in args.employment_record],
            team_name=args.team_name,
            domain=args.domain,
            output_path=Path(args.output),
        )
        print(str(Path(args.output)))
        return 0

    if args.command == "run-hired-team-cycle":
        run_hired_team_cycle(
            Path(args.team),
            objective=args.objective,
            workspace_dir=Path(args.workspace),
            quality_label={
                "score": args.score,
                "reviewed_by": args.reviewed_by,
                "status": args.status,
            },
            output_path=Path(args.output),
        )
        print(str(Path(args.output)))
        return 0

    if args.command == "assemble-hired-projection-swarm":
        assemble_hired_projection_swarm(
            Path(args.employment_record),
            swarm_name=args.swarm_name,
            domain=args.domain,
            output_path=Path(args.output),
        )
        print(str(Path(args.output)))
        return 0

    if args.command == "run-hired-projection-swarm-cycle":
        run_hired_projection_swarm_cycle(
            Path(args.swarm),
            objective=args.objective,
            workspace_dir=Path(args.workspace),
            quality_label={
                "score": args.score,
                "reviewed_by": args.reviewed_by,
                "status": args.status,
            },
            output_path=Path(args.output),
        )
        print(str(Path(args.output)))
        return 0

    if args.command == "audit-release":
        audit_foundry_release(
            Path(args.run_dir),
            output_path=Path(args.output),
        )
        print(str(Path(args.output)))
        return 0

    if args.command == "build-public-program-manifest":
        build_public_program_manifest(
            Path(args.run_dir),
            output_path=Path(args.output),
        )
        print(str(Path(args.output)))
        return 0

    if args.command == "build-agent-program":
        program = build_agent_program(
            Path(args.employment_record),
            output_path=Path(args.output) if args.output else None,
            program_name=args.name,
            program_name_ko=args.name_ko,
        )
        output_path = Path(args.output) if args.output else Path(args.employment_record).parent / "22b_paideia_agent_program.json"
        print(str(output_path))
        return 0

    if args.command == "build-paideia-agent-kit":
        build_paideia_agent_install_kit(
            Path(args.employment_record),
            output_dir=Path(args.output_dir),
            program_name=args.name,
            program_name_ko=args.name_ko,
        )
        print(str(Path(args.output_dir) / "paideia_agent_install_manifest.json"))
        return 0

    if args.command == "doctor-agent-program":
        output_path = Path(args.output) if args.output else Path(args.program).parent / "paideia_doctor_report.json"
        doctor_agent_program(
            Path(args.program),
            output_path=output_path,
        )
        print(str(output_path))
        return 0

    if args.command == "migrate-agent-assets":
        output_path = Path(args.output) if args.output else Path(args.paideia_kit) / "paideia_skill_migration_report.json"
        migrate_external_agent_assets(
            Path(args.source),
            paideia_kit_dir=Path(args.paideia_kit),
            source_runtime=args.source_runtime,
            output_path=output_path,
        )
        print(str(output_path))
        return 0

    if args.command == "run-agent-program-chat":
        llm_mode = "live" if args.live_llm else args.llm_mode
        run_agent_program_chat(
            Path(args.program),
            message=args.message,
            output_path=Path(args.output) if args.output else None,
            llm_mode=llm_mode,
            llm_model=args.llm_model,
            learn_from_chat=args.learn_from_chat,
        )
        output_path = Path(args.output) if args.output else Path(args.program).parent / "last_paideia_agent_chat.json"
        print(str(output_path))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
