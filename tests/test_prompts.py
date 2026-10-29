"""Tests for prompt templates - no live OpenAI calls."""

from __future__ import annotations

from src.prompts import (
    ASSESSMENT_CHAT_TEMPLATE,
    ASSESSMENT_JSON_SCHEMA,
    ASSESSMENT_PROMPT_TEMPLATE,
    NARRATIVE_CHAT_TEMPLATE,
    SYSTEM_SAFETY_RULES,
    build_assessment_prompt_inputs,
    build_narrative_prompt_inputs,
)


SAMPLE = {
    "age": 25,
    "gender": "Female",
    "symptoms_text": "Runny nose, Sore throat",
    "duration": "1-3 days",
    "severity": 2,
    "existing_conditions": "None reported",
    "medications": "None reported",
    "notes": "None",
    "language": "English",
}


class TestPromptSafety:
    def test_system_rules_forbid_diagnosis(self):
        lowered = SYSTEM_SAFETY_RULES.lower()
        assert "not a doctor" in lowered or "never" in lowered
        assert "confirmed diagnosis" in lowered or "diagnosis" in lowered

    def test_json_schema_contains_required_keys(self):
        for key in (
            "summary",
            "possible_conditions",
            "urgency_level",
            "recommended_next_steps",
            "questions_for_doctor",
            "warning_signs",
        ):
            assert key in ASSESSMENT_JSON_SCHEMA


class TestPromptFormatting:
    def test_prompt_template_formats(self):
        text = ASSESSMENT_PROMPT_TEMPLATE.format(**SAMPLE)
        assert "25" in text
        assert "Runny nose" in text
        assert "urgency_level" in text

    def test_chat_prompt_template_formats_messages(self):
        messages = ASSESSMENT_CHAT_TEMPLATE.format_messages(**SAMPLE)
        assert len(messages) == 2
        assert messages[0].type == "system"
        assert messages[1].type == "human"
        assert "Sore throat" in messages[1].content
        assert "JSON" in messages[0].content or "json" in messages[0].content.lower()

    def test_narrative_template_formats(self):
        assessment = {
            "summary": "Mild upper respiratory symptoms.",
            "possible_conditions": [
                {"name": "Common cold", "reason": "Congestion and sore throat"}
            ],
            "urgency_level": "LOW",
            "recommended_next_steps": ["Rest", "Fluids"],
            "warning_signs": ["Trouble breathing"],
        }
        inputs = build_narrative_prompt_inputs(SAMPLE, assessment)
        messages = NARRATIVE_CHAT_TEMPLATE.format_messages(**inputs)
        assert len(messages) == 2
        assert "LOW" in messages[1].content
        assert "Common cold" in messages[1].content

    def test_build_assessment_prompt_inputs(self):
        normalized = {
            "age": 40,
            "gender": "Male",
            "symptoms_text": "Fever, Cough",
            "duration": "4-7 days",
            "severity": 6,
            "existing_conditions": "Asthma",
            "medications": "Inhaler",
            "notes": "Worse at night",
            "language": "Urdu",
        }
        out = build_assessment_prompt_inputs(normalized)
        assert out["language"] == "Urdu"
        assert out["symptoms_text"] == "Fever, Cough"
