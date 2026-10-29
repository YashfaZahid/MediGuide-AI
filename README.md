# MediGuide AI

Educational Streamlit + LangChain prototype for preliminary symptom guidance.

> **Not a medical device.** This app does **not** provide diagnosis or treatment.
> Always consult a licensed healthcare professional. Seek emergency care for
> severe or worsening symptoms.

## Features

- Patient form (age, gender, symptoms, duration, severity, history, notes, language)
- LangChain `ChatOpenAI` + `LLMChain` structured JSON assessment
- `PromptTemplate` and `ChatPromptTemplate` with System / Human / AI messages
- Safe JSON parsing (never crashes on bad output)
- Live narrative streaming via `st.write_stream`
- Switchable **InMemoryCache** and **SQLiteCache**, plus app-level result cache
- Safety disclaimers on sidebar, main view, and results
- Compact **Intake / Results** workspace (navy, teal, warm-white theme; light/dark via Settings)
- Bonus: session history + urgency tallies, PDF report download, Docker image

## Setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...
streamlit run app.py
```

Open the Local URL shown in the terminal (usually http://localhost:8501).

## Caching (InMemory vs SQLite)

| | InMemoryCache | SQLiteCache |
|---|---|---|
| Storage | RAM | File on disk (`.db`) |
| Speed | Fastest | Fast, slightly slower |
| Survives restart? | No | Yes |
| Best for | One session | Reusing across sessions |

Register a cache with LangChain's `set_llm_cache(...)`. The sidebar toggles
**Off / In-memory / SQLite**. The app also stores parsed assessments by input
hash so submitting the same form twice is visibly faster (assignment scenario 4).

## Project layout

```text
app.py                 # Streamlit UI
src/config.py          # Settings + form options + disclaimers
src/prompts.py         # PromptTemplate + ChatPromptTemplate
src/chains.py          # ChatOpenAI, LLMChain, streaming
src/cache_manager.py   # InMemory + SQLite + result cache
src/utils.py           # Validation + safe JSON parse
docs/                  # Assignment PDF, architecture, implementation report
tests/                 # Automated unit tests (no live API)
```

## Tests

```bash
.venv\Scripts\python.exe -m pytest tests/ -q
```

## Deployment (Streamlit Community Cloud)

1. Push this repo to GitHub (do not commit `.env`).
2. Create an app on share.streamlit.io with main file `app.py`.
3. Add secret `OPENAI_API_KEY` in the Cloud app settings.
4. Ensure `data/` is writable for SQLite cache files.

## Docs

- `docs/architecture.md` - design and phased plan
- `docs/implementation_report.md` - build progress and test results
- `docs/Medical_AI_Assignment.pdf` - assignment brief

## License / use

For coursework and portfolio demonstration only.
