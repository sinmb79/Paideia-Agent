from __future__ import annotations

import json
import re
from typing import Any


TOKEN_SAVING_REPORT_SCHEMA = "paideia-kibo-token-saving-report/v1"


def estimate_tokens(value: Any) -> int:
    if isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    elif isinstance(value, (list, tuple, set)):
        text = " ".join(str(item) for item in value)
    else:
        text = str(value or "")
    word_count = len(re.findall(r"[0-9A-Za-z가-힣_]+", text))
    char_count = len(text)
    return max(1, int(max(word_count * 1.3, char_count / 5)))


def estimate_token_saving_ratio(
    *,
    task: Any,
    reused_steps: list[str],
    llm_required_parts: list[str],
) -> float:
    task_tokens = estimate_tokens(task)
    reused_tokens = estimate_tokens(reused_steps)
    required_tokens = estimate_tokens(llm_required_parts)
    no_reuse_estimate = task_tokens + reused_tokens + required_tokens
    if no_reuse_estimate <= 0:
        return 0.0
    reusable = reused_tokens if reused_steps else 0
    penalty = max(0, required_tokens - task_tokens // 4)
    ratio = (reusable - penalty) / no_reuse_estimate
    return round(max(0.0, min(0.95, ratio)), 4)


def build_token_saving_report(
    *,
    task: Any,
    reused_steps: list[str],
    llm_called_parts: list[str],
    actual_prompt_tokens_without_reuse: int | None = None,
    actual_prompt_tokens_with_reuse: int | None = None,
) -> dict:
    estimated = estimate_token_saving_ratio(
        task=task,
        reused_steps=reused_steps,
        llm_required_parts=llm_called_parts,
    )
    actual = None
    if actual_prompt_tokens_without_reuse and actual_prompt_tokens_without_reuse > 0:
        with_reuse = actual_prompt_tokens_with_reuse or 0
        actual = round(
            max(0.0, min(0.95, (actual_prompt_tokens_without_reuse - with_reuse) / actual_prompt_tokens_without_reuse)),
            4,
        )
    return {
        "schema": TOKEN_SAVING_REPORT_SCHEMA,
        "estimated_token_saving_ratio": estimated,
        "actual_token_saving_ratio": actual,
        "reused_steps": list(reused_steps),
        "llm_called_parts": list(llm_called_parts),
        "token_estimates": {
            "task": estimate_tokens(task),
            "reused_steps": estimate_tokens(reused_steps),
            "llm_called_parts": estimate_tokens(llm_called_parts),
        },
    }
