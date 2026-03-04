# GROWW Weekly App Review Pulse

A production-grade, automated pipeline that scrapes mobile app reviews from the Google Play Store and Apple App Store, clusters them into themes using an LLM, generates an executive pulse report, and delivers it as a formatted HTML email — on demand or on a weekly schedule.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Features](#2-features)
3. [Architecture](#3-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Project Structure](#5-project-structure)
6. [Database Setup](#6-database-setup)
7. [Installation Guide](#7-installation-guide-local-setup)
8. [How to Use the Application](#8-how-to-use-the-application)
9. [Deployment Guide (Streamlit Cloud)](#9-deployment-guide-streamlit-cloud)
10. [Configuration](#10-configuration)
11. [Known Limitations](#11-known-limitations)
12. [Future Improvements](#12-future-improvements)
13. [Troubleshooting Guide](#13-troubleshooting-guide)

---

## 1. Project Overview

### What it does

GROWW Weekly App Review Pulse is an internal analytics tool that automates the process of collecting, analysing, and summarising user feedback from mobile app stores. It runs a multi-stage pipeline that:

1. Scrapes reviews from the Google Play Store and Apple App Store for a configurable date range.
2. Deduplicates reviews against a local SQLite cache.
3. Clusters them into semantic themes using OpenAI's language model.
4. Generates a structured executive analysis and a markdown pulse note.
5. Renders a production-quality HTML email report and optionally sends it via SMTP.

### Problem it solves

Manually reading hundreds of weekly app reviews is time-consuming and inconsistent. This tool provides product and engineering teams with a structured, weekly digest of user sentiment — automatically.

### Target users

- Product managers who need a weekly summary of app feedback.
- Engineering leads monitoring for quality regressions.
- QA teams tracking recurring bug reports.

### High-level workflow

```
Date Range Selection → Review Scraping → Deduplication → Theme Clustering
        → Report Generation → HTML Email Render → Dashboard Display → Optional Send
```

---

## 2. Features

### Core features

| Feature | Description |
|---|---|
| **Review Scraping** | Fetches reviews from Google Play and Apple App Store for any custom date range |
| **Incremental Scraping** | Tracks which date ranges have already been scraped; skips cached data |
| **LLM Theme Clustering** | Groups reviews into up to 5 non-overlapping semantic themes via OpenAI |
| **Executive Report** | Generates a structured pulse note with top themes, sentiment, and recommendations |
| **HTML Email** | Renders a production-quality HTML email ready for delivery |
| **Email Sending** | Sends reports to any recipient via configured SMTP |
| **History Dashboard** | Tabular view of all pipeline runs with status, date range, and download links |
| **Component Polling** | History table auto-refreshes every 5 seconds without reloading the page |
| **Data Purge** | Secure confirmation-gated purge of all files, database records, and logs |
| **Scheduled Run** | Optional weekly cron job via the FastAPI + APScheduler backend |
| **CLI Mode** | Run the pipeline headlessly from the terminal |

### Job lifecycle

```
triggered → running → succeeded
                    ↘ failed
```

Every pipeline run is tracked in the `run_history` table with timestamps and counts at each stage.

---

## 3. Architecture

### High-level overview

```
┌─────────────────────────────────────────────┐
│              Streamlit Frontend              │
│  ┌──────────────┐   ┌─────────────────────┐ │
│  │  Sidebar:    │   │  Main Area:         │ │
│  │  App Select  │   │  Report Viewer      │ │
│  │  Date Range  │   │  Email Send Panel   │ │
│  │  Trigger Btn │   │  Run Details JSON   │ │
│  │  Maintenance │   │                     │ │
│  └──────────────┘   └─────────────────────┘ │
│  ┌─────────────────────────────────────────┐ │
│  │  History Table  (@st.fragment, 5s poll) │ │
│  └─────────────────────────────────────────┘ │
└───────────────────┬─────────────────────────┘
                    │ direct Python call
                    ▼
┌─────────────────────────────────────────────┐
│              PulseOrchestrator               │
│  scraper → dedup → theme → report → email   │
└──────┬─────────────────────────┬────────────┘
       │                         │
       ▼                         ▼
┌─────────────┐        ┌──────────────────────┐
│  SQLite DB  │        │  File System         │
│  pulse.db   │        │  data/raw/           │
│             │        │  data/processed/     │
│  reviews    │        │  logs/               │
│  scrape_    │        └──────────────────────┘
│  history    │
│  run_history│
└─────────────┘
```

### Backend components

| Module | Responsibility |
|---|---|
| `src/orchestrator.py` | Top-level pipeline coordinator; calls all stages in sequence |
| `src/scraper_engine.py` | Fetches reviews from Google Play and App Store APIs |
| `src/ingestion.py` | Deduplication and insertion into the SQLite `reviews` table |
| `src/pii_cleaner.py` | Strips personally identifiable information before LLM processing |
| `src/theme_engine.py` | LLM-powered semantic theme clustering (≤5 themes, deterministic) |
| `src/report_generator.py` | Produces structured markdown analysis from themes |
| `src/email_generator.py` | Renders the HTML email from the analysis report |
| `src/email_service.py` | SMTP delivery |
| `src/data_manager.py` | All SQLite read/write operations |
| `src/db_init.py` | Idempotent DB schema bootstrapper; runs once per process |
| `api/routes.py` | FastAPI REST API (optional; for external consumers and scheduler) |
| `main_api.py` | FastAPI app entry point with APScheduler cron job |
| `main.py` | Headless CLI runner |

### Frontend — Streamlit structure

`streamlit_app.py` is the single-file Streamlit frontend. It is divided into logical sections:

- **Session state initialisation** — pipeline status, toast guard, run ID tracker.
- **`@st.cache_resource`** — ensures the `PulseOrchestrator` and `ThreadPoolExecutor` are created once per container.
- **Sidebar** — application selector, date range picker, trigger button, maintenance (purge) section.
- **Main area** — conditionally shows the report viewer (if a result exists) or the history table.
- **`_render_history_table()`** — `@st.fragment(run_every=5)` function that polls the DB and re-renders only the table every 5 seconds, without reloading the page.

### Polling mechanism

The history table uses Streamlit's `@st.fragment(run_every=5)` primitive:

- Only the table function re-runs every 5 seconds via an internal Streamlit WebSocket timer.
- The rest of the page (sidebar, report viewer, header) is **never re-rendered** between polls.
- Users can interact with all other controls while the table updates in the background.
- No `window.location.reload()` — no full browser navigation.

### Database design

Four tables in a single SQLite file (`data/pulse.db`):

```sql
-- Tracked applications and their store IDs (dynamically populated)
applications (app_name PK, playstore_id, appstore_id)

-- Raw review storage. UNIQUE constraint prevents duplicates.
reviews (id PK, platform, rating, title, review_text, date, raw_data)

-- Tracks which date ranges have been scraped per platform.
scrape_history (platform, scrape_date) [composite PK]

-- Pipeline run lifecycle tracking.
run_history (
    run_id PK, status, trigger_source, triggered_by,
    start_date, end_date,
    triggered_at, started_at, completed_at,
    reviews_processed, themes_identified, error_message
)
```

Indexes on `run_history(triggered_at DESC)` and `run_history(status)` for fast dashboard queries.

---

## 4. Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Frontend | Streamlit 1.33+ |
| REST API (optional) | FastAPI + Uvicorn |
| Scheduler | APScheduler |
| Database | SQLite (via `sqlite3` stdlib) |
| LLM | OpenAI API (GPT-4o / GPT-4 Turbo) |
| Scraping | `google-play-scraper`, `requests` |
| Email | SMTP (configurable), HTML templates |
| Data | pandas |
| Deployment | Streamlit Cloud |
| Testing | pytest |

---

## 5. Project Structure

```
weekly-app-review-pulse/
│
├── streamlit_app.py          # Streamlit frontend (single entry point for Cloud)
├── main.py                   # Headless CLI runner
├── main_api.py               # FastAPI server with APScheduler cron
│
├── src/
│   ├── orchestrator.py       # Top-level pipeline coordinator
│   ├── scraper_engine.py     # Google Play + App Store scraper
│   ├── ingestion.py          # Review deduplication and DB insertion
│   ├── theme_engine.py       # LLM theme clustering
│   ├── report_generator.py   # Markdown analysis generator
│   ├── email_generator.py    # HTML email renderer
│   ├── email_service.py      # SMTP delivery
│   ├── pii_cleaner.py        # PII scrubbing before LLM
│   ├── data_manager.py       # All SQLite operations
│   └── db_init.py            # Idempotent schema initialiser
│
├── api/
│   └── routes.py             # FastAPI route definitions
│
├── utils/
│   └── logger.py             # Centralised logging setup
│
├── tests/
│   └── test_data_manager.py  # Unit + regression tests for DataManager
│
├── data/
│   ├── pulse.db              # SQLite database (git-ignored)
│   ├── raw/                  # Raw scraped JSON (git-ignored)
│   └── processed/            # Generated HTML emails and reports (git-ignored)
│
├── logs/
│   └── pulse_pipeline.log    # Application log (git-ignored)
│
├── .streamlit/
│   └── config.toml           # Streamlit theme and server config
│
├── .env                      # Local secrets (git-ignored)
├── requirements.txt          # Python dependencies
└── .gitignore
```

---

## 6. Database Setup

### How the DB initialises

`src/db_init.py` exposes a single function:

```python
from src.db_init import ensure_initialized
ensure_initialized()  # idempotent; safe to call on every startup
```

It is called automatically at startup from both `streamlit_app.py` and `main_api.py`. Because of a module-level `_initialized` flag, the schema check runs **only once per process**, regardless of how often Streamlit reruns the script.

On first run:

1. Creates the `data/` directory if missing.
2. Opens (or creates) `data/pulse.db`.
3. Executes all `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` statements.
4. Applies any pending `ALTER TABLE` column migrations for existing DBs.
5. Sets `PRAGMA journal_mode=WAL` for concurrent-safe reads and writes.

### Schema creation

All DDL uses `IF NOT EXISTS` guards — redeploys on Streamlit Cloud or restarts locally are always safe.

### Migrations

New columns added to `run_history` after initial deployment are applied non-destructively via `ALTER TABLE`. Existing data is never dropped or modified.

### How purge works

The **Purge All History** button in the Maintenance section calls:

```
purge button → orchestrator.purge_all_data()
                 ├── deletes all files in data/raw/ and data/processed/
                 ├── data_manager.purge_data()
                 │     ├── Guard: aborts if any job is triggered or running
                 │     ├── DELETE FROM run_history   (atomic)
                 │     ├── DELETE FROM scrape_history (atomic)
                 │     └── DELETE FROM reviews        (atomic)
                 └── truncates logs/pulse_pipeline.log
```

All three `DELETE` statements execute in **one SQLite transaction**. If any step fails, the transaction rolls back — no partial purge.

### Constraints

- Purge is **blocked** while any pipeline job has status `triggered` or `running`.
- Reviews have a `UNIQUE(platform, review_text, date)` constraint — inserting duplicates is silently ignored.
- `run_id` is the natural primary key (e.g. `custom_20260213_20260220_143022`).

---

## 7. Installation Guide (Local Setup)

### Prerequisites

- Python 3.10 or higher
- A valid [OpenAI API key](https://platform.openai.com/api-keys)
- SMTP credentials for email delivery (optional)

### Step 1 — Clone the repository

```bash
git clone https://github.com/your-org/weekly-app-review-pulse.git
cd weekly-app-review-pulse
```

### Step 2 — Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure environment variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...

# Optional: SMTP email sending
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com

# Optional: override DB path (default: data/pulse.db)
PULSE_DB_PATH=data/pulse.db
```

### Step 5 — Run the Streamlit application

```bash
python -m streamlit run streamlit_app.py
```

The app will be available at **<http://localhost:8501>**.

The database is created automatically on first launch — no manual setup required.

### Step 6 — (Optional) Run the FastAPI server

```bash
python main_api.py
```

API will be available at **<http://localhost:8000>**. Swagger docs at **<http://localhost:8000/docs>**.

### Step 7 — (Optional) CLI mode

```bash
python main.py --weeks 4          # Analyse last 4 weeks
python main.py --weeks 1 --force  # Force re-run ignoring idempotency cache
```

### Expected output (first run)

```
INFO - Initializing database at: data/pulse.db
INFO - Database initialization complete.
INFO - Streamlit app started.
```

---

## 8. How to Use the Application

### Trigger the pipeline

1. Open the app at `http://localhost:8501`.
2. In the **sidebar**, select a tracked **Application** from the dropdown.
3. Select a **Start Date** and **End Date**.
4. Click **Generate Pulse Report**.
5. The pipeline runs in a background thread — the UI stays responsive.

### Monitor status

The **Report History** table updates automatically every 5 seconds. Status indicators:

| Badge | Meaning |
|---|---|
| 🟡 Triggered | Job queued, pipeline not yet started |
| 🔵 Running | Pipeline actively executing |
| 🟢 Succeeded | Pipeline completed; report available |
| 🔴 Failed | Pipeline encountered an error |

### View a report

Once a run reaches **Succeeded**, click the **Run ID link** in the history table to open the email report viewer.

### Download the email

In the report viewer, click **Download HTML Email** to save the rendered email as an `.html` file. A **⬇** button is also available directly in the history table row.

### Send the report

In the report viewer's right panel, enter a recipient email address and click **Send Email**.

### Purge all data

1. In the sidebar, scroll to **🛠️ Maintenance**.
2. Click **Purge All History**.
3. Type `delete` in the confirmation box.
4. Click **Confirm**.

This deletes all database records, generated files, and log content. All active jobs must be in a terminal state first.

---

## 9. Deployment Guide (Streamlit Cloud)

### Required files

Ensure the following are committed to the repository:

```
streamlit_app.py
src/
api/
utils/
requirements.txt
.streamlit/config.toml
```

The `data/` directory and all `.db`, `.json`, `.html`, `.md` files under it are **git-ignored** and must not be committed.

### Secrets configuration

In the Streamlit Cloud dashboard, navigate to your app → **Settings → Secrets** and add:

```toml
OPENAI_API_KEY = "sk-..."
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = "587"
SMTP_USER = "your-email@gmail.com"
SMTP_PASSWORD = "your-app-password"
EMAIL_FROM = "your-email@gmail.com"
```

Streamlit Cloud injects these as environment variables at runtime.

### DB initialisation behaviour on Cloud

- On every deploy or container restart, `ensure_initialized()` runs automatically.
- It creates `data/pulse.db` fresh in the container's ephemeral filesystem.
- All tables and indexes are created via `IF NOT EXISTS` — safe for repeated restarts.
- **Note:** Streamlit Cloud containers are ephemeral. Data written to `data/pulse.db` will be lost on container restart. For persistent production storage, mount an external volume or migrate to a hosted database (e.g. PostgreSQL via Supabase).

### Deploying

1. Push the repository to GitHub.
2. Log in to [share.streamlit.io](https://share.streamlit.io).
3. Click **New app** → select your repository and branch.
4. Set **Main file path** to `streamlit_app.py`.
5. Add secrets (see above).
6. Click **Deploy**.

---

## 10. Configuration

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | OpenAI API key for theme clustering |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP server port |
| `SMTP_USER` | — | SMTP authentication username |
| `SMTP_PASSWORD` | — | SMTP authentication password |
| `EMAIL_FROM` | — | Sender address for outbound emails |
| `PULSE_DB_PATH` | `data/pulse.db` | Override SQLite file path |

### Polling interval

The history table polling interval is set in `streamlit_app.py`:

```python
@st.fragment(run_every=5)   # seconds — change this value to adjust
def _render_history_table():
```

### DB location

Override via environment variable:

```env
PULSE_DB_PATH=/mount/data/pulse.db
```

---

## 11. Known Limitations

### SQLite concurrency

SQLite operates in WAL mode, which allows concurrent reads. However, it supports only one writer at a time. Under high concurrency (multiple simultaneous pipeline triggers), write operations will queue sequentially. For production multi-user workloads, consider migrating to PostgreSQL.

### Streamlit Cloud ephemeral storage

Data written to the local filesystem (including `pulse.db`) does not persist across container restarts on Streamlit Cloud. Treat each deployment as a fresh environment.

### Streamlit rerun behaviour

Streamlit reruns the full script on every user interaction. The `@st.cache_resource` decorator is used to avoid reconstructing the `PulseOrchestrator` on each rerun. The `_initialized` flag in `db_init.py` ensures schema creation runs only once per process.

### Single pipeline concurrency

The `ThreadPoolExecutor` is initialised with `max_workers=1`. Only one pipeline job can run at a time per Streamlit session. A second trigger while a job is running will be rejected.

### Apple App Store scraping

The App Store scraper relies on a public RSS endpoint. Rate limits and data availability are determined by Apple and may change without notice.

---

## 12. Future Improvements

- **Persistent storage** — Migrate to a hosted PostgreSQL database for durable, cross-restart persistence on Streamlit Cloud.
- **Multi-app support** — Extend the pipeline to scrape and compare multiple apps in a single run.
- **Trend analysis** — Add week-over-week sentiment trend charts to the dashboard.
- **Webhook notifications** — Notify Slack or Teams when a pipeline run completes.
- **Role-based access** — Add authentication to the Streamlit app for multi-user deployments.
- **Retry logic** — Automatic retry with exponential backoff for failed scraping or LLM API calls.
- **Export to CSV** — Allow bulk download of raw reviews per run.

---

## 13. Troubleshooting Guide

### App does not start

**Symptom:** `ModuleNotFoundError` on startup.

**Fix:** Ensure the virtual environment is activated and dependencies are installed.

```bash
pip install -r requirements.txt
```

---

### Database is not created

**Symptom:** `sqlite3.OperationalError: no such table: run_history`

**Fix:** The `data/` directory may not exist or `ensure_initialized()` was not called. Restart the app — it runs automatically on startup.

---

### Purge button does nothing / shows error

**Symptom:** Clicking Confirm has no visible effect, or shows "Purge blocked" error.

**Cause 1:** A pipeline job is still running (`triggered` or `running` status).  
**Fix:** Wait for the running job to finish, then retry.

**Cause 2:** App server is running old code (loaded before a code change).  
**Fix:** Restart the Streamlit server.

```bash
# Stop the current server (Ctrl+C), then:
python -m streamlit run streamlit_app.py
```

---

### History table does not refresh

**Symptom:** Status stays at "Running" even after the pipeline completes.

**Fix:** `@st.fragment(run_every=5)` requires Streamlit 1.33+. Check your installed version:

```bash
python -c "import streamlit; print(streamlit.__version__)"
```

Upgrade if needed:

```bash
pip install --upgrade streamlit
```

---

### Port conflict

**Symptom:** `OSError: [Errno 98] Address already in use` on port 8501.

**Fix:** Run on a different port:

```bash
python -m streamlit run streamlit_app.py --server.port 8502
```

Or kill the existing process using Task Manager (Windows) or:

```bash
# macOS / Linux
lsof -ti:8501 | xargs kill
```

---

### Email sending fails

**Symptom:** `Failed to send email` error in the UI.

**Fix:** Verify SMTP credentials in `.env`. For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833) — not your main account password. Ensure `SMTP_PORT=587` and TLS is enabled.

---

### OpenAI API errors

**Symptom:** Pipeline fails at the theme clustering stage with `openai.AuthenticationError` or `RateLimitError`.

**Fix:**

- Verify `OPENAI_API_KEY` is set correctly in `.env` or Streamlit Secrets.
- Check your OpenAI usage limits and billing status.
- The theme engine uses deterministic settings (`temperature=0`) — retrying after a brief wait is safe.

---

### Windows: `PermissionError` on `data/pulse.db`

**Symptom:** Tests fail with `PermissionError: [WinError 32]` when cleaning up test databases.

**Fix:** This is handled in the test suite via `pytest`'s `tmp_path` fixture, which provides isolated, auto-cleaned directories per test. Ensure you are running the latest test file:

```bash
python -m pytest tests/test_data_manager.py -v
```
