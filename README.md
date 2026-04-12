<div align="center">

# APOS — Agentic Applicant Processing Orchestration System

**Fully autonomous AI hiring agent — scores, ranks, emails, detects cheating, and self-improves. No human in the loop.**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Gmail API](https://img.shields.io/badge/Gmail_API-v1-EA4335?style=flat&logo=gmail&logoColor=white)](https://developers.google.com/gmail/api)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat)](LICENSE)

[Overview](#overview) · [What Changed in v2](#what-changed-in-v2) · [Architecture](#architecture) · [Components](#components) · [Installation](#installation) · [Usage](#usage) · [API Reference](#api-reference) · [Database Schema](#database-schema) · [Self-Learning](#self-learning) · [Deployment](#deployment)

</div>

---

## Overview

APOS is a production-grade autonomous hiring pipeline built for the GenoTek AI Agent Developer challenge. It handles the full lifecycle of applicant evaluation — from scraping Internshala via cookie-based authentication, scoring candidates with real GitHub API validation and embedding-based AI detection, driving multi-round email conversations with LLM-generated contextual replies, detecting cheaters through copy-ring analysis and timing forensics, and continuously adapting its scoring weights through a self-learning loop.

The system runs 24/7 on a server with zero human involvement. Every decision — scoring, emailing, flagging, eliminating — is persisted to SQLite with a full audit trail and used to improve future decisions.

### What it solves

| Problem | Solution |
|---|---|
| 1,140 applicants, no time to read them all | Multi-factor scorer with tier assignment in < 1s per candidate |
| Internshala has no public API and uses reCAPTCHA Enterprise | CDP attach to live Chrome + Playwright non-headless fallback |
| Chrome extensions block httpOnly cookies (`[BLOCKED]`) | `context.cookies()` via Playwright has native cookie store access |
| Session expires mid-scrape with no alert | `SessionExpiredException` + flag file + per-page checkpoint for resume |
| Candidates submitting empty GitHub profiles | Real `api.github.com` call — checks `public_repos`, `followers`, `last_updated` |
| Candidates using ChatGPT to write answers | Phrase fingerprints + embedding cosine similarity vs LLM reference answer |
| Candidates sharing answers in WhatsApp groups | Pairwise Jaccard similarity across all answers, auto-flag copy rings |
| Generic template follow-up emails | LLM-generated reply (Groq/Anthropic) reading candidate's actual response |
| Inbox flooded with non-candidate emails | Gmail label `APOS-Candidates` — only candidate replies are fetched |
| 50+ simultaneous email threads | SQLite thread tracking — one row per candidate, `INSERT OR IGNORE` |
| System forgets what it learned | `adaptive_weights.json` updated from R1→R2 correlation, persisted across restarts |

---

## What Changed in v2

This version fixes seven bugs present in the original submission and upgrades four components.

### Bugs Fixed

| # | File | Bug | Impact |
|---|---|---|---|
| 1 | `src/orchestrator.py` | `score, reason = score_candidate()` — missing third return value `details` | **Crash on first run** |
| 2 | `src/learner.py` | `get_top_thinking_candidates()` queried `reason LIKE '%question%'` — never matches scoring text | Always returned empty list |
| 3 | `src/orchestrator.py` | `check_incoming_emails()` called `thread.get("thread_id")` on a SQLite tuple | `AttributeError` on every reply |
| 4 | `data/applicants.csv` | Only weak candidates — no Fast-Track tier ever appeared in demo | Demo showed broken scoring |
| 5 | `src/access_internshala.py` | `fetch_page()` returned `None` on 403 silently | No alert, no checkpoint, empty data |
| 6 | `src/get_cookies.py` | CDP approach was missing entirely — old file was manual-only | Could not answer Bijoy's question |
| 7 | `Dockerfile` | `CMD ["python", "orchestrator.py"]` — wrong path | Container crashed immediately on start |

### Upgrades

| Component | v1 | v2 |
|---|---|---|
| GitHub validation | Regex URL check only — passes empty profiles | Real `api.github.com` call checking `public_repos`, `followers`, `last_updated` |
| AI detection | Phrase matching only | Phrase matching + embedding cosine similarity vs LLM reference (Groq/Anthropic) |
| Follow-up emails | `if/else` template selection | LLM-generated (Groq first, Anthropic fallback, template if no key) |
| Gmail inbox | Fetches ALL unread mail | Filtered by `APOS-Candidates` label — only candidate replies |
| Cookie extraction | Manual Playwright browser | CDP (`connect_over_cdp`) primary + Playwright non-headless fallback |
| Session expiry | Silent `None` on 403 | `SessionExpiredException` + `session_expired.flag` + page checkpoint |
| Pagination | No state between runs | `scrape_progress.json` — resumes from last successful page after re-auth |
| Deployment | No Docker | `Dockerfile` + `docker-compose.yml` with volume-mounted DB and restart policy |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        24/7 ORCHESTRATOR LOOP                        │
│                          src/orchestrator.py                         │
│                      Runs every 300s (configurable)                  │
└───────┬──────────────┬─────────────┬──────────────┬──────────────────┘
        │              │             │              │
        ▼              ▼             ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌──────────────────┐
│   ACCESS     │ │ INTELLIGENCE │ │ ENGAGEMENT │ │   ANTI-CHEAT     │
│              │ │              │ │            │ │                  │
│ get_cookies  │ │ scorer.py    │ │ email_mgr  │ │ anti_cheat.py    │
│ (CDP/PW)     │ │ ranker.py    │ │ response_  │ │ ai_detector.py   │
│ access_      │ │ ai_detector  │ │ generator  │ │                  │
│ internshala  │ │ github API   │ │ gmail_int  │ │ copy rings       │
│              │ │              │ │            │ │ timing analysis  │
└──────┬───────┘ └──────┬───────┘ └─────┬──────┘ └───────┬──────────┘
       │                │               │                │
       ▼                ▼               ▼                ▼
  cookies.json    ranked_cands    email_threads      strikes table
  progress.json   output JSON     emails table      (auto-elim at 3)
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
Raw CSV  /  Internshala scrape (aiohttp + BeautifulSoup, 57 pages)
        │
        ▼
src/ingestion.py          load_data → validate_columns → clean_data
        │
        ▼
src/scorer.py             check_github_profile (api.github.com)
                          detect_ai_response (phrases + embeddings)
                          score_candidate → (score, reason, details)
        │
        ▼
src/ranker.py             get_tier → Fast-Track | Standard | Review | Reject
        │
        ├──────────────────────────────────────────────────┐
        ▼                                                  ▼
src/email_manager.py      create_thread (INSERT OR IGNORE) src/anti_cheat.py
src/response_generator    LLM or template follow-up        find_copy_rings
src/gmail_integration     send + fetch (label filtered)    analyze_timing
                          mark_as_read                     auto_flag + strike
        │                                                  │
        └──────────────────────┬────────────────────────────┘
                               ▼
                    logs/interactions.db    (7 tables, full audit trail)
                               │
                               ▼
                    src/learner.py          analyze_r1_to_r2_correlation
                                            update_scoring_weights
                                            → logs/adaptive_weights.json
```

---

## Components

### Component 1 — ACCESS: `src/get_cookies.py` + `src/access_internshala.py`

Handles authenticated data extraction from Internshala without an official API.

#### Why every naive approach fails

| Approach | Failure Mode |
|---|---|
| Playwright headless | reCAPTCHA Enterprise fires before POST — form submits, HTTP 200 returns, but session cookie is never set. Navigation timeout. |
| Selenium + ChromeDriver | `navigator.webdriver = true` detected. Challenge fires silently. Identical outcome to Playwright headless. |
| EditThisCookie extension | Chrome extension API returns `[BLOCKED]` for `httpOnly` cookies. Internshala session IS `httpOnly`. Export is useless. |
| DevTools → copy-paste | Manual — not programmable. Breaks on session expiry with no detection or alert. |

#### What actually works — CDP (Chrome DevTools Protocol)

CDP attaches to an already-running Chrome instance. The user logs in once manually in that browser window. The script reads all cookies — including `httpOnly` — directly from the browser's native cookie store. reCAPTCHA is never touched because the login happened in a real, non-automated browser.

```bash
# Step 1: Start Chrome with remote debugging (separate terminal)
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_debug

# Step 2: Log in to Internshala in that Chrome window

# Step 3: Run APOS cookie extractor — CDP approach
python src/get_cookies.py --cdp

# Fallback if Chrome is not running:
python src/get_cookies.py --browser
# Opens a visible Chromium → log in manually → context.cookies() extracts all including httpOnly
```

`get_cookies.py` automatically saves to `data/cookies.json` and prints the `export INTERNSHALA_*` commands.

#### Session expiry detection

Sessions expire. The system detects it at three points and responds identically: raises `SessionExpiredException`, writes `data/session_expired.flag` with timestamp and instructions, and checkpoints the last successful page number to `data/scrape_progress.json` — pagination resumes from that page after re-auth, not from page 1.

| Trigger | HTTP Signal |
|---|---|
| `403 Forbidden` | IP mismatch or cookie invalid |
| Redirect to `/login` | Server terminated session |
| `200` but login form in body | Silent session drop — detected by scanning HTML for `name="login[email]"` |

```bash
# After re-auth, delete the flag to resume
rm data/session_expired.flag
python src/orchestrator.py --once
```

#### IP-binding caveat

Session cookies are bound to the originating IP. The scraper must run from the same machine where the cookie was extracted, or behind a residential proxy matching the login IP. Running the cookie from a server after extracting on a laptop returns HTTP 403.

#### Pagination

`fetch_all_applicants()` iterates `?page=1` through `?page=57` with a 1-second delay between requests. Each successful page writes to `scrape_progress.json`. Failed pages are logged and skipped — the rest of the batch continues.

---

### Component 2 — INTELLIGENCE: `src/scorer.py` + `src/ranker.py`

Multi-factor candidate scoring. Each candidate gets a numeric score, a human-readable reason string, and a details dict with GitHub API data and AI detection metadata.

#### Scoring rubric

| Factor | Points | Logic |
|---|---|---|
| Skill match | +10 per match, capped at +30 | Tokenises `skills` field against `required_skills` list |
| GitHub — active profile | +25 | `api.github.com` call: 10+ repos or 5+ followers |
| GitHub — moderate activity | +15 | 3–9 public repos |
| GitHub — low activity | +5 | 1–2 public repos |
| GitHub — 0 repos or not found | −15 | Empty profile or 404 |
| Detailed answer | +30 | Word count ≥ 30 |
| Moderate answer | +15 | Word count 15–29 |
| Short answer | +5 | Word count < 15 |
| AI-generated content | −(20 × confidence) | `ai_detector.py` score > 0.50 |
| Fast response | −10 | `response_time` < 5 minutes |
| Missing skills / GitHub / answer | −15 each | Field empty or invalid |

All scores are floor-clamped at 0. GitHub API results are cached in-memory per orchestrator run to avoid repeated calls for the same username.

#### Real GitHub API validation — why it matters

A simple URL regex passes `github.com/fakeperson123` with 0 repos. The real API call checks actual profile quality. The endpoint `api.github.com/users/{username}` is public — no token required. With a `GITHUB_TOKEN` env var the rate limit rises from 60 to 5,000 requests per hour.

```python
# What the API returns for check_github_profile():
{
    "score": 25,
    "reason": "GitHub: 47 repos, 312 followers — active",
    "details": {
        "public_repos": 47,
        "followers": 312,
        "account_age": "2018-03-14",
        "last_updated": "2026-04-10"
    }
}
```

#### Tier thresholds

```python
TIER_THRESHOLDS = {
    "Fast-Track": 65,   # priority R1 email next loop
    "Standard":   45,   # standard R1 email
    "Review":     25,   # held for manual spot-check
    # below 25 → Reject — no email sent
}
```

#### Real output (with network access, GitHub API live)

```
Arjun Menon     score=80  tier=Fast-Track   Matched 4 skills; GitHub: 47 repos, active; Detailed answer
Divya Sharma    score=70  tier=Fast-Track   Matched 3 skills; GitHub: 23 repos, active; Detailed answer
Karthik Raj     score=65  tier=Fast-Track   Matched 2 skills; GitHub: active; Detailed answer
Priya Singh     score=20  tier=Reject       AI-generated content (100%); Suspiciously fast response
Vikram Iyer     score=20  tier=Reject       AI-generated content (100%); Suspiciously fast response
Raj Kumar       score=10  tier=Reject       AI-generated content (100%); Suspiciously fast response
Neha Gupta      score= 0  tier=Reject       No GitHub; Short answer; Suspiciously fast response
```

---

### Component 3 — ENGAGEMENT: `src/email_manager.py` + `src/gmail_integration.py` + `src/response_generator.py`

Fully autonomous multi-round email conversations with per-candidate context tracking.

#### Thread management

Every candidate gets one row in `email_threads` via `INSERT OR IGNORE` — idempotent and safe to re-run. The `current_round` column tracks conversation stage. All emails for one candidate share a Gmail thread ID via `In-Reply-To` / `References` headers — replies stay threaded in the candidate's inbox.

#### Gmail label filtering

Every outbound email is tagged with the `APOS-Candidates` Gmail label (created automatically if absent). `fetch_unread_emails()` filters by this label — only candidate replies are fetched. Newsletters, spam, and unrelated mail are never processed.

#### LLM-powered follow-up generation

`response_generator.py` first tries Groq (`llama-3.1-8b-instant`, free) then falls back to Anthropic (`claude-haiku`), then falls back to template generation if no API key is set. The LLM prompt includes the candidate's actual reply and instructs the model to:

- Acknowledge one specific technical thing they mentioned
- Ask one deeper question that tests actual understanding
- Avoid generic phrases like "great response" or "thank you for sharing"

```python
# Candidate mentions CDP in their reply:
# LLM output →
"You mentioned connect_over_cdp() — did you run into the IP-binding
 issue where cookies from your laptop become invalid on a remote server?
 How would you handle that in a 24/7 deployment?"

# Template fallback would produce:
"Interesting that you mentioned playwright. Can you explain how you've
 used playwright in a real project?"
```

#### Gmail OAuth setup

```bash
# 1. Google Cloud Console → Enable Gmail API
# 2. OAuth consent screen → External → add your email as test user
# 3. Credentials → OAuth 2.0 Client ID → Desktop → Download JSON → save as credentials.json
# 4. One-time auth flow
python setup_gmail.py
# Browser opens → approve → token.pickle saved
# All future runs use token.pickle automatically
```

The orchestrator degrades gracefully if Gmail is not configured — scoring and anti-cheat continue, email sending is skipped.

---

### Component 4 — ANTI-CHEAT: `src/anti_cheat.py` + `src/ai_detector.py`

Three independent detection methods. Each adds a strike. At 3 strikes, `email_threads.status = 'eliminated'` — the orchestrator skips this candidate permanently.

#### 4a. AI-Generated Response Detection

**Layer 1 — Phrase fingerprints** (always runs, no API key needed):

```python
AI_PHRASES = [
    "I'd be happy to help",    "comprehensive overview",
    "in today's rapidly evolving",  "as an AI language model",
    "here is a detailed explanation",  "Certainly!",
    "Here's a",  "Below is",  "happy to help",  "I'd be glad to",
]
```

Each phrase match adds `+0.25` to the AI confidence score, capped at `0.75`. Regex structural patterns add `+0.15` each, capped at `0.45`. Long answers (100+ words) with 2+ phrase matches get `+0.15` boost. Confidence > 0.50 triggers an AI strike.

**Layer 2 — Embedding cosine similarity** (requires `GROQ_API_KEY` or `ANTHROPIC_API_KEY` + `USE_EMBEDDINGS=true`):

The same screening question (`screening_question` column) is submitted fresh to the LLM. Both answers — candidate's and LLM's — are embedded with `all-MiniLM-L6-v2`. Cosine similarity > 0.75 flags the answer as AI-generated.

```python
# Final score = max(phrase_score, embedding_similarity)
# Detailed output:
{
    "score": 0.91,
    "embedding_similarity": 0.91,
    "phrase_match_score": 0.60,
    "provider": "groq",
    "flagged": True
}
```

#### 4b. Cross-Candidate Copy Ring Detection

`find_copy_rings()` computes pairwise Jaccard token overlap across all candidate answers:

```
similarity = |tokens_A ∩ tokens_B| / |tokens_A ∪ tokens_B|
```

Threshold `0.60` for group rings (3+ candidates), `0.95` for direct pairs. All members of a detected ring get a `copy_ring` strike. Computed pairs are cached in `similarity_cache` to avoid recomputation on next loop.

```
# Real result from demo dataset:
Copy ring detected: ['priya@gmail.com', 'vikram@gmail.com', 'raj@gmail.com']
Similarity: 1.00 (identical text — same AI-generated paragraph submitted by all three)
All three receive copy_ring strike + AI detection strike = 2 strikes each
```

#### 4c. Response Timing Analysis

| Condition | Confidence | Strike |
|---|---|---|
| < 2 min AND > 100 words | 0.90 | `timing_suspicious` |
| < 1 min, any length | 0.70 | `timing_suspicious` |
| > 80 WPM typing speed | 0.60 | `timing_suspicious` |
| 15 min – 4 hours | 0.00 | None |

#### 4d. Strike System

```python
add_strike(candidate_email, strike_type, evidence, confidence)
# Inserts to strikes table
# Queries total strike count for this email
# At count >= 3: UPDATE email_threads SET status='eliminated'
# Orchestrator checks status before every send — eliminated candidates skipped permanently
```

---

### Component 5 — SELF-LEARNING: `src/learner.py`

Every interaction is logged. Every 4 orchestrator iterations, `update_scoring_weights()` runs.

**What gets logged:**

- Every `score_candidate()` call → `interactions` table
- Every email sent or received → `emails` table
- Every automated decision → `decision_log` table
- Every strike issued → `strikes` table
- Every similarity comparison → `similarity_cache` (avoids recomputing)

**Adaptive weight update logic:**

`analyze_r1_to_r2_correlation()` joins R1 and R2 scores per candidate. If `low_r1_high_r2 > 5` — meaning candidates who scored low in R1 consistently performed well in R2 — the system concludes that raw answer length is overweighted and skill match is underweighted:

```json
// Before (base weights)
{ "skill_weight": 1.0, "answer_length_weight": 1.0 }

// After learning from 50+ candidates
{ "skill_weight": 1.21, "answer_length_weight": 0.857,
  "insights": [{ "type": "r1_misses_gems",
                  "data": "8 low-R1 candidates improved in R2" }] }
```

Weights are persisted to `logs/adaptive_weights.json` and survive restarts.

**Queryable audit functions:**

```python
from src.learner import get_top_thinking_candidates, get_most_common_approach, analyze_patterns

# "Which 3 candidates showed most original thinking?"
get_top_thinking_candidates(n=3)
# → [{"email": "arjun@gmail.com", "score": 80, "tier": "Fast-Track"}, ...]

# "What % of candidates suggested Selenium first?"
get_most_common_approach()
# → {"approach": "selenium_playwright", "count": 412}

# Full pattern summary
analyze_patterns()
# → {"average_score": 47.3, "tier_distribution": {"Reject": 521, ...}, "patterns": [...]}
```

---

### Component 6 — ORCHESTRATOR: `src/orchestrator.py`

The 24/7 runtime loop that wires all components together.

**Loop sequence (every iteration):**

```
1. process_new_candidates()
   └── load CSV → score (3-tuple) → rank → write JSON → create threads → log interactions

2. run_anti_cheat_checks()
   └── pairwise Jaccard → auto-flag rings → add strikes → update eliminated status

3. check_incoming_emails()
   └── fetch unread (APOS-Candidates label) → match thread by email → LLM follow-up → send → mark read

4. send_followup_emails()
   └── iterate active threads → generate R1 email → send → log decision

5. update_learning_models()  [every 4th iteration]
   └── R1→R2 correlation → update adaptive_weights.json → log insights
```

**Fault tolerance:**

| Failure | Detection | Response |
|---|---|---|
| Gmail API down | Exception in `send_email()` | Retry 3x with backoff. Skip send, candidate stays active. |
| Session expired mid-scrape | `SessionExpiredException` | Flag file + checkpoint page + stop scraping only |
| Unknown CSV format | `validate_columns()` raises `ValueError` | Log error, skip iteration, loop continues |
| Database locked | `sqlite3.OperationalError` | `timeout=5` on all connections, 3 retries |
| Server restart | Process terminates | All state in `interactions.db` — loop restarts clean |
| GitHub API rate limit | `HTTPError 403` | Score 0 for GitHub signal only, log warning, continue |

---

## Installation

### Prerequisites

- Python 3.10+
- Gmail API credentials (for email features)
- Groq API key (free — for LLM follow-ups and embedding AI detection)

### Setup

```bash
# Clone
git clone https://github.com/Sudharsanselvaraj/Agentic-Applicant-Processing-Orchestration-System
cd Agentic-Applicant-Processing-Orchestration-System

# Virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# One-time Gmail auth
python setup_gmail.py
```

### Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
# ── GMAIL ────────────────────────────────────────────────────────
GMAIL_CREDENTIALS_PATH=credentials.json
HR_EMAIL=your.email@gmail.com
DEMO_CANDIDATE_EMAIL=your.test.inbox@gmail.com

# ── LLM (choose one — Groq is free) ─────────────────────────────
GROQ_API_KEY=gsk_your_key_here
# ANTHROPIC_API_KEY=sk-ant-...

# ── EMBEDDINGS (enables real AI detection) ───────────────────────
USE_EMBEDDINGS=true

# ── INTERNSHALA ──────────────────────────────────────────────────
INTERNSHALA_SESSION=your_session_cookie_value
INTERNSHALA_JOB_URL=https://internshala.com/employers/applications/YOUR_JOB_ID
INTERNSHALA_PAGES=57

# ── ORCHESTRATOR ─────────────────────────────────────────────────
LOOP_INTERVAL_SECONDS=300
```

---

## Usage

### Step 1 — Extract Internshala cookies

```bash
# CDP approach (preferred — fully programmatic)
# First, in a separate terminal:
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_debug
# Log in to Internshala in that Chrome window, then:
python src/get_cookies.py --cdp

# Playwright fallback (if Chrome not running)
python src/get_cookies.py --browser
```

### Step 2 — Single test run

```bash
python src/orchestrator.py --once
```

### Step 3 — 24/7 production loop

```bash
python src/orchestrator.py
```

### Scoring only

```bash
python src/main.py
# → output/ranked_candidates.csv
```

### REST API

```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

### Standalone anti-cheat

```python
from src.anti_cheat import check_all_candidates
from src.ingestion import load_data, validate_columns, clean_data

df = clean_data(validate_columns(load_data("data/applicants.csv")) or load_data("data/applicants.csv"))
results = check_all_candidates(df.to_dict("records"))
print(results)
# → {"total": 1140, "copy_rings": [...], "flagged": [...]}
```

---

## API Reference

Base URL: `http://localhost:8000`

### `POST /score`

Score a single candidate against the full rubric.

**Request:**
```json
{
  "name": "Arjun Menon",
  "skills": "Python, ML, SQL, aiohttp, FastAPI",
  "github": "https://github.com/arjunmenon",
  "answer": "I attempted Playwright headless first — reCAPTCHA blocked it at the POST level...",
  "response_time": 45.0
}
```

**Response:**
```json
{
  "name": "Arjun Menon",
  "score": 80,
  "tier": "Fast-Track",
  "reason": "Matched 4 relevant skills; GitHub: 12 repos, active; Detailed answer provided"
}
```

**Tier values:** `Fast-Track` | `Standard` | `Review` | `Reject`

### `GET /health`

```json
{"status": "ok"}
```

---

## Database Schema

All state lives in `logs/interactions.db`. Seven tables. The system restarts clean from this file — no candidate is ever lost.

```sql
-- Every scoring decision across all rounds
CREATE TABLE interactions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_email  TEXT,
    round_number     INTEGER,
    score            REAL,
    tier             TEXT,
    reason           TEXT,
    responded        INTEGER,        -- 1 = replied, 0 = no reply yet
    timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Per-candidate email thread state (one row per candidate)
CREATE TABLE email_threads (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_email  TEXT NOT NULL UNIQUE,
    candidate_name   TEXT,
    current_round    INTEGER DEFAULT 0,
    last_contact     DATETIME,
    status           TEXT DEFAULT 'active'   -- 'active' | 'eliminated' | 'completed'
);

-- Full email audit log
CREATE TABLE emails (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id        INTEGER,
    sender           TEXT,
    recipient        TEXT,
    subject          TEXT,
    body             TEXT,
    timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_ai_generated  INTEGER DEFAULT 0,
    FOREIGN KEY (thread_id) REFERENCES email_threads(id)
);

-- Every automated decision with timestamp
CREATE TABLE decision_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER,
    decision  TEXT,     -- 'sent_r1' | 'responded_followup' | 'eliminated' | 'fast_tracked'
    reason    TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES email_threads(id)
);

-- Anti-cheat strike ledger
CREATE TABLE strikes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_email  TEXT,
    strike_type      TEXT,   -- 'ai_generated' | 'copy_ring' | 'timing_suspicious'
    evidence         TEXT,
    confidence       REAL,
    timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Jaccard similarity cache (avoids recomputing known pairs)
CREATE TABLE similarity_cache (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_a      TEXT,
    candidate_b      TEXT,
    similarity_score REAL,
    timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Self-learning pattern discoveries
CREATE TABLE scoring_insights (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_type TEXT,
    data         TEXT,
    timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## Self-Learning

```
Iterations 1–4:   Process candidates with base weights (all 1.0)
                  Log every decision to interactions table

Iteration 4+:     analyze_r1_to_r2_correlation() runs
                  → finds which R1 signals predicted R2 performance
                  → updates weights in adaptive_weights.json

Iteration 8+:     Scorer reads updated weights
                  → later candidates evaluated with learned preferences
                  → insights rolling log (last 10 kept)
```

---

## Deployment

### Option 1 — Docker (recommended)

```bash
docker-compose up --build -d

# View logs
docker logs -f apos

# Check running containers
docker ps
```

`docker-compose.yml` runs two containers: `apos` (orchestrator loop) and `apos-api` (FastAPI). Both share `./data` and `./logs` as mounted volumes — `interactions.db` and `cookies.json` survive restarts and rebuilds.

### Option 2 — systemd (Linux VPS)

```ini
[Unit]
Description=APOS Hiring Agent
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/apos
EnvironmentFile=/home/ubuntu/apos/.env
ExecStart=/home/ubuntu/apos/venv/bin/python src/orchestrator.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable apos && sudo systemctl start apos
journalctl -u apos -f
```

### Option 3 — screen / tmux

```bash
screen -S apos
PYTHONPATH=. python src/orchestrator.py
# Ctrl+A, D to detach
```

---

## Folder Structure

```
Agentic-Applicant-Processing-Orchestration-System/
├── api/
│   └── server.py                   FastAPI REST endpoint (/score, /health)
├── data/
│   ├── applicants.csv              Input: raw applicant data (with screening_question column)
│   ├── cookies.json                Internshala session cookies — written by get_cookies.py
│   ├── scrape_progress.json        Pagination checkpoint — last successful page
│   └── session_expired.flag        Written on 403/redirect — delete after re-auth
├── logs/
│   ├── interactions.db             SQLite — all state, 7 tables
│   ├── orchestrator.log            Timestamped run log
│   └── adaptive_weights.json       Self-learning weights, updated every 4 iterations
├── output/
│   ├── ranked_candidates.csv       Scored + ranked output
│   └── ranked_candidates.json      Same data as JSON with details field
├── src/
│   ├── __init__.py
│   ├── access_internshala.py       Cookie-based async scraper + session expiry detection
│   ├── ai_detector.py              Phrase fingerprints + embedding cosine similarity
│   ├── anti_cheat.py               Copy rings, timing analysis, strike system
│   ├── config.py                   Constants, paths, tier thresholds
│   ├── email_manager.py            SQLite thread tracking (INSERT OR IGNORE)
│   ├── get_cookies.py              CDP primary + Playwright non-headless fallback
│   ├── gmail_integration.py        Gmail API: send, fetch (label-filtered), mark_as_read
│   ├── ingestion.py                CSV/Excel loader with column validation + cleaning
│   ├── learner.py                  Adaptive weights, R1→R2 correlation, audit queries
│   ├── logger.py                   DB logging helpers
│   ├── main.py                     Standalone scoring pipeline entry point
│   ├── orchestrator.py             24/7 main loop — connects all components
│   ├── ranker.py                   Tier assignment from score
│   ├── response_generator.py       LLM (Groq/Anthropic) + template follow-up generation
│   └── scorer.py                   Multi-factor scoring with real GitHub API validation
├── .env.example                    Environment variable template
├── demo_run.py                     Narrated step-by-step demo for screen recording
├── docker-compose.yml              Two containers: orchestrator + API server
├── Dockerfile                      Python 3.11-slim + Playwright
├── EXECUTION_EVIDENCE.md           Real test output with pass/fail verdicts
├── requirements.txt
├── setup_gmail.py                  One-time Gmail OAuth flow → saves token.pickle
└── run.sh                          Shell launcher
```

---

## Input Data Format

The scorer expects a CSV with these columns:

| Column | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Candidate full name |
| `email` | string | Yes | Contact email — used as thread key (must be unique) |
| `skills` | string | Yes | Comma-separated skills |
| `github` | string | No | GitHub profile URL — validated via `api.github.com` |
| `answer` | string | No | Answer to screening question |
| `response_time` | float | No | Minutes between email sent and reply received |
| `screening_question` | string | No | The question asked — used by AI detector for embedding comparison |

Missing required columns raise `ValueError`. Missing optional columns are filled with empty string — the scorer penalises missing data rather than crashing.

---

## Test Results

```
✅ Scoring pipeline        13 candidates scored, all 4 tiers produced
✅ GitHub API validation   Empty profiles caught, active profiles rewarded
✅ AI detection            100% confidence on ChatGPT-generated text (phrase layer)
✅ Copy ring detection     3-candidate ring detected (Priya, Vikram, Raj — identical answers)
✅ Timing analysis         Sub-minute replies flagged at 0.70–0.90 confidence
✅ Strike system           3-strike candidates set to 'eliminated' in email_threads
✅ Email threading         13 threads created, INSERT OR IGNORE verified idempotent
✅ Orchestrator --once     All 5 steps executed without error
✅ DB schema               All 7 tables created and populated correctly
✅ Session expiry          SessionExpiredException raised on 403, flag file written
✅ Adaptive weights        update_scoring_weights() runs, JSON persisted
```

Full output in `EXECUTION_EVIDENCE.md`.

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
playwright
aiohttp
beautifulsoup4
anthropic
```

Optional for free LLM follow-ups and embedding AI detection: Groq API key from [console.groq.com](https://console.groq.com) (free, no credit card).

---

## Author

**Sudharsan S**  
Pre-final year CSE @ SRMIST Trichy · CGPA 9.667 · BTech Honours in Quantum Computation

**Hackathon track record:**  
National Winner — Smart India Hackathon 2025 (Hardware Edition, ₹1,50,000)  
AIR 62 / 6,223 — Amazon ML Challenge 2025  
Top 5 / 981 — EduTantr (OrbitXOS) · 1st — Protothon 1.0 SRMIST

GitHub: [github.com/Sudharsanselvaraj](https://github.com/Sudharsanselvaraj)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
