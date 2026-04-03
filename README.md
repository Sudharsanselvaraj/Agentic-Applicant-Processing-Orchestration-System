# GenoTek AI Hiring Agent — Candidate Scoring & Ranking System

## Project Overview

This project implements a modular component of an **Autonomous Hiring System** designed to automatically analyze, score, and rank job applicants.

The system processes applicant data from structured files (CSV/Excel), evaluates candidate responses using rule-based logic and text similarity analysis, and outputs ranked candidate lists with tier classifications.

This implementation focuses on:

- Candidate scoring
- AI-generated response detection
- Ranking and tier assignment
- Logging and learning from interactions
- Modular architecture
- Production-ready workflow

---

## Objective

Build a working prototype that demonstrates:

- Real execution
- Handling messy real-world data
- Scoring logic transparency
- AI response detection
- Continuous logging
- Scalable system design

This system is designed to simulate part of a fully autonomous hiring workflow.

---

## System Architecture

```
Scheduler
   |
   v
Data Ingestion
   |
   v
AI Detection
   |
   v
Scoring Engine
   |
   v
Ranking Engine
   |
   v
Database / Logs
   |
   v
Learning Engine
```

---

## Technology Stack

Language: Python 3.10+

Libraries:
- pandas
- numpy
- scikit-learn
- sentence-transformers
- sqlite3
- fastapi
- uvicorn
- python-dotenv
- google-api-python-client

---

## Folder Structure

```
genotek-agent/
├── data/
│   └── applicants.csv
├── output/
│   └── ranked_candidates.csv
├── logs/
│   └── interactions.db
├── src/
│   ├── config.py
│   ├── ingestion.py
│   ├── ai_detector.py
│   ├── scorer.py
│   ├── ranker.py
│   ├── logger.py
│   ├── learner.py
│   ├── email_manager.py
│   ├── anti_cheat.py
│   ├── gmail_integration.py
│   ├── response_generator.py
│   └── main.py
├── api/
│   └── server.py
├── requirements.txt
├── README.md
└── run.sh
```

---

## Components

### 1. Data Ingestion (`src/ingestion.py`)
- Read CSV or Excel files
- Validate schema
- Handle missing fields
- Normalize text

### 2. AI Detection (`src/ai_detector.py`)
- Phrase detection for AI-generated content
- Pattern matching for common AI fingerprints
- Confidence scoring

### 3. Scoring Engine (`src/scorer.py`)
- Skill match scoring (+30)
- Valid GitHub link scoring (+20)
- Detailed answer scoring (+30)
- AI penalty (-20)
- Fast response penalty (-10)
- Missing data penalty (-15)

### 4. Ranking Engine (`src/ranker.py`)
- Fast-Track: score >= 75
- Standard: score >= 60
- Review: score >= 40
- Reject: score < 40

### 5. Logging System (`src/logger.py`)
- SQLite database
- Logs every interaction

### 6. Anti-Cheat (`src/anti_cheat.py`)
- Strike system for detected cheating
- Similarity caching
- Cross-candidate detection

### 7. Email Manager (`src/email_manager.py`)
- Thread tracking
- Multi-round conversation management

### 8. Gmail Integration (`src/gmail_integration.py`)
- Send emails via Gmail API
- Fetch and parse incoming emails
- Thread management

### 9. Response Generator (`src/response_generator.py`)
- Generate contextual follow-up emails
- Analyze candidate responses
- Decision logic for next questions

### 10. Learning Engine (`src/learner.py`)
- Analyze patterns every 10 candidates
- Extract insights from interactions
- Suggest improvements

---

## Installation

```bash
git clone <repo-url>
cd genotek-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Usage

### Run scoring pipeline
```bash
PYTHONPATH=. python3 src/main.py
```

### Run API server
```bash
PYTHONPATH=. uvicorn api.server:app --reload
```

### Run scheduler
```bash
chmod +x run.sh
./run.sh
```

---

## Database Schema

```sql
-- Interactions log
CREATE TABLE interactions (
    id INTEGER PRIMARY KEY,
    candidate_name TEXT,
    email TEXT,
    score INTEGER,
    tier TEXT,
    reason TEXT,
    ai_detected REAL,
    timestamp DATETIME
);

-- Email threads
CREATE TABLE email_threads (
    id INTEGER PRIMARY KEY,
    candidate_email TEXT UNIQUE,
    candidate_name TEXT,
    current_round INTEGER,
    last_contact DATETIME,
    status TEXT
);

-- Emails
CREATE TABLE emails (
    id INTEGER PRIMARY KEY,
    thread_id INTEGER,
    sender TEXT,
    recipient TEXT,
    subject TEXT,
    body TEXT,
    timestamp DATETIME
);

-- Strikes (anti-cheat)
CREATE TABLE strikes (
    id INTEGER PRIMARY KEY,
    candidate_email TEXT,
    strike_type TEXT,
    evidence TEXT,
    confidence REAL,
    timestamp DATETIME
);

-- Similarity cache
CREATE TABLE similarity_cache (
    id INTEGER PRIMARY KEY,
    candidate_a TEXT,
    candidate_b TEXT,
    similarity_score REAL,
    timestamp DATETIME
);
```

---

## API Endpoints

### POST /score
```json
{
  "name": "Rahul",
  "skills": "Python, ML",
  "github": "https://github.com/rahul",
  "answer": "My solution is...",
  "response_time": 15
}
```

### GET /health
Returns `{"status": "ok"}`

---

## Author

Sudharsan S  
AI / Backend / Data Systems Developer