"""
brain.py — The Brain
SQLite database with full optimisation:
- Indexed tables for fast queries
- Signal caching — avoid redundant scanning
- HubSpot prospect caching — 24 hour refresh
- Insight freshness tracking — 6 hour refresh
- Full logging to file
"""

import sqlite3
import os
import logging
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'leads.db')
LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'engine.log')

# ── LOGGING SETUP ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GTM-Engine")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def setup_database():
    """Creates all tables with indexes for fast queries."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS prospects (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            company          TEXT NOT NULL,
            industry         TEXT,
            country          TEXT,
            size             TEXT,
            pipeline_stage   TEXT DEFAULT 'cold',
            key_materials    TEXT,
            sourcing_regions TEXT,
            why_affected     TEXT,
            urgency_level    TEXT,
            talking_point    TEXT,
            signal_type      TEXT,
            created_at       TEXT DEFAULT CURRENT_TIMESTAMP
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
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id    INTEGER,
            signal_id      INTEGER,
            company        TEXT,
            signal_type    TEXT,
            keyword        TEXT,
            email_draft    TEXT,
            talking_point  TEXT,
            insight        TEXT,
            pipeline_stage TEXT,
            fired_at       TEXT DEFAULT CURRENT_TIMESTAMP,
            alert_date     TEXT,
            FOREIGN KEY (prospect_id) REFERENCES prospects (id),
            FOREIGN KEY (signal_id)   REFERENCES signals (id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS signal_cache (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_type  TEXT NOT NULL,
            keyword      TEXT NOT NULL,
            headline     TEXT,
            sources      TEXT,
            sources_count INTEGER,
            cached_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(signal_type, keyword)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS prospect_cache (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            company          TEXT NOT NULL UNIQUE,
            pipeline_stage   TEXT,
            key_materials    TEXT,
            sourcing_regions TEXT,
            cached_at        TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS insights (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            company      TEXT NOT NULL,
            signal_type  TEXT NOT NULL,
            keyword      TEXT NOT NULL,
            email_draft  TEXT,
            talking_point TEXT,
            insight      TEXT,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(company, signal_type, keyword)
        )
    """)

    # ── INDEXES for fast queries ──
    c.execute("CREATE INDEX IF NOT EXISTS idx_alerts_company ON alerts(company)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_alerts_date ON alerts(alert_date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_alerts_signal ON alerts(signal_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(signal_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_insights_lookup ON insights(company, signal_type, keyword)")

    conn.commit()
    conn.close()
    logger.info("Database ready — all tables and indexes created")


