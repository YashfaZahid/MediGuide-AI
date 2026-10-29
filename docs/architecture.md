# MediGuide AI ? Architecture & Implementation Plan

Educational Streamlit + LangChain prototype for preliminary symptom guidance. **Not a medical device.** Never claim a confirmed diagnosis. Every screen must show a clear disclaimer and direct users to licensed professionals / emergency care when urgent.

Source of truth for mandatory requirements: [`Medical_AI_Assignment.pdf`](./Medical_AI_Assignment.pdf).

---

## 1. Goals & Constraints

| Priority | Meaning |
|---|---|
| Assignment fidelity | Satisfy every mandatory concept, widget, schema, and test scenario |
| Safety | Disclaimers unavoidable; EMERGENCY ? seek help now; no confirmed diagnosis |
| Modularity | Backend in `src/`, UI in `app.py`, beginner-friendly comments |
| Reliability | Bad JSON / API errors never crash the app |
| Portfolio polish | Clean healthcare SaaS look without extra frameworks |
| Simplicity | No RAG vector DB, no agents, no Docker unless later as bonus |

**Out of scope for v1:** conversation memory, PDF export, voice input, analytics, Docker (all optional bonuses).

---

## 2. Technology Choices

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.10+ | Assignment requirement |
| UI | Streamlit | Required; `streamlit run app.py` |
| LLM | OpenAI via `ChatOpenAI` (`gpt-4o-mini` default) | Required + low cost |
| Framework | `langchain-core`, `langchain-openai`, `langchain-community`, `langchain` + **`langchain-classic`** | Assignment packages + classic for `LLMChain` on LangChain 1.x |
| Secrets | `python-dotenv` + `.env` | Never hard-code keys |
| Cache | `InMemoryCache` + `SQLiteCache` via `set_llm_cache` | Both required |

### Recommended pinned stack (compatible with this machine?s LangChain 1.x)

```text
streamlit>=1.28
python-dotenv>=1.0
openai>=1.40
langchain>=1.0,<2.0
langchain-core>=1.0,<2.0
langchain-openai>=1.0,<2.0
langchain-community>=0.3,<0.5
langchain-classic>=1.0,<2.0
```

Use a project `.venv`. Keep `requirements.txt` exact after first successful install (`pip freeze` of these packages only, not the whole env).

---

## 3. Dependency Compatibility Risks (LangChain)

These are the highest-risk items for this assignment.

### 3.1 `LLMChain` location (blocking)

- On **LangChain 1.x**, `from langchain.chains import LLMChain` **fails** (`ModuleNotFoundError`).
- `LLMChain` lives in **`langchain-classic`**: `from langchain_classic.chains import LLMChain`.
- It is deprecated in favor of LCEL (`prompt | model`), but the assignment **requires** `LLMChain` ? use classic, document why, do not replace with LCEL for the graded path.
- Alternative (not preferred here): pin entire stack to `langchain 0.3.x` so tutorial-style imports work; conflicts with already-installed 1.x and future breakage.

### 3.2 Package split & version alignment

- `ChatOpenAI` ? `langchain_openai`
- Messages / prompts ? `langchain_core` (or re-exports)
- Caches ? `langchain_community.cache` (`InMemoryCache`, `SQLiteCache`)
- Global cache hook ? `langchain_core.globals.set_llm_cache`
- Keep major versions aligned; mixing 0.2 / 0.3 / 1.x randomly causes import and type errors.

### 3.3 `langchain-community` sunset

- Community emits a deprecation/sunset warning; assignment still lists it.
- Keep it for `SQLiteCache` / `InMemoryCache` unless/until caches move to a stable package. Prefer community imports for the graded demo.

### 3.4 LLM cache vs `ChatOpenAI`

