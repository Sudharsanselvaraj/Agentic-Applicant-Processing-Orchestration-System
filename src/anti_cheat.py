import sqlite3
from src.config import DB_PATH

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