"""
brain.py — The Brain
SQLite database foundation for the GTM Intelligence Engine.
Handles all database operations: setup, read, write, deduplication, cleanup.
"""

import sqlite3
import os
from datetime import datetime, timedelta

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
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            company     TEXT NOT NULL,
            industry    TEXT,
            country     TEXT,
            size        TEXT,
            pipeline_stage TEXT DEFAULT 'cold',
            key_materials  TEXT,
            sourcing_regions TEXT,
            why_affected   TEXT,
            urgency_level  TEXT,
            talking_point  TEXT,
            signal_type    TEXT,
            created_at     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_type     TEXT NOT NULL,
            headline        TEXT NOT NULL,
            source          TEXT,
            keyword_matched TEXT,
            sources_count   INTEGER DEFAULT 1,
            validated       INTEGER DEFAULT 0,
            severity        TEXT DEFAULT 'medium',
            detected_at     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id     INTEGER,
            signal_id       INTEGER,
            company         TEXT,
            signal_type     TEXT,
            keyword         TEXT,
            email_draft     TEXT,
            talking_point   TEXT,
            insight         TEXT,
            pipeline_stage  TEXT,
            fired_at        TEXT DEFAULT CURRENT_TIMESTAMP,
            alert_date      TEXT,
            FOREIGN KEY (prospect_id) REFERENCES prospects (id),
            FOREIGN KEY (signal_id) REFERENCES signals (id)
        )
    """)

    conn.commit()
    conn.close()
    print("[Brain] Database ready — 3 tables created")


def already_alerted_today(company, signal_type, keyword):
    """
    Deduplication check.
    Returns True if this company + signal + keyword was already
    alerted on today. Prevents duplicate alerts same day.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    result = conn.execute("""
        SELECT COUNT(*) as count FROM alerts
        WHERE company = ?
        AND signal_type = ?
        AND keyword = ?
        AND alert_date = ?
    """, (company, signal_type, keyword, today)).fetchone()
    conn.close()
    return result["count"] > 0


def save_signal(signal_type, headline, source, keyword,
                sources_count, validated, severity="medium"):
    """Saves a detected signal to database."""
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO signals
        (signal_type, headline, source, keyword_matched,
         sources_count, validated, severity)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (signal_type, headline, source, keyword,
          sources_count, validated, severity))
    signal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return signal_id


def save_alert(prospect_id, signal_id, company, signal_type,
               keyword, email_draft, talking_point, insight, pipeline_stage):
    """Saves a fired alert to database with full details and date."""
    today = datetime.now().strftime("%Y-%m-%d")
    fired_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_connection()
    conn.execute("""
        INSERT INTO alerts
        (prospect_id, signal_id, company, signal_type, keyword,
         email_draft, talking_point, insight, pipeline_stage,
         fired_at, alert_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (prospect_id, signal_id, company, signal_type, keyword,
          email_draft, talking_point, insight, pipeline_stage,
          fired_at, today))
    conn.commit()
    conn.close()


def get_past_alerts(days=90):
    """
    Returns all alerts from the last N days.
    Used when no new signals — shows rep their history.
    """
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = get_connection()
    alerts = conn.execute("""
        SELECT * FROM alerts
        WHERE alert_date >= ?
        ORDER BY fired_at DESC
    """, (cutoff,)).fetchall()
    conn.close()
    return [dict(a) for a in alerts]


def cleanup_old_alerts(days=90):
    """
    Removes alerts older than 90 days.
    Keeps database lean and fast.
    """
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = get_connection()
    result = conn.execute(
        "DELETE FROM alerts WHERE alert_date < ?", (cutoff,)
    )
    deleted = result.rowcount
    conn.commit()
    conn.close()
    if deleted > 0:
        print(f"[Brain] Cleaned up {deleted} alerts older than {days} days")


def get_alert_history():
    """Returns all alerts ever fired."""
    conn = get_connection()
    alerts = conn.execute("""
        SELECT * FROM alerts
        ORDER BY fired_at DESC
    """).fetchall()
    conn.close()
    return [dict(a) for a in alerts]


if __name__ == "__main__":
    setup_database()
    print("[Brain] Test complete — database is working")