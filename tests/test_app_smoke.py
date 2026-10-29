"""Smoke tests that the Streamlit entrypoint imports cleanly."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_app_py_parses_as_utf8():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert "st.button" in source
    assert "st.write_stream" in source
    assert "Generate guidance" in source
    assert "_render_brand_header" in source
    assert "mg-mark" in source
    assert "mg-cross" in source


def test_config_toml_exists():
    path = ROOT / ".streamlit" / "config.toml"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "primaryColor" in text
    # Roman Reverie palette + Poppins
    assert "#5C6640" in text
    assert "#782E3B" in text
    assert "#B88343" in text
    assert "#D9C79F" in text
    assert "#2F2826" in text
    assert "Poppins" in text


def test_backend_exports_for_ui():
    from src import cache_manager, chains, config, prompts, utils

    assert config.APP_NAME
    assert callable(utils.validate_inputs)
    assert callable(chains.run_assessment)
    assert callable(cache_manager.enable_cache)
    assert prompts.ASSESSMENT_CHAT_TEMPLATE is not None
