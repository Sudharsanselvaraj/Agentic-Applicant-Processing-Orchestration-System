# GenoTek Hiring Agent — Complete Test Suite

## Prerequisites

```bash
pip install pandas numpy scikit-learn sentence-transformers beautifulsoup4 aiohttp
```

Note: Gmail integration requires Google credentials (optional for testing).

---

## Test 1: Unit Tests — Individual Components

```bash
# Test 1.1: Ingestion (load and validate data)
python3 -c "
from src.ingestion import load_data, validate_columns, clean_data
df = load_data('data/applicants.csv')
validate_columns(df)
df = clean_data(df)
print(f'✅ Loaded {len(df)} candidates')
"

# Test 1.2: Scoring
python3 -c "
from src.scorer import score_candidate
from src.ranker import get_tier
score, reason = score_candidate({'skills': 'python,sql', 'github': 'https://github.com/test', 'answer': 'I would use Selenium for automation with explicit waits.'})
tier = get_tier(score)
print(f'✅ Score: {score}, Tier: {tier}')
"

# Test 1.3: Anti-Cheat AI Detection
python3 -c "
from src.ai_detector import detect_ai_response
score = detect_ai_response(\"Here is a comprehensive overview. As an AI language model, I'd be happy to help you understand the design patterns in today's rapidly evolving tech landscape.\")
print(f'✅ AI Score: {score}')
"

# Test 1.4: Timing Analysis
python3 -c "
from src.anti_cheat import analyze_response_timing
result = analyze_response_timing(1, 150)
print(f'✅ Timing Flag: {result}')
"

# Test 1.5: Similarity Detection
python3 -c "
from src.anti_cheat import simple_similarity, find_copy_rings
sim = simple_similarity('I would use Selenium', 'I would use Selenium')
print(f'✅ Similarity: {sim}')
candidates = [
    {'email': 'a@test.com', 'answer': 'I would use Selenium to automate the browser'},
    {'email': 'b@test.com', 'answer': 'I would use Selenium to automate the browser'},
    {'email': 'c@test.com', 'answer': 'I would use Selenium to automate the browser'},
]
rings = find_copy_rings(candidates)
print(f'✅ Copy rings: {len(rings)}')
"

# Test 1.6: Learner Database
python3 -c "
from src.learner import analyze_patterns, init_learner_db
init_learner_db()
result = analyze_patterns()
print(f'✅ Patterns: {result}')
"

# Test 1.7: Email Manager
python3 -c "
from src.email_manager import init_email_db, create_thread, get_thread_by_email
init_email_db()
create_thread('test@example.com', 'Test User')
thread = get_thread_by_email('test@example.com')
print(f'✅ Thread created: {thread is not None}')
"
```

---

## Test 2: Integration Tests — Full Pipeline

```bash
# Test 2.1: Full Scoring Pipeline
python3 -c "
from src.ingestion import load_data, validate_columns, clean_data
from src.scorer import score_candidate
from src.ranker import rank_candidates

df = load_data('data/applicants.csv')
validate_columns(df)
df = clean_data(df)
candidates = df.to_dict('records')

scored = []
for c in candidates:
    score, reason = score_candidate(c)
    scored.append({**c, 'score': score, 'tier': get_tier(score)})

ranked = sorted(scored, key=lambda x: x['score'], reverse=True)
print(f'✅ Ranked {len(ranked)} candidates')
for r in ranked[:3]:
    print(f'   {r[\"name\"]}: {r[\"score\"]} ({r[\"tier\"]})')
"

# Test 2.2: Anti-Cheat Full Check
python3 -c "
from src.anti_cheat import check_all_candidates, auto_flag_copy_rings
import pandas as pd
df = pd.read_csv('data/applicants.csv')
candidates = df.to_dict('records')
results = check_all_candidates(candidates)
print(f'✅ Anti-cheat: {results[\"total\"]} candidates, {len(results[\"copy_rings\"])} rings')
"

# Test 2.3: Orchestrator Single Run
cd /Users/sudharsan/Genotek && python3 src/orchestrator.py --once
```

---

## Test 3: Mock Gmail (No Credentials Required)

