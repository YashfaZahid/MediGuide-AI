"""
Validation helpers, safe JSON parsing, urgency mapping, and cache-key hashing.

These helpers must never raise to the UI layer for expected failure cases
(bad JSON, empty symptoms). Callers receive structured (ok, data, error) results.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from src.config import SEVERITY_MAX, SEVERITY_MIN, URGENCY_LEVELS

# Keys required by the assignment JSON schema.
REQUIRED_ASSESSMENT_KEYS: tuple[str, ...] = (
    "summary",
    "possible_conditions",
    "urgency_level",
    "recommended_next_steps",
    "questions_for_doctor",
    "warning_signs",
)

# Match ```json ... ``` or ``` ... ``` fences the model sometimes wraps around JSON.
_FENCE_RE = re.compile(
    r"```(?:json)?\s*(.*?)\s*```",
    re.IGNORECASE | re.DOTALL,
)


def strip_code_fences(text: str) -> str:
    """Remove Markdown code fences and surrounding whitespace from model output."""
    if not text:
        return ""
    cleaned = text.strip()
    match = _FENCE_RE.search(cleaned)
    if match:
        return match.group(1).strip()
    # Also strip bare leading/trailing triple backticks without a full match.
    if cleaned.startswith("```"):
        cleaned = cleaned.lstrip("`")
        # Drop optional language tag on first line.
        if "\n" in cleaned:
            first, rest = cleaned.split("\n", 1)
            if first.strip().lower() in {"json", ""}:
                cleaned = rest
            else:
                cleaned = first + "\n" + rest
        cleaned = cleaned.rstrip("`").strip()
    return cleaned.strip()


def normalize_urgency(value: Any) -> str:
    """Map free-form urgency text to LOW | MEDIUM | HIGH | EMERGENCY."""
    raw = str(value or "").strip().upper().replace("-", " ").replace("_", " ")
    raw = " ".join(raw.split())

    if not raw:
        return "MEDIUM"

    # Direct hits and common synonyms.
    aliases = {
        "LOW": "LOW",
        "MILD": "LOW",
        "MINOR": "LOW",
        "MEDIUM": "MEDIUM",
        "MODERATE": "MEDIUM",
        "HIGH": "HIGH",
        "SEVERE": "HIGH",
        "URGENT": "HIGH",
        "EMERGENCY": "EMERGENCY",
        "CRITICAL": "EMERGENCY",
        "LIFE THREATENING": "EMERGENCY",
        "IMMEDIATE": "EMERGENCY",
    }
    if raw in aliases:
        return aliases[raw]

    for level in URGENCY_LEVELS:
        if level in raw:
            return level

    return "MEDIUM"


def urgency_streamlit_intent(urgency: str) -> str:
    """
    Map urgency to a Streamlit callout intent name.

    Returns one of: success, info, warning, error.
    """
    level = normalize_urgency(urgency)
    return {
        "LOW": "success",
        "MEDIUM": "info",
        "HIGH": "warning",
        "EMERGENCY": "error",
    }.get(level, "info")


def _default_assessment() -> dict[str, Any]:
    return {
        "summary": "",
        "possible_conditions": [],
        "urgency_level": "MEDIUM",
        "recommended_next_steps": [],
        "questions_for_doctor": [],
        "warning_signs": [],
    }


def _normalize_conditions(value: Any) -> list[dict[str, str]]:
    """Ensure possible_conditions is a list of {name, reason} dicts."""
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            normalized.append(
                {
                    "name": str(item.get("name", "")).strip(),
                    "reason": str(item.get("reason", "")).strip(),
                }
            )
        elif isinstance(item, str) and item.strip():
            normalized.append({"name": item.strip(), "reason": ""})
    return normalized


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def safe_parse_assessment_json(raw_text: str) -> tuple[bool, dict[str, Any], str]:
    """
    Parse model output into the assignment assessment schema.

    Returns (ok, data, error_message).
    - On total parse failure: ok=False, data={}, error_message set; never raises.
    - On partial schema: ok=True with defaults filled; error_message notes gaps.
    """
    if raw_text is None:
        return False, {}, "Model returned empty output."

    cleaned = strip_code_fences(str(raw_text))
    if not cleaned:
        return False, {}, "Model returned empty output."

    # If the model added prose, try to extract the outermost JSON object.
    if not cleaned.lstrip().startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return False, {}, f"Could not parse JSON ({exc})."

    if not isinstance(parsed, dict):
        return False, {}, "JSON root must be an object."

    result = _default_assessment()
    missing: list[str] = []

    for key in REQUIRED_ASSESSMENT_KEYS:
        if key not in parsed:
            missing.append(key)

    result["summary"] = str(parsed.get("summary", "") or "").strip()
    result["possible_conditions"] = _normalize_conditions(
        parsed.get("possible_conditions", [])
    )
    result["urgency_level"] = normalize_urgency(parsed.get("urgency_level", "MEDIUM"))
    result["recommended_next_steps"] = _normalize_string_list(
        parsed.get("recommended_next_steps", [])
    )
    result["questions_for_doctor"] = _normalize_string_list(
        parsed.get("questions_for_doctor", [])
    )
    result["warning_signs"] = _normalize_string_list(parsed.get("warning_signs", []))

    note = ""
    if missing:
        note = (
            "Some expected fields were missing and were filled with safe defaults: "
            + ", ".join(missing)
        )

    return True, result, note


def combine_symptoms(selected: list[str] | None, extra_text: str | None) -> list[str]:
    """Merge multiselect symptoms with optional free-text (comma/newline separated)."""
    combined: list[str] = []
    for item in selected or []:
        text = str(item).strip()
        if text and text not in combined:
            combined.append(text)

    extra = (extra_text or "").strip()
    if extra:
        parts = re.split(r"[,;\n]+", extra)
        for part in parts:
            text = part.strip()
            if text and text not in combined:
                combined.append(text)
    return combined


def validate_inputs(
    age: str | int | None,
    gender: str | None,
    symptoms: list[str] | None,
    duration: str | None,
    severity: int | float | None,
    existing_conditions: str | None = None,
    medications: str | None = None,
    notes: str | None = None,
    language: str | None = None,
    extra_symptoms: str | None = None,
) -> tuple[bool, dict[str, Any], list[str]]:
    """
    Validate patient form fields before any LLM call.

    Returns (ok, normalized_inputs, error_messages).
    Empty symptoms must fail so the UI can warn without calling the API.
    """
    errors: list[str] = []
    combined_symptoms = combine_symptoms(symptoms, extra_symptoms)

    # Age: required positive integer in a plausible human range.
    age_raw = str(age or "").strip()
    age_value: int | None = None
    if not age_raw:
        errors.append("Please enter the patient's age.")
    else:
        try:
            age_value = int(age_raw)
            if age_value < 0 or age_value > 120:
                errors.append("Age must be between 0 and 120.")
                age_value = None
        except ValueError:
            errors.append("Age must be a whole number.")

    if not combined_symptoms:
        errors.append(
            "Please select or enter at least one symptom before generating guidance."
        )

    try:
        severity_value = int(severity) if severity is not None else SEVERITY_MIN
    except (TypeError, ValueError):
        severity_value = SEVERITY_MIN
        errors.append("Severity must be a number from 1 to 10.")
    else:
        if severity_value < SEVERITY_MIN or severity_value > SEVERITY_MAX:
            errors.append(f"Severity must be between {SEVERITY_MIN} and {SEVERITY_MAX}.")

    gender_value = (gender or "").strip() or "Prefer not to say"
    duration_value = (duration or "").strip() or "Unknown"
    language_value = (language or "").strip() or "English"

    normalized = {
        "age": age_value if age_value is not None else age_raw,
        "gender": gender_value,
        "symptoms": combined_symptoms,
        "symptoms_text": ", ".join(combined_symptoms),
        "duration": duration_value,
        "severity": severity_value,
        "existing_conditions": (existing_conditions or "").strip() or "None reported",
        "medications": (medications or "").strip() or "None reported",
        "notes": (notes or "").strip() or "None",
        "language": language_value,
    }

    return len(errors) == 0, normalized, errors


def hash_inputs(inputs: dict[str, Any]) -> str:
    """
    Stable SHA-256 hash of normalized assessment inputs for app-level caching.

    Only patient-relevant fields are included so cache hits match identical forms.
    """
    payload = {
        "age": inputs.get("age"),
        "gender": inputs.get("gender"),
        "symptoms": inputs.get("symptoms"),
        "duration": inputs.get("duration"),
        "severity": inputs.get("severity"),
        "existing_conditions": inputs.get("existing_conditions"),
        "medications": inputs.get("medications"),
        "notes": inputs.get("notes"),
        "language": inputs.get("language"),
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
