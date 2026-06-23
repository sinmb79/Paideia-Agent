from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping

from .models import ActionPattern, ActionReceipt, CapabilityContract, SideEffectClass


ACTION_GATEWAY_VALIDATION_SCHEMA = "paideia-edge-action-gateway-validation/v1"
ACTION_GATEWAY_EXECUTION_SCHEMA = "paideia-edge-action-gateway-execution/v1"

EXECUTION_MODES = {
    "simulation",
    "shadow",
    "supervised_field",
    "autonomous_low_risk",
    "safe_degraded",
    "safe_halt",
}
LLM_DIRECT_MARKERS = ("llm", "openai", "anthropic", "chatgpt", "prompt")


@dataclass(frozen=True)
class ActionRequest:
    decision_cycle_id: str
    action_pattern_id: str
    step_id: str
    capability_id: str
    inputs: Mapping[str, Any]
    execution_mode: str = "simulation"
    approval_scope: str | None = None
    approved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_cycle_id": self.decision_cycle_id,
            "action_pattern_id": self.action_pattern_id,
            "step_id": self.step_id,
            "capability_id": self.capability_id,
            "inputs": dict(self.inputs),
            "execution_mode": self.execution_mode,
            "approval_scope": self.approval_scope,
            "approved": self.approved,
        }


@dataclass(frozen=True)
class ActionValidation:
    allowed: bool
    execution_mode: str
    capability_id: str
    status: str
    reasons: tuple[str, ...]
    safe_state: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": ACTION_GATEWAY_VALIDATION_SCHEMA,
            "allowed": self.allowed,
            "execution_mode": self.execution_mode,
            "capability_id": self.capability_id,
            "status": self.status,
            "reasons": list(self.reasons),
            "safe_state": self.safe_state,
        }


