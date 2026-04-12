import sqlite3
import json
from collections import Counter
from pathlib import Path
from src.config import DB_PATH, LOGS_DIR

ADAPTIVE_WEIGHTS_FILE = LOGS_DIR / "adaptive_weights.json"

def init_learner_db():
    """Ensure learner tables exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_email TEXT,
            round_number   INTEGER DEFAULT 1,
            score          REAL,
            tier           TEXT,
            reason         TEXT,
            responded      INTEGER DEFAULT 1,
            timestamp      DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scoring_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight_type TEXT,
            data TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def log_interaction(email, round_num, score, tier, reason, responded=True):
    """Log a candidate interaction."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Ensure table has all needed columns (init_learner_db may not have run)
    init_learner_db()
    cursor.execute("""
        INSERT INTO interactions 
        (candidate_email, round_number, score, tier, reason, responded)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (email, round_num, score, tier, reason, 1 if responded else 0))
    conn.commit()
    conn.close()

def get_responded_r1_candidates():
    """Get candidates who responded to Round 1."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT candidate_email, score, responded 
        FROM interactions 
        WHERE round_number = 1 AND responded = 1
    """)
    results = cursor.fetchall()
    conn.close()
    return results

def analyze_patterns():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT score FROM interactions ORDER BY id DESC LIMIT 10")
    recent_scores = [row[0] for row in cursor.fetchall()]
    
    avg_score = sum(recent_scores) / len(recent_scores) if recent_scores else 0
    
    cursor.execute("SELECT tier, COUNT(*) FROM interactions GROUP BY tier")
    tier_dist = {row[0]: row[1] for row in cursor.fetchall()}
    
    cursor.execute("SELECT reason FROM interactions")
    reasons = [row[0] for row in cursor.fetchall() if row[0]]
    
    conn.close()
    
    return {
        "average_score": round(avg_score, 2),
        "tier_distribution": tier_dist,
        "total_processed": sum(tier_dist.values()),
        "patterns": _extract_patterns(reasons)
    }

def _extract_patterns(reasons):
    patterns = []
    for reason in reasons:
        if "AI" in reason:
            patterns.append("AI detection active")
        if "fast" in reason.lower():
            patterns.append("Fast response detection active")
        if "missing" in reason.lower():
            patterns.append("Missing data handling active")
    return list(set(patterns))

# ============ SELF-LEARNING: ADAPTIVE SCORING (NEW) ============

def load_adaptive_weights() -> dict:
    """Load learned weights from file."""
    if ADAPTIVE_WEIGHTS_FILE.exists():
        try:
            with open(ADAPTIVE_WEIGHTS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "skill_weight": 1.0,
        "github_weight": 1.0,
        "answer_length_weight": 1.0,
        "ai_detection_weight": 1.0,
        "insights": []
    }

def save_adaptive_weights(weights: dict):
    """Save learned weights to file."""
    with open(ADAPTIVE_WEIGHTS_FILE, "w") as f:
        json.dump(weights, f, indent=2)

def analyze_r1_to_r2_correlation() -> dict:
    """
    Analyze which R1 responses predicted strong R2 responses.
    This is the key self-learning insight.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT i1.score as r1_score, i1.reason as r1_reason,
               (SELECT MAX(i2.score) FROM interactions i2 
                WHERE i2.candidate_email = i1.candidate_email AND i2.round_number = 2) as r2_score
        FROM interactions i1
        WHERE i1.round_number = 1
    """)
    pairs = cursor.fetchall()
    conn.close()
    
    if not pairs:
        return {"error": "No R1→R2 data yet"}
    
    high_r1 = [(p[0], p[1], p[2]) for p in pairs if p[0] >= 70 and p[2] and p[2] >= 70]
    low_r1 = [(p[0], p[1], p[2]) for p in pairs if p[0] < 50 and p[2] and p[2] >= 60]
    
    insights = []
    if len(high_r1) > 3:
        insights.append(f"{len(high_r1)} high-R1 candidates also scored high in R2")
    if len(low_r1) > 3:
        insights.append(f"{len(low_r1)} low-R1 candidates improved in R2 - R1 may miss potential")
    
    return {
        "total_pairs": len(pairs),
        "high_r1_high_r2": len(high_r1),
        "low_r1_high_r2": len(low_r1),
        "insights": insights
    }

def update_scoring_weights():
    """
    Automatically update scoring weights based on learnings.
    This is the self-learning loop.
    """
    weights = load_adaptive_weights()
    
    correlation = analyze_r1_to_r2_correlation()
    
    if "insights" in correlation and correlation.get("low_r1_high_r2", 0) > 5:
        weights["skill_weight"] *= 1.1
        weights["answer_length_weight"] *= 0.95
        weights["insights"].append({
            "type": "r1_misses_gems",
            "data": f"{correlation['low_r1_high_r2']} low-R1 candidates improved later"
        })
    
    weights["insights"] = weights["insights"][-10:]
    save_adaptive_weights(weights)
    
    print(f"✅ Updated adaptive weights: {weights}")
    return weights

def get_top_thinking_candidates(n: int = 3) -> list:
    """Find candidates with highest scores — proxy for original thinking."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT candidate_email, score, tier, reason
        FROM interactions
        ORDER BY score DESC
        LIMIT ?
    """, (n,))

    results = cursor.fetchall()
    conn.close()
    return [{"email": r[0], "score": r[1], "tier": r[2], "reason": r[3]} for r in results]

def get_most_common_approach() -> dict:
    """Analyze what approach candidates most commonly suggest."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT reason FROM interactions WHERE reason LIKE '%Selenium%' OR reason LIKE '%Playwright%'")
    selenium_count = len(cursor.fetchall())
    
    cursor.execute("SELECT reason FROM interactions WHERE reason LIKE '%API%'")
    api_count = len(cursor.fetchall())
    
    conn.close()
    
    approaches = {
        "selenium_playwright": selenium_count,
        "api_direct": api_count
    }
    
    top = max(approaches.items(), key=lambda x: x[1])
    return {"approach": top[0], "count": top[1]}

def suggest_improvements():
    analysis = analyze_patterns()
    suggestions = []
    
    if analysis["average_score"] < 50:
        suggestions.append("Consider lowering score thresholds or improving candidate quality")
    
    if analysis["tier_distribution"].get("Reject", 0) > analysis["total_processed"] * 0.5:
        suggestions.append("High rejection rate - review eligibility criteria")
    
    weights = load_adaptive_weights()
    if weights.get("insights"):
        for insight in weights["insights"][-3:]:
            suggestions.append(f"Insight: {insight.get('type', 'unknown')}")
    
    return suggestions