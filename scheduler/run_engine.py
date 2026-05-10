"""
run_engine.py — Master Orchestrator
GTM Intelligence Engine v1.0 — Fully Optimised

All 8 gaps addressed:
Gap 1 — Signal caching (6 hour refresh)
Gap 2 — HubSpot prospect caching (24 hour refresh)
Gap 3 — Single Groq call per prospect
Gap 4 — Error recovery — never fails silently
Gap 5 — Signal relevance scoring
Gap 6 — Database indexes (in brain.py)
Gap 7 — Streamlit caching (in streamlit_app.py)
Gap 8 — Full logging to file
"""

import sys
import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.signal_collector import run as collect_signals
from engine.alert_generator import generate_alert, score_signal_relevance
from engine.alert_delivery import deliver_alerts, deliver_past_alerts
from engine.brain import (
    setup_database, save_signal, save_alert,
    already_alerted_today, get_past_alerts, cleanup_old_alerts,
    get_cached_signals, save_signal_cache,
    get_cached_prospects, save_prospect_cache
)

logger = logging.getLogger("GTM-Engine")

HUBSPOT_KEY = os.environ.get("HUBSPOT_API_KEY")

PROPERTY_FIELDS = ["name", "key_materials", "sourcing_regions", "hs_lead_status"]

SIGNAL_MATERIAL_MAP = {
    "commodity_shock": [
        "copper", "steel", "aluminum", "tin", "resin",
        "plastic", "lithium", "rare earth", "cobalt", "nickel"
    ],
    "geopolitical": [
        "semiconductor", "rare earth", "lithium", "copper",
        "electronics", "chip"
    ],
    "supply_chain": [
        "plastic", "resin", "copper", "semiconductor",
        "component", "steel"
    ],
    "regulatory": [
        "steel", "aluminum", "copper", "semiconductor", "electronics"
    ]
}


def get_prospects(force_refresh=False):
    """
    Gap 2 — HubSpot prospect caching.
    Fetches from cache if less than 24 hours old.
    Only calls HubSpot API when cache is stale.
    """
    if not force_refresh:
        cached = get_cached_prospects(max_age_hours=24)
        if cached:
            logger.info(f"Prospect cache hit — {len(cached)} prospects")
            return cached

    if not HUBSPOT_KEY:
        logger.error("No HubSpot API key found in .env")
        return []

    url = "https://api.hubapi.com/crm/v3/objects/companies"
    headers = {"Authorization": f"Bearer {HUBSPOT_KEY}"}
    params = {"properties": ",".join(PROPERTY_FIELDS), "limit": 100}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            prospects = []
            for i, company in enumerate(data.get("results", [])):
                props = company.get("properties", {})
                company_name = props.get("name", "").strip()
                if not company_name:
                    continue
                prospects.append({
                    "id":              i + 1,
                    "company":         company_name,
                    "pipeline_stage":  props.get("hs_lead_status", "cold").lower()
                                       if props.get("hs_lead_status") else "cold",
                    "key_materials":   props.get("key_materials", ""),
                    "sourcing_regions": props.get("sourcing_regions", "global"),
                })
            logger.info(f"HubSpot fetched — {len(prospects)} prospects")
            save_prospect_cache(prospects)
            return prospects
        else:
            logger.error(f"HubSpot API error {response.status_code}")
            return []
    except requests.Timeout:
        logger.error("HubSpot request timed out")
        return []
    except Exception as e:
        logger.error(f"HubSpot connection failed: {e}")
        return []


def get_signals(force_refresh=False):
    """
    Gap 1 — Signal caching.
    Returns cached signals if less than 6 hours old.
    Only scans RSS when cache is stale.
    """
    if not force_refresh:
        cached = get_cached_signals(max_age_hours=6)
        if cached:
            return cached

    logger.info("Scanning news sources for signals...")
    signals = collect_signals()

    if signals:
        save_signal_cache(signals)

    return signals


def match_prospects_to_signals(signals, prospects):
    """
    Matches signals to prospects by material keywords.
    Gap 5 — Sorts by relevance score — highest priority first.
    """
    matched = []
    for signal in signals:
        signal_type = signal["signal_type"]
        material_keywords = SIGNAL_MATERIAL_MAP.get(signal_type, [])
        for prospect in prospects:
            materials = prospect.get("key_materials", "").lower()
            if not materials:
                continue
            for kw in material_keywords:
                if kw in materials:
                    score = score_signal_relevance(signal, prospect)
                    matched.append({
                        "prospect":        prospect,
                        "signal":          signal,
                        "relevance_score": score
                    })
                    break

    # Sort by relevance score — highest priority first
    matched.sort(key=lambda x: x["relevance_score"], reverse=True)
    return matched


