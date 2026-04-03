import sqlite3
from collections import Counter
from src.config import DB_PATH

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

def suggest_improvements():
    analysis = analyze_patterns()
    suggestions = []
    
    if analysis["average_score"] < 50:
        suggestions.append("Consider lowering score thresholds or improving candidate quality")
    
    if analysis["tier_distribution"].get("Reject", 0) > analysis["total_processed"] * 0.5:
        suggestions.append("High rejection rate - review eligibility criteria")
    
    return suggestions