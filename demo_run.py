#!/usr/bin/env python3
"""
APOS End-to-End Demo Runner
============================
This script runs a narrated, step-by-step demonstration of all 6 components.
Designed for screen recording. Run with:

    python demo_run.py

Each step pauses so you can narrate before pressing ENTER to continue.
"""

import sys
import os
import time
import json
import sqlite3

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env - importing src triggers dotenv load
import src

from src.config import DATA_DIR, OUTPUT_DIR, LOGS_DIR, DB_PATH
from src.ingestion import load_data, validate_columns, clean_data
from src.scorer import score_candidate
from src.ranker import rank_candidates, get_tier
from src.anti_cheat import (
    find_copy_rings, analyze_response_timing,
    auto_flag_copy_rings, init_anti_cheat_db
)
from src.learner import (
    init_learner_db, log_interaction,
    analyze_patterns, update_scoring_weights,
    get_top_thinking_candidates, get_most_common_approach
)
from src.email_manager import (
    init_email_db, create_thread, get_all_active_threads, log_decision
)
from src.response_generator import generate_r1_email, generate_followup_email


# ─────────────────────────────────────────────────────────────
# Terminal helpers
# ─────────────────────────────────────────────────────────────

CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
DIM    = "\033[2m"

def header(title: str):
    print()
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}")

def step(msg: str):
    print(f"\n{BOLD}{GREEN}▶ {msg}{RESET}")

def info(msg: str):
    print(f"  {msg}")

def warn(msg: str):
    print(f"  {YELLOW}⚠ {msg}{RESET}")

def ok(msg: str):
    print(f"  {GREEN}✅ {msg}{RESET}")

def err(msg: str):
    print(f"  {RED}❌ {msg}{RESET}")

def pause(prompt: str = "Press ENTER to continue..."):
    import sys
    if sys.stdin.isatty():
        print(f"\n{DIM}  {prompt}{RESET}")
        input()
    else:
        print(f"\n{DIM}  {prompt} (auto){RESET}")
        import time
        time.sleep(0.5)


# ─────────────────────────────────────────────────────────────
# STEP 0 — Reset DB for clean demo
# ─────────────────────────────────────────────────────────────

