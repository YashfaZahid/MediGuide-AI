# MediGuide AI - Implementation Report

Living document. Updated after each implementation phase.
Distinguish **completed**, **pending**, and **unverified**.

---

## Status overview

| Phase | Scope | Status |
|---|---|---|
| 0 | Project skeleton, requirements, stubs | **Completed** |
| 1 | `config.py` + `utils.py` + tests | **Completed** |
| 2 | `prompts.py` | **Completed** |
| 3 | `cache_manager.py` | **Completed** |
| 4 | `chains.py` | **Completed** (unit-tested with mocks; live OpenAI **unverified**) |
| 5 | Streamlit UI shell + theme | **Completed** |
| 6 | Assessment wiring + results dashboard | **Completed** |
| 7 | Streaming + cache demo UX | **Completed** |
| 8 | README + smoke tests + docs sync | **Completed** |
| Live API scenarios 1-4, 6 | Manual with real key | **Unverified** |

---

## Phase 0 - Project skeleton

### Completed
- Folder structure: `src/`, `tests/`, `data/`, `docs/`, `.streamlit/`
- `requirements.txt` (LangChain 1.x + `langchain-classic` for `LLMChain`)
- `.env.example`, `.gitignore`, stub `README.md`, stub `app.py`
- `src/__init__.py`, `pytest.ini`
- Assignment PDF in `docs/Medical_AI_Assignment.pdf`

### Key decisions
- Pin LangChain 1.x and add `langchain-classic` so the graded `LLMChain` API works.
- Keep UI entry at repo-root `app.py` per assignment.

### Testing
- `import src` succeeded.
- Project `.venv` install completed successfully (`langchain` 1.4.7, `langchain-classic` 1.0.8, `streamlit` 1.66.1, etc.).

### Files changed
- `requirements.txt`, `.env.example`, `.gitignore`, `README.md`, `app.py`, `pytest.ini`
- `src/__init__.py`, placeholder stubs later replaced
- `data/.gitkeep`, `docs/implementation_report.md`

---

## Phase 1 - Config + utils

### Completed
- `src/config.py`: dotenv loading, model settings, form option lists, disclaimer constants, `has_api_key()`, `ensure_data_dir()`
- `src/utils.py`: fence stripping, safe JSON parse, urgency normalization, input validation (empty symptoms blocked), input hashing
- `tests/test_utils.py`

### Key decisions
- Validation returns `(ok, data, errors)` instead of raising, so Streamlit can show warnings without crashing.
- Partial JSON schemas are filled with safe defaults and a note, rather than hard-failing.

### Testing (run)
```text
python -m pytest tests/test_utils.py -q
# 17 passed
```

### Files changed
- `src/config.py`, `src/utils.py`, `tests/test_utils.py`, `tests/__init__.py`

---

## Phase 2 - Prompts

### Completed
- `src/prompts.py`: safety system rules, JSON schema, `PromptTemplate`, `ChatPromptTemplate` (assessment), narrative `ChatPromptTemplate`, input builders
- `tests/test_prompts.py`

### Key decisions / fix
- Literal `{` `}` in the JSON schema must be escaped as `{{` `}}` inside LangChain templates; otherwise PromptTemplate validation fails with "Invalid format specifier / nested replacement fields".
- No architecture change: same modules and data flow as `docs/architecture.md`.

### Testing (run)
```text
python -m pytest tests/test_prompts.py -q
# included in full suite below
```

### Files changed
- `src/prompts.py`, `tests/test_prompts.py`

---

## Phase 3 - Cache manager

### Completed
- `src/cache_manager.py`: `enable_cache(off|memory|sqlite)` via `set_llm_cache`, InMemoryCache + SQLiteCache, app-level result cache (memory + SQLite table), comparison table helper
- `tests/test_cache_manager.py`

### Key decisions
- Dual-layer caching as planned: LangChain global cache for assignment compliance + hashed result cache for reliable "second submit is faster" demos with ChatOpenAI.

### Testing (run)
Covered by full suite (enable off/memory/sqlite + result roundtrip).

