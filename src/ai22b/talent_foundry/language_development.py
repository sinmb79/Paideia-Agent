from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LANGUAGE_DEVELOPMENT_SCHEMA = "ai-talent-language-development-program/v1"

RESEARCH_BASIS = [
    {
        "id": "cdc_developmental_milestones",
        "name": "CDC Developmental Milestones",
        "url": "https://www.cdc.gov/milestones",
        "design_use": "language and communication are tracked as developmental milestones, not only school subjects",
    },
    {
        "id": "nidcd_speech_language",
        "name": "NIDCD Speech and Language Developmental Milestones",
        "url": "https://www.nidcd.nih.gov/health/speech-and-language",
        "design_use": "birth-to-five language growth is modeled before formal schooling",
    },
    {
        "id": "asha_social_communication",
        "name": "ASHA Components of Social Communication",
        "url": "https://www.asha.org/practice-portal/clinical-topics/social-communication-disorder/components-of-social-communication/",
        "design_use": "conversation requires social interaction, social cognition, pragmatics, and language processing",
    },
    {
        "id": "tomasello_joint_attention",
        "name": "The role of joint attentional processes in early language development",
        "url": "https://scholars.duke.edu/publication/1457995",
        "design_use": "joint attention is treated as an early bridge between shared experience and words",
    },
    {
        "id": "dialogic_reading",
        "name": "Dialogic reading and language development",
        "url": "https://files.eric.ed.gov/fulltext/ED450418.pdf",
        "design_use": "adult-child question, feedback, expansion, and retelling loops become conversation practice",
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_language_development_program(
    *,
    talent_name: str,
    primary_language: str = "ko-KR",
) -> dict[str, Any]:
    stages = [
        {
            "stage_id": "prenatal_prosody",
            "age_band": "prenatal",
            "development_focus": "rhythm_prosody_and_parent_voice",
            "experiences": [
                "mother_voice_rhythm",
                "father_voice_warmth",
                "family_emotional_tone",
            ],
            "conversation_skills": [
                "comfort_with_human_voice_patterns",
                "turn_timing_seed",
            ],
            "assessment": "responds_to_voice_and_rhythm_simulation",
        },
        {
            "stage_id": "infancy_joint_attention",
            "age_band": "0-1",
            "development_focus": "shared_attention_before_words",
            "experiences": [
                "peekaboo",
                "pointing_and_gaze_following",
                "caregiver_naming_shared_objects",
            ],
            "conversation_skills": [
                "notice_speaker_focus",
                "connect_word_to_shared_object",
                "wait_for_turn",
            ],
            "assessment": "joint_attention_and_turn_waiting_check",
        },
        {
            "stage_id": "toddler_first_words",
            "age_band": "1-3",
            "development_focus": "first_words_requests_and_repair",
            "experiences": [
                "naming_family_food_places",
                "requesting_help",
                "simple_choice_answering",
                "misunderstanding_repair",
            ],
            "conversation_skills": [
                "answer_simple_questions",
                "ask_for_help",
                "repair_when_not_understood",
            ],
            "assessment": "two_turn_dialogue_repair_check",
        },
        {
            "stage_id": "preschool_story_play",
            "age_band": "3-6",
            "development_focus": "story_play_emotion_words_and_rules",
            "experiences": [
                "storybook_retelling",
                "pretend_play_roles",
                "emotion_labeling",
                "apology_and_reconciliation",
            ],
            "conversation_skills": [
                "tell_short_story",
                "name_emotion",
                "follow_conversation_rules",
                "respond_to_correction",
            ],
            "assessment": "story_retell_and_emotion_dialogue",
        },
        {
            "stage_id": "elementary_pragmatics",
            "age_band": "7-12",
            "development_focus": "school_conversation_and_pragmatics",
            "experiences": [
                "classroom_question_answer",
                "friend_conflict_resolution",
                "reading_summary_talk",
                "teacher_feedback_revision",
            ],
            "conversation_skills": [
                "summarize_reading",
                "ask_clarifying_question",
                "separate_fact_feeling_opinion",
                "accept_feedback_without_defensiveness",
            ],
            "assessment": "classroom_discussion_and_feedback_repair",
        },
        {
            "stage_id": "adolescent_perspective_argument",
            "age_band": "13-18",
            "development_focus": "perspective_taking_argument_and_identity",
            "experiences": [
                "debate_club",
                "peer_disagreement",
                "mentor_feedback",
                "long_form_explanation",
            ],
            "conversation_skills": [
                "state_claim_evidence_limit",
                "recognize_other_perspective",
                "distinguish_question_from_challenge",
                "recover_after_being_wrong",
            ],
            "assessment": "argument_dialogue_and_conflict_repair",
        },
        {
            "stage_id": "university_professional_discourse",
            "age_band": "19-22",
            "development_focus": "academic_and_professional_dialogue",
            "experiences": [
                "seminar_questions",
                "report_presentation",
                "source_citation_discussion",
                "team_project_coordination",
            ],
            "conversation_skills": [
                "answer_before_process_dump",
                "cite_source_when_needed",
                "separate_uncertainty_from_conclusion",
                "adapt_depth_to_listener",
            ],
            "assessment": "seminar_qa_and_presentation_feedback",
        },
        {
            "stage_id": "graduate_research_dialogue",
            "age_band": "23+",
            "development_focus": "research_supervision_and_error_correction",
            "experiences": [
                "advisor_meeting",
                "paper_defense",
                "failed_hypothesis_review",
                "peer_review_response",
            ],
            "conversation_skills": [
                "summarize_reasoning_publicly",
                "do_not_expose_private_chain_of_thought",
                "revise_after_counterexample",
                "ask_for_missing_context",
            ],
            "assessment": "defense_qa_and_revision_plan",
        },
        {
            "stage_id": "hired_agent_conversation_growth",
            "age_band": "post-hire",
            "development_focus": "boss_dialogue_and_work_chat",
            "experiences": [
                "boss_greeting",
                "boss_correction",
                "task_request",
                "ambiguous_question",
                "long_running_work_review",
            ],
            "conversation_skills": [
                "classify_intent_before_answer",
                "answer_naturally_for_small_talk",
                "show_reviewable_reasoning_for_work",
                "repair_after_boss_feedback",
                "keep_learning_from_chat_logs",
            ],
            "assessment": "live_chat_intent_routing_and_repair",
        },
    ]
    return {
        "schema": LANGUAGE_DEVELOPMENT_SCHEMA,
        "created_at_utc": _now(),
        "talent_name": talent_name,
        "primary_language": primary_language,
        "purpose": "Make language and conversation a staged human-like development track, not a late chat patch.",
        "research_basis": RESEARCH_BASIS,
        "stages": stages,
        "growth_policy": {
            "starts_before_school": True,
            "requires_social_pragmatics": True,
            "conversation_is_not_only_reasoning": True,
            "continues_after_hire": True,
            "private_reasoning_trace": "do_not_store",
        },
        "chat_transfer_rules": [
            "First classify whether the Boss is greeting, correcting, asking for a story, assigning work, or asking a meta question.",
            "For ordinary talk, answer naturally before showing any reasoning summary.",
            "For work or correction, show a reviewable reasoning summary without hidden chain-of-thought.",
            "If the Boss says the answer is wrong, treat that as a learning event and reclassify the intent.",
        ],
    }


def write_language_development_program(path: Path, program: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(program, ensure_ascii=False, indent=2), encoding="utf-8")