- Historically, `set_llm_cache` was reliable for completion LLMs, less so for chat models.
- **Mitigation (required for scenario 4):** still register `InMemoryCache` / `SQLiteCache` with `set_llm_cache` as assigned, **and** add a small app-level result cache in `cache_manager.py` keyed by a normalized hash of form inputs ? parsed JSON. That guarantees ?same form twice is faster? even if the provider path misses the LangChain LLM cache.
- Document both layers and the InMemory vs SQLite difference in README.

### 3.5 Streaming + caching interaction

- Streaming (`.stream()`) and cache hits can behave differently (cache may return full text at once).
- Plan: structured assessment via `LLMChain` (cacheable path); narrative via `.stream()` into `st.write_stream`. If a narrative cache hit returns a full string, yield it as one chunk so the UI still works.

### 3.6 Prompt / message APIs

- Prefer `langchain_core.prompts` (`PromptTemplate`, `ChatPromptTemplate`) and `langchain_core.messages` (`SystemMessage`, `HumanMessage`, `AIMessage`).
- Avoid old `langchain.prompts` / `langchain.schema` imports that break across versions.

### 3.7 JSON mode reliability

- Instruct ?JSON only? in the system prompt; optionally set model `temperature` low (e.g. 0?0.2) for the assessment chain.
- Do **not** depend solely on provider JSON mode; always strip \`\`\`json fences and `try/except` around `json.loads`.

---

## 4. Folder Structure

```text
medical_ai_assistant/          # repo root (this project)
??? app.py                     # Streamlit UI only
??? requirements.txt
??? .env.example               # OPENAI_API_KEY=...
??? .gitignore                 # .env, __pycache__, *.db, .venv
??? README.md                  # setup, run, caching explanation, safety
??? src/
?   ??? __init__.py
?   ??? config.py              # env, model defaults, form option lists
?   ??? prompts.py             # system rules, JSON schema, PromptTemplate, ChatPromptTemplate
?   ??? chains.py              # ChatOpenAI, LLMChain, message demo, stream_narrative
?   ??? cache_manager.py       # InMemory + SQLite + optional app-level result cache
?   ??? utils.py               # safe JSON parse, urgency colors, validation helpers
??? docs/
    ??? Medical_AI_Assignment.pdf
    ??? architecture.md        # this file
```

No nested UI packages. No separate FastAPI. Keep one entrypoint.

---

## 5. Module Responsibilities

| Module | Responsibility | Does not do |
|---|---|---|
| `config.py` | Load `.env`; expose `OPENAI_API_KEY`, model name, temperature, form options (genders, durations, severities, languages, symptom list), disclaimer text constants | No LLM calls |
| `prompts.py` | Safety system text; exact JSON schema string; `PromptTemplate` (single-string); `ChatPromptTemplate` (system+human); narrative chat template | No Streamlit, no API |
| `chains.py` | Build `ChatOpenAI`; build reusable `LLMChain` for assessment; `demo_messages()` showing System/Human/AIMessage; `run_assessment(inputs)`; `stream_narrative(llm, inputs)` generator | No UI widgets |
| `cache_manager.py` | `enable_cache(mode: off\|memory\|sqlite)`; path for SQLite `.db`; explain helpers; app-level get/set for identical submissions | No prompts |
| `utils.py` | `validate_inputs`; `strip_code_fences`; `safe_parse_assessment_json`; urgency ? Streamlit intent mapping; input hash for cache key | No LLM |
| `app.py` | Sidebar, form, validation messages, call src APIs, render dashboard, stream narrative, disclaimers | Minimal business logic |

---

## 6. Data Flow

```text
User fills form (app.py)
        ?
        ?
validate_inputs (utils) ??fail??? st.warning / stop (no API call)
        ? ok
        ?
build prompt variables dict (age, gender, symptoms, duration, severity,
                            conditions, medications, notes, language)
        ?
        ?
cache_manager.enable_cache(selected mode)
        ?
        ?
app-level cache lookup by input hash ??hit??? reuse parsed JSON (fast path)
        ? miss
        ?
