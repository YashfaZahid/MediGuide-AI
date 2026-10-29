# -*- coding: utf-8 -*-
"""
MediGuide AI - Streamlit UI.

Educational symptom guidance assistant (not a medical device).
Run:  streamlit run app.py
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st

from src.cache_manager import (
    cache_comparison_table,
    enable_cache,
    get_cached_assessment,
    mode_from_label,
    store_cached_assessment,
)
from src.chains import MissingAPIKeyError, demo_messages, run_assessment, stream_narrative
from src.config import (
    APP_NAME,
    APP_TAGLINE,
    CACHE_MODE_OPTIONS,
    DISCLAIMER_FULL,
    DISCLAIMER_SHORT,
    DURATION_OPTIONS,
    EMERGENCY_BANNER,
    GENDER_OPTIONS,
    LANGUAGE_OPTIONS,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    SEVERITY_DEFAULT,
    SEVERITY_MAX,
    SEVERITY_MIN,
    SYMPTOM_OPTIONS,
    clear_api_key,
    has_api_key,
    looks_like_api_key,
    set_api_key,
)
from src.report import build_guidance_pdf
from src.utils import hash_inputs, urgency_streamlit_intent, validate_inputs

st.set_page_config(
    page_title=APP_NAME,
    page_icon=":material/health_and_safety:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
_STATE_DEFAULTS: dict[str, Any] = {
    "assessment": None,
    "normalized_inputs": None,
    "raw_model_text": "",
    "parse_note": "",
    "from_cache": False,
    "elapsed_seconds": None,
    "run_narrative": False,
    "workspace": "Intake",
    "session_history": [],
    "narrative_text": "",
    "api_authenticated": False,
}
for _key, _value in _STATE_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _value


def _reset_results() -> None:
    st.session_state.assessment = None
    st.session_state.normalized_inputs = None
    st.session_state.raw_model_text = ""
    st.session_state.parse_note = ""
    st.session_state.from_cache = False
    st.session_state.elapsed_seconds = None
    st.session_state.run_narrative = False
    st.session_state.narrative_text = ""
    st.session_state.workspace = "Intake"


def _render_login_page() -> None:
    """Gate: collect OpenAI API key before showing the main app."""
    st.html(
        """