### Files changed
- `src/cache_manager.py`, `tests/test_cache_manager.py`

### Known warnings
- `langchain-community` sunset DeprecationWarning on import (expected; still required by assignment for caches).

---

## Phase 4 - Chains

### Completed
- `src/chains.py`: `ChatOpenAI` factory, `LLMChain` from `langchain_classic`, `run_assessment`, `demo_messages` (System/Human/AI), `stream_narrative`
- `tests/test_chains.py` (FakeListChatModel + mocks; no live API)

### Key decisions
- Import `LLMChain` from `langchain_classic.chains` (confirmed required on LangChain 1.x).
- Assessment and narrative remain separate calls for graded streaming vs structured JSON.
- Deprecation warning for `LLMChain` is accepted; assignment mandates it.

### Testing (run)
```text
python -m pytest tests/ -q
# 40 passed
```

### Unverified
- Live OpenAI assessment + streaming (needs a real `OPENAI_API_KEY` in `.env`). Not claimed as passing.

### Files changed
- `src/chains.py`, `tests/test_chains.py`

---

## Full backend test result (Phases 0-4)

| Command | Result |
|---|---|
| `python -m pytest tests/ -q` | **40 passed** |

Warnings observed (non-blocking): pytest/anyio CallSpec rename; langchain-community sunset; LLMChain deprecation.

---

## Phase 5 - Streamlit UI shell + theme

### Completed
- `.streamlit/config.toml` healthcare SaaS theme: teal primary `#0F766E`, navy sidebar `#0B1F33`, warm-white background `#F7F5F2`
- `app.py` sidebar (name, description, disclaimer, model config, cache mode, language)
- Main form with required widgets: `text_input`, `text_area`, `selectbox`, `multiselect`, `slider`, `button`
- Disclaimers on sidebar and main

### Files changed
- `app.py`, `.streamlit/config.toml`

---

## Phase 6 - Assessment + dashboard

### Completed
- Validate inputs before API (empty symptoms -> warning, no call)
- Wire `enable_cache` -> app cache / `run_assessment` -> safe parse
- Results dashboard: metrics, urgency callouts, tabs (summary / conditions / steps / questions / warnings), raw JSON expander
- EMERGENCY banner via `st.error`

### Files changed
- `app.py`

---

## Phase 7 - Streaming + cache demo

### Completed
- `st.write_stream(stream_narrative(...))` after assessment
- Cache hit timing shown in success message + metric delta
- Sidebar InMemory vs SQLite comparison expander
- Optional LangChain message demo expander

### Files changed
- `app.py`

---

## Phase 8 - Docs + smoke tests

### Completed
- README setup, caching table, layout, Cloud deploy notes
- `tests/test_app_smoke.py` (UTF-8 parse, theme file, backend imports)
- This report updated

### Testing (run)
```text
.venv\Scripts\python.exe -m pytest tests/ -q
# 43 passed
```

### UI polish (results dashboard redesign)
- Compact Intake vs Results workspace (no endless stacked scroll).
- Removed irrelevant charts; tabbed results (Overview / Conditions / Action plan / Narrative / Debug).
- Theme: Roman Reverie palette (Espresso / Olive / Burgundy / Ochre / Travertine) with
  Cormorant Garamond, light+dark variants, animated MG crest + wordmark in `app.py`.
- Bonuses: session history + analytics tallies, PDF download (`src/report.py`), Dockerfile.
- Coverage matrix: `docs/assignment_coverage.md`.

### Unverified
- Live OpenAI scenarios 1-4 and 6 (requires real `OPENAI_API_KEY` in `.env`)

### Pending / follow-up
| Item | Notes |
|---|---|
| Live API smoke test | Copy `.env.example` -> `.env`, set key, exercise scenarios 1-6 |
| Demo recording | Screen capture for submission |

---

## Architecture drift

None. Implementation follows `docs/architecture.md`. Minor implementation note (JSON brace escaping in prompts) documented above; folder structure and module responsibilities unchanged.
