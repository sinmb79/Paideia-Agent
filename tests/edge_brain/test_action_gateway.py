from ai22b.edge_brain import ActionRequest, CapabilityContract, ShadowActionGateway, SideEffectClass

from tests.edge_brain.test_models_contracts import _action_pattern


def _contract(capability_id="cap.inspect_zone", *, side_effect=SideEffectClass.READ_ONLY.value, runtime_adapter=None):
    return CapabilityContract(
        capability_id=capability_id,
        version="v1",
        input_schema_ref="inspect-input/v1",
        output_schema_ref="inspect-output/v1",
        side_effect_class=side_effect,
        required_permissions=("sensor.read",),
        idempotent=True,
        reversible=True,
        timeout_ms=500,
        simulator_adapter="deterministic.inspect",
        runtime_adapter=runtime_adapter,
        safe_fallback_capability_id=None,
    )


def _request(**overrides):
    data = {
        "decision_cycle_id": "cycle-1",
        "action_pattern_id": "ap-1",
        "step_id": "inspect",
        "capability_id": "cap.inspect_zone",
        "inputs": {"zone_id": "A1"},
        "execution_mode": "shadow",
    }
    data.update(overrides)
    return ActionRequest(**data)


def test_shadow_action_gateway_records_allowed_shadow_receipt_without_runtime_actuation():
    gateway = ShadowActionGateway({"cap.inspect_zone": _contract(runtime_adapter="real.inspect")})

    result = gateway.execute(_request(), _action_pattern())

    assert result["schema"] == "paideia-edge-action-gateway-execution/v1"
    assert result["validation"]["allowed"] is True
    assert "runtime_adapter_ignored_in_shadow_mode" in result["validation"]["reasons"]
    assert result["action_receipt"]["status"] == "shadow_recorded"
    assert result["policy"]["physical_actuation_enabled"] is False


def test_action_gateway_blocks_unregistered_or_unallowlisted_capability():
    gateway = ShadowActionGateway({})

    result = gateway.execute(_request(capability_id="cap.unknown"), _action_pattern())

    assert result["validation"]["allowed"] is False
    assert "capability_not_registered" in result["validation"]["reasons"]
    assert "capability_not_allowlisted" in result["validation"]["reasons"]
    assert result["action_receipt"]["status"] == "blocked"


def test_action_gateway_blocks_direct_llm_as_actuator_path():
    gateway = ShadowActionGateway({"openai.llm.tool": _contract("openai.llm.tool")})
    pattern = _action_pattern()

    result = gateway.execute(_request(capability_id="openai.llm.tool"), pattern)

    assert result["validation"]["allowed"] is False
    assert "llm_direct_action_forbidden" in result["validation"]["reasons"]


def test_action_gateway_blocks_disguised_llm_contract_or_adapter_path():
    disguised_contract = _contract("openai.llm.tool", runtime_adapter="openai.responses.create")
    gateway = ShadowActionGateway({"cap.inspect_zone": disguised_contract})

    result = gateway.execute(_request(), _action_pattern())

    assert result["validation"]["allowed"] is False
    assert "registry_contract_id_mismatch" in result["validation"]["reasons"]
    assert "llm_direct_action_forbidden" in result["validation"]["reasons"]


def test_action_gateway_requires_approval_for_consequential_capability():
    contract = _contract(side_effect=SideEffectClass.CONSEQUENTIAL.value)
    pattern = _action_pattern()
    pattern = pattern.__class__.from_dict(
        {
            **pattern.to_dict(),
            "autonomy_envelope": {
                **pattern.autonomy_envelope.to_dict(),
                "allowed_side_effect_classes": [SideEffectClass.CONSEQUENTIAL.value],
            },
        }
    )
    gateway = ShadowActionGateway({"cap.inspect_zone": contract})

    blocked = gateway.execute(_request(execution_mode="supervised_field"), pattern)
    boolean_only = gateway.execute(_request(execution_mode="supervised_field", approved=True), pattern)
    allowed = gateway.execute(_request(execution_mode="supervised_field", approved=True, approval_scope="consequential"), pattern)

    assert "human_or_certified_approval_required" in blocked["validation"]["reasons"]
    assert blocked["validation"]["allowed"] is False
    assert "approval_scope_not_authorized" in boolean_only["validation"]["reasons"]
    assert boolean_only["validation"]["allowed"] is False
    assert allowed["validation"]["allowed"] is True
    assert allowed["action_receipt"]["status"] == "validated_not_executed"
    assert allowed["action_receipt"]["observed_side_effects"] == []


def test_action_gateway_rejects_step_approval_scope_not_authorized_by_envelope():
    contract = _contract(side_effect=SideEffectClass.CONSEQUENTIAL.value)
    pattern = _action_pattern()
    payload = pattern.to_dict()
    payload["steps"][0]["approval_scope"] = "unauthorized_scope"
    payload["autonomy_envelope"]["allowed_side_effect_classes"] = [SideEffectClass.CONSEQUENTIAL.value]
    payload["autonomy_envelope"]["human_approval_scopes"] = []
    pattern = pattern.__class__.from_dict(payload)
    gateway = ShadowActionGateway({"cap.inspect_zone": contract})

    result = gateway.execute(
        _request(execution_mode="supervised_field", approved=True, approval_scope="unauthorized_scope"),
        pattern,
    )

    assert result["validation"]["allowed"] is False
    assert "approval_scope_not_authorized" in result["validation"]["reasons"]


def test_action_gateway_field_modes_validate_but_do_not_claim_execution_success():
    gateway = ShadowActionGateway({"cap.inspect_zone": _contract(runtime_adapter="real.inspect")})

    result = gateway.execute(_request(execution_mode="autonomous_low_risk", approved=True), _action_pattern())

    assert result["validation"]["allowed"] is True
    assert result["action_receipt"]["status"] == "validated_not_executed"
    assert result["action_receipt"]["observed_side_effects"] == []
    assert result["policy"]["field_mode_validates_without_actuation"] is True


def test_action_gateway_safe_halt_blocks_action_and_abort_writes_receipt():
    gateway = ShadowActionGateway({"cap.inspect_zone": _contract()})

    blocked = gateway.execute(_request(execution_mode="safe_halt"), _action_pattern())
    aborted = gateway.abort(_request(), _action_pattern(), reason="operator_stop")

    assert blocked["validation"]["safe_state"] == "safe_halt"
    assert "safe_halt_blocks_action" in blocked["validation"]["reasons"]
    assert aborted["action_receipt"]["status"] == "aborted"
    assert aborted["action_receipt"]["error_code"] == "operator_stop"
