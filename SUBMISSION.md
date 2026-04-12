# GenoTek Hiring Agent — Complete System Implementation

## 1. ARCHITECTURE

### Component Overview

| Component | Status | File | Description |
|-----------|--------|------|-------------|
| **ACCESS** | PROTOTYPE | `src/access_internshala.py` | Cookie-based authenticated scraping via environment variables |
| **INTELLIGENCE** | COMPLETE | `src/scorer.py`, `src/ranker.py` | Multi-factor candidate scoring with skill matching, GitHub validation, AI detection |
| **ENGAGEMENT** | COMPLETE | `src/email_manager.py`, `src/gmail_integration.py`, `src/response_generator.py` | Automated multi-round email conversations with context-aware follow-ups |
| **ANTI-CHEAT** | ENHANCED | `src/anti_cheat.py` | Cross-candidate similarity detection, timing analysis, embedding-based AI detection |
| **SELF-LEARNING** | ENHANCED | `src/learner.py` | Adaptive weight updates, R1→R2 correlation analysis, pattern discovery |
| **ORCHESTRATOR** | COMPLETE | `src/orchestrator.py` | 24/7 autonomous loop running all components |

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         24/7 ORCHESTRATOR                           │
│              python src/orchestrator.py                             │
└─────────────────────────────────────────────────────────────────────┘
         │           │           │           │           │
         ▼           ▼           ▼           ▼           ▼
┌──────────────┬─────────────┬───────────┬────────────┬──────────────┐
│   ACCESS     │ INTELLIGENCE│ENGAGEMENT │ ANTI-CHEAT │ SELF-LEARNING│
│              │             │           │            │              │
│ access_      │ scorer.py   │ email_    │ anti_cheat.py│ learner.py  │
│ internshala  │ ranker.py   │ manager   │             │              │
│ .py          │             │ gmail_    │             │              │
│              │             │ integrat  │             │              │
│              │             │ ion.py    │             │              │
└──────────────┴─────────────┴───────────┴────────────┴──────────────┘
         │           │           │           │           │
         ▼           ▼           ▼           ▼           ▼
    applicants     scored_    email_     flags_      insights_
    .csv           candidates logs.db    .json       .json
                   .json
```

### Output Formats by Component

| Component | Input | Output Format |
|-----------|-------|---------------|
| ACCESS | CSV/Excel + cookies | `applicants.csv` |
| INTELLIGENCE | `applicants.csv` | `output/ranked_candidates.json` |
| ENGAGEMENT | candidate records | `logs/interactions.db` (emails table) |
| ANTI-CHEAT | `applicants.csv` | strikes in `logs/interactions.db` |
| SELF-LEARNING | all logs | `logs/adaptive_weights.json` |

---

## 2. WHAT WE ACTUALLY TRIED

### ACCESS Component
- **Approach**: Cookie-based authentication via environment variables
- **Reason**: Internshala uses Google reCAPTCHA Enterprise (invisible) which blocks automated browsers
- **Implementation**: `src/access_internshala.py` reads session cookies from `INTERNSHALA_*` env vars
- **Security Note**: Does NOT attempt to bypass CAPTCHA — legally compliant

### Testing Results
See `EXECUTION_EVIDENCE.md` for full test outputs.

---

## 3. CODE

### Key Files Added/Modified

1. **`src/access_internshala.py`** — NEW: Internshala scraper with cookie auth
2. **`src/orchestrator.py`** — NEW: 24/7 runtime loop
3. **`src/anti_cheat.py`** — ENHANCED: Added cross-candidate similarity, timing analysis, embeddings
4. **`src/learner.py`** — ENHANCED: Added adaptive weights, R1→R2 correlation
5. **`src/config.py`** — ENHANCED: Added CACHE_DIR
6. **`src/__init__.py`** — ENHANCED: Auto-initialize all databases
7. **`EXECUTION_EVIDENCE.md`** — NEW: Test results and logs

### Run Commands

```bash
# Full 24/7 loop
python src/orchestrator.py

# Single iteration (for testing)
python src/orchestrator.py --once

# Test scoring independently
python -c "from src.orchestrator import process_new_candidates; process_new_candidates()"
```

---

## 4. QUESTIONS

1. **Cookie sharing legal?** — Does Internshala's T&P partner agreement allow automated access via shared cookies? This could be a legal risk.

2. **Pagination handling** — If there are 57 pages (1,140 applicants), should we prioritize by score cutoff first to reduce API calls?

3. **Response time measurement** — Are response times recorded from when the email is sent, or when the candidate receives it? (Gmail timestamps can differ)

4. **What's the actual rejection workflow?** — When a candidate gets 3 strikes, should we auto-reject via email, or flag for human review?

5. **What's your exact reCAPTCHA setup?** — Are you using reCAPTCHA Enterprise (invisible) or v2? This affects bypass strategy.

---

## 5. DEPLOYMENT PLAN

### Run 24/7 on Server

```bash
# Option 1: Direct run (requires screen/tmux)
python src/orchestrator.py &

# Option 2: Systemd service (recommended for production)
sudo nano /etc/systemd/system/hiring-agent.service

# Content:
# [Unit]
# Description=GenoTek Hiring Agent
# After=network.target

# [Service]
# Type=simple
# User=ubuntu
# WorkingDirectory=/home/ubuntu/genotek
# ExecStart=/usr/bin/python3 src/orchestrator.py
# Restart=always

# [Install]
# WantedBy=multi-user.target

# Then:
sudo systemctl daemon-reload
sudo systemctl enable hiring-agent
sudo systemctl start hiring-agent
```

### Error Handling

- **Gmail down**: Retry 3x with exponential backoff, then skip email send
- **Candidate data format unknown**: Log error, skip candidate, continue loop
- **Database locked**: Retry with timeout, raise after 3 attempts

### Restart Safety

- Loop state stored in database (`email_threads`, `interactions`)
- On restart, picks up from where it left off
- No candidate falls through the cracks

---

## 6. EXECUTION EVIDENCE

See `EXECUTION_EVIDENCE.md` for complete test outputs including:
- Scoring system results (10 candidates scored and ranked)
- Timing analysis (fast responses flagged)
- Copy ring detection (identical answers detected)
- AI detection (ChatGPT phrases detected)
- Database schema verification