LLMChain.invoke / predict (ChatOpenAI + ChatPromptTemplate or PromptTemplate)
        ?
        ?
raw model text ? strip fences ? safe_parse_assessment_json
        ? fail ? friendly error + raw debug expander; stop
        ? ok  ? store in app-level cache
        ?
render results dashboard (metrics, urgency color, expanders, tabs/columns)
        ?
        ?
stream_narrative ? st.write_stream (live typing effect)
```

Assessment JSON and narrative are **two calls** (clear separation for grading streaming vs structured output). Keep both temperature-controlled and safety-bound by the same system rules.

---

## 7. Required LangChain Concepts ? Where They Live

| Concept | Implementation |
|---|---|
| `ChatOpenAI` | `chains.py` factory |
| System / Human / AI messages | `chains.demo_messages()` + templates in `prompts.py`; show AIMessage in a small ?How messages work? expander in UI |
| `PromptTemplate` | `prompts.py` ? single-string assessment template with all patient variables |
| `ChatPromptTemplate` | `prompts.py` ? System (safety + JSON schema) + Human (patient data); used by primary `LLMChain` |
| Structured JSON | Schema in prompts; parse in `utils.safe_parse_assessment_json` |
| `LLMChain` | `chains.build_assessment_chain()` using **langchain-classic** |
| Streaming | `chains.stream_narrative` + `st.write_stream` |
| Caching | Both `InMemoryCache` and `SQLiteCache`; sidebar toggle; README comparison table |

### Exact JSON schema (mandatory)

```json
{
  "summary": "",
  "possible_conditions": [{ "name": "", "reason": "" }],
  "urgency_level": "",
  "recommended_next_steps": [],
  "questions_for_doctor": [],
  "warning_signs": []
}
```

`urgency_level` values used in UI: `LOW` | `MEDIUM` | `HIGH` | `EMERGENCY` (normalize case on parse).

---

## 8. UI / UX Design (Healthcare SaaS, Streamlit-only)

### Visual direction

- Calm clinical SaaS: soft blue?teal primary, white/light gray surfaces, clear red only for EMERGENCY / errors.
- Custom `.streamlit/config.toml` theme (primary color, background, font) ? no React, no custom component server.
- Brand: **MediGuide AI** as the strongest first-screen label; subtitle: educational symptom guidance assistant.
- Persistent disclaimer banner (sidebar + main + results). Tone: calm, direct, non-alarmist except EMERGENCY.

### Layout

1. **Sidebar:** app name, short description, medical disclaimer, model name/temperature, cache mode (`Off` / `In-memory` / `SQLite`), answer language.
2. **Main ? Patient form:** compact sections (Demographics ? Symptoms ? History ? Notes) using required widgets:
   - `st.text_input` (age)
   - `st.selectbox` (gender, duration, language if not only in sidebar)
   - `st.multiselect` + optional `st.text_input`/`st.text_area` (extra symptoms)
   - `st.slider` (severity 1?10)
   - `st.text_area` (conditions, medications, notes)
   - `st.button` (Generate guidance)
3. **Results dashboard:**
   - Urgency as colored `st.success` / `st.info` / `st.warning` / `st.error` + `st.metric`
   - Tabs or columns: Summary | Possible conditions (education only) | Next steps | Doctor questions | Warning signs
   - `st.expander` for raw JSON / debug
   - Streaming narrative via `st.write_stream`
4. Empty symptoms ? warn and **do not** call the API (scenario 5).

### Safety copy (always visible)

> MediGuide AI is an educational prototype only. It is **not** a doctor, diagnosis, or emergency service. Do not rely on it for treatment decisions. If you have severe or worsening symptoms, seek emergency care immediately.

For `EMERGENCY` results, force a top `st.error` instructing immediate emergency help.

---

## 9. Medical Safety Rules (encode in system prompt + UI)

1. Label as educational AI, not a clinician.
2. Never output a confirmed diagnosis; phrase conditions as ?possible topics to discuss with a professional.?
3. Prefer conservative urgency when uncertain.
4. Always include warning signs and ?see a professional? next steps.
5. EMERGENCY / severe chest pain / breathing difficulty ? explicit emergency-care instruction.
6. Disclaimers on sidebar, form view, and results view.

---

## 10. Error Handling Strategy

| Failure | Behavior |
|---|---|
| Missing API key | Block run with clear setup message pointing to `.env.example` |
| Empty / invalid age or no symptoms | `st.warning`; no LLM call |
| Network / OpenAI error | `st.error` with short message; no stack trace in main view |
| Invalid JSON | Friendly message + expander with raw model text |
| Partial schema | Fill missing keys with safe defaults; flag incomplete parse in expander |
| Cache DB permission issues | Fall back to in-memory or off; show `st.info` |

---

## 11. Testing Strategy

### Manual scenarios (assignment ?18) ? must pass before submission

| # | Input | Expected |
|---|---|---|
| 1 | Age 25, runny nose + sore throat, 1?3 days, severity 2 | Urgency LOW; calm monitoring |
| 2 | Age 40, fever + cough, 4?7 days, severity 6 | MEDIUM/HIGH; see a professional |
| 3 | Severe chest pain + shortness of breath | HIGH/EMERGENCY; immediate help |
| 4 | Same form twice, cache on | Second run visibly faster; same result |
| 5 | Empty symptoms | Warn; no API call |
| 6 | Language = Urdu | Narrative/guidance in Urdu |

### Lightweight automated checks (optional but useful)

- `tests/test_utils.py`: fence stripping, valid JSON, malformed JSON, urgency normalization, empty-symptom validation.
- No live OpenAI calls in CI; mock `ChatOpenAI` if adding chain tests later.

### Dev checklist per phase

Each phase below ends with a **Done when** gate so work can stop and resume safely.

---

## 12. Streamlit Deployment Plan

### Local

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then set OPENAI_API_KEY
streamlit run app.py
```

### Sharing / demo

1. **Streamlit Community Cloud:** push public GitHub repo; add `OPENAI_API_KEY` in app secrets (not in git); set main file `app.py`.
2. Keep SQLite cache path writable (`./data/langchain_cache.db`); create `data/` at runtime; gitignore `*.db`.
3. Screen recording for submission: show form ? streaming narrative ? urgency dashboard ? second identical submit with cache.

### Security

- `.gitignore`: `.env`, `.venv/`, `__pycache__/`, `*.db`, `.streamlit/secrets.toml`
- Ship `.env.example` only
- README: ?education only? + caching table (InMemory vs SQLite)

---

## 13. Phased Implementation Plan

Implement and test one phase at a time. Do not start the next phase until the gate passes.

### Phase 0 ? Project skeleton (no LLM)

**Build:** folder structure, `requirements.txt`, `.env.example`, `.gitignore`, empty `src` modules with docstrings, stub `README`, copy assignment PDF under `docs/`.

**Test:** `pip install -r requirements.txt` in fresh venv; `python -c "import src"`.

**Done when:** repo matches ?4 structure; installs cleanly.

---

### Phase 1 ? Config + utils (no LLM)

**Build:** `config.py` (options + disclaimer constants + dotenv load); `utils.py` (validation, fence strip, safe JSON parse, urgency helpers, input hash).

**Test:** unit-style manual/script checks for good JSON, fenced JSON, bad JSON, empty symptoms.

**Done when:** invalid JSON never raises to caller; empty symptoms detected.

---

### Phase 2 ? Prompts (no API key required)

**Build:** `prompts.py` with safety system text, JSON schema instruction, `PromptTemplate`, `ChatPromptTemplate`, narrative template; variables cover all form fields + language.

**Test:** `.format` / `.format_messages` with sample dict; print messages; confirm no missing variables.

**Done when:** both template types format successfully; system text forbids confirmed diagnosis.

---

### Phase 3 ? Cache manager

