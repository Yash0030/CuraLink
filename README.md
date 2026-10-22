# CuraLink — Autonomous Personal Health Record Organizer

An intelligent agentic platform that automates the collection, extraction, verification, and consolidation of medical diagnostic records scattered across multiple lab portals into a single, unified health timeline.

---

## 🌟 Overview

Patients frequently undergo diagnostic tests across multiple independent laboratories and imaging centers. Each portal has its own authentication, interface layout, and download format, leaving health histories fragmented across disconnected accounts.

**CuraLink** solves this with an agentic architecture:
1. **Connects** to multiple lab portals concurrently using intelligent browser automation.
2. **Navigates** login and CAPTCHA challenges with real-time Human-in-the-Loop interaction.
3. **Downloads & Stages** diagnostic PDFs securely.
4. **Extracts & Normalizes** clinical metadata (patient details, test names, report dates, reference IDs) using pattern extraction paired with LLM reasoning.
5. **Verifies & Deduplicates** records against historical data to ensure authenticity and prevent repeated entries.
6. **Presents** a structured review panel for human approval before committing files to permanent storage.
7. **Compiles** a searchable, chronological health timeline with an integrated PDF viewer.

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Diagnostic Portals                            │
│   [ Table Layout ]      [ Cards Layout ]     [ Paginated Layout ]      │
└───────────┬────────────────────┬───────────────────────┬───────────────┘
            │                    │                       │
     (Auth & Session)     (CAPTCHA Trigger)       (CAPTCHA Trigger)
            │                    │                       │
            │             ┌──────▼───────────────────────▼──────┐
            │             │   Human-in-the-Loop CAPTCHA Solver  │
            │             │   • Real-time screenshot display    │
            │             │   • Manual input / Live browser view│
            │             └──────┬───────────────────────┬──────┘
            │                    │                       │
     (Tool: List)         (Tool: List)            (Tool: List)
     (Tool: Download)     (Tool: Download)        (Tool: Download)
            │                    │                       │
            └────────────────────┼───────────────────────┘
                                 ▼
                     [ Document Staging Storage ]
                                 │
                     [ Extractor Agent ]
                     • Structured pattern extraction
                     • Targeted LLM fallback for unparsed layouts
                     • Anti-hallucination verification against document text
                                 │
                     [ Verification & Quality Checker ]
                     • PDF header & format authenticity verification
                     • Patient identity matching & token normalization
                     • Anomaly detection (portal vs. document date discrepancies)
                     • Multi-factor deduplication (checksums & report IDs)
                                 │
                     [ Human Approval Checkpoint ]
                     • Granular per-document review & decision overrides
                     • Multi-document selection & batch actions
                                 │
                     [ Permanent Record Storage ]
                     • Idempotent record storage with database integrity constraints
                                 │
                     [ Verification Re-Check ]
                     • Post-storage byte verification of patient data
                                 │
                     [ Unified Health Timeline ]
                     • Chronological record with integrated PDF viewer
```

---

## ⚡ Core Features

- **Multi-Portal Autonomous Fetching**:
  - Concurrent browser workers adaptively navigate different portal architectures (tables, cards, pagination).
  - Ability to connect and configure custom external lab portals dynamically.

- **Human-in-the-Loop CAPTCHA Resolution**:
  - Automatically detects CAPTCHA challenges during portal sign-in.
  - Presents a high-resolution screenshot modal to the user with options to solve via text input or directly within an interactive cloud browser session.

- **Intelligent Metadata Extraction**:
  - Hybrid extraction pipeline combining pattern parsing with localized LLM fallbacks.
  - Strict guardrails: any field suggested by the model must be grounded in the raw document text, preventing hallucinations.

- **Multi-Factor Deduplication & Verification**:
  - Detects duplicate records across different portals or previous collection runs using SHA-256 cryptographic hashes and report identifiers.
  - Robust name matching handles variations in patient name formatting (e.g., uppercase, inverted ordering, or punctuation).
  - Flags discrepancies between portal metadata and internal report dates for human review.

- **Granular Human Approval**:
  - LangGraph checkpoint interruptions halt execution until the user inspects candidate files.
  - Full control to override agent recommendations (accepting, rejecting, or batch-approving reports).

- **Unified Health Timeline**:
  - Chronological, filterable medical feed with laboratory origin badges, test metadata, and SHA-256 verification tags.
  - Built-in PDF reader modal allowing instant preview and download of original documents.

- **Live Activity Audit Log**:
  - Every step is streamed in real-time with clear actor labeling (`Human Action` vs `Agent Activity`).

- **User Authentication & Privacy**:
  - User accounts secured with bcrypt password encryption and token sessions.
  - Portal credentials are kept strictly in transient memory during active fetch tasks and wiped immediately afterward.

- **Refined User Experience**:
  - Modern dark mode and light mode with accessible calendar selectors and responsive layouts.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3.12, FastAPI, LangGraph, Pydantic v2, Uvicorn |
| **Frontend** | React 18, Vite, TypeScript, Lucide Icons, Vanilla CSS |
| **Database** | PostgreSQL with `psycopg3` async connection pooling |
| **Browser Automation** | Playwright (local Chromium) & Browserbase (cloud sessions) |
| **LLM & Reasoning** | Groq API (`langchain-groq`) |
| **Document Processing**| `pypdf`, `reportlab`, `beautifulsoup4` |
| **Testing** | `pytest`, `pytest-asyncio`, `httpx` |

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.12+**
- **Node.js 18+** and **npm**
- **PostgreSQL** instance (local database or hosted provider such as Neon)

### 2. Clone the Repository
```bash
git clone https://github.com/Yash0030/CuraLink.git
cd CuraLink
```

### 3. Backend Setup
```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

Create a `.env` file in the `backend/` directory:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/curalink
SECRET_KEY=your_secure_random_key_here
GROQ_API_KEY=your_groq_api_key_here

# Optional: Browserbase integration for cloud live-view CAPTCHA
BROWSERBASE_API_KEY=your_browserbase_key
BROWSERBASE_PROJECT_ID=your_project_id
```

Initialize the database tables:
```bash
python sql/init_db.py
```

Start the backend server:
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### 4. Frontend Setup
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173** in your browser.

---

## 🧪 Testing

The automated test suite verifies end-to-end functionality including authentication, multi-portal parsing, name matching, duplicate detection, and file integrity:

```bash
# Run the complete test suite
python -m pytest backend/tests -v
```

---

## 🔒 Security & Privacy

- **Ephemeral Credentials**: Lab portal login passwords provided during collection runs exist solely in transient memory during fetch worker execution and are immediately purged once the collection completes or is cancelled.
- **Isolated User Storage**: All runs, staged files, custom lab portals, and timeline records are strictly scoped to the authenticated user.
- **Cryptographic Verification**: Every document ingested is tagged with its SHA-256 checksum to guarantee data integrity across storage and retrieval.
