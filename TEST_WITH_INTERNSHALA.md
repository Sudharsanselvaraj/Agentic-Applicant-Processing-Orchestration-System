# GenoTek Hiring Agent — Test with Real Internshala

## Quick Start

### Step 1: Extract Cookies (Browser Login)

```bash
cd /Users/sudharsan/Genotek
PYTHONPATH=. python3 src/get_cookies.py
```

This will:
1. Open a Chromium browser window
2. Navigate to Internshala
3. Wait for YOU to log in manually
4. Press ENTER to extract cookies
5. Save cookies to `data/cookies.json`

### Step 2: Run Full Pipeline

```bash
# Option A: Use extracted cookies to scrape
PYTHONPATH=. python3 src/access_internshala.py

# Option B: If scraping fails, use manual export
# (Download CSV from Internshala dashboard → save as data/applicants.csv)

# Run scoring + ranking
PYTHONPATH=. python3 src/orchestrator.py --once
```

---

## Full Workflow Test

```bash
cd /Users/sudharsan/Genotek

# 1. Open browser, log in to Internshala
PYTHONPATH=. python3 src/get_cookies.py

# 2. Verify cookies saved
ls -la data/cookies*

# 3. Try to fetch applicants (requires cookies)
PYTHONPATH=. python3 src/access_internshala.py

# 4. If scraping fails, use manual export
# Download from: Internshala Employer → Applications → Export CSV
# Save to: data/applicants.csv

# 5. Run full pipeline
PYTHONPATH=. python3 src/orchestrator.py --once

# 6. View results
cat output/ranked_candidates.json | python3 -m json.tool | head -30
```

---

## If Scraping Doesn't Work

Internshala may block server-side requests due to:
- IP mismatch (cookies are IP-bound)
- reCAPTCHA detection
- Anti-bot measures

**Solution: Manual Export**

1. Log into Internshala in your browser
2. Go to Employer Dashboard → Applications
3. Click "Export CSV"
4. Save the file as `data/applicants.csv`
5. Run: `PYTHONPATH=. python3 src/orchestrator.py --once`

This bypasses all scraping issues and uses official export feature.

---

## What Happens After

| Step | Output |
|------|--------|
| 1. Extract cookies | `data/cookies.json` |
| 2. Scrape applicants | `output/scraped_applicants.csv` |
| 3. Score & rank | `output/ranked_candidates.json` |
| 4. Anti-cheat check | Strikes in `logs/interactions.db` |
| 5. Email (optional) | If Gmail configured |