"""Tests for cache_manager - no live OpenAI calls."""

from __future__ import annotations

from pathlib import Path

from src import cache_manager as cm
from src.config import APP_RESULT_CACHE_PATH, SQLITE_CACHE_PATH


class TestEnableCache:
    def setup_method(self):
        cm.clear_memory_result_cache()
        cm.enable_cache("off")

    def test_enable_off(self):
        ok, msg = cm.enable_cache("off")
        assert ok is True
        assert cm.get_current_mode() == "off"
        assert "disabled" in msg.lower()

    def test_enable_memory(self):
        ok, msg = cm.enable_cache("memory")
        assert ok is True
        assert cm.get_current_mode() == "memory"
        assert "InMemory" in msg or "memory" in msg.lower()

    def test_enable_sqlite_creates_db(self):
        ok, msg = cm.enable_cache("sqlite")
        assert ok is True
        assert cm.get_current_mode() == "sqlite"
        assert SQLITE_CACHE_PATH.exists() or "SQLite" in msg

    def test_label_mapping(self):
        assert cm.mode_from_label("In-memory") == "memory"
        assert cm.mode_from_label("SQLite") == "sqlite"
        assert cm.mode_from_label("Off") == "off"


class TestAppResultCache:
    def setup_method(self):
        cm.clear_memory_result_cache()
        cm.enable_cache("memory")

    def test_memory_roundtrip(self):
        payload = {
            "summary": "test",
            "urgency_level": "LOW",
            "possible_conditions": [],
            "recommended_next_steps": [],
            "questions_for_doctor": [],
            "warning_signs": [],
        }
        cm.store_cached_assessment("hash-abc", payload)
        got = cm.get_cached_assessment("hash-abc")
        assert got is not None
        assert got["summary"] == "test"
        assert got["urgency_level"] == "LOW"

    def test_miss_returns_none(self):
        assert cm.get_cached_assessment("missing-key-xyz") is None

    def test_sqlite_result_roundtrip(self, tmp_path: Path, monkeypatch):
        db_path = tmp_path / "result_cache.db"
        monkeypatch.setattr(cm, "APP_RESULT_CACHE_PATH", db_path)
        # Also keep enable_cache sqlite path isolated if needed.
        monkeypatch.setattr(
            "src.cache_manager.APP_RESULT_CACHE_PATH",
            db_path,
        )
        cm.enable_cache("sqlite")
        payload = {"summary": "sqlite", "urgency_level": "MEDIUM"}
        cm.store_cached_assessment("hash-sql", payload)
        cm.clear_memory_result_cache()
        got = cm.get_cached_assessment("hash-sql")
        assert got is not None
        assert got["summary"] == "sqlite"

    def test_comparison_table_mentions_both(self):
        table = cm.cache_comparison_table()
        assert "InMemoryCache" in table
        assert "SQLiteCache" in table
