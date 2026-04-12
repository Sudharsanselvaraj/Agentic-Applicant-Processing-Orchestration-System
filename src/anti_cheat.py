import sqlite3
import re
import pickle
from collections import defaultdict
from pathlib import Path
from src.config import DB_PATH
from src.config import CACHE_DIR

COPY_THRESHOLD = 0.60
PAIR_THRESHOLD = 0.95  # For exact duplicates (2 candidates with nearly identical answers)
MIN_GROUP_SIZE = 3

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
embedding_cache_file = CACHE_DIR / "embeddings.pkl"

def get_embedding_model():
    """Load or create embedding model."""
    cache_file = embedding_cache_file
    
    if cache_file.exists():
        try:
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass
    
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(EMBEDDING_MODEL)
        
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(model, f)
        except Exception:
            pass
        
        return model
    except ImportError:
        return None

def init_anti_cheat_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS strikes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_email TEXT,
            strike_type TEXT,
            evidence TEXT,
            confidence REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS similarity_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_a TEXT,
            candidate_b TEXT,
            similarity_score REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def add_strike(candidate_email, strike_type, evidence, confidence):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO strikes (candidate_email, strike_type, evidence, confidence)
        VALUES (?, ?, ?, ?)
    """, (candidate_email, strike_type, evidence, confidence))
    conn.commit()
    
    cursor.execute("""
        SELECT COUNT(*) FROM strikes WHERE candidate_email = ?
    """, (candidate_email,))
    count = cursor.fetchone()[0]
    
    if count >= 3:
        try:
            cursor.execute("""
                UPDATE email_threads SET status = 'eliminated' 
                WHERE candidate_email = ?
            """, (candidate_email,))
        except sqlite3.OperationalError:
            pass
    
    conn.commit()
    conn.close()
    return count

def get_candidate_strikes(candidate_email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM strikes WHERE candidate_email = ?
    """, (candidate_email,))
    strikes = cursor.fetchall()
    conn.close()
    return strikes

def cache_similarity(candidate_a, candidate_b, score):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO similarity_cache (candidate_a, candidate_b, similarity_score)
        VALUES (?, ?, ?)
    """, (candidate_a, candidate_b, score))
    conn.commit()
    conn.close()

def get_cached_similarity(candidate_a, candidate_b):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT similarity_score FROM similarity_cache 
        WHERE (candidate_a = ? AND candidate_b = ?) 
        OR (candidate_a = ? AND candidate_b = ?)
    """, (candidate_a, candidate_b, candidate_b, candidate_a))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# ============ CROSS-CANDIDATE SIMILARITY (NEW) ============

def normalize_forComparison(text: str) -> str:
    """Remove personal context for comparison."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.lower().strip()

def simple_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity using simple token overlap.
    No external dependencies required.
    """
    if not text1 or not text2:
        return 0.0
    
    norm1 = set(normalize_forComparison(text1).split())
    norm2 = set(normalize_forComparison(text2).split())
    
    if not norm1 or not norm2:
        return 0.0
    
    intersection = norm1 & norm2
    union = norm1 | norm2
    
    return len(intersection) / len(union) if union else 0.0

def find_copy_rings(candidates: list, answer_key: str = "answer") -> list:
    """
    Find groups of candidates with similar answers (potential copy ring).
    
    Args:
        candidates: List of candidate dicts with 'email' and answer field
        answer_key: Field name containing the answer text
    
    Returns:
        List of copy ring groups (list of candidate emails)
    """
    if len(candidates) < 2:
        return []
    
    answers = {}
    for c in candidates:
        email = c.get("email", "")
        answer = c.get(answer_key, "")
        if email and answer:
            answers[email] = answer
    
    candidates_list = list(answers.keys())
    similar_groups = []
    checked = set()
    
    for i, cand_a in enumerate(candidates_list):
        if cand_a in checked:
            continue
        
        group = [cand_a]
        answer_a = answers[cand_a]
        
        for cand_b in candidates_list[i+1:]:
            if cand_b in checked:
                continue
            
            answer_b = answers[cand_b]
            sim = simple_similarity(answer_a, answer_b)
            
            if sim >= PAIR_THRESHOLD:
                cache_similarity(cand_a, cand_b, sim)
                group.append(cand_b)
                checked.add(cand_b)
            elif sim >= COPY_THRESHOLD:
                cache_similarity(cand_a, cand_b, sim)
                group.append(cand_b)
                checked.add(cand_b)
        
        if len(group) >= 2:
            similar_groups.append(group)
            for c in group:
                checked.add(c)
    
    return similar_groups

