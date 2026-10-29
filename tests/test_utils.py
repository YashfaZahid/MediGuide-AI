"""Automated tests for src.utils - no live OpenAI calls."""

from __future__ import annotations

import json

from src.utils import (
    combine_symptoms,
    hash_inputs,
    normalize_urgency,
    safe_parse_assessment_json,
    strip_code_fences,
    urgency_streamlit_intent,
    validate_inputs,
)


class TestStripCodeFences:
    def test_plain_json_unchanged(self):
        raw = '{"summary": "ok"}'
        assert strip_code_fences(raw) == raw

    def test_json_fence_removed(self):
        raw = '```json\n{"summary": "ok"}\n```'
        assert strip_code_fences(raw) == '{"summary": "ok"}'

    def test_bare_fence_removed(self):
        raw = '```\n{"a": 1}\n```'
        assert strip_code_fences(raw) == '{"a": 1}'


class TestSafeParseAssessmentJson:
    def test_valid_json(self):
        payload = {
            "summary": "Mild cold symptoms.",
            "possible_conditions": [
                {"name": "Common cold", "reason": "Runny nose and sore throat"}
            ],
            "urgency_level": "LOW",
            "recommended_next_steps": ["Rest", "Hydrate"],
            "questions_for_doctor": ["How long should symptoms last?"],
            "warning_signs": ["High fever", "Difficulty breathing"],
        }
        ok, data, err = safe_parse_assessment_json(json.dumps(payload))
        assert ok is True
        assert err == ""
        assert data["summary"] == "Mild cold symptoms."
        assert data["urgency_level"] == "LOW"
        assert data["possible_conditions"][0]["name"] == "Common cold"
        assert len(data["recommended_next_steps"]) == 2

    def test_fenced_json(self):
        raw = '```json\n{"summary": "x", "urgency_level": "high", '
        raw += '"possible_conditions": [], "recommended_next_steps": [], '
        raw += '"questions_for_doctor": [], "warning_signs": []}\n```'
        ok, data, err = safe_parse_assessment_json(raw)
        assert ok is True
        assert data["urgency_level"] == "HIGH"

    def test_malformed_json_does_not_raise(self):
        ok, data, err = safe_parse_assessment_json("not-json {{{")
        assert ok is False
        assert data == {}
        assert "parse" in err.lower() or "json" in err.lower()

    def test_partial_schema_fills_defaults(self):
        ok, data, err = safe_parse_assessment_json('{"summary": "Only summary"}')
        assert ok is True
        assert data["summary"] == "Only summary"
        assert data["possible_conditions"] == []
        assert data["urgency_level"] == "MEDIUM"
        assert "missing" in err.lower()

    def test_empty_output(self):
        ok, data, err = safe_parse_assessment_json("   ")
        assert ok is False
        assert data == {}
        assert "empty" in err.lower()


class TestUrgency:
    def test_normalize_aliases(self):
        assert normalize_urgency("low") == "LOW"
        assert normalize_urgency("moderate") == "MEDIUM"
        assert normalize_urgency("severe") == "HIGH"
        assert normalize_urgency("emergency") == "EMERGENCY"
        assert normalize_urgency("critical") == "EMERGENCY"

    def test_streamlit_intent_mapping(self):
        assert urgency_streamlit_intent("LOW") == "success"
        assert urgency_streamlit_intent("MEDIUM") == "info"
        assert urgency_streamlit_intent("HIGH") == "warning"
        assert urgency_streamlit_intent("EMERGENCY") == "error"


class TestValidateInputs:
    def test_empty_symptoms_blocked(self):
        ok, _, errors = validate_inputs(
            age="25",
            gender="Female",
            symptoms=[],
            duration="1-3 days",
            severity=2,
            extra_symptoms="",
        )
        assert ok is False
        assert any("symptom" in e.lower() for e in errors)

    def test_valid_minimal_form(self):
        ok, data, errors = validate_inputs(
            age="25",
            gender="Female",
            symptoms=["Runny nose", "Sore throat"],
            duration="1-3 days",
            severity=2,
            language="English",
        )
        assert ok is True
        assert errors == []
        assert data["age"] == 25
        assert data["symptoms_text"] == "Runny nose, Sore throat"
        assert data["severity"] == 2

    def test_invalid_age(self):
        ok, _, errors = validate_inputs(
            age="abc",
            gender="Male",
            symptoms=["Cough"],
            duration="1-3 days",
            severity=3,
        )
        assert ok is False
        assert any("age" in e.lower() for e in errors)

    def test_extra_symptoms_merged(self):
        ok, data, _ = validate_inputs(
            age="40",
            gender="Male",
            symptoms=["Fever"],
            duration="4-7 days",
            severity=6,
            extra_symptoms="Cough, Fatigue",
        )
        assert ok is True
        assert "Fever" in data["symptoms"]
        assert "Cough" in data["symptoms"]
        assert "Fatigue" in data["symptoms"]


class TestCombineAndHash:
    def test_combine_symptoms_dedupes(self):
        result = combine_symptoms(["Cough", "Fever"], "Fever, Headache")
        assert result == ["Cough", "Fever", "Headache"]

    def test_hash_stable_for_same_inputs(self):
        a = {
            "age": 25,
            "gender": "Female",
            "symptoms": ["Runny nose"],
            "duration": "1-3 days",
            "severity": 2,
            "existing_conditions": "None reported",
            "medications": "None reported",
            "notes": "None",
            "language": "English",
        }
        b = dict(a)
        assert hash_inputs(a) == hash_inputs(b)

    def test_hash_changes_when_field_changes(self):
        a = {"age": 25, "gender": "Female", "symptoms": ["Cough"], "severity": 2}
        b = {"age": 25, "gender": "Female", "symptoms": ["Cough"], "severity": 9}
        assert hash_inputs(a) != hash_inputs(b)
