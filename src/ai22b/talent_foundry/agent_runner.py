from __future__ import annotations

from pathlib import Path
from typing import Any

from ai22b.talent_foundry.agent_execution_loop import run_agent_execution_loop, write_agent_run_log
from ai22b.talent_foundry.llm_clients import LLMClient


RUN_SCHEMA = "ai-talent-agent-run/v1"


def run_agent_from_manifest(
    manifest: dict[str, Any],
    *,
    task: str,
    output_log_path: Path | None = None,
    runtime_config: dict[str, Any] | None = None,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    llm_client: LLMClient | None = None,
    tool_artifact_dir: Path | None = None,
) -> dict[str, Any]:
    """Run a Paideia agent through the P0 execution loop.

    The public return shape stays compatible with the original prototype runner
    while adding action intents, capability policy, LLM planning, tool execution,
    verification, memory write decisions, and audit events.
    """

    result = run_agent_execution_loop(
        manifest,
        task=task,
        runtime_config=runtime_config,
        llm_mode=llm_mode,
        llm_model=llm_model,
        llm_client=llm_client,
        tool_artifact_dir=tool_artifact_dir,
    )
    if output_log_path is not None:
        write_agent_run_log(output_log_path, result)
    return result
