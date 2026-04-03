import sqlite3
from datetime import datetime
from pathlib import Path
from src.config import DB_PATH

def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_name TEXT NOT NULL,
            email TEXT,
            score INTEGER,
            tier TEXT,
            reason TEXT,
            ai_detected REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def log_interaction(name, email, score, tier, reason, ai_detected=0.0):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO interactions (candidate_name, email, score, tier, reason, ai_detected, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, email, score, tier, reason, ai_detected, datetime.now()))
    conn.commit()
    conn.close()

def get_logs(limit=100):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interactions ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows