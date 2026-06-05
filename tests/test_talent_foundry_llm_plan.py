from __future__ import annotations

import json
import unittest


def _manifest() -> dict:
    return {
        "schema": "ai-talent-agent-manifest/v1",
        "agent": {
            "name": "planner-test-agent",
            "role": "local research agent",
            "major_goal": "Verify reviewable LLM planning.",
        },
        "memory_profile": {
            "procedural_principles": ["Define the task before tool execution.", "Keep evidence reviewable."],
            "semantic_themes": ["planning", "tool boundary"],
            "chain_of_thought_policy": "do_not_store_private_trace",
        },
        "llm_policy": {
            "role": "application_engine_not_identity",
            "private_reasoning_trace": "do_not_store",
        },
        "tool_policy": {
            "allowed_tools": ["work_session", "evidence_packet", "assessment"],
            "blocked_tools": [],
        },
    }


class FakePlanningClient:
    def generate(self, messages, *, tools=None, policy=None):
        return {
            "schema": "paideia-llm-client-result/v1",
            "engine": "fake_planning_llm",
            "status": "completed",
            "model": "fake-planner",
            "text": json.dumps(
                {
                    "assistant_reply": "보스 검토용 리서치 계획을 구조화했습니다.",
                    "reviewable_reasoning_summary": [
                        {"step": "define", "summary": "요청을 리서치 작업으로 한정했습니다."},
                        {"step": "evidence", "summary": "근거 패킷을 남겨 검토 가능하게 합니다."},
                    ],
                    "suggested_next_actions": ["근거 패킷 확인", "보스 검토 후 학습 후보로 남기기"],
                    "tool_plan": [
                        {"tool": "evidence_packet", "purpose": "근거와 정책 경계를 기록합니다."},
                    ],
                    "chain_of_thought": "private hidden trace must not be stored",
                },
                ensure_ascii=False,
            ),
        }


class TalentFoundryLlmPlanTests(unittest.TestCase):
    def test_agent_run_stores_reviewable_llm_plan_not_private_trace(self) -> None:
        from ai22b.talent_foundry.agent_runner import run_agent_from_manifest
        from ai22b.talent_foundry.llm_runtime import build_llm_runtime_config

        result = run_agent_from_manifest(
            _manifest(),
            task="거시경제 리서치 계획을 세워줘.",
            runtime_config=build_llm_runtime_config(engine="openrouter_api", model="fake-planner"),
            llm_mode="live",
            llm_client=FakePlanningClient(),
        )

        llm_plan = result["llm_runtime_result"]["llm_plan"]
        evidence_packet = next(
            item["output"]
            for item in result["tool_execution"]["tool_results"]
            if item["tool"] == "evidence_packet"
        )
        work_session = next(
            item["output"]
            for item in result["tool_execution"]["tool_results"]
            if item["tool"] == "work_session"
        )
        serialized = json.dumps(result, ensure_ascii=False)

        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(result["verification"]["status"], "passed")
        self.assertEqual(result["execution_contract"]["llm_runtime"]["reviewable_plan_schema"], "paideia-llm-reviewable-plan/v1")
        self.assertEqual(llm_plan["schema"], "paideia-llm-reviewable-plan/v1")
        self.assertEqual(llm_plan["source"], "json_object")
        self.assertEqual(llm_plan["assistant_reply"], "보스 검토용 리서치 계획을 구조화했습니다.")
        self.assertEqual(llm_plan["tool_plan"][0]["tool"], "evidence_packet")
        self.assertEqual(llm_plan["tool_plan"][0]["registration_status"], "registered")
        self.assertEqual(work_session["llm_plan_schema"], "paideia-llm-reviewable-plan/v1")
        self.assertIn("llm_reviewable_plan", {item["id"] for item in evidence_packet["evidence_items"]})
        self.assertEqual(evidence_packet["llm_plan_policy"], "suggestions_only_registered_executor_decides")
        self.assertNotIn("private hidden trace", serialized)


if __name__ == "__main__":
    unittest.main()