```bash
# Create mock email data for testing without Gmail
mkdir -p data/mock
cat > data/mock/emails.json << 'EOF'
[
  {"from": "rahul@gmail.com", "subject": "Re: Application Status", "body": "Hi, thank you for the opportunity. I have experience with Python and Selenium. I can share code samples if needed.", "timestamp": "2026-04-05T10:00:00"},
  {"from": "priya@gmail.com", "subject": "Re: Application Status", "body": "Here is a comprehensive overview of the approach. As an AI language model I'd be happy to help.", "timestamp": "2026-04-05T10:05:00"}
]
EOF

python3 -c "
import json
from src.response_generator import generate_followup_email, analyze_response_for_context

with open('data/mock/emails.json') as f:
    emails = json.load(f)

for email in emails:
    context = analyze_response_for_context(email['body'])
    subject, body = generate_followup_email('Candidate', [email['body']], context)
    print(f'✅ Generated reply for {email[\"from\"]}')
"
```

---

## Test 4: End-to-End Simulation

```bash
# Simulate full candidate pipeline
python3 << 'EOF'
import json
from datetime import datetime

print("=" * 60)
print("GenoTek Hiring Agent — E2E Test")
print("=" * 60)

# Step 1: Load candidates
from src.ingestion import load_data, validate_columns, clean_data
df = load_data('data/applicants.csv')
validate_columns(df)
df = clean_data(df)
candidates = df.to_dict('records')
print(f"\n[1] Loaded {len(candidates)} candidates")

# Step 2: Score candidates
from src.scorer import score_candidate
from src.ranker import get_tier
scored = []
for c in candidates:
    score, reason = score_candidate(c)
    tier = get_tier(score)
    scored.append({**c, 'score': score, 'tier': tier, 'reason': reason})
print(f"[2] Scored {len(scored)} candidates")

# Step 3: Anti-cheat checks
from src.anti_cheat import check_all_candidates
cheat_results = check_all_candidates(candidates)
print(f"[3] Anti-cheat: {len(cheat_results['copy_rings'])} rings, {cheat_results['flagged']} flagged")

# Step 4: Rank and output
ranked = sorted(scored, key=lambda x: x['score'], reverse=True)
print(f"[4] Ranked candidates")

# Step 5: Log to database
from src.learner import log_interaction
for r in ranked[:3]:
    log_interaction(r['email'], 1, r['score'], r['tier'], r['reason'])
print(f"[5] Logged top 3 to database")

# Step 6: Save output
import os
os.makedirs('output', exist_ok=True)
with open('output/ranked_candidates.json', 'w') as f:
    json.dump(ranked, f, indent=2)
print(f"[6] Saved to output/ranked_candidates.json")

print("\n" + "=" * 60)
print("TIER DISTRIBUTION")
print("=" * 60)
tiers = {}
for r in ranked:
    t = r['tier']
    tiers[t] = tiers.get(t, 0) + 1
for tier, count in sorted(tiers.items()):
    print(f"  {tier}: {count}")

print("\n" + "=" * 60)
print("TOP 5 CANDIDATES")
print("=" * 60)
for r in ranked[:5]:
    print(f"  {r['name']}: {r['score']} ({r['tier']})")
    if 'AI' in r.get('reason', ''):
        print(f"    ⚠️ AI-generated detected")

print("\n✅ E2E Test Complete!")
EOF
```

---

## Test 5: Verify Database State

```bash
# Check all tables
python3 -c "
import sqlite3
conn = sqlite3.connect('logs/interactions.db')
cursor = conn.cursor()

tables = ['interactions', 'strikes', 'similarity_cache', 'email_threads', 'emails', 'decision_log', 'scoring_insights']
for table in tables:
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = cursor.fetchone()[0]
    print(f'{table}: {count} rows')
conn.close()
"
```

---

## Test 6: Run Orchestrator in Background

```bash
# Run full loop with 10 second interval (for testing)
LOOP_INTERVAL_SECONDS=10 python3 src/orchestrator.py

# Press Ctrl+C to stop
```

---

## Quick Test Summary

| Test | Command | Expected Result |
|------|---------|----------------|
| Scoring | `python3 -c "from src.scorer import score_candidate; print(score_candidate({'skills':'python,sql','github':'https://github.com/test','answer':'I would use Selenium'}))"` | (score, reason) |
| AI Detection | `python3 -c "from src.ai_detector import detect_ai_response; print(detect_ai_response('Here is a comprehensive overview as an AI language model'))"` | 0.6+ |
| Copy Ring | `python3 -c "from src.anti_cheat import find_copy_rings; print(find_copy_rings([{'email':'a','answer':'test'},{'email':'b','answer':'test'},{'email':'c','answer':'test'}]))"` | 1 ring |
| E2E | `python3 src/orchestrator.py --once` | Ranked output |
| Full Loop | `LOOP_INTERVAL_SECONDS=10 python3 src/orchestrator.py` | Continuous |