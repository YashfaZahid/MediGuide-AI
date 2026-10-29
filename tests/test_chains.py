"""Unit tests for chains.py using mocks - no live OpenAI calls."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.chains import (
    MissingAPIKeyError,
    _extract_chain_text,
    build_assessment_chain,
    build_llm,
    demo_messages,
    run_assessment,
    stream_narrative,
)


class TestExtractChainText:
    def test_dict_text_key(self):
        assert _extract_chain_text({"text": "hello"}) == "hello"

    def test_string(self):
        assert _extract_chain_text("plain") == "plain"

    def test_content_attr(self):
        assert _extract_chain_text(SimpleNamespace(content="from-attr")) == "from-attr"


class TestBuildLlm:
    def test_missing_key_raises(self):
        with patch("src.chains.has_api_key", return_value=False):
            with pytest.raises(MissingAPIKeyError):
                build_llm()


class TestBuildAssessmentChain:
    def test_returns_llmchain_with_fake_llm(self):
        fake_llm = FakeListChatModel(responses=['{"summary": "ok"}'])
        chain = build_assessment_chain(llm=fake_llm, use_chat_prompt=True)
        assert chain is not None
        assert chain.llm is fake_llm
        # PromptTemplate path also works.
        chain2 = build_assessment_chain(llm=fake_llm, use_chat_prompt=False)
        assert chain2.prompt is not None


class TestRunAssessment:
    def test_parses_valid_json_from_chain(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = {
            "text": (
                '{"summary": "Mild symptoms.", "possible_conditions": [], '
                '"urgency_level": "LOW", "recommended_next_steps": ["Rest"], '
                '"questions_for_doctor": ["Any fever?"], '
                '"warning_signs": ["Trouble breathing"]}'
            )
        }
        with patch("src.chains.build_assessment_chain", return_value=mock_chain):
            ok, data, note, raw = run_assessment(
                {
                    "age": 25,
                    "gender": "Female",
                    "symptoms_text": "Runny nose",
                    "duration": "1-3 days",
                    "severity": 2,
                    "existing_conditions": "None",
                    "medications": "None",
                    "notes": "None",
                    "language": "English",
                }
            )
        assert ok is True
        assert data["urgency_level"] == "LOW"
        assert "Mild" in data["summary"]
        assert raw

    def test_bad_json_does_not_raise(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = {"text": "not-json"}
        with patch("src.chains.build_assessment_chain", return_value=mock_chain):
            ok, data, err, raw = run_assessment(
                {
                    "age": 25,
                    "gender": "Female",
                    "symptoms_text": "Cough",
                    "duration": "1-3 days",
                    "severity": 3,
                    "existing_conditions": "None",
                    "medications": "None",
                    "notes": "None",
                    "language": "English",
                }
            )
        assert ok is False
        assert data == {}
        assert raw == "not-json"
        assert err


class TestDemoAndStream:
    def test_demo_messages_includes_all_roles(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Educational guidance only.")
        messages = demo_messages(llm=mock_llm)
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[1], HumanMessage)
        assert isinstance(messages[2], AIMessage)
        assert "Educational" in messages[2].content

    def test_stream_narrative_yields_chunks(self):
        mock_llm = MagicMock()
        mock_llm.stream.return_value = [
            SimpleNamespace(content="Hello "),
            SimpleNamespace(content="world"),
        ]
        chunks = list(
            stream_narrative(
                {
                    "age": 25,
                    "gender": "Female",
                    "symptoms_text": "Sore throat",
                    "duration": "1-3 days",
                    "severity": 2,
                    "existing_conditions": "None",
                    "medications": "None",
                    "notes": "None",
                    "language": "English",
                },
                {
                    "summary": "Mild",
                    "urgency_level": "LOW",
                    "possible_conditions": [],
                    "recommended_next_steps": ["Rest"],
                    "warning_signs": [],
                },
                llm=mock_llm,
            )
        )
        assert "".join(chunks) == "Hello world"
