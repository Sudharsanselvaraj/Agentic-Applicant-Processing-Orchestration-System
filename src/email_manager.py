import sqlite3
from datetime import datetime
from pathlib import Path
from src.config import DB_PATH

def init_email_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_email TEXT NOT NULL UNIQUE,
            candidate_name TEXT,
            current_round INTEGER DEFAULT 0,
            last_contact DATETIME,
            status TEXT DEFAULT 'active'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER,
            sender TEXT,
            recipient TEXT,
            subject TEXT,
            body TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_ai_generated INTEGER DEFAULT 0,
            FOREIGN KEY (thread_id) REFERENCES email_threads(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decision_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER,
            decision TEXT,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (thread_id) REFERENCES email_threads(id)
        )
    """)
    
    conn.commit()
    conn.close()

def create_thread(candidate_email, candidate_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO email_threads (candidate_email, candidate_name, current_round, last_contact)
        VALUES (?, ?, 1, ?)
    """, (candidate_email, candidate_name, datetime.now()))
    conn.commit()
    conn.close()

def log_email(thread_id, sender, recipient, subject, body):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO emails (thread_id, sender, recipient, subject, body)
        VALUES (?, ?, ?, ?, ?)
    """, (thread_id, sender, recipient, subject, body))
    conn.commit()
    conn.close()

def log_decision(thread_id, decision, reason):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO decision_log (thread_id, decision, reason)
        VALUES (?, ?, ?)
    """, (thread_id, decision, reason))
    conn.commit()
    conn.close()

def get_thread_by_email(email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM email_threads WHERE candidate_email = ?", (email,))
    thread = cursor.fetchone()
    conn.close()
    return thread

def get_thread_emails(thread_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM emails WHERE thread_id = ? ORDER BY timestamp", (thread_id,))
    emails = cursor.fetchall()
    conn.close()
    return emails

def get_all_active_threads():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM email_threads WHERE status = 'active'")
    threads = cursor.fetchall()
    conn.close()
    return threads