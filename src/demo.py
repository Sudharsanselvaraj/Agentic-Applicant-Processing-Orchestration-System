#!/usr/bin/env python3
"""
Full Demo Script — Complete GenoTek Hiring Agent Demo

Usage:
    python3 src/demo.py

This script:
1. Opens browser for login
2. Extracts cookies
3. Scrapes applicant data
4. Runs full scoring/ranking pipeline
5. Shows results
"""

import os
import sys
import json
import shutil
import asyncio
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def print_header():
    print("=" * 70)
    print("   GenoTek AI Hiring Agent — Full System Demo")
    print("=" * 70)
    print()

def step_1_extract_cookies():
    """Step 1: Open browser and get cookies."""
    print("📌 STEP 1: Login to Internshala")
    print("-" * 40)
    print("Opening browser for you to log in...")
    print()
    
    from src.get_cookies import main as get_cookies_main
    
    # Run the cookie extraction
    asyncio.run(get_cookies_main())
    
    # Check if cookies were saved
    cookie_file = Path("data/cookies.json")
    raw_file = Path("data/cookies_raw.txt")
    
    if cookie_file.exists() or raw_file.exists():
        print("\n✅ Cookies saved successfully!")
        return True
    else:
        print("\n⚠️ No cookies found. Will use manual CSV method.")
        return False

def step_2_scrape_applicants():
    """Step 2: Try to scrape applicant data."""
    print("\n📌 STEP 2: Scrape Applicant Data")
    print("-" * 40)
    
    from src.access_internshala import fetch_all_applicants, export_applicants
    
    url = os.environ.get("INTERNSHALA_JOB_URL", "")
    
    if not url:
        print("⚠️ INTERNSHALA_JOB_URL not set")
        print("   Skipping scrape - will use existing data/applicants.csv")
        return False
    
    print(f"Scraping from: {url}")
    
    async def run_scrape():
        applicants = await fetch_all_applicants(url, pages=3)
        if applicants:
            export_applicants(applicants)
            return True
        return False
    
    result = asyncio.run(run_scrape())
    
    if result:
        # Copy to input directory
        scraped = Path("output/scraped_applicants.csv")
        if scraped.exists():
            shutil.copy(scraped, "data/applicants.csv")
            print("✅ Copied scraped data to data/applicants.csv")
        return True
    else:
        print("⚠️ Scraping failed - will use existing data")
        return False

def step_3_run_pipeline():
    """Step 3: Run full scoring pipeline."""
    print("\n📌 STEP 3: Score & Rank Candidates")
    print("-" * 40)
    
    from src.ingestion import load_data, validate_columns, clean_data
    from src.scorer import score_candidate
    from src.ranker import get_tier
    from src.anti_cheat import check_all_candidates
    from src.learner import log_interaction
    
    # Check for data
    data_file = Path("data/applicants.csv")
    if not data_file.exists():
        print("❌ No applicant data found!")
        print("   Either scrape (Step 2) or manually add data/applicants.csv")
        return False
    
    print(f"Loading data from {data_file}...")
    
    try:
        df = load_data(str(data_file))
        validate_columns(df)
        df = clean_data(df)
        candidates = df.to_dict('records')
        print(f"✅ Loaded {len(candidates)} candidates")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return False
    
    # Score candidates
    print("\nScoring candidates...")
    scored = []
    for c in candidates:
        score, reason = score_candidate(c)
        tier = get_tier(score)
        scored.append({
            **c,
            'score': score,
            'tier': tier,
            'reason': reason
        })
        log_interaction(c.get('email', ''), 1, score, tier, reason)
    
    # Anti-cheat check
    print("Running anti-cheat checks...")
    cheat_results = check_all_candidates(candidates)
    flagged = len(cheat_results.get('flagged', []))
    
    # Rank
    ranked = sorted(scored, key=lambda x: x['score'], reverse=True)
    
    # Save output
    output_file = Path("output/ranked_candidates.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(ranked, f, indent=2)
    
    print(f"✅ Scored and ranked {len(ranked)} candidates")
    print(f"   Flagged for cheating: {flagged}")
    
    return ranked, cheat_results

def step_4_display_results(ranked, cheat_results):
    """Step 4: Display the results."""
    print("\n📌 STEP 4: Results")
    print("-" * 40)
    
    # Tier distribution
    tiers = {}
    for r in ranked:
        t = r['tier']
        tiers[t] = tiers.get(t, 0) + 1
    
    print("TIER DISTRIBUTION:")
    for tier, count in sorted(tiers.items()):
        bar = "█" * count
        print(f"   {tier:12} : {count:3} {bar}")
    
    print("\nTOP 5 CANDIDATES:")
    for i, r in enumerate(ranked[:5], 1):
        ai_flag = " ⚠️ AI" if 'AI' in r.get('reason', '') else ""
        print(f"   {i}. {r['name']:15} — Score: {r['score']:3} ({r['tier']}){ai_flag}")
    
    # Copy ring info
    rings = cheat_results.get('copy_rings', [])
    if rings:
        print(f"\n⚠️ COPY RINGS DETECTED: {len(rings)}")
        for ring in rings:
            print(f"   {ring}")
    
    print(f"\n✅ Full results saved to: output/ranked_candidates.json")

def main():
    print_header()
    
    # Step 1: Get cookies (optional - user can skip if using manual CSV)
    cookies_worked = step_1_extract_cookies()
    
    # Step 2: Scrape data (optional - falls back to existing CSV)
    step_2_scrape_applicants()
    
    # Step 3: Run pipeline (REQUIRED)
    result = step_3_run_pipeline()
    
    if result:
        ranked, cheat_results = result
        step_4_display_results(ranked, cheat_results)
    
    print("\n" + "=" * 70)
    print("   Demo Complete!")
    print("=" * 70)
    print()
    print("To run full 24/7 loop:")
    print("   PYTHONPATH=. python3 src/orchestrator.py")
    print()

if __name__ == "__main__":
    main()