<style>
section[data-testid="stSidebar"] { display: none !important; }
div[data-testid="stSidebarCollapsedControl"] { display: none !important; }
@keyframes mg-login-rise {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
div[class*="st-key-login_panel"] {
  animation: mg-login-rise 0.45s ease-out;
}
</style>
"""
    )
    _, center, _ = st.columns([1, 1.25, 1])
    with center:
        with st.container(border=True, key="login_panel"):
            _render_brand_header(compact=False)
            st.markdown(
                "Enter your **OpenAI API key** to open the educational "
                "symptom guidance workspace."
            )
            with st.form("api_key_login", clear_on_submit=False, border=False):
                api_key = st.text_input(
                    "OpenAI API key",
                    type="password",
                    placeholder="sk-...",
                    help=(
                        "Your key stays in this browser session only. "
                        "It is not written to disk or committed to git."
                    ),
                    autocomplete="current-password",
                )
                submitted = st.form_submit_button(
                    "Continue to app",
                    type="primary",
                    icon=":material/login:",
                    width="stretch",
                )
            if submitted:
                if not looks_like_api_key(api_key):
                    st.error(
                        "Enter a valid OpenAI API key (starts with sk-).",
                        icon=":material/key_off:",
                    )
                else:
                    set_api_key(api_key)
                    st.session_state.api_authenticated = True
                    st.rerun()
            st.caption(
                "Keys come from platform.openai.com. MediGuide never stores "
                "your key in the repository."
            )
            st.info(DISCLAIMER_SHORT, icon=":material/health_and_safety:")


def _render_brand_header(*, compact: bool = False) -> None:
    """
    Professional animated mark + Poppins wordmark.

    Uses full Roman Reverie palette with high-contrast text:
    Espresso / Olive / Burgundy / Ochre / Travertine.
    """
    size = 38 if compact else 52
    title_size = "1.15rem" if compact else "1.7rem"
    gap = "0.7rem" if compact else "0.85rem"
    # Sidebar: Travertine on Espresso. Main: Espresso on Travertine.
    title_color = "#F3EBDD" if compact else "#2F2826"
    accent_color = "#D9C79F" if compact else "#5C6640"
    tag_color = "#D9C79F" if compact else "#5A524C"
    html = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
@keyframes mg-pulse {{
  0%, 100% {{ box-shadow: 0 0 0 0 rgba(92, 102, 64, 0.45); }}
  70% {{ box-shadow: 0 0 0 10px rgba(92, 102, 64, 0); }}
}}
@keyframes mg-cross-fade {{
  0%, 100% {{ opacity: 0.95; }}
  50% {{ opacity: 1; }}
}}
.mg-brand {{
  display: flex;
  align-items: center;
  gap: {gap};
  margin: 0.1rem 0 0.4rem 0;
  font-family: Poppins, 'Segoe UI', sans-serif;
}}
.mg-mark {{
  width: {size}px;
  height: {size}px;
  flex: 0 0 auto;
  border-radius: 12px;
  /* Olive field + Ochre edge + Burgundy depth */
  background: linear-gradient(160deg, #6F7852 0%, #5C6640 52%, #782E3B 160%);
  border: 2px solid #B88343;
  display: grid;
  place-items: center;
  animation: mg-pulse 2.8s ease-out infinite;
}}
.mg-cross {{
  position: relative;
  width: {int(size * 0.42)}px;
  height: {int(size * 0.42)}px;
  animation: mg-cross-fade 3s ease-in-out infinite;
}}
.mg-cross::before,
.mg-cross::after {{
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  /* Travertine cross on olive - high contrast */
  background: #F3EBDD;
  border-radius: 2px;
  transform: translate(-50%, -50%);
}}
.mg-cross::before {{
  width: 28%;
  height: 100%;
}}
.mg-cross::after {{
  width: 100%;
  height: 28%;
}}
.mg-wordmark {{
  display: flex;
  flex-direction: column;
  gap: 0.12rem;
  min-width: 0;
}}
.mg-title {{
  margin: 0;
  font-family: Poppins, 'Segoe UI', sans-serif;
  font-size: {title_size};
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.15;
  color: {title_color};
}}
.mg-title span {{
  color: {accent_color};
  font-weight: 600;
}}
.mg-tag {{
  margin: 0;
  font-family: Poppins, 'Segoe UI', sans-serif;
  font-size: {'0.68rem' if compact else '0.78rem'};
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: {tag_color};
  font-weight: 500;
}}
.mg-swatches {{
  display: flex;
  gap: 0.28rem;
  margin-top: 0.15rem;
}}
.mg-swatches i {{
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: inline-block;
  border: 1px solid rgba(47, 40, 38, 0.25);
}}
</style>
<div class="mg-brand" role="banner" aria-label="MediGuide AI">
  <div class="mg-mark" aria-hidden="true"><div class="mg-cross"></div></div>
  <div class="mg-wordmark">
    <p class="mg-title">MediGuide <span>AI</span></p>
    <p class="mg-tag">Educational clinical guidance</p>
    <div class="mg-swatches" aria-hidden="true" title="Roman Reverie palette">
      <i style="background:#2F2826"></i>
      <i style="background:#5C6640"></i>
      <i style="background:#782E3B"></i>
      <i style="background:#B88343"></i>
      <i style="background:#D9C79F"></i>
    </div>
  </div>
</div>
"""
    st.html(html)


def _append_history(assessment: dict[str, Any], normalized: dict[str, Any]) -> None:
    """Bonus: keep a short in-session history of assessments."""
    entry = {
        "time": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        "urgency": str(assessment.get("urgency_level", "")).upper(),
        "symptoms": normalized.get("symptoms_text", ""),
        "severity": normalized.get("severity"),
        "summary": assessment.get("summary", ""),
    }
    history = list(st.session_state.session_history)
    history.insert(0, entry)
    st.session_state.session_history = history[:20]


def _show_urgency(urgency: str) -> None:
    intent = urgency_streamlit_intent(urgency)
    copy = {
        "success": (
            "Urgency: LOW",
            "Symptoms appear mild based on the information provided. This is not a diagnosis.",
        ),
        "info": (
            "Urgency: MEDIUM",
            "Consider contacting a healthcare professional for advice soon.",
        ),
        "warning": (
            "Urgency: HIGH",
            "Please arrange prompt medical review. Do not delay if symptoms worsen.",
        ),
        "error": ("Urgency: EMERGENCY", EMERGENCY_BANNER),
    }
    title, body = copy.get(intent, copy["info"])
    getattr(st, intent)(
        body,
        icon=":material/emergency:" if intent == "error" else ":material/monitor_heart:",
        title=title,
    )


def _bullet_list(items: list[Any], empty: str) -> None:
    if not items:
        st.caption(empty)
        return
    for index, item in enumerate(items, start=1):
        st.markdown(f"{index}. {item}")


def _render_results(assessment: dict[str, Any], normalized: dict[str, Any]) -> None:
    """Compact, tabbed results dashboard - no charts, all JSON fields shown."""
    urgency = str(assessment.get("urgency_level") or "MEDIUM").upper()
    conditions = assessment.get("possible_conditions") or []
    steps = list(assessment.get("recommended_next_steps") or [])
    questions = list(assessment.get("questions_for_doctor") or [])
    warnings = list(assessment.get("warning_signs") or [])
    summary_text = assessment.get("summary") or "No summary returned."

    st.markdown("### Assessment results")
    st.caption("Educational guidance only - not a confirmed diagnosis.")

    if urgency == "EMERGENCY":
        st.error(
            EMERGENCY_BANNER,
            icon=":material/emergency:",
            title="Seek emergency help now",
        )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Urgency", urgency, border=True, icon=":material/monitor_heart:")
    m2.metric(
        "Severity",
        f"{normalized.get('severity', '-')}/10",
        border=True,
        icon=":material/thermostat:",
    )
    m3.metric("Conditions", len(conditions), border=True, icon=":material/clinical_notes:")
    m4.metric("Warnings", len(warnings), border=True, icon=":material/warning:")

    _show_urgency(urgency)

    cache_label = "Cache hit" if st.session_state.from_cache else "Fresh run"
    timing = (
        f"{st.session_state.elapsed_seconds:.2f}s"
        if st.session_state.elapsed_seconds is not None
        else "-"
    )
    st.caption(
        f"{cache_label} | {timing} | Language: {normalized.get('language', 'N/A')}"
    )

    overview, conditions_tab, plan_tab, narrative_tab, debug_tab = st.tabs(
        [
            "Overview",
            "Conditions",
            "Action plan",
            "Narrative",
            "Debug",
        ]
    )

    with overview:
        left, right = st.columns((1.4, 1), gap="large")
        with left:
            st.markdown("#### AI summary")
            st.write(summary_text)
        with right:
            st.markdown("#### Patient context")
            st.markdown(
                f"**Symptoms:** {normalized.get('symptoms_text', 'N/A')}  \n"
                f"**Duration:** {normalized.get('duration', 'N/A')}  \n"
                f"**Age / gender:** {normalized.get('age', 'N/A')} / "
                f"{normalized.get('gender', 'N/A')}  \n"
                f"**Existing conditions:** {normalized.get('existing_conditions', 'N/A')}  \n"
                f"**Medications:** {normalized.get('medications', 'N/A')}"
            )
            if normalized.get("notes") and normalized.get("notes") != "None":
                st.markdown(f"**Notes:** {normalized.get('notes')}")

        st.divider()
        dl1, dl2 = st.columns(2)
        with dl1:
            # Bonus: PDF download
            try:
                pdf_bytes = build_guidance_pdf(assessment, normalized)
                st.download_button(
                    "Download PDF report",
                    data=pdf_bytes,
                    file_name="mediguide_guidance.pdf",
                    mime="application/pdf",
                    icon=":material/picture_as_pdf:",
                    width="stretch",
                )
            except Exception as exc:  # noqa: BLE001
                st.caption(f"PDF export unavailable ({exc}).")
        with dl2:
            payload = {
                "intake": normalized,
                "assessment": assessment,
            }
            st.download_button(
                "Download JSON",
                data=json.dumps(payload, indent=2, ensure_ascii=False),
                file_name="mediguide_assessment.json",
                mime="application/json",
                icon=":material/data_object:",
                width="stretch",
            )

    with conditions_tab:
        st.caption("Educational topics only - not a diagnosis.")
        if not conditions:
            st.info("No possible conditions were returned.", icon=":material/info:")
        else:
            rows = []
            for item in conditions:
                if isinstance(item, dict):
                    rows.append(
                        {
                            "Condition": str(item.get("name", "")).strip() or "Unnamed",
                            "Explanation": str(item.get("reason", "")).strip()
                            or "No explanation provided.",
                        }
                    )
                else:
                    rows.append(
                        {
                            "Condition": str(item),
                            "Explanation": "No explanation provided.",
                        }
                    )
            st.dataframe(
                pd.DataFrame(rows),
                width="stretch",
                hide_index=True,
                height="auto",
                alt="Possible conditions with explanations",
                column_config={
                    "Condition": st.column_config.TextColumn("Condition", width="medium"),
                    "Explanation": st.column_config.TextColumn(
                        "Explanation", width="large"
                    ),
                },
            )

    with plan_tab:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("#### Recommended next steps")
            _bullet_list(steps, "No next steps returned.")
        with c2:
            st.markdown("#### Questions for your doctor")
            _bullet_list(questions, "No clinician questions returned.")
        st.divider()
        st.markdown("#### Warning signs")
        if warnings:
            st.warning(
                "Seek urgent or emergency care if any of these appear or worsen.",
                icon=":material/warning:",
            )
            _bullet_list(warnings, "No warning signs returned.")
        else:
            st.info("No warning signs were returned.", icon=":material/info:")

    with narrative_tab:
        st.caption("Streamed guidance narrative (educational only).")
        if st.session_state.run_narrative:
            try:
                chunks = st.write_stream(
                    stream_narrative(normalized, assessment)
                )
                if isinstance(chunks, str):
                    st.session_state.narrative_text = chunks
                elif isinstance(chunks, list):
                    st.session_state.narrative_text = "".join(
                        str(c) for c in chunks if isinstance(c, str)
                    )
            except MissingAPIKeyError as exc:
                st.error(str(exc), icon=":material/key_off:")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Narrative streaming failed: {exc}", icon=":material/error:")
            finally:
                st.session_state.run_narrative = False
        else:
            if st.session_state.narrative_text:
                st.write(st.session_state.narrative_text)
            else:
                st.caption("No narrative yet. Use Replay to stream again.")
            if st.button("Replay narrative stream", icon=":material/play_arrow:"):
                st.session_state.run_narrative = True
                st.rerun()

    with debug_tab:
        if st.session_state.parse_note:
            st.caption(st.session_state.parse_note)
        st.code(
            st.session_state.raw_model_text
            or json.dumps(assessment, indent=2, ensure_ascii=False),
            language="json",
        )


# ---------------------------------------------------------------------------
# API key login gate
# ---------------------------------------------------------------------------
if not st.session_state.api_authenticated:
    _render_login_page()
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    _render_brand_header(compact=True)
    st.caption(APP_TAGLINE)
    st.info(DISCLAIMER_SHORT, icon=":material/info:")
    with st.expander("Full medical disclaimer"):
        st.write(DISCLAIMER_FULL)

    st.divider()
    st.markdown("### Model")
    st.text(f"{OPENAI_MODEL}  |  temp {OPENAI_TEMPERATURE}")
    if has_api_key():
        st.success("API key active", icon=":material/check_circle:")
    else:
        st.error("API key missing", icon=":material/key_off:")
    if st.button("Sign out", icon=":material/logout:", width="stretch"):
        clear_api_key()
        st.session_state.api_authenticated = False
        _reset_results()
        st.rerun()

    cache_label = st.selectbox("Cache mode", CACHE_MODE_OPTIONS, index=1)
    language = st.selectbox("Answer language", LANGUAGE_OPTIONS, index=0)

    with st.expander("Caching: InMemory vs SQLite"):
        st.markdown(cache_comparison_table())
        st.caption("Use Settings (menu) to switch light / dark appearance.")

    # Bonus: session analytics (compact, no charts)
    history = st.session_state.session_history
    if history:
        st.divider()
        st.markdown("### Session analytics")
        counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "EMERGENCY": 0}
        for row in history:
            key = str(row.get("urgency", "")).upper()
            if key in counts:
                counts[key] += 1
        a1, a2 = st.columns(2)
        a1.metric("Assessments", len(history))
        top = max(counts, key=counts.get)
        a2.metric("Most common", top if any(counts.values()) else "-")
        st.caption(
            " / ".join(f"{k}: {v}" for k, v in counts.items() if v)
            or "No urgency tallies yet."
        )
        with st.expander("Session history"):
            for row in history[:8]:
                st.markdown(
                    f"**{row['time']}** - {row['urgency']} - "
                    f"{row['symptoms'][:60]}"
                )

    with st.expander("LangChain message demo"):
        st.caption("SystemMessage + HumanMessage + AIMessage")
        if st.button("Run message demo", icon=":material/forum:"):
            if not has_api_key():
                st.warning("Add an API key first.")
            else:
                try:
                    with st.spinner("Calling the model..."):
                        msgs = demo_messages()
                    for msg in msgs:
                        st.markdown(f"**{msg.__class__.__name__}**")
                        st.write(getattr(msg, "content", str(msg)))
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Demo failed: {exc}")


