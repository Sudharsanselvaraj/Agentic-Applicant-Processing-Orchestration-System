# Internshala Full Integration Test Guide

## ⚠️ Prerequisites

You need:
1. A **real Internshala employer account** with active job postings
2. Access to applicant data (you must be the poster of the job)

---

## Step 1: Get Cookies from Your Browser

### Chrome/Edge
1. Go to **internshala.com** and log in as employer
2. Open **Developer Tools** (F12 or Right-click → Inspect)
3. Click **Application** tab (in Chrome) or **Storage** (in Edge)
4. Expand **Cookies** → Click **internshala.com**
5. Find and copy these cookies:
   - `session` (the main auth cookie)
   - `banner` (if present)
   - `_ga`, `_gid` (analytics - optional)

### Copy the Values
```
session = abc123xyz... (long string)
banner = xyz789...
```

---

## Step 2: Set Environment Variables

```bash
# Replace with YOUR actual cookie values (no spaces around =)
export INTERNSHALA_SESSION="session=YOUR_SESSION_COOKIE_VALUE"
export INTERNSHALA_BANNER="banner=YOUR_BANNER_VALUE"

# Your job URL from Internshala (employer dashboard → applications)
export INTERNSHALA_JOB_URL="https://internshala.com/employer/list/application/12345678"

# How many pages to fetch (57 pages = 1140 applicants)
export INTERNSHALA_PAGES=5
```

**Verify they're set:**
```bash
echo $INTERNSHALA_SESSION
echo $INTERNSHALA_JOB_URL
```

---

## Step 3: Test Connection to Internshala

```bash
cd /Users/sudharsan/Genotek
PYTHONPATH=. python3 -c "
import os
from src.access_internshala import get_cookies

cookies = get_cookies()
print('Cookies found:', list(cookies.keys()))
print('Session:', cookies.get('session', 'NOT FOUND')[:20] + '...')
"
```

**Expected output:**
```
Cookies found: ['session', 'banner']
Session: abc123xyz...
```

---

## Step 4: Fetch Applicants from Internshala

```bash
cd /Users/sudharsan/Genotek
PYTHONPATH=. python3 src/access_internshala.py
```

**Expected output:**
```
📄 Fetching page 1...
   Found 20 applicants
📄 Fetching page 2...
   Found 20 applicants
...
✅ Exported 100 applicants to output/scraped_applicants.csv
```

**If you get 403 Forbidden:**
- Cookies are expired → Re-login and get new cookies
- IP mismatch → Some employers block server IPs (common)

---

## Step 5: Run Full Pipeline on Scraped Data

Once you have `output/scraped_applicants.csv`:

```bash
cd /Users/sudharsan/Genotek
PYTHONPATH=. python3 << 'EOF'
import shutil
from pathlib import Path

# Copy scraped data to input
src = Path("output/scraped_applicants.csv")
dst = Path("data/applicants.csv")

if src.exists():
    shutil.copy(src, dst)
    print(f"✅ Copied {src} → {dst}")
else:
    print("❌ No scraped data found")
EOF
```

Then run the orchestrator:

```bash
PYTHONPATH=. python3 src/orchestrator.py --once
```

---

## Step 6: Check Results

```bash
# See ranked candidates
cat output/ranked_candidates.json | head -50

# See database stats
python3 -c "
import sqlite3
conn = sqlite3.connect('logs/interactions.db')
c = conn.cursor()
c.execute('SELECT tier, COUNT(*) FROM interactions GROUP BY tier')
for row in c.fetchall():
    print(f'{row[0]}: {row[1]}')
conn.close()
"
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `403 Forbidden` | Invalid/expired cookies | Re-login, get new session |
| `0 applicants found` | Wrong URL or HTML changed | Check job URL format |
| `No cookies found` | Env vars not set | Run export commands again |
| `reCAPTCHA detected` | Blocked by Internshala | Cookies don't work - need different approach |

---

## Alternative: If Cookies Don't Work

If Internshala blocks automated access, use this workaround:

1. **Manual export**: In Internshala dashboard → Applications → "Export CSV"
2. **Save as**: `data/applicants.csv` 
3. **Run pipeline**: `python3 src/orchestrator.py --once`

This bypasses the scraping issue entirely.

---

## What the Code Does

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Browser        │     │  access_          │     │  data/          │
│  (you login)    │────▶│  internshala.py   │────▶│  applicants.csv │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  orchestrator.py  │◀────│  scorer.py      │
                        │  (24/7 loop)      │     │  ranker.py      │
                        └──────────────────┘     └─────────────────┘
                                 │                       │
                                 ▼                       ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  output/          │     │  anti_cheat.py  │
                        │  ranked_*.json    │     │  learner.py     │
                        └──────────────────┘     └─────────────────┘
```

The system takes your scraped/exported applicant data and:
1. **Scores** each candidate (skills, GitHub, answer quality, AI detection)
2. **Ranks** them (Fast-Track / Standard / Review / Reject)
3. **Flags** cheating (copy rings, fast responses, AI-generated answers)
4. **Learns** over time (adaptive scoring)
5. **Sends** follow-up emails (when Gmail is configured)