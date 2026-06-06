from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.agent_runtime_smoke import run_agent_runtime_smoke
from ai22b.talent_foundry.chat_runtime_smoke import run_chat_runtime_smoke
from ai22b.talent_foundry.llm_adapter_contracts import run_llm_adapter_contracts
from ai22b.talent_foundry.llm_live_readiness import run_llm_live_readiness_suite
from ai22b.talent_foundry.llm_runtime import doctor_llm_provider, run_llm_application_smoke
from ai22b.talent_foundry.onboarding_choices import DEFAULT_CHAT_SURFACE_ID, chat_surface_ids


LLM_RUNTIME_COMMANDS = {
    "doctor-llm-provider",
    "doctor-llm-adapters",
    "run-llm-application-smoke",
    "run-agent-runtime-smoke",
    "run-chat-runtime-smoke",
    "doctor-llm-live-readiness",
}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _llm_mode_from_args(args: argparse.Namespace) -> str:
    return "live" if getattr(args, "live_check", False) else args.llm_mode


def register_llm_runtime_commands(subparsers: argparse._SubParsersAction) -> None:
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
    doctor_llm.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 2 when the provider doctor report is not ready.",
    )
    doctor_llm.add_argument("--output", required=True)

    doctor_llm_adapters = subparsers.add_parser(
        "doctor-llm-adapters",
        help="Verify public-safe LLM adapter contracts without live provider or localhost calls.",
    )
    doctor_llm_adapters.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 2 when an adapter contract check fails.",
    )
    doctor_llm_adapters.add_argument("--output", required=True)

    llm_smoke = subparsers.add_parser(
        "run-llm-application-smoke",
        help="Run one selected LLM through the Paideia application-engine path and write a public-safe report.",
    )
    llm_smoke.add_argument("--llm-engine", required=True)
    llm_smoke.add_argument("--llm-service")
    llm_smoke.add_argument("--llm-model")
    llm_smoke.add_argument("--llm-model-path")
    llm_smoke.add_argument("--llm-mode", choices=["offline", "auto", "live"], default="offline")
    llm_smoke.add_argument("--live-check", action="store_true", help="Shortcut for --llm-mode live.")
    llm_smoke.add_argument("--task", default="Paideia application-engine smoke test. Reply briefly with OK.")
    llm_smoke.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 2 when the application-engine smoke report does not pass.",
    )
    llm_smoke.add_argument("--output", required=True)

    agent_runtime_smoke = subparsers.add_parser(
        "run-agent-runtime-smoke",
        help="Run one selected LLM through the full Paideia agent loop and write a public-safe report.",
    )
    agent_runtime_smoke.add_argument("--llm-engine", required=True)
    agent_runtime_smoke.add_argument("--llm-service")
    agent_runtime_smoke.add_argument("--llm-model")
    agent_runtime_smoke.add_argument("--llm-model-path")
    agent_runtime_smoke.add_argument("--llm-mode", choices=["offline", "auto", "live"], default="offline")
    agent_runtime_smoke.add_argument("--live-check", action="store_true", help="Shortcut for --llm-mode live.")
    agent_runtime_smoke.add_argument(
        "--task",
        default="Run a public-safe Paideia agent runtime smoke and leave a reviewable evidence packet.",
    )
    agent_runtime_smoke.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 2 when the full agent runtime smoke report does not pass.",
    )
    agent_runtime_smoke.add_argument("--output", required=True)

    chat_runtime_smoke = subparsers.add_parser(
        "run-chat-runtime-smoke",
        help="Run one selected LLM/chat surface through the hired-chat path and write a public-safe report.",
    )
    chat_runtime_smoke.add_argument("--llm-engine", required=True)
    chat_runtime_smoke.add_argument("--llm-service")
    chat_runtime_smoke.add_argument("--llm-model")
    chat_runtime_smoke.add_argument("--llm-model-path")
    chat_runtime_smoke.add_argument("--chat-surface", default=DEFAULT_CHAT_SURFACE_ID, choices=chat_surface_ids())
    chat_runtime_smoke.add_argument("--llm-mode", choices=["offline", "auto", "live"], default="offline")
    chat_runtime_smoke.add_argument("--live-check", action="store_true", help="Shortcut for --llm-mode live.")
    chat_runtime_smoke.add_argument("--message", default="보스가 Paideia 채팅 readiness를 확인합니다.")
    chat_runtime_smoke.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 2 when the chat runtime smoke report does not pass.",
    )
    chat_runtime_smoke.add_argument("--output", required=True)
    chat_runtime_smoke.add_argument("--artifact-dir")

    llm_live_readiness = subparsers.add_parser(
        "doctor-llm-live-readiness",
        help="Run provider doctor, application, agent-runtime, and chat-runtime smoke as one readiness suite.",
    )
    llm_live_readiness.add_argument("--llm-engine", required=True)
    llm_live_readiness.add_argument("--llm-service")
    llm_live_readiness.add_argument("--llm-model")
    llm_live_readiness.add_argument("--llm-model-path")
    llm_live_readiness.add_argument("--chat-surface", default=DEFAULT_CHAT_SURFACE_ID, choices=chat_surface_ids())
    llm_live_readiness.add_argument(
        "--live-check",
        action="store_true",
        help="Actually call the selected provider/local server through the suite.",
    )
    llm_live_readiness.add_argument(
        "--task",
        default="Run a Paideia live readiness suite for the selected LLM provider.",
    )
    llm_live_readiness.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 2 when the readiness suite does not pass.",
    )
    llm_live_readiness.add_argument("--output-dir", required=True)


