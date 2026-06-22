from ai22b.kibo_reuse.fingerprint import build_task_fingerprint


def test_investment_request_builds_high_risk_fresh_fingerprint():
    fingerprint = build_task_fingerprint(
        "Assess buy opportunity using current market price, technical chart analysis, and theme sensitivity.",
        owner="Boss",
    )

    assert fingerprint.domain == "investment_research"
    assert fingerprint.task_type == "comparative_analysis"
    assert fingerprint.intent == "assess_buy_opportunity"
    assert fingerprint.risk_level == "high"
    assert fingerprint.freshness_required is True
    assert "web_research" in fingerprint.required_capabilities
    assert "valuation" in fingerprint.required_capabilities