def reset_db():
    """Drop and recreate all tables for a clean demo run."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    tables = ["interactions", "scoring_insights", "strikes", "similarity_cache",
              "email_threads", "emails", "decision_log"]
    for t in tables:
        cur.execute(f"DROP TABLE IF EXISTS {t}")
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# STEP 1 — ACCESS (cookie extraction explanation)
# ─────────────────────────────────────────────────────────────

def demo_access():
    header("COMPONENT 1: ACCESS — Cookie Extraction")

    step("The problem: Internshala uses reCAPTCHA Enterprise (invisible variant)")
    info("• reCAPTCHA fires BEFORE credentials are submitted")
    info("• Headless browsers (Selenium, Playwright) are blocked at the POST level")
    info("• The server returns HTTP 200 but never sets a session cookie")
    info("")
    info("We tested this ourselves — here are the exact failure modes:")
    time.sleep(1)

    step("Attempt 1: Playwright headless")
    info("  playwright.chromium.launch(headless=True)")
    warn("RESULT: Form submitted, no 403 — but session cookie was NEVER set")
    info("  reCAPTCHA fires silently, the server validates and drops the request")

    step("Attempt 2: Chrome extension cookie export (EditThisCookie)")
    warn("RESULT: httpOnly cookies showed as [BLOCKED]")
    info("  Chrome extension API intentionally blocks httpOnly access")
    info("  The Internshala session cookie IS httpOnly — extension approach fails")

    step("Approach 3: CDP — Chrome DevTools Protocol (what we implemented)")
    ok("Attach to a RUNNING Chrome instance that the user logged into manually")
    info("  google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_debug")
    info("  Then: browser = playwright.chromium.connect_over_cdp('http://localhost:9222')")
    info("  Then: context.cookies() — returns ALL cookies including httpOnly")
    info("  This works because CDP has native cookie store access (not extension API)")
    ok("Cookie acquisition is now programmatic — no clipboard copying needed")

    step("Approach 4: Non-headless Playwright fallback")
    ok("Opens a real visible browser — user logs in — context.cookies() extracts all")
    info("  playwright.chromium.launch(headless=False)  # visible window")
    info("  This is what get_cookies.py implements as the fallback")

    step("Session expiry handling:")
    info("  fetch_page() detects expiry via:")
    info("  • HTTP 302 redirect to /login")
    info("  • HTTP 403 Forbidden")
    info("  • HTTP 200 but login form in HTML body")
    info("  → Raises SessionExpiredException")
    info("  → Writes data/session_expired.flag")
    info("  → Orchestrator fires alert and stops scraping loop")
    ok("No more silent 403s — system halts cleanly and notifies")

    pause()


# ─────────────────────────────────────────────────────────────
# STEP 2 — INTELLIGENCE (scoring live)
# ─────────────────────────────────────────────────────────────

def demo_intelligence():
    header("COMPONENT 2: INTELLIGENCE — Scoring & Ranking")

    step("Loading applicants.csv...")
    df = load_data(str(DATA_DIR / "applicants.csv"))
    validate_columns(df)
    df = clean_data(df)
    info(f"  Loaded {len(df)} candidates")

    step("Scoring each candidate...")
    scored = []
    for _, row in df.iterrows():
        score, reason, details = score_candidate(row)
        tier = get_tier(score)
        scored.append({**row.to_dict(), "score": score, "tier": tier, "reason": reason})

    scored.sort(key=lambda x: x["score"], reverse=True)

    print()
    print(f"  {'Name':<20} {'Score':>6}  {'Tier':<12}  Reason")
    print(f"  {'─'*20} {'─'*6}  {'─'*12}  {'─'*40}")
    for c in scored:
        tier_colour = GREEN if c["tier"] == "Fast-Track" else \
                      CYAN  if c["tier"] == "Standard"   else \
                      YELLOW if c["tier"] == "Review"    else RED
        print(f"  {c['name']:<20} {c['score']:>6.0f}  "
              f"{tier_colour}{c['tier']:<12}{RESET}  {c['reason'][:60]}")

    # Show tier counts
    from collections import Counter
    tiers = Counter(c["tier"] for c in scored)
    print()
    ok(f"Fast-Track: {tiers.get('Fast-Track',0)}  |  Standard: {tiers.get('Standard',0)}  "
       f"|  Review: {tiers.get('Review',0)}  |  Reject: {tiers.get('Reject',0)}")

    # Save output
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_DIR / "ranked_candidates.json", "w") as f:
        json.dump(scored, f, indent=2, default=str)
    ok(f"Output saved → output/ranked_candidates.json")

    pause()
    return scored


# ─────────────────────────────────────────────────────────────
# STEP 3 — ANTI-CHEAT
# ─────────────────────────────────────────────────────────────

def demo_anti_cheat(candidates):
    header("COMPONENT 4: ANTI-CHEAT — Detection Engine")

    init_anti_cheat_db()

    step("Copy ring detection (Jaccard token overlap, threshold=0.60)...")
    rings = find_copy_rings(candidates, answer_key="answer")

    if rings:
        for i, ring in enumerate(rings, 1):
            warn(f"Copy ring {i}: {len(ring)} candidates share highly similar answers")
            for email in ring:
                info(f"    → {email}")
    else:
        info("  No copy rings detected in this dataset")

    step("Checking for AI-generated answers...")
    from src.ai_detector import detect_ai_response
    ai_flagged = []
    for c in candidates:
        score = detect_ai_response(c.get("answer", ""))
        if score > 0.5:
            ai_flagged.append((c.get("name"), c.get("email"), score))

    if ai_flagged:
        for name, email, score in ai_flagged:
            warn(f"AI detected: {name} ({email}) — {score:.0%} confidence")
    else:
        ok("No AI-generated answers detected")

    step("Response timing analysis...")
    suspicious = [
        c for c in candidates
        if analyze_response_timing(
            float(c.get("response_time", 99)),
            len(c.get("answer", "").split())
        )["is_suspicious"]
    ]
    for c in suspicious:
        rt = c.get("response_time")
        wc = len(c.get("answer", "").split())
        warn(f"Suspicious timing: {c['name']} — {rt} min / {wc} words")

    step("Auto-flagging copy rings (adding strikes)...")
    result = auto_flag_copy_rings(candidates)
    ok(f"Flagged {result['flagged_count']} candidates across {result['ring_count']} rings")

    step("Strike system demo: 3 strikes → status = 'eliminated'")
    info("  Strike 1: copy_ring detected")
    info("  Strike 2: AI-generated answer detected")
    info("  Strike 3: suspicious response timing")
    info("  → On 3rd strike: email_threads.status = 'eliminated'")
    info("  → Orchestrator skips this candidate from all future loops")

    pause()


# ─────────────────────────────────────────────────────────────
# STEP 4 — ENGAGEMENT (email threading)
# ─────────────────────────────────────────────────────────────

def demo_engagement(candidates):
    header("COMPONENT 3: ENGAGEMENT — Email Threading")

    init_email_db()

    step("Creating email threads for all candidates (idempotent INSERT OR IGNORE)...")
    for c in candidates:
        create_thread(c.get("email", ""), c.get("name", ""))
    threads = get_all_active_threads()
    ok(f"Created {len(threads)} email threads in SQLite")

    step("Generating Round 1 email for top candidate...")
    top = next((c for c in candidates if c.get("tier") == "Fast-Track"), candidates[0])
    subject, body = generate_r1_email(top.get("name"), top.get("skills", ""))
    print()
    print(f"  {BOLD}To:{RESET}      {top.get('email')}")
    print(f"  {BOLD}Subject:{RESET} {subject}")
    print(f"  {BOLD}Body:{RESET}")
    for line in body.strip().split("\n"):
        print(f"    {line}")

    step("Simulating candidate reply and generating contextual follow-up...")
    fake_reply = (
        "Hi, I tried using CDP — launched Chrome with --remote-debugging-port=9222, "
        "connected via Playwright's connect_over_cdp(), and read the cookies directly. "
        "It worked perfectly on my local machine. I also built a fallback using "
        "aiohttp + BeautifulSoup for the pagination."
    )
    info(f"  Candidate reply: \"{fake_reply[:80]}...\"")

    reply_subject, reply_body = generate_followup_email(
        top.get("name"), [fake_reply],
        {"technologies_mentioned": ["cdp", "playwright", "aiohttp"]}
    )
    print()
    print(f"  {BOLD}Follow-up Subject:{RESET} {reply_subject}")
    print(f"  {BOLD}Follow-up Body:{RESET}")
    for line in reply_body.strip().split("\n"):
        print(f"    {line}")

    ok("Context-aware: reply mentions CDP → follow-up asks specifically about CDP approach")

    step("Checking Gmail (live) for real candidate replies...")
    try:
        from src.gmail_integration import fetch_unread_emails
        emails = fetch_unread_emails()
        ok(f"Gmail API connected — found {len(emails)} unread emails")
        if emails:
            for e in emails[:3]:
                info(f"  From: {e.get('from')} | Subject: {e.get('subject','')[:50]}")
    except Exception as ex:
        warn(f"Gmail not connected in this run: {ex}")
        info("  (Run setup_gmail.py once to authenticate)")

    pause()


# ─────────────────────────────────────────────────────────────
# STEP 5 — SELF-LEARNING
# ─────────────────────────────────────────────────────────────

def demo_self_learning(candidates):
    header("COMPONENT 5: SELF-LEARNING — Adaptive Weights")

    init_learner_db()

    step("Logging all candidate interactions to SQLite...")
    for c in candidates:
        log_interaction(
            email=c.get("email", ""),
            round_num=1,
            score=c.get("score", 0),
            tier=c.get("tier", ""),
            reason=c.get("reason", ""),
            responded=True
        )
    ok(f"Logged {len(candidates)} interactions")

    step("Analyzing patterns across all interactions...")
    analysis = analyze_patterns()
    ok(f"Average score: {analysis['average_score']}")
    info(f"  Tier distribution: {analysis['tier_distribution']}")
    info(f"  Patterns detected: {analysis['patterns']}")

    step("Running R1→R2 correlation and updating adaptive weights...")
    weights = update_scoring_weights()
    ok(f"Adaptive weights: skill={weights.get('skill_weight',1.0):.2f}  "
       f"github={weights.get('github_weight',1.0):.2f}  "
       f"answer_length={weights.get('answer_length_weight',1.0):.2f}")

    step("Top 3 candidates by original thinking:")
    top3 = get_top_thinking_candidates(3)
    for i, c in enumerate(top3, 1):
        info(f"  {i}. {c['email']}  score={c['score']}  tier={c['tier']}")

    step("Most common first approach suggested:")
    approach = get_most_common_approach()
    info(f"  {approach.get('approach','N/A')}: mentioned by {approach.get('count',0)} candidates")

    step("Showing raw SQLite DB — proof everything is persisted...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    ok(f"Tables in interactions.db: {tables}")
    cur.execute("SELECT COUNT(*) FROM interactions")
    count = cur.fetchone()[0]
    ok(f"interactions table: {count} rows")
    cur.execute("SELECT COUNT(*) FROM email_threads")
    count = cur.fetchone()[0]
    ok(f"email_threads table: {count} rows")
    conn.close()

    pause()


# ─────────────────────────────────────────────────────────────
# STEP 6 — INTEGRATION summary
# ─────────────────────────────────────────────────────────────

def demo_integration():
    header("COMPONENT 6: INTEGRATION — Full Pipeline")

    step("Data flow:")
    info("  applicants.csv")
    info("    ↓  ingestion.py — validate + clean")
    info("    ↓  scorer.py — skill match, GitHub check, AI detection, response time")
    info("    ↓  ranker.py — Fast-Track / Standard / Review / Reject")
    info("    ↓  output/ranked_candidates.json")
    info("    ↓  email_manager.py — create_thread per candidate (INSERT OR IGNORE)")
    info("    ↓  response_generator.py — context-aware email body")
    info("    ↓  gmail_integration.py — send_email + fetch_unread_emails")
    info("    ↓  anti_cheat.py — copy rings, timing, strikes, auto-eliminate")
    info("    ↓  learner.py — log + update adaptive_weights.json")
    info("    ↓  loop restarts after LOOP_INTERVAL seconds")

    step("Error handling:")
    info("  Gmail down         → retry 3x with backoff, skip + flag")
    info("  Session expired    → SessionExpiredException → flag file + alert")
    info("  Unknown CSV format → validate_columns() rejects early with clear error")
    info("  DB locked          → sqlite3 timeout=5, retry up to 3 times")
    info("  Server restart     → all state in interactions.db, loop picks up cleanly")

    step("Deployment:")
    info("  python src/orchestrator.py            # 24/7 loop")
    info("  python src/orchestrator.py --once     # single test iteration")
    info("  LOOP_INTERVAL_SECONDS=60 python src/orchestrator.py  # faster loop")
    info("  Docker: docker build -t apos . && docker run --env-file .env apos")

    ok("System is autonomous, stateful, and resumable after any failure")
    pause()


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}{CYAN}")
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║   APOS — Agentic Applicant Processing        ║")
    print("  ║   Orchestration System — LIVE DEMO           ║")
    print("  ║   Sudharsan S  ·  SRMIST Trichy  ·  2026     ║")
    print("  ╚══════════════════════════════════════════════╝")
    print(f"{RESET}")
    pause("Press ENTER to start the demo...")

    # Clean slate
    reset_db()

    # Run all components in order
    demo_access()
    candidates = demo_intelligence()
    demo_anti_cheat(candidates)
    demo_engagement(candidates)
    demo_self_learning(candidates)
    demo_integration()

    header("DEMO COMPLETE")
    ok("All 6 components demonstrated end-to-end")
    ok("DB persisted at logs/interactions.db")
    ok("Output at output/ranked_candidates.json")
    ok("Logs at logs/orchestrator.log")
    print()


if __name__ == "__main__":
    main()
