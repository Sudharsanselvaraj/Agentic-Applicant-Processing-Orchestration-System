<div align="center">

# APOS — Agentic Applicant Processing Orchestration System

**Fully autonomous AI hiring agent — scores, ranks, emails, detects cheating, and self-improves. No human in the loop.**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Gmail API](https://img.shields.io/badge/Gmail_API-v1-EA4335?style=flat&logo=gmail&logoColor=white)](https://developers.google.com/gmail/api)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat)](LICENSE)

[Overview](#overview) · [Architecture](#architecture) · [Components](#components) · [Installation](#installation) · [Usage](#usage) · [API Reference](#api-reference) · [Database Schema](#database-schema) · [Self-Learning](#self-learning) · [Deployment](#deployment)

</div>

---

## Overview

APOS is a production-grade autonomous hiring pipeline built for the GenoTek AI Agent Developer challenge. It handles the full lifecycle of applicant evaluation — from ingesting raw applicant data and scoring candidate quality, to driving multi-round email conversations, detecting AI-generated or plagiarised responses, and continuously adapting its scoring weights from accumulated data.

The system is designed to run 24/7 on a server with zero human involvement. Every decision it makes — scoring, emailing, flagging, eliminating — is logged to a SQLite database and used to improve future decisions.

### What it solves

| Problem | Solution |
|---|---|
| 1,140 applicants, no time to read them | Multi-factor scorer with tier assignment in < 1s per candidate |
| Internshala has no public API | Cookie-based authenticated async scraper with pagination |
| Candidates using ChatGPT | Phrase detection + regex pattern matching + embedding cosine similarity |
| Candidates sharing answers in WhatsApp groups | Pairwise Jaccard similarity across all candidates, copy ring detection |
| No context-aware recruiter follow-ups | Response parser + LLM-style conditional branching in email replies |
| System forgets what it learned | Adaptive weight updates stored in JSON, fed back into scorer |
| 50+ simultaneous email threads | SQLite thread tracking — every candidate email has a persistent thread ID |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           24/7 ORCHESTRATOR LOOP                                │
│                         src/orchestrator.py                                     │
│                     Runs every 300s (configurable)                              │
└──────────┬──────────────┬─────────────┬──────────────┬──────────────────────────┘
           │              │             │              │
           ▼              ▼             ▼              ▼
   ┌──────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
   │   ACCESS     │  │INTELLIG- │  │ENGAGEMENT│  │  ANTI-CHEAT  │
   │              │  │ENCE      │  │          │  │              │
   │ access_      │  │ scorer   │  │ email_   │  │ anti_cheat   │
   │ internshala  │  │ ranker   │  │ manager  │  │ ai_detector  │
   │              │  │ ai_det   │  │ gmail    │  │              │
   └──────┬───────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘
          │               │             │               │
          ▼               ▼             ▼               ▼
   applicants.csv   ranked_cand-   email_threads    strikes table
                    idates.json    + emails table   (auto-elim at 3)
                         │
                         ▼
               ┌──────────────────┐
               │  SELF-LEARNING   │
               │   learner.py     │
               │ adaptive_weights │
               │    .json         │
               └──────────────────┘
```

### Data Flow

```
Raw CSV / Internshala scrape
        │
        ▼
src/ingestion.py          load_data → validate_columns → clean_data
        │
        ▼
src/ai_detector.py        detect_ai_response → float confidence score
        │
        ▼
src/scorer.py             score_candidate → (int score, str reason)
        │
        ▼
src/ranker.py             get_tier → Fast-Track | Standard | Review | Reject
        │
        ├──────────────────────────────────────────────────┐
        ▼                                                  ▼
src/email_manager.py      create_thread (idempotent)    src/anti_cheat.py
src/response_generator    generate_r1_email             find_copy_rings
src/gmail_integration     send_email                    analyze_response_timing
        │                                               auto_flag_copy_rings
        │                                                  │
        ▼                                                  ▼
logs/interactions.db      all state persisted         strikes table
        │
        ▼
src/learner.py            analyze_r1_to_r2_correlation
                          update_scoring_weights
                          → logs/adaptive_weights.json
```

---

## Components

### Component 1 — ACCESS: `src/access_internshala.py`

Handles authenticated data extraction from Internshala without an official API.

**Why not Playwright/Selenium?**  
Internshala uses Google reCAPTCHA Enterprise (invisible variant). Headless browsers pass field filling but the POST request is blocked server-side before the session cookie is ever issued. The server detects non-human clients silently — HTTP 200 returns but no auth cookie is set.

**Why not browser extension cookie export?**  
Chrome extension APIs block `httpOnly` cookies — they return `[BLOCKED]` instead of the value. Internshala's session cookie is `httpOnly`, so extensions are useless for this.

**What actually works:**  
DevTools → Application → Cookies has native access (bypasses extension restrictions). The raw cookie value is copied and passed via environment variables. The scraper sends authenticated GET requests via `aiohttp` and parses HTML with `BeautifulSoup`.

```python
# Set your cookies as environment variables before running
export INTERNSHALA_SESSION="session=YOUR_SESSION_VALUE"
export INTERNSHALA_BANNER="banner=YOUR_BANNER_VALUE"
export INTERNSHALA_USER="user=YOUR_USER_VALUE"
export INTERNSHALA_JOB_URL="https://internshala.com/employers/applications/..."
export INTERNSHALA_PAGES=57
```

**IP-binding caveat:**  
Session cookies are bound to the originating IP. The scraper must run from the same IP where the cookie was created (your local machine, or a matching proxy). Using the cookie from a remote server returns HTTP 403.

**Pagination:**  
`fetch_all_applicants()` iterates `?page=1` through `?page=N` with a 1-second rate limit between requests. Failed pages are logged and skipped — the rest of the batch continues.

```python
from src.access_internshala import fetch_all_applicants, export_applicants
import asyncio

applicants = asyncio.run(fetch_all_applicants(base_url="https://internshala.com/...", pages=57))
export_applicants(applicants)
# → output/scraped_applicants.csv
```

---

### Component 2 — INTELLIGENCE: `src/scorer.py` + `src/ranker.py`

Multi-factor candidate scoring. Each candidate gets a numeric score and a human-readable reason string.

**Scoring rubric:**

| Factor | Points | Logic |
|---|---|---|
| Skill match | +10 per match, capped at +30 | Tokenises `skills` field, checks against required_skills list |
| Valid GitHub | +20 | Regex: `https?://github\.com/[\w-]+` |
| Detailed answer | +30 | Word count ≥ 30 |
| Moderate answer | +15 | Word count 15–29 |
| Short answer | +5 | Word count < 15 |
| AI-generated content | −(20 × confidence) | From `ai_detector.py` confidence score |
| Fast response | −10 | `response_time` < 5 minutes |
| Missing skills | −15 | `skills` field empty |
| Missing GitHub | −15 | `github` field empty or invalid |
| Missing answer | −15 | `answer` field empty |

All scores are floor-clamped at 0.

**Tier thresholds:**

```python
TIER_THRESHOLDS = {
    "Fast-Track": 75,   # top candidates, immediate deep-dive
    "Standard":   60,   # solid candidates, proceed to R1
    "Review":     40,   # borderline, human spot-check
    # below 40 → Reject
}
```

**Example output:**
```json
{
  "name": "Rahul",
  "email": "rahul@gmail.com",
  "score": 65,
  "tier": "Standard",
  "reason": "Matched 3 relevant skills; Valid GitHub profile; Moderate answer length"
}
```

---

### Component 3 — ENGAGEMENT: `src/email_manager.py` + `src/gmail_integration.py` + `src/response_generator.py`

Fully autonomous multi-round email conversations with per-candidate context tracking.

**Thread tracking:**

Every candidate gets one row in `email_threads` (inserted via `INSERT OR IGNORE` — idempotent, safe to re-run). The `current_round` column tracks which round the conversation is in. All emails for one candidate share a thread ID via Gmail's `In-Reply-To` / `References` headers — replies stay in the same thread in the candidate's inbox.

**Contextual response generation:**

`analyze_response_for_context()` parses the candidate's reply for:

- Technologies mentioned (`selenium`, `playwright`, `python`, `api`, etc.)
- First-person project references (`I built`, `I created`, `I developed`)
- Response length bucket (`detailed` / `moderate` / `short`)
- Candidate asking a question back (`?` present in reply)

The follow-up email adapts based on what was found:

```python
# If candidate mentioned a specific tech → ask them to go deeper on it
# If candidate asked a question → answer it, then ask a deeper one
# If response was short → ask for a specific project story
# Default → ask for a technical challenge they solved
```

**Gmail API setup:**

```bash
# 1. Enable Gmail API in Google Cloud Console
# 2. Download credentials.json to project root
# 3. Run auth flow once to generate token.pickle
python -c "from src.gmail_integration import get_gmail_service; get_gmail_service()"
# 4. Set credentials path in env
export GMAIL_CREDENTIALS_PATH="credentials.json"
```

The orchestrator degrades gracefully if Gmail is not configured — scoring and anti-cheat continue, email sending is skipped with a warning.

---

### Component 4 — ANTI-CHEAT: `src/anti_cheat.py` + `src/ai_detector.py`

Three independent detection methods. Each fires a strike on the candidate's record. At 3 strikes, the candidate is auto-eliminated — `email_threads.status` is set to `eliminated`, stopping all further contact.

#### 4a. AI-Generated Response Detection (`src/ai_detector.py`)

Two-layer detection — phrase matching + regex pattern matching.

**Phrase list** (from `config.py`):
```python
AI_PHRASES = [
    "I'd be happy to help",
    "comprehensive overview",
    "in today's rapidly evolving",
    "as an AI language model",
    "here is a detailed explanation",
    "Certainly!",
    "Here's a",
    "Below is",
    ...
]
```

Each phrase match adds `+0.30` to a confidence float, capped at `1.0`.

**Regex patterns** (structural fingerprints):
```python
patterns = [
    r"^here (is|are)",
    r"^certainly",
    r"as an (ai|language model)",
    r"i'd (be|glad|happy)",
    r"comprehensive",
    r"step-by-step",
    r"in today's rapidly",
]
```

Each pattern match adds `+0.20`, capped at `0.60`. Long answers (100+ words) with 2+ phrase matches get an additional `+0.20` boost. Confidence > 0.50 triggers an AI strike.

**High-precision alternative** — embedding cosine similarity:

```python
from src.anti_cheat import find_similar_with_embeddings

# Compares candidate answer against fresh LLM output using sentence-transformers
# Threshold 0.80 = likely AI-generated
pairs = find_similar_with_embeddings(candidates, threshold=0.80)
```

Requires `sentence-transformers` installed. Falls back to token overlap automatically if not available.

#### 4b. Cross-Candidate Copy Ring Detection

`find_copy_rings()` computes pairwise Jaccard similarity across every candidate's answer:

```
similarity = |tokens_A ∩ tokens_B| / |tokens_A ∪ tokens_B|
```

Threshold: `0.60`. If 3+ candidates exceed the threshold against each other, they are flagged as a copy ring. All members get a `copy_ring` strike.

The similarity matrix is cached in `similarity_cache` table — pairs already computed are not recomputed on the next loop iteration.

```python
from src.anti_cheat import find_copy_rings

rings = find_copy_rings(candidates)
# Returns: [["a@test.com", "b@test.com", "c@test.com"], ...]
```

**Test result:**
```
Found 1 ring: ['a@test.com', 'b@test.com', 'c@test.com']
✅ PASS: 3 identical answers correctly detected as copy ring
```

#### 4c. Timing Analysis

`analyze_response_timing()` flags suspiciously fast replies:

| Condition | Verdict | Confidence |
|---|---|---|
| < 2 min + > 100 words | Suspicious | 0.9 |
| < 1 min any length | Suspicious | 0.7 |
| > 80 WPM typing speed | Suspicious | 0.6 |
| Otherwise | Normal | 0.0 |

```python
from src.anti_cheat import analyze_response_timing

result = analyze_response_timing(response_time_minutes=1.0, answer_length=150)
# → {"is_suspicious": True, "reason": "Response time 1.0min with 150 words is unusually fast", "confidence": 0.9}
```

#### 4d. Strike System

```python
from src.anti_cheat import add_strike, get_candidate_strikes

strike_count = add_strike(
    candidate_email="candidate@gmail.com",
    strike_type="ai_generated",       # or "copy_ring", "timing"
    evidence="87% phrase match",
    confidence=0.87
)

# At strike_count >= 3: email_threads.status → "eliminated"
# Orchestrator skips eliminated candidates in all future loops
```

---

### Component 5 — SELF-LEARNING: `src/learner.py`

The system gets smarter with every batch of candidates it processes.

**Interaction logging:**

Every scoring decision is logged to `interactions` table:
```python
log_interaction(email, round_num=1, score=65, tier="Standard", reason="...", responded=True)
```

**Adaptive weight updates** (run every 4 orchestrator iterations):

`analyze_r1_to_r2_correlation()` joins R1 and R2 scores per candidate:

- If `low_r1_high_r2 > 5` → skill matching is underweighted, answer length is overweighted → `skill_weight *= 1.1`, `answer_length_weight *= 0.95`
- Insights appended to `adaptive_weights.json`, last 10 kept

```json
{
  "skill_weight": 1.1,
  "github_weight": 1.0,
  "answer_length_weight": 0.95,
  "insights": [
    {
      "type": "r1_misses_gems",
      "data": "7 low-R1 candidates improved significantly in R2"
    }
  ]
}
```

**Queryable insights:**

```python
from src.learner import get_top_thinking_candidates, get_most_common_approach, analyze_patterns

# "Which 3 candidates showed the most original thinking?"
top = get_top_thinking_candidates(n=3)

# "What is the most common first approach candidates try?"
approach = get_most_common_approach()
# → {"approach": "selenium_playwright", "count": 412}

# "What's the overall pattern across all processed candidates?"
analysis = analyze_patterns()
# → {"average_score": 47.3, "tier_distribution": {"Reject": 521, "Review": 489, ...}, "patterns": [...]}
```

---

### Component 6 — ORCHESTRATOR: `src/orchestrator.py`

The 24/7 runtime loop that connects all components.

**Loop sequence (every iteration):**

```
1. process_new_candidates()
   └── load CSV → score → rank → write output JSON → create email threads → log interactions

2. run_anti_cheat_checks()
   └── pairwise copy ring detection → auto-flag → add strikes

3. check_incoming_emails()
   └── fetch unread Gmail → match to thread → generate contextual reply → send → log decision

4. send_followup_emails()
   └── iterate active threads → generate R1/followup email → send → log

5. update_learning_models()  [every 4th iteration]
   └── R1→R2 correlation → update adaptive weights → log insights
```

**Fault tolerance:**

- Any component failure is caught and logged — the loop continues to the next iteration
- All state is in `interactions.db` — a restart picks up from the current file state
- No candidate can fall through: `create_thread()` uses `INSERT OR IGNORE`, so re-processing the same CSV never duplicates threads

---

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+ (optional, for API server)
- Gmail API credentials (optional, for email features)

### Setup

```bash
# Clone the repository
git clone https://github.com/Sudharsanselvaraj/Agentic-Applicant-Processing-Orchestration-System
cd Agentic-Applicant-Processing-Orchestration-System

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Install optional embedding model (for high-precision similarity)
pip install sentence-transformers

# Verify installation
PYTHONPATH=. python -c "from src.orchestrator import run_once; run_once()"
```

### Environment Variables

Create a `.env` file in the project root:

```env
# ── INTERNSHALA ACCESS ──────────────────────────────────────────────
# Get from: DevTools (F12) → Application → Cookies → internshala.com
INTERNSHALA_SESSION=session=YOUR_SESSION_COOKIE_VALUE
INTERNSHALA_BANNER=banner=YOUR_BANNER_VALUE
INTERNSHALA_USER=user=YOUR_USER_VALUE
INTERNSHALA_JOB_URL=https://internshala.com/employers/applications/YOUR_JOB_ID
INTERNSHALA_PAGES=57

# ── GMAIL ────────────────────────────────────────────────────────────
GMAIL_CREDENTIALS_PATH=credentials.json

# ── ORCHESTRATOR ─────────────────────────────────────────────────────
LOOP_INTERVAL_SECONDS=300   # How often the main loop runs (default: 5 min)
```

---

## Usage

### Run the full 24/7 orchestrator

```bash
PYTHONPATH=. python src/orchestrator.py
```

### Run a single iteration (for testing)

```bash
PYTHONPATH=. python src/orchestrator.py --once
```

### Run only the scoring pipeline

```bash
PYTHONPATH=. python src/main.py
```

### Run the REST API server

```bash
PYTHONPATH=. uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

### Scrape Internshala applicants directly

```bash
# Set cookies in env first, then:
PYTHONPATH=. python src/access_internshala.py
# → output/scraped_applicants.csv
```

### Run anti-cheat checks standalone

```python
from src.anti_cheat import check_all_candidates
from src.ingestion import load_data, clean_data

df = clean_data(load_data("data/applicants.csv"))
candidates = df.to_dict("records")
results = check_all_candidates(candidates)
print(results)
# → {"total": 1140, "copy_rings": [...], "flagged": [...]}
```

---

## API Reference

Base URL: `http://localhost:8000`

### `POST /score`

Score a single candidate.

**Request body:**
```json
{
  "name": "Rahul Sharma",
  "skills": "Python, ML, SQL",
  "github": "https://github.com/rahulsharma",
  "answer": "I would approach this by first analysing the HTTP request structure...",
  "response_time": 15.0
}
```

**Response:**
```json
{
  "name": "Rahul Sharma",
  "score": 65,
  "tier": "Standard",
  "reason": "Matched 3 relevant skills; Valid GitHub profile; Moderate answer length"
}
```

**Tier values:** `Fast-Track` | `Standard` | `Review` | `Reject`

---

### `GET /health`

Health check.

**Response:**
```json
{"status": "ok"}
```

---

## Database Schema

All persistent state lives in `logs/interactions.db` (SQLite). The file survives restarts — the orchestrator always picks up from where it left off.

```sql
-- Every scoring decision ever made
CREATE TABLE interactions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_email  TEXT,
    round_number     INTEGER,
    score            REAL,
    tier             TEXT,
    reason           TEXT,
    responded        INTEGER,              -- 1 = replied, 0 = no reply
    timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Adaptive scoring insights
CREATE TABLE scoring_insights (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_type TEXT,
    data         TEXT,
    timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Per-candidate email thread state
CREATE TABLE email_threads (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_email  TEXT NOT NULL UNIQUE,
    candidate_name   TEXT,
    current_round    INTEGER DEFAULT 0,
    last_contact     DATETIME,
    status           TEXT DEFAULT 'active'  -- 'active' | 'eliminated' | 'hired'
);

-- Every email sent or received
CREATE TABLE emails (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id      INTEGER,
    sender         TEXT,
    recipient      TEXT,
    subject        TEXT,
    body           TEXT,
    timestamp      DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_ai_generated INTEGER DEFAULT 0,
    FOREIGN KEY (thread_id) REFERENCES email_threads(id)
);

-- Every hiring decision made
CREATE TABLE decision_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER,
    decision  TEXT,   -- 'sent_r1' | 'responded_r1' | 'eliminated' | 'fast_tracked'
    reason    TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES email_threads(id)
);

-- Anti-cheat strikes
CREATE TABLE strikes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_email  TEXT,
    strike_type      TEXT,   -- 'ai_generated' | 'copy_ring' | 'timing'
    evidence         TEXT,
    confidence       REAL,
    timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Similarity computation cache (avoids recomputing known pairs)
CREATE TABLE similarity_cache (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_a      TEXT,
    candidate_b      TEXT,
    similarity_score REAL,
    timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## Self-Learning

The adaptive weight system closes the feedback loop between early and late candidate evaluation.

```
Iteration 1–9:   Process candidates with base weights (all 1.0)
                 Log every decision to interactions table

Iteration 10+:   analyze_r1_to_r2_correlation() runs
                 → finds which R1 signals predicted good R2 performance
                 → updates skill_weight, github_weight, answer_length_weight
                 → writes to logs/adaptive_weights.json

Iteration 11+:   Scorer reads updated weights
                 → later candidates evaluated with learned preferences
```

**Example weight evolution:**

```json
// After 10 candidates (base)
{"skill_weight": 1.0, "answer_length_weight": 1.0}

// After 50 candidates (learned: short answers ≠ bad candidates)
{"skill_weight": 1.21, "answer_length_weight": 0.857}
```

**Queryable audit log:**

```python
from src.learner import analyze_patterns, suggest_improvements

analysis = analyze_patterns()
# → average score, tier distribution, detected patterns

improvements = suggest_improvements()
# → ["High rejection rate — review eligibility criteria",
#    "Insight: r1_misses_gems — 7 low-R1 candidates improved later"]
```

---

## Deployment

### Option 1 — systemd service (recommended for Linux VPS)

```bash
sudo nano /etc/systemd/system/apos.service
```

```ini
[Unit]
Description=APOS — Agentic Applicant Processing Orchestration System
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/apos
EnvironmentFile=/home/ubuntu/apos/.env
ExecStart=/home/ubuntu/apos/venv/bin/python src/orchestrator.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable apos
sudo systemctl start apos
sudo systemctl status apos

# View live logs
journalctl -u apos -f
```

### Option 2 — screen / tmux (quick setup)

```bash
screen -S apos
PYTHONPATH=. python src/orchestrator.py
# Ctrl+A, D to detach
# screen -r apos to reattach
```

### Option 3 — Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV PYTHONPATH=/app
CMD ["python", "src/orchestrator.py"]
```

```bash
docker build -t apos .
docker run -d \
  --env-file .env \
  --name apos \
  --restart unless-stopped \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/output:/app/output \
  apos
```

---

## Folder Structure

```
Agentic-Applicant-Processing-Orchestration-System/
├── api/
│   └── server.py                   FastAPI REST endpoint (/score, /health)
├── data/
│   ├── applicants.csv              Input: raw applicant data
│   ├── applicants_test.csv         Test dataset (10 synthetic candidates)
│   └── cookies.json                Internshala session cookies (gitignored)
├── logs/
│   ├── interactions.db             SQLite — all state, 7 tables
│   └── orchestrator.log            Timestamped run log
├── output/
│   ├── ranked_candidates.csv       Scored + ranked output
│   └── ranked_candidates.json      Same data as JSON
├── src/
│   ├── __init__.py                 Auto-initialises all DB tables on import
│   ├── access_internshala.py       Cookie-based Internshala scraper
│   ├── ai_detector.py              Phrase + regex AI content detection
│   ├── anti_cheat.py               Copy rings, timing analysis, strike system
│   ├── config.py                   All constants + directory setup
│   ├── email_manager.py            SQLite thread tracking for email conversations
│   ├── get_cookies.py              Cookie extraction helper
│   ├── gmail_integration.py        Gmail API send/receive
│   ├── ingestion.py                CSV/Excel loader with validation + cleaning
│   ├── learner.py                  Adaptive weight updates, R1→R2 correlation
│   ├── logger.py                   DB interaction logging
│   ├── main.py                     Standalone scoring pipeline entry point
│   ├── orchestrator.py             24/7 main loop — connects all components
│   ├── ranker.py                   Tier assignment from score
│   ├── response_generator.py       Context-aware follow-up email generation
│   ├── scorer.py                   Multi-factor candidate scoring
│   └── test_browser.py             Browser automation test harness
├── EXECUTION_EVIDENCE.md           Real test output with pass/fail verdicts
├── INTERNSHALA_TEST_GUIDE.md       Step-by-step cookie extraction guide
├── README.md                       This file
├── requirements.txt
├── run.sh                          Shell launcher
└── SUBMISSION.md                   GenoTek challenge response
```

---

## Input Data Format

The scorer expects a CSV with these columns:

| Column | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Candidate full name |
| `email` | string | Yes | Contact email (thread key) |
| `skills` | string | Yes | Comma-separated skills |
| `github` | string | No | GitHub profile URL |
| `answer` | string | No | Answer to screening question |
| `response_time` | float | No | Minutes between email sent and reply received |

Missing columns raise `ValueError`. Missing values in optional columns are filled with empty string — the scorer penalises them rather than crashing.

---

## Test Results

All tests were run against synthetic data. Full output in `EXECUTION_EVIDENCE.md`.

```
✅ Scoring system          10 candidates scored and tiered correctly
✅ AI detection            ChatGPT phrases detected at 60% confidence
✅ Copy ring detection     3 identical answers flagged as one ring
✅ Timing analysis         1-min / 150-word response flagged as suspicious
✅ Orchestrator full loop  All 5 components executed without error
✅ DB schema               All 7 tables created successfully
```

---

## Requirements

```
pandas
numpy
scikit-learn
sentence-transformers
fastapi
uvicorn
python-dotenv
google-api-python-client
google-auth
google-auth-oauthlib
aiohttp
beautifulsoup4
playwright
```

---

## Author

**Sudharsan S**  
ML Engineer Intern @ ALKF, Hong Kong (Remote)  
Pre-final year CSE @ SRMIST Trichy · CGPA 9.667 · BTech Honours in Quantum Computation  

**Hackathon track record:**  
National Winner — Smart India Hackathon 2025 (Hardware Edition, ₹1,50,000)  
AIR 62 / 6,223 — Amazon ML Challenge 2025  
Top 5 / 981 — EduTantr (OrbitXOS) · 1st — Protothon 1.0 SRMIST

GitHub: [github.com/Sudharsanselvaraj](https://github.com/Sudharsanselvaraj)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
