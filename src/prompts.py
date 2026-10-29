"""
Prompt templates and JSON schema instructions for MediGuide AI.

Provides:
- PromptTemplate (single-string) for reusable patient assessment text
- ChatPromptTemplate (System + Human) for the primary LLMChain
- Narrative ChatPromptTemplate for streamed guidance
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

# Exact schema the model must return (assignment section 10).
ASSESSMENT_JSON_SCHEMA = """
{
  "summary": "",
  "possible_conditions": [ { "name": "", "reason": "" } ],
  "urgency_level": "",
  "recommended_next_steps": [],
  "questions_for_doctor": [],
  "warning_signs": []
}
""".strip()

# PromptTemplate treats {..} as variables; escape literal JSON braces as {{ }}.
ASSESSMENT_JSON_SCHEMA_ESCAPED = ASSESSMENT_JSON_SCHEMA.replace("{", "{{").replace(
    "}", "}}"
)

# Safety rules encoded so the model behaves conservatively.
# No unescaped curly braces here so templates stay valid.
SYSTEM_SAFETY_RULES = """
You are MediGuide AI, an educational health-information assistant for a school
programming assignment. You are NOT a doctor and you must NEVER present a
confirmed diagnosis, prescribe medication, or claim certainty about a condition.

Mandatory safety rules:
1. Label all possible conditions as educational topics to discuss with a
   licensed healthcare professional - never as a diagnosis.
2. Prefer a more conservative (higher) urgency when information is uncertain.
3. Always include practical next steps and warning signs that need urgent care.
4. If symptoms suggest emergency (severe chest pain, difficulty breathing,
   stroke signs, severe bleeding, sudden confusion, suicidal thoughts), set
   urgency_level to EMERGENCY and tell the user to seek emergency help now.
5. urgency_level must be exactly one of: LOW, MEDIUM, HIGH, EMERGENCY.
6. Respond in the requested answer language for all user-facing string values.
7. Return ONLY valid JSON matching the schema. No markdown fences. No prose
   outside JSON for the assessment response.
""".strip()

JSON_OUTPUT_INSTRUCTIONS = """
Return ONLY a valid JSON object with this exact structure (fill every field):
""" + ASSESSMENT_JSON_SCHEMA_ESCAPED + """

Field guidance:
- summary: brief plain-language overview of the reported symptoms (not a diagnosis)
- possible_conditions: 1-4 educational possibilities with short reasons
- urgency_level: LOW | MEDIUM | HIGH | EMERGENCY
- recommended_next_steps: actionable self-care / when to seek care
- questions_for_doctor: useful questions for a clinician visit
- warning_signs: red flags that need immediate attention
""".strip()

# Shared variable names used by both templates and the Streamlit form.
PATIENT_INPUT_VARIABLES = [
    "age",
    "gender",
    "symptoms_text",
    "duration",
    "severity",
    "existing_conditions",
    "medications",
    "notes",
    "language",
]

_PATIENT_BLOCK = """
Patient information:
- Age: {age}
- Gender: {gender}
- Symptoms: {symptoms_text}
- Duration: {duration}
- Severity (1-10): {severity}
- Existing conditions: {existing_conditions}
- Current medications: {medications}
- Additional notes: {notes}
- Answer language: {language}
""".strip()

# ---------------------------------------------------------------------------
# PromptTemplate - single reusable string template (assignment requirement)
# ---------------------------------------------------------------------------
ASSESSMENT_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=PATIENT_INPUT_VARIABLES,
    template=(
        SYSTEM_SAFETY_RULES
        + "\n\n"
        + JSON_OUTPUT_INSTRUCTIONS
        + "\n\n"
        + _PATIENT_BLOCK
        + "\n\nProduce the JSON assessment now."
    ),
)

# ---------------------------------------------------------------------------
# ChatPromptTemplate - System + Human (primary assessment path)
# ---------------------------------------------------------------------------
ASSESSMENT_CHAT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            SYSTEM_SAFETY_RULES + "\n\n" + JSON_OUTPUT_INSTRUCTIONS,
        ),
        (
            "human",
            _PATIENT_BLOCK
            + "\n\nPlease return ONLY the JSON object for this educational assessment.",
        ),
    ]
)

# ---------------------------------------------------------------------------
# Narrative template - used with llm.stream() for live typing effect
# ---------------------------------------------------------------------------
NARRATIVE_CHAT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are MediGuide AI, an educational assistant. You are not a doctor. "
                "Never claim a confirmed diagnosis. Write a short, calm, supportive "
                "guidance narrative in the requested language. Remind the reader to "
                "consult a licensed professional. If urgency is EMERGENCY or HIGH, "
                "clearly advise seeking urgent or emergency care."
            ),
        ),
        (
            "human",
            (
                "Write a brief patient-friendly narrative (about 120-180 words) based on:\n"
                + _PATIENT_BLOCK
                + "\n\nStructured assessment summary:\n{assessment_summary}\n"
                "Urgency level: {urgency_level}\n"
                "Possible conditions (education only): {conditions_text}\n"
                "Recommended next steps: {next_steps_text}\n"
                "Warning signs: {warning_signs_text}\n\n"
                "Do not output JSON. Write plain prose only in {language}."
            ),
        ),
    ]
)


def build_assessment_prompt_inputs(normalized: dict) -> dict:
    """Map validated form inputs to template variables."""
    return {
        "age": normalized.get("age", ""),
        "gender": normalized.get("gender", ""),
        "symptoms_text": normalized.get("symptoms_text", ""),
        "duration": normalized.get("duration", ""),
        "severity": normalized.get("severity", ""),
        "existing_conditions": normalized.get("existing_conditions", "None reported"),
        "medications": normalized.get("medications", "None reported"),
        "notes": normalized.get("notes", "None"),
        "language": normalized.get("language", "English"),
    }


def build_narrative_prompt_inputs(
    normalized: dict,
    assessment: dict,
) -> dict:
    """Combine patient inputs with parsed assessment fields for narrative streaming."""
    base = build_assessment_prompt_inputs(normalized)
    conditions = assessment.get("possible_conditions") or []
    if isinstance(conditions, list):
        conditions_text = "; ".join(
            f"{c.get('name', '')}: {c.get('reason', '')}".strip(": ")
            for c in conditions
            if isinstance(c, dict)
        ) or "None listed"
    else:
        conditions_text = str(conditions)

    def _join_list(value: object) -> str:
        if isinstance(value, list):
            return "; ".join(str(v) for v in value) if value else "None listed"
        return str(value or "None listed")

    base.update(
        {
            "assessment_summary": assessment.get("summary", ""),
            "urgency_level": assessment.get("urgency_level", "MEDIUM"),
            "conditions_text": conditions_text,
            "next_steps_text": _join_list(assessment.get("recommended_next_steps")),
            "warning_signs_text": _join_list(assessment.get("warning_signs")),
        }
    )
    return base
