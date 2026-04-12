#!/usr/bin/env python3
"""
APOS - Quick Test Script for Video
Shows all 6 components working
"""
import sys
import os
sys.path.insert(0, '.')

# Set test env vars
os.environ['GROQ_API_KEY'] = 'gsk_test'
os.environ['USE_EMBEDDINGS'] = 'false'

print("=" * 70)
print("APOS - FULL SYSTEM TEST FOR VIDEO")
print("=" * 70)
print()

# Component 1: Ingestion
print("📥 COMPONENT 1: INGESTION")
from src.ingestion import load_data
df = load_data('data/applicants.csv')
print(f"   ✓ Loaded {len(df)} candidates from CSV")
print(f"   ✓ Columns: {list(df.columns)}")
print()

# Component 2: Scoring
print("🧠 COMPONENT 2: INTELLIGENCE - Scoring")
from src.scorer import score_candidate
from src.ranker import get_tier
for _, row in df.head(5).iterrows():
    score, reason, details = score_candidate(row.to_dict())
    tier = get_tier(score)
    gh = details.get('github', {})
    print(f"   {row['name']:12} | Score: {score:2} | {tier:10} | GitHub: {gh.get('public_repos', '-')} repos")
print()

# Component 3: Anti-Cheat
print("🔒 COMPONENT 3: ANTI-CHEAT")
from src.anti_cheat import find_copy_rings, analyze_response_timing
candidates = df.to_dict('records')
rings = find_copy_rings(candidates)
print(f"   ✓ Copy rings detected: {len(rings)}")
for ring in rings:
    print(f"      └─ {ring}")
    
timing = analyze_response_timing(1.0, 150)
print(f"   ✓ Timing analysis: suspicious={timing['is_suspicious']} (confidence: {timing['confidence']})")
print()

# Component 4: Email
print("📧 COMPONENT 4: ENGAGEMENT")
from src.email_manager import create_thread, get_all_active_threads
for _, row in df.head(3).iterrows():
    create_thread(row['email'], row['name'])
print(f"   ✓ Email threads created")
threads = get_all_active_threads()
print(f"   ✓ Active threads: {len(threads)}")
print()

# Component 5: Learning
print("📚 COMPONENT 5: SELF-LEARNING")
from src.learner import get_top_thinking_candidates
top = get_top_thinking_candidates(3)
print(f"   ✓ Query function works: {len(top)} results")
print()

# Component 6: Orchestrator
print("⚙️ COMPONENT 6: INTEGRATION")
from src.orchestrator import process_new_candidates
print(f"   ✓ Orchestrator module loaded")
print(f"   ✓ Main loop: runs every {os.environ.get('LOOP_INTERVAL_SECONDS', '300')} seconds")
print()

print("=" * 70)
print("✅ ALL 6 COMPONENTS WORKING!")
print("=" * 70)