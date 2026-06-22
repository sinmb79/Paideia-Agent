from ai22b.kibo_reuse.token_meter import build_token_saving_report, estimate_token_saving_ratio


def test_token_meter_estimates_saving_ratio():
    ratio = estimate_token_saving_ratio(
        task={"request": "write a report"},
        reused_steps=["market structure analysis", "risk matrix"],
        llm_required_parts=["fresh_external_data"],
    )

    assert 0 < ratio <= 0.95


def test_token_report_includes_actual_ratio_when_usage_is_available():
    report = build_token_saving_report(
        task="task",
        reused_steps=["step"],
        llm_called_parts=["fresh_external_data"],
        actual_prompt_tokens_without_reuse=1000,
        actual_prompt_tokens_with_reuse=650,
    )

    assert report["schema"] == "paideia-kibo-token-saving-report/v1"
    assert report["actual_token_saving_ratio"] == 0.35
