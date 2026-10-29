"""
ChatOpenAI, LLMChain assessment pipeline, message demo, and narrative streaming.

LLMChain is imported from langchain_classic because LangChain 1.x removed
legacy chains from the main `langchain` package. The assignment still requires
LLMChain, so classic is the supported path.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from langchain_classic.chains import LLMChain
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE, has_api_key
from src.prompts import (
    ASSESSMENT_CHAT_TEMPLATE,
    ASSESSMENT_PROMPT_TEMPLATE,
    NARRATIVE_CHAT_TEMPLATE,
    SYSTEM_SAFETY_RULES,
    build_assessment_prompt_inputs,
    build_narrative_prompt_inputs,
)
from src.utils import safe_parse_assessment_json


class MissingAPIKeyError(RuntimeError):
    """Raised when OPENAI_API_KEY is missing before an LLM call."""


def build_llm(
    model: str | None = None,
    temperature: float | None = None,
    streaming: bool = False,
) -> ChatOpenAI:
    """Create a ChatOpenAI client. API key comes from the environment / .env."""
    if not has_api_key():
        raise MissingAPIKeyError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and add your key."
        )
    return ChatOpenAI(
        model=model or OPENAI_MODEL,
        temperature=OPENAI_TEMPERATURE if temperature is None else temperature,
        api_key=OPENAI_API_KEY,
        streaming=streaming,
    )


def build_assessment_chain(
    llm: ChatOpenAI | None = None,
    use_chat_prompt: bool = True,
) -> LLMChain:
    """
    Build the reusable assessment LLMChain.

    Default uses ChatPromptTemplate (System + Human). Set use_chat_prompt=False
    to demonstrate the single-string PromptTemplate path.
    """
    chat_model = llm or build_llm(streaming=False)
    prompt = ASSESSMENT_CHAT_TEMPLATE if use_chat_prompt else ASSESSMENT_PROMPT_TEMPLATE
    return LLMChain(llm=chat_model, prompt=prompt)


def run_assessment(
    normalized_inputs: dict[str, Any],
    *,
    llm: ChatOpenAI | None = None,
    use_chat_prompt: bool = True,
) -> tuple[bool, dict[str, Any], str, str]:
    """
    Run the assessment chain and safely parse JSON.

    Returns (ok, assessment_dict, error_or_note, raw_text).
    Never raises for JSON parse failures.
    """
    try:
        chain = build_assessment_chain(llm=llm, use_chat_prompt=use_chat_prompt)
        prompt_vars = build_assessment_prompt_inputs(normalized_inputs)
        # LLMChain.invoke returns a dict with 'text' (classic) for the completion.
        result = chain.invoke(prompt_vars)
        raw_text = _extract_chain_text(result)
    except MissingAPIKeyError:
        raise
    except Exception as exc:  # noqa: BLE001 - convert provider errors for the UI
        return False, {}, f"Assessment request failed: {exc}", ""

    ok, data, note = safe_parse_assessment_json(raw_text)
    if not ok:
        return False, {}, note or "Could not parse model JSON.", raw_text
    return True, data, note, raw_text


def _extract_chain_text(result: Any) -> str:
    """Normalize LLMChain / chat outputs to a plain string."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for key in ("text", "output", "content", "response"):
            if key in result and result[key] is not None:
                return str(result[key])
        # Fall back to first string-like value.
        for value in result.values():
            if isinstance(value, str):
                return value
    if hasattr(result, "content"):
        return str(getattr(result, "content"))
    return str(result)


def demo_messages(
    sample_question: str = "I have a mild sore throat. What should I know?",
    llm: ChatOpenAI | None = None,
) -> list[Any]:
    """
    Demonstrate SystemMessage, HumanMessage, and AIMessage in one short turn.

    Used in the UI expander so graders can see all three message types.
    """
    messages: list[Any] = [
        SystemMessage(content=SYSTEM_SAFETY_RULES),
        HumanMessage(content=sample_question),
    ]
    chat_model = llm or build_llm(streaming=False)
    ai_response = chat_model.invoke(messages)
    # Ensure we always return an AIMessage instance for the demo.
    if isinstance(ai_response, AIMessage):
        messages.append(ai_response)
    else:
        messages.append(AIMessage(content=str(getattr(ai_response, "content", ai_response))))
    return messages


def stream_narrative(
    normalized_inputs: dict[str, Any],
    assessment: dict[str, Any],
    *,
    llm: ChatOpenAI | None = None,
) -> Iterator[str]:
    """
    Yield narrative text chunks via ChatOpenAI.stream() for st.write_stream.

    Matches the assignment streaming pattern.
    """
    prompt_vars = build_narrative_prompt_inputs(normalized_inputs, assessment)
    messages = NARRATIVE_CHAT_TEMPLATE.format_messages(**prompt_vars)
    chat_model = llm or build_llm(streaming=True)

    try:
        for chunk in chat_model.stream(messages):
            content = getattr(chunk, "content", None)
            if not content:
                continue
            # Some providers return list content blocks; normalize to text.
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, str):
                        parts.append(block)
                    elif isinstance(block, dict) and block.get("type") == "text":
                        parts.append(str(block.get("text", "")))
                text = "".join(parts)
            else:
                text = str(content)
            if text:
                yield text
    except MissingAPIKeyError:
        raise
    except Exception as exc:  # noqa: BLE001
        yield f"\n\n[Narrative streaming interrupted: {exc}]"