**Build:** `cache_manager.py` ? switch Off / InMemory / SQLite via `set_llm_cache`; app-level dict/SQLite helper for parsed results; create `data/` for DB file.

**Test:** enable each mode without crash; write/read app-level cache by hash.

**Done when:** toggling modes works; SQLite file created on disk; README draft table exists.

---

### Phase 4 ? Chains + OpenAI integration

**Build:** `chains.py` ? `ChatOpenAI`; `LLMChain` from `langchain_classic`; `run_assessment`; `demo_messages`; `stream_narrative`.

**Test:** one CLI/script call with real key for a mild symptom sample; parse JSON; stream chunks to console.

**Done when:** chain returns parseable JSON; streaming yields text; message demo returns an `AIMessage`.

---

### Phase 5 ? Streamlit UI shell

**Build:** `app.py` sidebar + form using **all** required widgets; disclaimers; validation-only submit path; theme via `.streamlit/config.toml`.

**Test:** scenarios 5 (empty symptoms); UI loads with `streamlit run app.py` without key until submit.

**Done when:** form collects every required field; empty symptoms blocked; disclaimer visible sidebar + main.

---

### Phase 6 ? Wire assessment + results dashboard

**Build:** connect form ? cache ? chain ? parse ? dashboard (`st.metric`, warning/info/error/success, expander, tabs/columns).

**Test:** scenarios 1?3; EMERGENCY styling; raw JSON expander on failure.

**Done when:** dashboard shows all seven output areas; bad JSON handled; urgency colors correct.

---

### Phase 7 ? Streaming narrative + cache demo

**Build:** `st.write_stream(stream_narrative(...))`; cache mode in sidebar; timing note or spinner so scenario 4 is obvious.

**Test:** scenarios 4 and 6 (Urdu); second submit faster with cache on.

**Done when:** live typing effect works; cache toggle demonstrates both backends; Urdu output returns.

---

### Phase 8 ? Hardening + submission pack

**Build:** polish copy, comments, README (setup, run, caching explanation, safety), verify rubric coverage, short demo recording checklist.

**Test:** full ?18 matrix; fresh clone path (venv ? install ? `.env` ? run).

**Done when:** all mandatory rubric rows demonstrable; repo safe to share (no secrets).

---

## 14. Rubric Coverage Map

| Criterion | Phase / location |
|---|---|
| Streamlit UI/UX (15) | 5?7, theme + dashboard |
| ChatOpenAI (10) | 4 `chains.py` |
| PromptTemplate (10) | 2 `prompts.py` |
| ChatPromptTemplate + messages (10) | 2?4 |
| LLMChain (10) | 4 via `langchain-classic` |
| Structured JSON (10) | 2 + 1 + 6 |
| Streaming (10) | 4 + 7 |
| Caching (10) | 3 + 7 + README |
| Code quality / docs (10) | 0 + 8 |
| Testing / creativity (5) | ?18 + light utils tests + polished safety UI |

---

## 15. Implementation Principles (keep complexity down)

1. One assessment chain, one narrative stream ? no agents, tools, or vector RAG.
2. Prefer explicit functions over classes except where LangChain requires objects.
3. Comments explain *why* (safety, cache, parse), not obvious syntax.
4. Portfolio polish = typography, spacing, color, and trust copy ? not extra libraries.
5. If a LangChain import breaks after an upgrade, fix imports / pins first; do not rewrite the assignment architecture.

---

## 16. Next Action

Phases 0-8 are implemented. Unit tests pass (see `docs/implementation_report.md`).

**Remaining for submission:** add a real `OPENAI_API_KEY` in `.env`, manually verify assignment scenarios 1-6, record a short demo, push to GitHub.

### Implementation note (no structural change)

JSON schema braces inside `PromptTemplate` / `ChatPromptTemplate` must be escaped as `{{` / `}}` or LangChain 1.x rejects the template. Handled in `src/prompts.py`.
