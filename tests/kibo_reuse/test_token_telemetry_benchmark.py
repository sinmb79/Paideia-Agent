from ai22b.kibo_reuse.benchmark_runner import build_pattern_loop_benchmark_report
from ai22b.kibo_reuse.token_telemetry import build_token_usage_receipt, summarize_token_usage


def _manifest():
    return {
        "schema": "paideia-cross-repo-compatibility/v1",
        "contracts_release": "2.0.0",
        "paideia_agent": ">=0.x,<1.0",
        "paideia_engines": ">=0.x,<1.0",
        "genius_derivation": ">=0.x,<1.0",
        "contract_hashes": {"token_usage_receipt": "t" * 64},
    }


def test_token_usage_receipt_uses_actual_provider_usage_when_available():
    receipt = build_token_usage_receipt(
        _manifest(),
        run_id="run-a2-1",
        provider="openai",
        model="gpt-test",
        call_purpose="baseline_answer",
        usage={"input_tokens": 1000, "output_tokens": 200, "cached_input_tokens": 100, "monetary_cost": 0.12},
        created_at="2026-06-23T00:00:00Z",
    )

    assert receipt["schema"] == "paideia-kibo-v2-token-usage-receipt/v2"
    assert receipt["estimated"] is False
    assert receipt["input_tokens"] == 1000
    assert receipt["output_tokens"] == 200
    assert receipt["monetary_cost"] == 0.12


def test_token_usage_receipt_flags_local_estimates_when_usage_missing():
    receipt = build_token_usage_receipt(
        _manifest(),
        run_id="run-a5-1",
        provider="local",
        model="offline",
        call_purpose="pattern_validation",
        prompt="short prompt",
        completion="short answer",
        created_at="2026-06-23T00:00:00Z",
    )

    assert receipt["estimated"] is True
    assert receipt["estimation_method"] == "paideia_local_token_estimate"
    assert receipt["input_tokens"] > 0
    assert receipt["output_tokens"] > 0


def test_benchmark_report_uses_actual_receipts_for_token_saving_and_success_lift():
    manifest = _manifest()
    receipts = [
        build_token_usage_receipt(
            manifest,
            run_id="baseline-1",
            provider="openai",
            model="gpt-test",
            call_purpose="baseline_answer",
            usage={"input_tokens": 1000, "output_tokens": 200},
            created_at="2026-06-23T00:00:00Z",
        ),
        build_token_usage_receipt(
            manifest,
            run_id="full-1",
            provider="openai",
            model="gpt-test",
            call_purpose="full_loop_answer",
            usage={"input_tokens": 500, "output_tokens": 100},
            created_at="2026-06-23T00:00:01Z",
        ),
    ]
    report = build_pattern_loop_benchmark_report(
        {
            "benchmark_id": "learning-validity-smoke",
            "groups": ["A2", "A5"],
            "baseline_group": "A2",
            "full_loop_group": "A5",
            "min_success_lift": 0.10,
            "min_token_saving": 0.25,
        },
        [
            {"run_id": "baseline-1", "group": "A2", "success": False, "failure_recurrence_count": 2},
            {"run_id": "full-1", "group": "A5", "success": True, "failure_recurrence_count": 0},
        ],
        token_receipts=receipts,
    )

    assert summarize_token_usage(receipts)["actual_receipt_count"] == 2
    assert report["schema"] == "paideia-pattern-loop-benchmark-report/v1"
    assert report["status"] == "passed"
    assert report["benchmark_comparison"]["success_rate_delta"] == 1.0
    assert report["benchmark_comparison"]["net_token_saving_ratio"] == 0.5


def test_benchmark_report_requires_both_success_lift_and_actual_token_saving():
    manifest = _manifest()
    estimated_receipts = [
        build_token_usage_receipt(
            manifest,
            run_id="baseline-1",
            provider="local",
            model="offline",
            call_purpose="baseline_answer",
            prompt="x " * 1000,
            completion="x " * 200,
            created_at="2026-06-23T00:00:00Z",
        ),
        build_token_usage_receipt(
            manifest,
            run_id="full-1",
            provider="local",
            model="offline",
            call_purpose="full_loop_answer",
            prompt="x " * 100,
            completion="x " * 20,
            created_at="2026-06-23T00:00:01Z",
        ),
    ]
    report = build_pattern_loop_benchmark_report(
        {"groups": ["A2", "A5"], "baseline_group": "A2", "full_loop_group": "A5"},
        [
            {"run_id": "baseline-1", "group": "A2", "success": False},
            {"run_id": "full-1", "group": "A5", "success": True},
        ],
        token_receipts=estimated_receipts,
    )

    assert report["checks"]["actual_token_receipt_comparison"] is False
    assert report["checks"]["token_saving_passed"] is False
    assert report["status"] == "blocked"


def test_benchmark_report_blocks_when_only_one_threshold_passes():
    manifest = _manifest()
    receipts = [
        build_token_usage_receipt(
            manifest,
            run_id="baseline-1",
            provider="openai",
            model="gpt-test",
            call_purpose="baseline_answer",
            usage={"input_tokens": 1000, "output_tokens": 200},
            created_at="2026-06-23T00:00:00Z",
        ),
        build_token_usage_receipt(
            manifest,
            run_id="full-1",
            provider="openai",
            model="gpt-test",
            call_purpose="full_loop_answer",
            usage={"input_tokens": 500, "output_tokens": 100},
            created_at="2026-06-23T00:00:01Z",
        ),
    ]
    report = build_pattern_loop_benchmark_report(
        {"groups": ["A2", "A5"], "baseline_group": "A2", "full_loop_group": "A5", "min_success_lift": 0.10},
        [
            {"run_id": "baseline-1", "group": "A2", "success": True},
            {"run_id": "full-1", "group": "A5", "success": True},
        ],
        token_receipts=receipts,
    )

    assert report["checks"]["token_saving_passed"] is True
    assert report["checks"]["success_lift_passed"] is False
    assert report["status"] == "blocked"