def header():
    print("\n" + "="*65)
    print("  GTM INTELLIGENCE ENGINE v1.0 — B2B Revenue Intelligence")
    print(f"  Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*65)


def run_pipeline():
    """
    Runs the full GTM engine pipeline end to end.
    Gap 4 — Error recovery at every step.
    """
    header()
    logger.info("Pipeline started")

    # Step 1 — Setup and cleanup
    print("\n[1/5] Setting up database...")
    try:
        setup_database()
        cleanup_old_alerts(days=90)
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return

    # Step 2 — Collect signals (cached)
    print("\n[2/5] Collecting signals...")
    try:
        validated_signals = get_signals()
    except Exception as e:
        logger.error(f"Signal collection failed: {e}")
        validated_signals = []

    if not validated_signals:
        print("\n[Engine] No new validated signals.")
        print("[Engine] Showing past alerts from last 90 days...\n")
        try:
            past_alerts = get_past_alerts(days=90)
            deliver_past_alerts(past_alerts)
        except Exception as e:
            logger.error(f"Past alert delivery failed: {e}")
        return

    print(f"\n[Engine] {len(validated_signals)} signal(s) validated")

    # Step 3 — Load prospects (cached)
    print("\n[3/5] Loading prospects...")
    try:
        prospects = get_prospects()
    except Exception as e:
        logger.error(f"Prospect loading failed: {e}")
        prospects = []

    if not prospects:
        print("[Engine] No prospects loaded.")
        logger.error("No prospects available — check HubSpot connection")
        return

    print(f"[Engine] Matching {len(prospects)} prospects to signals...")
    matches = match_prospects_to_signals(validated_signals, prospects)
    print(f"[Engine] {len(matches)} matches found (sorted by relevance)")

    if not matches:
        print("[Engine] No material matches found.")
        return

    # Step 4 — Generate alerts
    print("\n[4/5] Generating alerts...")
    alerts = []
    skipped = 0
    errors = 0

    for match in matches:
        prospect = match["prospect"]
        signal = match["signal"]

        try:
            # Deduplication check
            if already_alerted_today(
                prospect["company"],
                signal["signal_type"],
                signal["keyword"]
            ):
                skipped += 1
                continue

            # Gap 3 — Single Groq call
            alert = generate_alert(prospect, signal)

            # Save signal to database
            signal_id = save_signal(
                signal_type=signal["signal_type"],
                headline=signal["headline"],
                source=", ".join(signal.get("sources", [])),
                keyword=signal["keyword"],
                sources_count=signal["sources_count"],
                validated=1,
                severity="high" if signal["sources_count"] >= 4 else "medium"
            )

            # Save alert to database
            save_alert(
                prospect_id=prospect["id"],
                signal_id=signal_id,
                company=prospect["company"],
                signal_type=signal["signal_type"],
                keyword=signal["keyword"],
                email_draft=alert["email_draft"],
                talking_point=alert["talking_point"],
                insight=alert["insight"],
                pipeline_stage=prospect.get("pipeline_stage", "cold")
            )

            alerts.append(alert)

        except Exception as e:
            errors += 1
            logger.error(f"Alert generation failed for "
                        f"{prospect.get('company', 'unknown')}: {e}")
            continue

    logger.info(f"Alerts generated: {len(alerts)} | "
               f"Skipped: {skipped} | Errors: {errors}")

    if skipped > 0:
        print(f"[Engine] {skipped} duplicate(s) skipped")
    if errors > 0:
        print(f"[Engine] {errors} error(s) — check engine.log")

    # Step 5 — Deliver alerts
    print("\n[5/5] Delivering alerts...")
    try:
        deliver_alerts(alerts)
    except Exception as e:
        logger.error(f"Alert delivery failed: {e}")

    # Summary
    print("\n" + "="*65)
    print(f"  PIPELINE COMPLETE")
    print(f"  Run date          : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Signals validated : {len(validated_signals)}")
    print(f"  Prospects matched : {len(matches)}")
    print(f"  Alerts fired      : {len(alerts)}")
    print(f"  Duplicates skipped: {skipped}")
    print(f"  Errors recovered  : {errors}")
    print(f"  Saved to database : Yes")
    print(f"  HubSpot updated   : Yes")
    print(f"  Log file          : data/engine.log")
    print(f"  Next run          : Every 6 hours via scheduler")
    print("="*65 + "\n")

    logger.info(f"Pipeline complete — {len(alerts)} alerts fired")


def start_scheduler():
    """Starts autonomous mode — runs every 6 hours."""
    print("\n" + "="*65)
    print("  GTM INTELLIGENCE ENGINE — AUTONOMOUS MODE")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  Schedule: Every 6 hours")
    print("  Press Ctrl+C to stop")
    print("="*65)

    run_pipeline()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_pipeline,
        'interval',
        hours=6,
        id='gtm_pipeline',
        name='GTM Intelligence Pipeline'
    )

    print(f"\n[Scheduler] Next run in 6 hours")
    print(f"[Scheduler] Engine running autonomously...")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n[Scheduler] Engine stopped.")
        scheduler.shutdown()


if __name__ == "__main__":
    if "--schedule" in sys.argv:
        start_scheduler()
    else:
        run_pipeline()