# ---------------------------------------------------------------------------
# Main workspace (Intake vs Results - avoids stacking endless scroll)
# ---------------------------------------------------------------------------
_render_brand_header(compact=False)
st.info(DISCLAIMER_SHORT, icon=":material/health_and_safety:")

workspace_options = ["Intake"]
if st.session_state.assessment is not None:
    workspace_options.append("Results")

default_index = (
    workspace_options.index(st.session_state.workspace)
    if st.session_state.workspace in workspace_options
    else 0
)
workspace = st.segmented_control(
    "Workspace",
    options=workspace_options,
    default=workspace_options[default_index],
    label_visibility="collapsed",
)
if workspace:
    st.session_state.workspace = workspace

# ---- Intake ----
if st.session_state.workspace == "Intake" or st.session_state.assessment is None:
    st.markdown("### Patient intake")
    st.caption("Enter details, then generate educational guidance.")

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            age = st.text_input("Patient age", placeholder="e.g. 25")
        with c2:
            gender = st.selectbox("Gender", GENDER_OPTIONS)
        with c3:
            duration = st.selectbox("Duration of symptoms", DURATION_OPTIONS, index=1)

        symptoms = st.multiselect("Symptoms", SYMPTOM_OPTIONS)
        extra_symptoms = st.text_input(
            "Additional symptoms (optional)",
            placeholder="Comma-separated extras",
        )
        severity = st.slider(
            "Severity (1-10)", SEVERITY_MIN, SEVERITY_MAX, SEVERITY_DEFAULT
        )

        h1, h2 = st.columns(2)
        with h1:
            existing_conditions = st.text_area(
                "Existing medical conditions",
                placeholder="e.g. asthma, diabetes",
                height=80,
            )
        with h2:
            medications = st.text_area(
                "Current medications",
                placeholder="List medications",
                height=80,
            )
        notes = st.text_area(
            "Additional notes",
            placeholder="Anything else to consider",
            height=70,
        )

        b1, b2 = st.columns([3, 1], vertical_alignment="bottom")
        with b1:
            submitted = st.button(
                "Generate guidance",
                type="primary",
                icon=":material/stethoscope:",
                width="stretch",
            )
        with b2:
            clear_clicked = st.button(
                "Clear", icon=":material/delete:", width="stretch"
            )

    if clear_clicked:
        _reset_results()
        st.rerun()

    if submitted:
        ok, normalized, errors = validate_inputs(
            age=age,
            gender=gender,
            symptoms=symptoms,
            duration=duration,
            severity=severity,
            existing_conditions=existing_conditions,
            medications=medications,
            notes=notes,
            language=language,
            extra_symptoms=extra_symptoms,
        )
        if not ok:
            for err in errors:
                st.warning(err, icon=":material/warning:")
            st.stop()

        if not has_api_key():
            st.error(
                "Cannot call the model without an OpenAI API key. "
                "Sign out and enter your key again.",
                icon=":material/key_off:",
            )
            st.stop()

        cache_mode = mode_from_label(cache_label)
        cache_ok, cache_msg = enable_cache(cache_mode)
        if not cache_ok:
            st.info(cache_msg, icon=":material/info:")

        input_hash = hash_inputs(normalized)
        started = time.perf_counter()
        cached = get_cached_assessment(input_hash) if cache_mode != "off" else None

        if cached:
            assessment = cached
            raw = json.dumps(cached, indent=2, ensure_ascii=False)
            note = "Served from app-level result cache."
            from_cache = True
            assess_ok = True
        else:
            with st.spinner("Analyzing symptoms with MediGuide AI..."):
                try:
                    assess_ok, assessment, note, raw = run_assessment(normalized)
                except MissingAPIKeyError as exc:
                    st.error(str(exc), icon=":material/key_off:")
                    st.stop()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Assessment failed: {exc}", icon=":material/error:")
                    st.stop()
            from_cache = False
            if assess_ok:
                store_cached_assessment(input_hash, assessment)

        elapsed = time.perf_counter() - started
        st.session_state.elapsed_seconds = elapsed
        st.session_state.raw_model_text = raw
        st.session_state.parse_note = note
        st.session_state.from_cache = from_cache

        if not assess_ok:
            st.error(
                "The model response could not be parsed as valid JSON.",
                icon=":material/error:",
            )
            with st.expander("Raw model output"):
                st.code(raw or "(empty)", language="json")
            st.stop()

        st.session_state.assessment = assessment
        st.session_state.normalized_inputs = normalized
        st.session_state.run_narrative = True
        st.session_state.narrative_text = ""
        st.session_state.workspace = "Results"
        _append_history(assessment, normalized)
        st.rerun()

# ---- Results ----
elif st.session_state.assessment and st.session_state.normalized_inputs:
    with st.container(border=True):
        st.markdown(DISCLAIMER_SHORT)
    _render_results(st.session_state.assessment, st.session_state.normalized_inputs)

st.caption(
    f"{APP_NAME} is for education and coursework only. "
    "It is not a medical device and must not be used for real diagnosis or treatment."
)
