# GenoTek AI Hiring Agent — Execution Evidence

## Test Run 1: Scoring System

```
=== SCORING TEST ===
Rahul: score=65, tier=Standard
  Reason: Matched 3 relevant skills; Valid GitHub profile; Moderate answer length
Priya: score=40, tier=Review
  Reason: Matched 2 relevant skills; Valid GitHub profile; Detailed answer provided; AI-generated content detected (60%)
Akash: score=45, tier=Review
  Reason: Matched 1 relevant skills; Valid GitHub profile; Moderate answer length
Neha: score=0, tier=Reject
  Reason: No GitHub provided; Short answer; Suspiciously fast response
Vikram: score=35, tier=Reject
  Reason: Valid GitHub profile; Moderate answer length
Sneha: score=55, tier=Review
  Reason: Matched 2 relevant skills; Valid GitHub profile; Moderate answer length
Raj: score=32, tier=Reject
  Reason: Matched 1 relevant skills; Valid GitHub profile; Detailed answer provided; AI-generated content detected (60%)
Amit: score=0, tier=Reject
  Reason: Matched 1 relevant skills; No GitHub provided; Short answer
Priya2: score=40, tier=Review
  Reason: Matched 2 relevant skills; Valid GitHub profile; Detailed answer provided; AI-generated content detected (60%)
Ankit: score=45, tier=Review
  Reason: Matched 1 relevant skills; Valid GitHub profile; Moderate answer length
```

## Test Run 2: Timing Analysis

```
=== TIMING ANALYSIS TEST ===
Response: 1 min, 150 words -> is_suspicious=True, reason='Response time 1.0min with 150 words is unusually fast', confidence=0.9
Response: 90 min, 50 words -> is_suspicious=False, reason='Response timing appears normal', confidence=0.0

✅ PASS: Fast responses with long answers flagged as suspicious
```

## Test Run 3: Copy Ring Detection

```
=== SIMILARITY TEST ===
Rahul vs Ankit: 1.00 (identical answers)
Rahul vs Priya: 0.09 (completely different)

=== COPY RING WITH EXACT DUPLICATES ===
Found 1 ring: ['a@test.com', 'b@test.com', 'c@test.com']

✅ PASS: 3 identical answers correctly detected as copy ring
```

## Test Run 4: Orchestrator Full Loop

```
=== ORCHESTRATOR TEST ===
[2026-04-05T19:35:31.024451] [INFO] === PROCESSING NEW CANDIDATES ===
[2026-04-05T19:35:31.091895] [INFO] Scored 10 candidates
[2026-04-05T19:35:31.092099] [INFO] Fast-Track candidates: 0
Processed 10 candidates
Top 3:
  Rahul: 65 (Standard)
  Sneha: 55 (Review)
  Akash: 45 (Review)

=== TIER DISTRIBUTION ===
  Reject: 4
  Review: 5
  Standard: 1

=== ANTI-CHEAT CHECKS ===
[2026-04-05T19:35:41.931812] [INFO] === RUNNING ANTI-CHEAT CHECKS ===
[2026-04-05T19:35:41.957375] [INFO] Total candidates: 10
[2026-04-05T19:35:41.957649] [INFO] Copy rings found: 0

✅ PASS: Orchestrator runs successfully
```

## Test Run 5: AI Detection

```
Input: "Here is a comprehensive overview of the approach. As an AI language model, I'd be happy to help you understand the design patterns used in enterprise applications. In today's rapidly evolving tech landscape, it's important to consider scalability and maintainability."

AI Detection Score: 0.60
Flag: AI-generated content detected (60%)
Confidence: HIGH

✅ PASS: AI-generated phrases correctly detected
```

## Database Schema Verified

```
Tables created:
  - interactions
  - strikes
  - similarity_cache
  - email_threads
  - emails
  - decision_log
  - scoring_insights

✅ PASS: All tables created successfully
```

## Access Component Note

The ACCESS component uses cookie-based authentication. We tested with mock data since the actual Internshala scraping requires user-provided cookies via environment variables.

```
Authentication approach: Cookie-based via environment variables
  - INTERNSHALA_SESSION=session_value
  - INTERNSHALA_BANNER=banner_value
  - INTERNSHALA_USER=user_value

Note: System does NOT attempt to bypass CAPTCHA protections.
This approach is legal and production-safe.
```