def auto_flag_copy_rings(candidates: list) -> dict:
    """
    Automatically flag candidates in copy rings.
    
    Returns:
        Dict with 'rings' (list of groups) and 'flagged' (list of flagged emails)
    """
    rings = find_copy_rings(candidates)
    
    flagged = []
    for ring in rings:
        for email in ring:
            add_strike(
                email,
                "copy_ring",
                f"Similar to {len(ring)-1} other candidates",
                COPY_THRESHOLD
            )
            flagged.append(email)
    
    return {
        "ring_count": len(rings),
        "rings": rings,
        "flagged_count": len(flagged),
        "flagged": flagged
    }

# ============ TIMING ANALYSIS (NEW) ============

def analyze_response_timing(response_time_minutes: float, answer_length: int) -> dict:
    """
    Analyze if response timing is suspicious.
    
    Args:
        response_time_minutes: Time between email sent and response received
        answer_length: Word count of the answer
    
    Returns:
        Dict with 'is_suspicious', 'reason', 'confidence'
    """
    words_per_minute = answer_length / max(response_time_minutes, 0.1)
    
    # Fast response + long answer = suspicious
    if response_time_minutes < 2 and answer_length > 100:
        return {
            "is_suspicious": True,
            "reason": f"Response time {response_time_minutes:.1f}min with {answer_length} words is unusually fast",
            "confidence": 0.9
        }
    
    # Very fast response + any answer
    if response_time_minutes < 1:
        return {
            "is_suspicious": True,
            "reason": f"Response in under 1 minute",
            "confidence": 0.7
        }
    
    # Typing speed analysis (avg human: 40 WPM)
    if words_per_minute > 80:
        return {
            "is_suspicious": True,
            "reason": f"Typing speed {words_per_minute:.0f} WPM exceeds human limit",
            "confidence": 0.6
        }
    
    return {
        "is_suspicious": False,
        "reason": "Response timing appears normal",
        "confidence": 0.0
    }

# ============ EMBEDDING-BASED SIMILARITY (NEW) ============

def compute_embeddings_batch(texts: list) -> list:
    """Compute embeddings for a list of texts."""
    model = get_embedding_model()
    if not model:
        return [None] * len(texts)
    
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings

def cosine_similarity(a: list, b: list) -> float:
    """Compute cosine similarity between two vectors."""
    if a is None or b is None:
        return 0.0
    
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    
    if norm_a * norm_b == 0:
        return 0.0
    
    return dot / (norm_a * norm_b)

def find_similar_with_embeddings(candidates: list, threshold: float = 0.8) -> list:
    """
    Find similar candidate pairs using embeddings.
    More accurate than token overlap.
    
    Args:
        candidates: List of candidate dicts with 'email' and 'answer'
        threshold: Similarity threshold (default 0.8 = 80%)
    
    Returns:
        List of (email_a, email_b, similarity) tuples
    """
    model = get_embedding_model()
    if not model:
        print("⚠ Embedding model not available, falling back to token similarity")
        return find_copy_rings(candidates)
    
    answers = [c.get("answer", "") for c in candidates]
    emails = [c.get("email", "") for c in candidates]
    
    valid_idx = [i for i, a in enumerate(answers) if a]
    valid_answers = [answers[i] for i in valid_idx]
    valid_emails = [emails[i] for i in valid_idx]
    
    if not valid_answers:
        return []
    
    embeddings = compute_embeddings_batch(valid_answers)
    
    similar_pairs = []
    for i in range(len(valid_answers)):
        for j in range(i + 1, len(valid_answers)):
            sim = cosine_similarity(embeddings[i], embeddings[j])
            if sim >= threshold:
                similar_pairs.append((valid_emails[i], valid_emails[j], round(sim, 2)))
    
    return similar_pairs

def check_all_candidates(candidates: list) -> dict:
    """
    Run all anti-cheat checks on a candidate list.
    """
    results = {
        "total": len(candidates),
        "flagged": [],
        "copy_rings": [],
        "timing_flags": [],
        "ai_flags": 0
    }
    
    rings = find_copy_rings(candidates)
    results["copy_rings"] = rings
    results["flagged"].extend([email for ring in rings for email in ring])
    
    return results