def already_alerted_today(company, signal_type, keyword):
    """Deduplication check — returns True if already alerted today."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    result = conn.execute("""
        SELECT COUNT(*) as count FROM alerts
        WHERE company = ? AND signal_type = ?
        AND keyword = ? AND alert_date = ?
    """, (company, signal_type, keyword, today)).fetchone()
    conn.close()
    return result["count"] > 0


def get_cached_insight(company, signal_type, keyword, max_age_hours=6):
    """
    Fetches cached insight if less than max_age_hours old.
    Returns None if no cache or cache is stale.
    """
    conn = get_connection()
    result = conn.execute("""
        SELECT * FROM insights
        WHERE company = ? AND signal_type = ? AND keyword = ?
    """, (company, signal_type, keyword)).fetchone()
    conn.close()

    if not result:
        return None

    generated_at = datetime.strptime(result["generated_at"], "%Y-%m-%d %H:%M:%S")
    age_hours = (datetime.now() - generated_at).total_seconds() / 3600

    if age_hours > max_age_hours:
        logger.info(f"Insight cache stale ({age_hours:.1f}h old) — regenerating for {company}")
        return None

    logger.info(f"Insight cache hit ({age_hours:.1f}h old) — fetching for {company}")
    return dict(result)


def save_cached_insight(company, signal_type, keyword,
                        email_draft, talking_point, insight):
    """Saves or updates insight cache."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO insights
        (company, signal_type, keyword, email_draft, talking_point,
         insight, generated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(company, signal_type, keyword) DO UPDATE SET
            email_draft   = excluded.email_draft,
            talking_point = excluded.talking_point,
            insight       = excluded.insight,
            generated_at  = excluded.generated_at
    """, (company, signal_type, keyword, email_draft, talking_point,
          insight, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_cached_signals(max_age_hours=6):
    """Returns cached signals if less than max_age_hours old."""
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(hours=max_age_hours)).strftime(
        "%Y-%m-%d %H:%M:%S")
    results = conn.execute("""
        SELECT * FROM signal_cache WHERE cached_at > ?
    """, (cutoff,)).fetchall()
    conn.close()

    if not results:
        return None

    signals = []
    for r in results:
        signals.append({
            "signal_type":  r["signal_type"],
            "keyword":      r["keyword"],
            "headline":     r["headline"],
            "sources":      r["sources"].split(",") if r["sources"] else [],
            "sources_count": r["sources_count"],
            "detected_at":  r["cached_at"],
            "validated":    True
        })
    logger.info(f"Signal cache hit — {len(signals)} signals loaded from cache")
    return signals


def save_signal_cache(signals):
    """Saves validated signals to cache."""
    conn = get_connection()
    conn.execute("DELETE FROM signal_cache")
    for s in signals:
        conn.execute("""
            INSERT OR REPLACE INTO signal_cache
            (signal_type, keyword, headline, sources, sources_count)
            VALUES (?, ?, ?, ?, ?)
        """, (s["signal_type"], s["keyword"], s["headline"],
              ",".join(s["sources"]), s["sources_count"]))
    conn.commit()
    conn.close()
    logger.info(f"Signal cache updated — {len(signals)} signals saved")


def get_cached_prospects(max_age_hours=24):
    """Returns cached HubSpot prospects if less than 24 hours old."""
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(hours=max_age_hours)).strftime(
        "%Y-%m-%d %H:%M:%S")
    results = conn.execute("""
        SELECT * FROM prospect_cache WHERE cached_at > ?
    """, (cutoff,)).fetchall()
    conn.close()

    if not results:
        return None

    prospects = [dict(r) for r in results]
    logger.info(f"Prospect cache hit — {len(prospects)} prospects loaded from cache")
    return prospects


def save_prospect_cache(prospects):
    """Saves HubSpot prospects to local cache."""
    conn = get_connection()
    conn.execute("DELETE FROM prospect_cache")
    for i, p in enumerate(prospects):
        conn.execute("""
            INSERT OR REPLACE INTO prospect_cache
            (company, pipeline_stage, key_materials, sourcing_regions)
            VALUES (?, ?, ?, ?)
        """, (p["company"], p.get("pipeline_stage", "cold"),
              p.get("key_materials", ""), p.get("sourcing_regions", "")))
    conn.commit()
    conn.close()
    logger.info(f"Prospect cache updated — {len(prospects)} prospects saved")


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
               keyword, email_draft, talking_point, insight,
               pipeline_stage):
    """Saves a fired alert to database."""
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
    logger.info(f"Alert saved — {company} | {signal_type} | {keyword}")


def get_past_alerts(days=90):
    """Returns alerts from last N days — uses index for speed."""
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
    """Removes alerts older than N days."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = get_connection()
    result = conn.execute(
        "DELETE FROM alerts WHERE alert_date < ?", (cutoff,))
    deleted = result.rowcount
    conn.commit()
    conn.close()
    if deleted > 0:
        logger.info(f"Cleaned up {deleted} alerts older than {days} days")


def get_alert_history():
    """Returns all alerts ever fired."""
    conn = get_connection()
    alerts = conn.execute(
        "SELECT * FROM alerts ORDER BY fired_at DESC"
    ).fetchall()
    conn.close()
    return [dict(a) for a in alerts]


if __name__ == "__main__":
    setup_database()
    logger.info("Brain test complete — database is working")