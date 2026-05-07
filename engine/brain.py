"""
brain.py — The Brain
SQLite database foundation for the GTM Intelligence Engine.
Handles all database operations: setup, read, write.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'leads.db')


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def setup_database():
    """Creates all tables if they don't exist."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS prospects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            industry TEXT,
            country TEXT,
            size TEXT,
            pipeline_stage TEXT DEFAULT 'cold',
            key_materials TEXT,
            sourcing_regions TEXT,
            why_affected TEXT,
            urgency_level TEXT,
            talking_point TEXT,
            signal_type TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_type TEXT NOT NULL,
            headline TEXT NOT NULL,
            source TEXT,
            keyword_matched TEXT,
            sources_count INTEGER DEFAULT 1,
            validated INTEGER DEFAULT 0,
            detected_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id INTEGER,
            signal_id INTEGER,
            email_draft TEXT,
            talking_point TEXT,
            insight TEXT,
            fired_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prospect_id) REFERENCES prospects (id),
            FOREIGN KEY (signal_id) REFERENCES signals (id)
        )
    """)

    conn.commit()
    conn.close()
    print("[Brain] Database ready — 3 tables created")


def get_all_prospects():
    """Returns all prospects from database."""
    conn = get_connection()
    prospects = conn.execute("SELECT * FROM prospects").fetchall()
    conn.close()
    return [dict(p) for p in prospects]


def get_prospects_by_signal(signal_type):
    """Returns prospects affected by a specific signal type."""
    conn = get_connection()
    prospects = conn.execute(
        "SELECT * FROM prospects WHERE signal_type = ? AND pipeline_stage != 'closed'",
        (signal_type,)
    ).fetchall()
    conn.close()
    return [dict(p) for p in prospects]


def save_signal(signal_type, headline, source, keyword, sources_count, validated):
    """Saves a detected signal to database."""
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO signals 
        (signal_type, headline, source, keyword_matched, sources_count, validated)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (signal_type, headline, source, keyword, sources_count, validated))
    signal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return signal_id


def save_alert(prospect_id, signal_id, email_draft, talking_point, insight):
    """Saves a fired alert to database."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO alerts 
        (prospect_id, signal_id, email_draft, talking_point, insight)
        VALUES (?, ?, ?, ?, ?)
    """, (prospect_id, signal_id, email_draft, talking_point, insight))
    conn.commit()
    conn.close()


def get_alert_history():
    """Returns all alerts ever fired."""
    conn = get_connection()
    alerts = conn.execute("""
        SELECT a.*, p.company, p.pipeline_stage
        FROM alerts a
        JOIN prospects p ON a.prospect_id = p.id
        ORDER BY a.fired_at DESC
    """).fetchall()
    conn.close()
    return [dict(a) for a in alerts]


if __name__ == "__main__":
    setup_database()
    print("[Brain] Test complete — database is working")