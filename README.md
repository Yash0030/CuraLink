# Personal Health Record Organizer

An Agentic AI application built for the **Ziro Agentic AI Hackathon 2026**.

The app autonomously collects diagnostic reports spread across three disparate lab portals (`labA` / A1, `labB` / CityScan Imaging, and `labC` / Vitals), deduplicates and filters records using strict deterministic code and LLM guardrails, gates human approval, and compiles a unified, verified, and dated health timeline.

Operates **strictly on synthetic data only**.

---

## Architecture Overview

```
[ Lab A: A1 (Table) ]      [ Lab B: CityScan (Cards) ]      [ Lab C: Vitals (Paginated) ]
         │                               │                               │
   (Tool 1: Login)                 (Mock CAPTCHA)                  (Mock CAPTCHA)
         │                         (Human Solver)                  (Human Solver)
   (Tool 2: List)                  (Tool 2: List)                  (Tool 2: List)
   (Tool 3: Download)              (Tool 3: Download)              (Tool 3: Download)
         └───────────────────────────────┬───────────────────────────────┘
                                         ▼
                             [ Staging in Postgres ]
                                         │
                             [ Extractor Agent ]
                             • Template Regex First
                             • Anti-Hallucination Guardrail (drops invented values)
                             • LLM Fallback (only when Name/Date missing)
                                         │
                             [ Checker Agent ]
                             • Legitimacy: %PDF check (TC4), Patient ID, Name matching
                             • Token normalization: "ROY, AARAV" == "Aarav Roy"
                             • Look-alike exclusion: score < 0.75 -> Exclude (TC3)
                             • Deduplication: Same ID or SHA-256 -> Duplicate (TC2)
                             • Discrepancies: Portal date != PDF date -> Review
                                         │
                             [ Human Approval Gate ]
                             • LangGraph interrupt() & Command(resume=...)
                             • Override decision resolution ('keep' / 'skip')
                                         │
                             [ Idempotent Storage ]
                             • UNIQUE (patient_key, report_id) & (patient_key, sha256)
                                         │
                             [ Verification Re-Check ]
                             • Re-opens raw PDF bytes & re-verifies Name & Date
                                         │
                             [ Unified Dated Health Timeline ]
```

---

## Tech Stack & Database Rules

- **Backend**: Python 3.12, FastAPI, LangGraph (async StateGraph), Pydantic v2.
- **Frontend**: React 18, Vite, TypeScript, Vanilla CSS (rich dark mode design system).
- **Database**: Neon Postgres with `psycopg3` (`psycopg[binary,pool]`).
  - **Neon Pool Rule**: Application pool uses the pooled URL (`ep-*-pooler.neon.tech`) configured with `prepare_threshold=None`.
  - **Checkpointer Rule**: LangGraph AsyncPostgresSaver uses the direct URL (`-pooler` stripped). In-memory `MemorySaver` is used automatically for local/offline testing.
- **LLM**: Groq via `langchain-groq` (model: `openai/gpt-oss-20b`).
- **Browser Automation**: Playwright (local Chromium mode and Browserbase cloud mode for `ap-southeast-1`).
- **Libraries**: `pypdf`, `beautifulsoup4`, `reportlab`, `httpx`, `pytest`, `pytest-asyncio`.

---

## Local Run Steps

### 1. Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- PostgreSQL / Neon account (or local Postgres)

### 2. Install Backend Dependencies
```bash
# From workspace root:
pip install -r backend/requirements.txt
playwright install chromium
```

### 3. Configure Environment Variables
Copy example configurations for backend and frontend:
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```
*(Never write production secrets or credentials into Git. Both `.env` files are gitignored.)*

### 4. Initialize Database Tables
Run the database schema migration:
```bash
python sql/init_db.py
```
This executes `sql/schema.sql` against `DATABASE_URL` with `prepare_threshold=None` and creates:
- `runs`
- `candidates`
- `reports`
- `events`
- `approvals`

### 5. Start the Backend Server
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
- API Documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- Built-in Mock Lab Portals: http://localhost:8000/labA/reports, http://localhost:8000/labB/reports, http://localhost:8000/labC/reports

### 6. Start the Frontend
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 in your browser.

---

## Acceptance Test Suite

The test suite covers all acceptance criteria:
- **TC1**: Three portals produce one combined, dated timeline.
- **TC2**: The same report downloaded twice is stored once (deduplicated by ID / SHA-256).
- **TC3**: A report with another patient's name is excluded, including look-alikes like "Anita Sharma-Rao" (score < 0.75).
- **TC4**: Login HTML saved as `.pdf` is rejected (`not_pdf`).
- **Discrepancy**: Portal date differing from date inside PDF goes to review.
- **Cross-run**: Second run for the same patient treats everything already stored as duplicate.
- **E2E API Lifecycle**: Full test with stubbed fetchers, approval interrupts, and PDF streaming.

To run all 24 automated tests:
```bash
python -m pytest backend/tests -v
```

---

## Honest Disclosure & Production Notes

In the spirit of complete engineering honesty:
1. **Live Browserbase & Groq Endpoints**: The test suite runs deterministically with local Chromium and offline fallbacks. Testing against live Browserbase cloud sessions in `ap-southeast-1` and live Groq LLM API requires valid API keys in `backend/.env`.
2. **Portal Selectors**: The selectors in `backend/app/portal_selectors.py` match standard semantic elements and the included Next.js-style mock portal. When connecting to an external production portal, verify and update the selectors in `backend/app/portal_selectors.py` to match any specific production DOM modifications.
3. **No Vector Store / RAG**: As explicitly mandated by the hackathon constraints, this app uses zero vector stores or RAG, relying strictly on deterministic parsing, pypdf text analysis, and targeted LLM fallbacks.