class ShadowActionGateway:
    """Deterministic ActionGateway foundation for simulation and shadow execution."""

    def __init__(self, capability_registry: Mapping[str, CapabilityContract | Mapping[str, Any]]) -> None:
        self._registry = {
            capability_id: contract if isinstance(contract, CapabilityContract) else CapabilityContract.from_dict(dict(contract))
            for capability_id, contract in capability_registry.items()
        }

    def validate(self, request: ActionRequest, action_pattern: ActionPattern) -> ActionValidation:
        reasons: list[str] = []
        mode = str(request.execution_mode or "simulation")
        if mode not in EXECUTION_MODES:
            reasons.append("unsupported_execution_mode")
        if request.action_pattern_id != action_pattern.action_pattern_id:
            reasons.append("action_pattern_mismatch")
        step = next((item for item in action_pattern.steps if item.step_id == request.step_id), None)
        if step is None:
            reasons.append("unknown_step")
        elif step.capability_id != request.capability_id:
            reasons.append("step_capability_mismatch")
        contract = self._registry.get(request.capability_id)
        if contract is None:
            reasons.append("capability_not_registered")
        elif contract.capability_id != request.capability_id:
            reasons.append("registry_contract_id_mismatch")
        envelope = action_pattern.autonomy_envelope
        if request.capability_id not in envelope.allowed_capabilities:
            reasons.append("capability_not_allowlisted")
        if request.capability_id in envelope.prohibited_capabilities:
            reasons.append("capability_prohibited")
        if _looks_like_direct_llm_capability(request.capability_id):
            reasons.append("llm_direct_action_forbidden")
        if contract is not None:
            if _looks_like_direct_llm_capability(contract.capability_id) or _looks_like_direct_llm_adapter(contract):
                reasons.append("llm_direct_action_forbidden")
            if contract.side_effect_class == SideEffectClass.PROHIBITED.value:
                reasons.append("prohibited_side_effect")
            if contract.side_effect_class not in envelope.allowed_side_effect_classes:
                reasons.append("side_effect_not_allowed_by_envelope")
            if mode in {"autonomous_low_risk", "safe_degraded"} and contract.side_effect_class not in {
                SideEffectClass.READ_ONLY.value,
                SideEffectClass.REVERSIBLE.value,
            }:
                reasons.append("mode_requires_low_risk_side_effect")
            if contract.side_effect_class in {SideEffectClass.CONSEQUENTIAL.value, SideEffectClass.SAFETY_CRITICAL.value} and not request.approved:
                reasons.append("human_or_certified_approval_required")
            if contract.side_effect_class in {SideEffectClass.CONSEQUENTIAL.value, SideEffectClass.SAFETY_CRITICAL.value}:
                required_scope, scope_authorized = _required_approval_scope(step, envelope.human_approval_scopes)
                if not required_scope:
                    reasons.append("approval_scope_required")
                elif not scope_authorized:
                    reasons.append("approval_scope_not_authorized")
                elif request.approval_scope != required_scope:
                    reasons.append("approval_scope_not_authorized")
            if mode in {"simulation", "shadow"} and contract.runtime_adapter:
                reasons.append("runtime_adapter_ignored_in_shadow_mode")
        if mode == "safe_halt":
            reasons.append("safe_halt_blocks_action")
        blocking = [reason for reason in reasons if reason != "runtime_adapter_ignored_in_shadow_mode"]
        allowed = not blocking
        safe_state = None
        if not allowed:
            safe_state = "safe_halt" if mode == "safe_halt" else "safe_degraded"
        return ActionValidation(
            allowed=allowed,
            execution_mode=mode,
            capability_id=request.capability_id,
            status="allowed" if allowed else "blocked",
            reasons=tuple(reasons),
            safe_state=safe_state,
        )

    def execute(self, request: ActionRequest, action_pattern: ActionPattern) -> dict[str, Any]:
        validation = self.validate(request, action_pattern)
        now = _now()
        input_digest = _digest(dict(request.inputs))
        field_mode = request.execution_mode in {"supervised_field", "autonomous_low_risk"}
        status = _success_status(request.execution_mode) if validation.allowed else "blocked"
        if validation.allowed and field_mode:
            status = "validated_not_executed"
        receipt = ActionReceipt(
            receipt_id=_stable_id("edge-receipt", request.decision_cycle_id, request.step_id, request.capability_id, request.execution_mode, input_digest, status),
            decision_cycle_id=request.decision_cycle_id,
            action_pattern_id=action_pattern.action_pattern_id,
            step_id=request.step_id,
            capability_id=request.capability_id,
            requested_at=now,
            completed_at=now,
            status=status,
            input_digest=input_digest,
            output_ref=None,
            output_digest=_digest({"status": status, "mode": request.execution_mode}),
            observed_side_effects=_observed_side_effects(
                self._registry.get(request.capability_id),
                validation.allowed and not field_mode,
                approval_scope=request.approval_scope,
            ),
            error_code=None if validation.allowed else ";".join(validation.reasons),
            rollback_status="not_required" if validation.allowed else None,
        )
        return {
            "schema": ACTION_GATEWAY_EXECUTION_SCHEMA,
            "validation": validation.to_dict(),
            "action_receipt": receipt.to_dict(),
            "policy": {
                "llm_direct_action_forbidden": True,
                "physical_actuation_enabled": False,
                "shadow_mode_records_without_runtime_adapter": request.execution_mode in {"simulation", "shadow"},
                "field_mode_validates_without_actuation": field_mode,
            },
        }

    def abort(self, request: ActionRequest, action_pattern: ActionPattern, *, reason: str = "aborted") -> dict[str, Any]:
        now = _now()
        receipt = ActionReceipt(
            receipt_id=_stable_id("edge-abort", request.decision_cycle_id, request.step_id, request.capability_id, now),
            decision_cycle_id=request.decision_cycle_id,
            action_pattern_id=action_pattern.action_pattern_id,
            step_id=request.step_id,
            capability_id=request.capability_id,
            requested_at=now,
            completed_at=now,
            status="aborted",
            input_digest=_digest(dict(request.inputs)),
            output_ref=None,
            output_digest=None,
            observed_side_effects=(),
            error_code=reason,
            rollback_status="not_required",
        )
        return {
            "schema": ACTION_GATEWAY_EXECUTION_SCHEMA,
            "validation": ActionValidation(False, request.execution_mode, request.capability_id, "aborted", (reason,), "safe_halt").to_dict(),
            "action_receipt": receipt.to_dict(),
            "policy": {
                "llm_direct_action_forbidden": True,
                "physical_actuation_enabled": False,
                "shadow_mode_records_without_runtime_adapter": True,
            },
        }


def _looks_like_direct_llm_capability(capability_id: str) -> bool:
    normalized = capability_id.casefold()
    return any(marker in normalized for marker in LLM_DIRECT_MARKERS)


def _looks_like_direct_llm_adapter(contract: CapabilityContract) -> bool:
    values = (contract.simulator_adapter, contract.runtime_adapter or "")
    return any(marker in value.casefold() for value in values for marker in LLM_DIRECT_MARKERS)


def _required_approval_scope(step: object, envelope_scopes: tuple[str, ...]) -> tuple[str | None, bool]:
    if step is not None and getattr(step, "approval_scope", None):
        scope = str(getattr(step, "approval_scope"))
        return scope, scope in envelope_scopes
    return (envelope_scopes[0], True) if envelope_scopes else (None, False)


def _success_status(mode: str) -> str:
    if mode == "shadow":
        return "shadow_recorded"
    if mode == "simulation":
        return "simulated"
    if mode == "safe_degraded":
        return "safe_degraded_executed"
    return "succeeded"


def _observed_side_effects(contract: CapabilityContract | None, allowed: bool, *, approval_scope: str | None = None) -> tuple[str, ...]:
    if not allowed or contract is None:
        return ()
    effects = [contract.side_effect_class]
    if approval_scope:
        effects.append(f"approval_scope:{approval_scope}")
    return tuple(effects)


def _digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
