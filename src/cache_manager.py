"""
LangChain InMemoryCache + SQLiteCache switches, plus an app-level result cache.

Why two layers?
1) set_llm_cache(...) satisfies the assignment (both cache backends).
2) App-level result cache stores parsed assessment JSON by input hash so
   identical form submissions are reliably fast even if ChatOpenAI misses
   the global LLM cache.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Literal

from langchain_community.cache import InMemoryCache, SQLiteCache
from langchain_core.globals import set_llm_cache

from src.config import (
    APP_RESULT_CACHE_PATH,
    SQLITE_CACHE_PATH,
    ensure_data_dir,
)

CacheMode = Literal["off", "memory", "sqlite"]

# Map sidebar labels to internal mode keys.
CACHE_LABEL_TO_MODE: dict[str, CacheMode] = {
    "Off": "off",
    "In-memory": "memory",
    "SQLite": "sqlite",
}

_lock = threading.Lock()
_current_mode: CacheMode = "off"
_memory_result_cache: dict[str, dict[str, Any]] = {}


def mode_from_label(label: str) -> CacheMode:
    """Convert a UI label to an internal cache mode."""
    return CACHE_LABEL_TO_MODE.get(label, "off")


def get_current_mode() -> CacheMode:
    return _current_mode


def enable_cache(mode: CacheMode | str = "off") -> tuple[bool, str]:
    """
    Register the selected LangChain LLM cache via set_llm_cache.

    Returns (ok, message). Never raises for expected failures; falls back safely.
    """
    global _current_mode
    normalized: CacheMode
    if mode in ("off", "memory", "sqlite"):
        normalized = mode  # type: ignore[assignment]
    else:
        normalized = mode_from_label(str(mode))

    try:
        if normalized == "off":
            set_llm_cache(None)
            _current_mode = "off"
            return True, "LangChain LLM cache disabled."

        if normalized == "memory":
            set_llm_cache(InMemoryCache())
            _current_mode = "memory"
            return True, "InMemoryCache enabled (RAM only; cleared on restart)."

        # sqlite
        ensure_data_dir()
        set_llm_cache(SQLiteCache(database_path=str(SQLITE_CACHE_PATH)))
        _current_mode = "sqlite"
        return True, f"SQLiteCache enabled at {SQLITE_CACHE_PATH.name}."
    except Exception as exc:  # noqa: BLE001 - surface friendly message to UI
        # Fall back to in-memory so the app remains usable.
        try:
            set_llm_cache(InMemoryCache())
            _current_mode = "memory"
            return False, (
                f"Could not enable '{normalized}' cache ({exc}). "
                "Fell back to InMemoryCache."
            )
        except Exception as inner:  # noqa: BLE001
            set_llm_cache(None)
            _current_mode = "off"
            return False, f"Caching unavailable ({inner}). Cache disabled."


def _ensure_result_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS assessment_results (
            input_hash TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def get_cached_assessment(input_hash: str) -> dict[str, Any] | None:
    """Return a previously stored assessment dict, or None on miss."""
    if not input_hash:
        return None

    with _lock:
        if input_hash in _memory_result_cache:
            return dict(_memory_result_cache[input_hash])

        if _current_mode != "sqlite":
            return None

        try:
            ensure_data_dir()
            with sqlite3.connect(APP_RESULT_CACHE_PATH) as conn:
                _ensure_result_table(conn)
                row = conn.execute(
                    "SELECT payload FROM assessment_results WHERE input_hash = ?",
                    (input_hash,),
                ).fetchone()
            if not row:
                return None
            data = json.loads(row[0])
            if isinstance(data, dict):
                _memory_result_cache[input_hash] = data
                return dict(data)
        except Exception:
            return None
    return None


def store_cached_assessment(input_hash: str, assessment: dict[str, Any]) -> None:
    """Persist a parsed assessment for identical future submissions."""
    if not input_hash or not isinstance(assessment, dict):
        return

    with _lock:
        _memory_result_cache[input_hash] = dict(assessment)

        if _current_mode != "sqlite":
            return

        try:
            ensure_data_dir()
            with sqlite3.connect(APP_RESULT_CACHE_PATH) as conn:
                _ensure_result_table(conn)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO assessment_results (input_hash, payload)
                    VALUES (?, ?)
                    """,
                    (input_hash, json.dumps(assessment, ensure_ascii=False)),
                )
                conn.commit()
        except Exception:
            # App-level cache is a performance aid; never break the main flow.
            return


def clear_memory_result_cache() -> None:
    """Clear the in-process result cache (useful in tests)."""
    with _lock:
        _memory_result_cache.clear()


def cache_comparison_table() -> str:
    """Markdown table explaining InMemory vs SQLite for the README / UI."""
    return (
        "| | InMemoryCache | SQLiteCache |\n"
        "|---|---|---|\n"
        "| Storage | RAM (memory) | File on disk (.db) |\n"
        "| Speed | Fastest | Fast, slightly slower |\n"
        "| Survives restart? | No | Yes |\n"
        "| Best for | One session | Reusing across sessions |\n"
    )
