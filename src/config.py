"""
Application settings, form option lists, and medical disclaimer copy.

Loads secrets from a local .env file via python-dotenv. Never hard-code API keys.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Resolve project root so .env works regardless of the process working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# OpenAI / model settings
# ---------------------------------------------------------------------------
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
# Low temperature keeps structured JSON more consistent for the assessment chain.
OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR: Path = PROJECT_ROOT / "data"
SQLITE_CACHE_PATH: Path = DATA_DIR / "langchain_cache.db"
APP_RESULT_CACHE_PATH: Path = DATA_DIR / "result_cache.db"

# ---------------------------------------------------------------------------
# Form option lists (used by Streamlit widgets)
# ---------------------------------------------------------------------------
GENDER_OPTIONS: list[str] = [
    "Prefer not to say",
    "Female",
    "Male",
    "Non-binary",
    "Other",
]

DURATION_OPTIONS: list[str] = [
    "Less than 24 hours",
    "1-3 days",
    "4-7 days",
    "1-2 weeks",
    "More than 2 weeks",
]

# Common symptoms for multiselect; users can still add free-text extras.
SYMPTOM_OPTIONS: list[str] = [
    "Runny nose",
    "Sore throat",
    "Cough",
    "Fever",
    "Fatigue",
    "Headache",
    "Nausea",
    "Vomiting",
    "Diarrhea",
    "Abdominal pain",
    "Chest pain",
    "Shortness of breath",
    "Dizziness",
    "Muscle aches",
    "Rash",
    "Loss of appetite",
    "Chills",
    "Sweating",
]

LANGUAGE_OPTIONS: list[str] = [
    "English",
    "Urdu",
    "Arabic",
    "Spanish",
    "French",
    "Hindi",
]

CACHE_MODE_OPTIONS: list[str] = [
    "Off",
    "In-memory",
    "SQLite",
]

SEVERITY_MIN: int = 1
SEVERITY_MAX: int = 10
SEVERITY_DEFAULT: int = 5

URGENCY_LEVELS: tuple[str, ...] = ("LOW", "MEDIUM", "HIGH", "EMERGENCY")

# ---------------------------------------------------------------------------
# Medical safety copy (must appear on every relevant screen)
# ---------------------------------------------------------------------------
APP_NAME: str = "MediGuide AI"
APP_TAGLINE: str = "Educational symptom guidance assistant"

DISCLAIMER_SHORT: str = (
    "MediGuide AI is an educational prototype only. It is **not** a doctor, "
    "diagnosis, or emergency service."
)

DISCLAIMER_FULL: str = (
    "MediGuide AI is an educational AI system only. It does **not** provide "
    "medical advice, a confirmed diagnosis, or emergency care. Do not use it "
    "as a replacement for a licensed healthcare professional. If you have "
    "severe, sudden, or worsening symptoms - especially chest pain, trouble "
    "breathing, confusion, or severe bleeding - seek emergency help immediately."
)

EMERGENCY_BANNER: str = (
    "**Seek emergency medical help immediately.** Based on the information "
    "provided, symptoms may indicate a serious situation. Call your local "
    "emergency number or go to the nearest emergency department now."
)


def has_api_key() -> bool:
    """Return True when a non-placeholder OpenAI API key is configured."""
    if not OPENAI_API_KEY:
        return False
    if OPENAI_API_KEY.startswith("sk-your-key"):
        return False
    return True


def ensure_data_dir() -> Path:
    """Create the data directory used for SQLite caches if missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR
