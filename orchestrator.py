"""
GenoTek Hiring Agent — 24/7 Runtime Orchestrator

This is the main loop that runs the entire system autonomously.
Each iteration:
1. Check for new applicants
2. Score and rank them
3. Send follow-up emails
4. Check for AI/copy cheating
5. Update learning models

Run: python src/orchestrator.py
"""

import time
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Load .env
import src

from src.config import DATA_DIR, OUTPUT_DIR, LOGS_DIR, CACHE_DIR, HR_EMAIL
from src.ingestion import load_data, validate_columns, clean_data
from src.scorer import score_candidate
from src.ranker import rank_candidates, get_tier
from src.anti_cheat import (
    find_copy_rings,
    analyze_response_timing,
    check_all_candidates,
    add_strike,
    auto_flag_copy_rings
)
from src.learner import (
    init_learner_db,
    log_interaction,
    analyze_r1_to_r2_correlation,
    update_scoring_weights,
    get_top_thinking_candidates,
    get_most_common_approach
)
from src.email_manager import (
    init_email_db,
    create_thread,
    get_thread_by_email,
    get_all_active_threads,
    log_email,
    log_decision
)
from src.response_generator import (
    generate_r1_email,
    generate_followup_email,
    determine_round_context,
    analyze_response_for_context
)

try:
    from src.gmail_integration import fetch_unread_emails, send_email, mark_as_read
except ImportError:
    def fetch_unread_emails(): return []
    def send_email(*a, **k): return None
    def mark_as_read(*a, **k): return None
    print("⚠ Gmail integration not available — email features disabled")

LOOP_INTERVAL = int(os.environ.get("LOOP_INTERVAL_SECONDS", "300"))
LOG_FILE = LOGS_DIR / "orchestrator.log"
SESSION_EXPIRED_FLAG = DATA_DIR / "session_expired.flag"


class SessionExpiredException(Exception):
    pass

def log(message: str, level: str = "INFO"):
    """Log to file and stdout."""
    timestamp = datetime.now().isoformat()
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def load_candidates_from_file() -> List[Dict]:
    """Load candidates from CSV/Excel file."""
    try:
        df = load_data(str(DATA_DIR / "applicants.csv"))
        validate_columns(df)
        df = clean_data(df)
        return df.to_dict('records')
    except FileNotFoundError:
        log("No applicants.csv found, waiting for new data", "WARN")
        return []
    except Exception as e:
        log(f"Error loading data: {e}", "ERROR")
        return []

def process_new_candidates():
    """Score and rank new candidates."""
    log("=== PROCESSING NEW CANDIDATES ===")
    
    candidates = load_candidates_from_file()
    if not candidates:
        return
    
    scored = []
    for cand in candidates:
        score, reason = score_candidate(cand)
        tier = get_tier(score)
        scored.append({
            **cand,
            "score": score,
            "tier": tier,
            "reason": reason
        })
        
        create_thread(cand.get("email", ""), cand.get("name", ""))
        log_interaction(
            cand.get("email", ""),
            round_num=1,
            score=score,
            tier=tier,
            reason=reason
        )
    
    ranked = sorted(scored, key=lambda x: x["score"], reverse=True)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "ranked_candidates.json"
    with open(output_file, "w") as f:
        json.dump(ranked, f, indent=2)
    
    log(f"Scored {len(ranked)} candidates")
    
    fast_track = [c for c in ranked if c["tier"] == "Fast-Track"]
    log(f"Fast-Track candidates: {len(fast_track)}")
    
    return ranked

def send_followup_emails():
    """Send follow-up emails to candidates."""
    log("=== SENDING FOLLOW-UP EMAILS ===")
    
    threads = get_all_active_threads()
    sent_count = 0
    
    for thread in threads:
        thread_id, email, name, round_num, last_contact, status = thread
        
        if status != "active":
            continue
        
        subject, body = generate_r1_email(name, "")
        
        result = send_email(email, subject, body)
        if result:
            log_email(thread_id, "hr@genotek.global", email, subject, body)
            log_decision(thread_id, "sent_r1", "Automated R1 email")
            sent_count += 1
    
    log(f"Sent {sent_count} emails")
    return sent_count

def check_incoming_emails():
    """Check for new candidate replies and send contextual follow-ups."""
    log("=== CHECKING INCOMING EMAILS ===")

    emails = fetch_unread_emails()
    replies = 0

    for email_item in emails:
        from_email = email_item.get("from", "")
        body = email_item.get("body", "")
        subject = email_item.get("subject", "")

        # Only process replies (Re: prefix)
        if not subject.lower().startswith("re:"):
            continue

        thread = get_thread_by_email(from_email)
        if not thread:
            log(f"No thread found for {from_email} — skipping")
            continue

        # thread is a tuple: (id, candidate_email, candidate_name, current_round, last_contact, status)
        thread_id    = thread[0]
        candidate_name = thread[2] or "Candidate"
        status       = thread[5]

        if status != "active":
            log(f"Thread {thread_id} is {status} — skipping")
            continue

        log_email(thread_id, from_email, HR_EMAIL, subject, body)

        context = analyze_response_for_context(body)
        reply_subject, reply_body = generate_followup_email(candidate_name, [body], context)

        gmail_thread_id = email_item.get("thread_id")
        send_email(from_email, reply_subject, reply_body, gmail_thread_id)
        mark_as_read(email_item["id"])

        log_decision(thread_id, "responded_followup", f"Candidate replied — sent contextual R{thread[3]+1}")
        replies += 1
        log(f"✅ Replied to {from_email} with context-aware follow-up")

    log(f"Processed {replies} candidate replies")
    return replies

def run_anti_cheat_checks():
    """Run anti-cheat detection on all candidates."""
    log("=== RUNNING ANTI-CHEAT CHECKS ===")
    
    candidates = load_candidates_from_file()
    if len(candidates) < 3:
        log("Not enough candidates for copy ring detection", "WARN")
        return
    
    results = check_all_candidates(candidates)
    log(f"Total candidates: {results['total']}")
    log(f"Copy rings found: {len(results['copy_rings'])}")
    
    if results['copy_rings']:
        for ring in results['copy_rings']:
            log(f"Copy ring detected: {len(ring)} candidates", "WARN")
    
    ring_result = auto_flag_copy_rings(candidates)
    log(f"Flagged {ring_result['flagged_count']} candidates for copying")
    
    return results

def update_learning_models():
    """Update adaptive scoring based on accumulated data."""
    log("=== UPDATING LEARNING MODELS ===")
    
    try:
        correlation = analyze_r1_to_r2_correlation()
        if "total_pairs" in correlation:
            log(f"R1→R2 correlation: {correlation['total_pairs']} pairs analyzed")
        
        weights = update_scoring_weights()
        log(f"Updated adaptive weights: skill={weights.get('skill_weight', 1.0)}")
        
        top_candidates = get_top_thinking_candidates(3)
        if top_candidates:
            log(f"Top thinking candidates: {len(top_candidates)}")
        
        approach = get_most_common_approach()
        if approach.get("count", 0) > 0:
            log(f"Most common approach: {approach['approach']} ({approach['count']})")
            
    except Exception as e:
        log(f"Learning update error: {e}", "ERROR")

def main_loop():
    """Main 24/7 orchestrator loop."""
    log("=" * 50)
    log("GenoTek APOS Hiring Agent STARTING")
    log(f"Loop interval: {LOOP_INTERVAL} seconds")
    log("=" * 50)

    # Initialise databases once at startup
    init_email_db()
    init_learner_db()

    # Check for stale session flag
    if SESSION_EXPIRED_FLAG.exists():
        log("⚠ Session expired flag found — clear data/session_expired.flag after re-auth", "WARN")

    iteration = 0

    while True:
        iteration += 1
        log(f"\n--- ITERATION {iteration} ---")

        try:
            process_new_candidates()
            run_anti_cheat_checks()
            check_incoming_emails()
            send_followup_emails()

            if iteration % 4 == 0:
                update_learning_models()

            log(f"✅ Iteration {iteration} complete. Sleeping {LOOP_INTERVAL}s...")

        except SessionExpiredException:
            log("🔴 CRITICAL: Internshala session expired — writing flag and pausing scraper", "ERROR")
            SESSION_EXPIRED_FLAG.touch()
            log("Re-run get_cookies.py then delete data/session_expired.flag to resume", "ERROR")

        except Exception as e:
            log(f"Loop error: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "ERROR")

        time.sleep(LOOP_INTERVAL)


def run_once():
    """Run single iteration (for demo / testing)."""
    log("=" * 50)
    log("GenoTek APOS — SINGLE ITERATION RUN")
    log("=" * 50)

    init_email_db()
    init_learner_db()

    process_new_candidates()
    run_anti_cheat_checks()
    check_incoming_emails()
    send_followup_emails()
    update_learning_models()

    log("✅ Single run complete")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_once()
    else:
        main_loop()