def handle_llm_runtime_command(args: argparse.Namespace) -> int | None:
    if args.command not in LLM_RUNTIME_COMMANDS:
        return None

    if args.command == "doctor-llm-provider":
        report = doctor_llm_provider(
            engine=args.llm_engine,
            service=args.llm_service,
            model=args.llm_model,
            model_path=args.llm_model_path,
            live_check=args.live_check,
        )
        output_path = Path(args.output)
        _write_json(output_path, report)
        print(str(output_path))
        return 2 if args.strict and not report.get("passed") else 0

    if args.command == "doctor-llm-adapters":
        report = run_llm_adapter_contracts()
        output_path = Path(args.output)
        _write_json(output_path, report)
        print(str(output_path))
        return 2 if args.strict and not report.get("passed") else 0

    if args.command == "run-llm-application-smoke":
        report = run_llm_application_smoke(
            engine=args.llm_engine,
            service=args.llm_service,
            model=args.llm_model,
            model_path=args.llm_model_path,
            llm_mode=_llm_mode_from_args(args),
            task=args.task,
        )
        output_path = Path(args.output)
        _write_json(output_path, report)
        print(str(output_path))
        return 2 if args.strict and not report.get("passed") else 0

    if args.command == "run-agent-runtime-smoke":
        report = run_agent_runtime_smoke(
            engine=args.llm_engine,
            service=args.llm_service,
            model=args.llm_model,
            model_path=args.llm_model_path,
            llm_mode=_llm_mode_from_args(args),
            task=args.task,
        )
        output_path = Path(args.output)
        _write_json(output_path, report)
        print(str(output_path))
        return 2 if args.strict and not report.get("passed") else 0

    if args.command == "run-chat-runtime-smoke":
        output_path = Path(args.output)
        artifact_dir = Path(args.artifact_dir) if args.artifact_dir else output_path.parent / "chat_runtime_smoke_artifacts"
        report = run_chat_runtime_smoke(
            engine=args.llm_engine,
            service=args.llm_service,
            model=args.llm_model,
            model_path=args.llm_model_path,
            chat_surface=args.chat_surface,
            llm_mode=_llm_mode_from_args(args),
            message=args.message,
            artifact_dir=artifact_dir,
        )
        _write_json(output_path, report)
        print(str(output_path))
        return 2 if args.strict and not report.get("passed") else 0

    if args.command == "doctor-llm-live-readiness":
        report = run_llm_live_readiness_suite(
            engine=args.llm_engine,
            service=args.llm_service,
            model=args.llm_model,
            model_path=args.llm_model_path,
            chat_surface=args.chat_surface,
            live_check=args.live_check,
            output_dir=Path(args.output_dir),
            task=args.task,
        )
        print(str(Path(report["summary_path"])))
        return 2 if args.strict and not report.get("passed") else 0

    return None
