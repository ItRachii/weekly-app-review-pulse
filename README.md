# 🌱 GROWW — Weekly App Review Pulse

An automated sentiment analysis and executive reporting pipeline for app store reviews. It scrapes reviews from the **Google Play Store** and **Apple App Store**, clusters them into semantic themes using GPT-4o-mini, generates executive pulse notes, and delivers HTML email reports — all with a single command.

---

## Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Configuration](#-configuration)
- [Usage](#-usage)
  - [CLI](#1-cli-command-line)
  - [REST API](#2-rest-api-fastapi)
  - [Dashboard](#3-streamlit-dashboard)
- [API Reference](#-api-reference)
- [How It Works](#-how-it-works)
- [Testing](#-testing)
- [Important Notes](#-important-notes)

---

## ✨ Features

| Feature | Description |
|:---|:---|
| **Multi-Platform Scraping** | Fetches reviews from Google Play Store and Apple App Store automatically. |
| **PII Masking** | Strips emails, phone numbers, URLs, and Indian ID patterns (PAN/Aadhaar) from all review text before storage. |
| **LLM Theme Clustering** | Uses GPT-4o-mini to group reviews into ≤5 non-overlapping semantic themes with high-signal quotes and actionable ideas. |
| **Executive Pulse Note** | Generates a ≤250-word executive summary for leadership. |
| **HTML Email Reports** | Produces a styled, professional HTML email ready to send via SMTP. |
| **Incremental Scraping** | Tracks scrape history in SQLite — only fetches data for date ranges not yet covered. |
| **Idempotency** | Prevents duplicate pipeline runs for the same calendar week (overridable with `--force`). |
| **Async Pipeline** | Non-blocking execution with background workers and real-time toast notifications. |
| **Persisted Run History** | Stores execution metadata (Run ID, counts, dates) in SQLite for historical analysis. |
| **Three Interfaces** | Accessible via CLI, REST API (FastAPI), or Standalone Streamlit Dashboard. |
| **Groww Brand Theme** | Fully branded UI with Groww's official color palette and logo across dashboard and email reports. |
| **Structured Logging** | Rotating file logs + console output with configurable log levels. |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Data Sources                                 │
│     Google Play Store ──┐            ┌── Apple App Store (RSS)      │
│                         ▼            ▼                              │
│                   ┌──────────────────────┐                          │
│                   │   ScraperEngine      │                          │
│                   │  (Play: library,     │                          │
│                   │   iOS: iTunes RSS)   │                          │
│                   └──────────┬───────────┘                          │
│                              ▼                                      │
│                   ┌──────────────────────┐                          │
│                   │   IngestionModule    │                          │
│                   │  + PIICleaner        │                          │
│                   └──────────┬───────────┘                          │
│                              ▼                                      │
│                   ┌──────────────────────┐                          │
│                   │   DataManager        │                          │
│                   │   (SQLite DB)        │                          │
│                   └──────────┬───────────┘                          │
│                              ▼                                      │
│                   ┌───────────────────────┐                         │
│                   │ ThemeClusteringEngine │                         │
│                   │ (GPT-4o-mini)         │                         │
│                   └──────────┬────────────┘                         │
│                              ▼                                      │
│                ┌─────────────┴─────────────┐                        │
│                ▼                           ▼                        │
│   ┌──────────────────┐       ┌─────────────────────┐                │
│   │ PulseReportGen   │       │   EmailGenerator    │                │
│   │ (Markdown Note)  │       │   (HTML Email)      │                │
│   └──────────────────┘       └─────────────────────┘                │
│                                        │                            │
│                                        ▼                            │
│                              ┌──────────────────┐                   │
│                              │  EmailService    │                   │
│                              │  (SMTP Sender)   │                   │
│                              └──────────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
```

Orchestrated by `PulseOrchestrator`, which coordinates the entire pipeline end-to-end.

---

## 🛠 Tech Stack

| Category | Technology |
|:---|:---|
| **Language** | Python 3.11+ |
| **Play Store Scraping** | [`google-play-scraper`](https://pypi.org/project/google-play-scraper/) |
| **App Store Scraping** | Python `urllib` (iTunes RSS Feed) |
| **LLM** | OpenAI GPT-4o-mini |
| **Validation** | Pydantic |
| **Database** | SQLite |
| **REST API** | FastAPI + Uvicorn |
| **Dashboard** | Streamlit |
| **Email** | `smtplib` (TLS/SSL) |
| **Scheduling** | APScheduler (weekly cron) |
| **Logging** | `RotatingFileHandler` |

---

## 📁 Project Structure

```text
weekly-app-review-pulse/
├── main.py                  # CLI entry point
├── main_api.py              # FastAPI server entry point (with APScheduler)
├── streamlit_app.py         # Standalone Streamlit dashboard (Directly imports Orchestrator)
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (not committed)
├── architecture.md          # Detailed architecture documentation
│
├── .streamlit/
│   └── config.toml          # Streamlit theme (Groww brand colors)
│
├── assets/
│   └── groww_logo.png       # Groww brand logo (favicon + header)
│
├── api/
│   ├── __init__.py
│   └── routes.py            # FastAPI route definitions (7 endpoints)
│
├── src/
│   ├── orchestrator.py      # Pipeline orchestrator (coordinates all stages)
│   ├── scraper_engine.py    # Play Store + App Store scraper
│   ├── ingestion.py         # CSV ingestion, validation, PII cleaning
│   ├── data_manager.py      # SQLite persistence & incremental scrape tracking
│   ├── theme_engine.py      # LLM-powered semantic theme clustering
│   ├── report_generator.py  # Executive pulse note generation (≤250 words)
│   ├── email_generator.py   # HTML email template (Groww branded)
│   ├── email_service.py     # SMTP email delivery
│   └── pii_cleaner.py       # Regex-based PII masking
│
├── utils/
│   ├── __init__.py
│   └── logger.py            # Structured logging setup (console + rotating file)
│
├── tests/                   # Unit and integration tests
│   ├── test_ingestion.py
│   ├── test_theme_engine.py
│   ├── test_data_manager.py
│   ├── test_email_service.py
│   ├── test_report_generation.py
│   ├── test_pii_leakage.py
│   ├── test_hallucination.py
│   ├── test_quote_extraction.py
│   ├── test_edge_cases.py
│   └── integration/
│
├── data/
│   ├── raw/                 # Scraped review JSON files
│   ├── processed/           # Generated reports, analysis, and run manifests
│   └── pulse.db             # SQLite database
│
└── logs/
    └── pulse_pipeline.log   # Rotating log file (10 MB, 5 backups)
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- An [OpenAI API key](https://platform.openai.com/api-keys)
- (Optional) Gmail App Password for email delivery

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/ItRachii/weekly-app-review-pulse.git
cd weekly-app-review-pulse

# 2. Create a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Quick Setup

```bash
# 4. Create your .env file (see Configuration section below)
copy .env.example .env   # Windows
cp .env.example .env     # macOS/Linux

# 5. Add your OpenAI API key to .env
# OPENAI_API_KEY=sk-your-key-here

# 6. Run the pipeline
python main.py
```

---

## ⚙ Configuration

Create a `.env` file in the project root with the following variables:

```env
# Required — OpenAI
OPENAI_API_KEY=sk-your-openai-api-key

# Optional — App Settings
WEEKS_BACK=12          # How many weeks of reviews to look back (default: 12)
LOG_LEVEL=INFO         # DEBUG, INFO, WARNING, ERROR (default: INFO)

# Optional — SMTP (required only for email delivery)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
```

> **Note for Gmail users:** You need to generate an [App Password](https://myaccount.google.com/apppasswords) (not your regular password). Enable 2-Step Verification first.

---

## 📖 Usage

The system provides **three interfaces** — use whichever fits your workflow.

### 1. CLI (Command Line)

Best for one-off runs, cron jobs, or CI/CD pipelines.

```bash
# Default run (12 weeks lookback, idempotent)
python main.py

# Custom lookback period
python main.py --weeks 8

# Force re-run (bypass idempotency)
python main.py --force
```

**Output:** Generates files in `data/processed/`:

- `pulse_note_<run_id>.md` — Executive summary
- `pulse_email_<run_id>.html` — Styled HTML email
- `analysis_<run_id>.json` — Theme analysis data

---

### 2. REST API (FastAPI)

Best for integrations, CI/CD hooks, and programmatic access.

```bash
# Start the API server
python main_api.py
# Server starts at http://localhost:8000
# API docs available at http://localhost:8000/docs
```

The API server also includes an **APScheduler cron job** that automatically runs the pipeline every **Monday at 9:00 AM**.

---

### 3. Streamlit Dashboard

Best for interactive use, date range selection, and email sending.

> **Note:** The dashboard now runs largely standalone by importing the orchestrator directly, but shares the same `data/` directory.

```bash
# Start the dashboard
streamlit run streamlit_app.py
# Dashboard opens at http://localhost:8501
```

**Dashboard features:**

- **Async Execution:** Triggers the pipeline in a background thread. You can continue using the app while the report generates.
- **Real-time Feedback:** Toast notifications for trigger confirmation and run completion.
- **Deep Linking:** Clickable "Run ID" links in history load reports directly via URL parameters.
- **Groww Brand Theme:** Fully branded UI with official colors.
- **Report History:** Tabular view of past runs with "Reviews Processed" stats and download buttons.
- **Data Maintenance:** Secure "Purge All Data" functionality.

---

## 📡 API Reference

All endpoints are prefixed with `/api/v1`.

### Health Check

```
GET /api/v1/health
```

**Response:**

```json
{ "status": "healthy", "service": "Pulse Report Pipeline" }
```

---

### Trigger Pipeline

```http
POST /api/v1/trigger
Content-Type: application/json
```

Runs the full scrape → clean → cluster → report pipeline **synchronously** and returns results.

**Request body:**

```json
{
  "start_date": "2026-02-09",
  "end_date": "2026-02-16",
  "force": false
}
```

| Field | Type | Required | Description |
|:---|:---|:---|:---|
| `start_date` | string | ❌ | ISO date (defaults to system calculation) |
| `end_date` | string | ❌ | ISO date (defaults to today) |
| `force` | bool | ❌ | Bypass weekly idempotency check (default: `false`) |

**Response:**

```json
{
  "status": "success",
  "reviews_count": 142,
  "themes_count": 5,
  "run_id": "custom_20260209_20260216_234027",
  "artifacts": {
    "email_html": "data/processed/pulse_email_custom_20260209_20260216_234027.html",
    "pulse_note": "data/processed/pulse_note_custom_20260209_20260216_234027.md"
  }
}
```

---

### Upload Reviews

```http
POST /api/v1/upload
Content-Type: multipart/form-data
```

Upload a CSV or JSON file of reviews for manual processing.

| Parameter | Type | Description |
|:---|:---|:---|
| `file` | File | `.csv` or `.json` file |

---

### List Reports

```http
GET /api/v1/reports
```

Returns all generated reports with metadata (filename, type, date, size).

**Response:**

```json
{
  "reports": [
    {
      "filename": "pulse_email_custom_20260209_20260216_234027.html",
      "type": "html",
      "modified_at": "2026-02-16T23:40:48.567924",
      "size_bytes": 3075
    }
  ],
  "count": 1
}
```

---

### Get Report Content

```http
GET /api/v1/reports/{filename}
```

Returns the content of a specific report file. Used by the dashboard for previewing and downloading reports without direct filesystem access.

| Parameter | Type | Description |
|:---|:---|:---|
| `filename` | path | Report filename (e.g., `pulse_email_custom_20260209_20260216_234027.html`) |

**Response:** Raw file content with appropriate `Content-Type` (`text/html` or `text/markdown`).

---

### Purge All Data

```http
DELETE /api/v1/purge
```

⚠️ **Destructive action** — Deletes all reviews, reports, logs, and resets the database.

| Header | Value | Required |
|:---|:---|:---|
| `X-Confirm-Purge` | `delete` | ✅ Yes (safety guard) |

**Example:**

```bash
curl -X DELETE http://localhost:8000/api/v1/purge \
  -H "X-Confirm-Purge: delete"
```

**Response:**

```json
{ "status": "purged", "message": "All data has been purged successfully." }
```

---

### Send Email Report

```http
POST /api/v1/send-email
Content-Type: application/json
```

Sends a previously generated HTML report via SMTP.

**Request body:**

```json
{
  "to_email": "manager@company.com",
  "subject": "[GROWW] Weekly Pulse — Feb 16, 2026",
  "report_file": "pulse_email_custom_20260209_20260216_234027.html"
}
```

| Field | Type | Required | Description |
|:---|:---|:---|:---|
| `to_email` | string | ✅ | Recipient email address |
| `subject` | string | ❌ | Custom subject line (auto-generated if omitted) |
| `report_file` | string | ✅ | Filename from `data/processed/` |

**Response:**

```json
{ "status": "sent", "to": "manager@company.com", "report": "pulse_email_custom_20260209_20260216_234027.html" }
```

---

## ⚡ How It Works

The pipeline executes in **4 stages**, orchestrated by `PulseOrchestrator`:

### Stage 1 — Intelligent Scraping

- **Play Store**: Uses `google-play-scraper` library to fetch up to 500 reviews sorted by newest.
- **App Store**: Hits the iTunes RSS JSON endpoint for the most recent reviews.
- **Incremental**: Only scrapes date ranges not already in the database by checking `scrape_history`.
- **PII Cleaning**: All reviews pass through `PIICleaner` which masks emails, phones, URLs, and Indian ID patterns.

### Stage 2 — Theme Clustering

- Sends up to 100 reviews to **GPT-4o-mini** with a structured prompt.
- The LLM groups feedback into ≤5 non-overlapping semantic themes.
- Each theme includes: a label, review count, summary, 3 high-signal quotes, and 3 actionable ideas.
- Output is validated via Pydantic schemas (`Theme`, `ThemeOutput`).

### Stage 3 — Report Generation

- **Pulse Note**: An executive-ready ≤250-word markdown summary generated by GPT-4o-mini.
- **HTML Email**: A styled, responsive HTML email rendered from a professional template.

### Stage 4 — Delivery & Finalization

- Reports are saved to `data/processed/`.
- The current week is marked as completed in the run manifest (for idempotency).
- Email can be sent via SMTP (Gmail TLS/SSL with automatic fallback).

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_ingestion.py

# Run minimal tests (no external API calls)
python run_minimal_tests.py
```

### Test Coverage

| Test File | What It Tests |
|:---|:---|
| `test_ingestion.py` | CSV parsing, Pydantic validation, date filtering |
| `test_theme_engine.py` | LLM clustering output schema, theme count limits |
| `test_data_manager.py` | SQLite CRUD, incremental scrape tracking |
| `test_email_service.py` | SMTP configuration, email delivery |
| `test_report_generation.py` | Pulse note generation, word count enforcement |
| `test_pii_leakage.py` | PII masking for emails, phones, URLs, IDs |
| `test_hallucination.py` | Ensures LLM quotes exist in source data |
| `test_quote_extraction.py` | High-signal quote selection validation |
| `test_edge_cases.py` | Empty inputs, malformed data, boundary conditions |

---

## ⚠ Important Notes

### Things to Keep in Mind

1. **OpenAI API Key is required.** The theme clustering and report generation stages call the OpenAI API. Without a valid key in `.env`, these stages will fail (with a graceful fallback for clustering).

2. **App Store RSS limitations.** The iTunes RSS feed returns only the most recent ~500 reviews. For weekly analysis, this is sufficient, but it cannot fetch deep historical data.

3. **Play Store scraping is unofficial.** The `google-play-scraper` library uses Google Play's internal APIs. While reliable, it could break if Google changes their endpoints.

4. **PII masking is regex-based.** It covers emails, phones, URLs, and PAN/Aadhaar patterns. It does not perform NER-based name detection. Exercise caution with reports containing user names embedded in review text.

5. **Idempotency is week-based.** The pipeline tracks completed weeks in `data/processed/run_manifest.json`. Use `--force` or `force=True` to override. Custom date-range runs (via Streamlit/API) always execute regardless.

6. **SQLite is local.** The database (`data/pulse.db`) is a local file. For multi-instance deployments, switch to PostgreSQL (as outlined in `architecture.md`).

7. **SMTP requires an App Password for Gmail.** Regular Google account passwords won't work. Generate one at [Google App Passwords](https://myaccount.google.com/apppasswords).

8. **Token budget.** The clustering prompt sends up to 100 reviews to the LLM. For apps with very high review volume, this is a representative sample, not the full set.

9. **Dashboard is Standalone.** The Streamlit dashboard imports `PulseOrchestrator` directly for simpler deployment. It does NOT require the API server to be running, but they can coexist.

### Customizing for Your App

To use this pipeline for a **different app** (not Groww), update these values in `src/orchestrator.py`:

```python
# Line 96-98 in orchestrator.py
platforms = [
    {"name": "ios", "id": "YOUR_APP_STORE_ID"},      # e.g., "389801252" for Instagram
    {"name": "android", "id": "YOUR_PACKAGE_NAME"},   # e.g., "com.instagram.android"
]
```

And update the LLM prompts in `src/theme_engine.py` and `src/report_generator.py` to replace "GROWW" with your app's name.

---

## 📄 License

This project is for internal use. Contact the repository owner for licensing details.
