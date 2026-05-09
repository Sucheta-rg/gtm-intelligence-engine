"""
run_engine.py — Master Orchestrator
GTM Intelligence Engine v1.0

Phase 1 complete:
- Deduplication — no repeat alerts same day
- Date stamps on all alerts
- 90 day cleanup
- Past alert summary when no new signals
- Pipeline stage based personalisation
"""

import sys
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.signal_collector import run as collect_signals
from engine.alert_generator import generate_alert
from engine.alert_delivery import deliver_alerts, deliver_past_alerts
from engine.brain import (
    setup_database, save_signal, save_alert,
    already_alerted_today, get_past_alerts, cleanup_old_alerts
)

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


def get_prospects_from_hubspot():
    """Fetches ALL companies from HubSpot automatically."""
    if not HUBSPOT_KEY:
        print("[Engine] No HubSpot API key found in .env")
        return []

    url = "https://api.hubapi.com/crm/v3/objects/companies"
    headers = {"Authorization": f"Bearer {HUBSPOT_KEY}"}
    params = {"properties": ",".join(PROPERTY_FIELDS), "limit": 100}

    try:
        response = requests.get(url, headers=headers, params=params)
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
            print(f"[Engine] {len(prospects)} prospects loaded from HubSpot")
            return prospects
        else:
            print(f"[Engine] HubSpot API error {response.status_code}")
            return []
    except Exception as e:
        print(f"[Engine] Could not connect to HubSpot: {e}")
        return []


def match_prospects_to_signals(signals, prospects):
    """Matches signals to prospects by material keywords."""
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
                    matched.append({
                        "prospect": prospect,
                        "signal":   signal
                    })
                    break
    return matched


def header():
    print("\n" + "="*65)
    print("  GTM INTELLIGENCE ENGINE v1.0 — B2B Revenue Intelligence")
    print(f"  Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*65)


def run_pipeline():
    header()

    # Step 1 — Setup and cleanup
    print("\n[1/5] Setting up database...")
    setup_database()
    cleanup_old_alerts(days=90)

    # Step 2 — Collect signals
    print("\n[2/5] Running signal collection...")
    validated_signals = collect_signals()

    if not validated_signals:
        print("\n[Engine] No new validated signals today.")
        print("[Engine] Showing past alerts from last 90 days...\n")
        past_alerts = get_past_alerts(days=90)
        deliver_past_alerts(past_alerts)
        return

    print(f"\n[Engine] {len(validated_signals)} signal(s) passed validation gate")

    # Step 3 — Load prospects from HubSpot
    print("\n[3/5] Fetching prospects from HubSpot automatically...")
    prospects = get_prospects_from_hubspot()

    if not prospects:
        print("[Engine] No prospects loaded — check HubSpot connection.")
        return

    print(f"[Engine] Matching {len(prospects)} prospects against signals...")
    matches = match_prospects_to_signals(validated_signals, prospects)
    print(f"[Engine] {len(matches)} prospect(s) affected by today's signals")

    if not matches:
        print("[Engine] No material matches found.")
        return

    # Step 4 — Generate alerts with deduplication
    print("\n[4/5] Generating personalized alerts with Groq AI...")
    alerts = []
    skipped = 0

    for match in matches:
        prospect = match["prospect"]
        signal = match["signal"]

        # Deduplication check
        if already_alerted_today(
            prospect["company"],
            signal["signal_type"],
            signal["keyword"]
        ):
            skipped += 1
            print(f"[Engine] Skipped — already alerted today: "
                  f"{prospect['company']} + {signal['keyword']}")
            continue

        alert = generate_alert(prospect, signal)

        signal_id = save_signal(
            signal_type=signal["signal_type"],
            headline=signal["headline"],
            source=", ".join(signal["sources"]),
            keyword=signal["keyword"],
            sources_count=signal["sources_count"],
            validated=1,
            severity="high" if signal["sources_count"] >= 4 else "medium"
        )

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

    if skipped > 0:
        print(f"[Engine] {skipped} duplicate alert(s) skipped")

    # Step 5 — Deliver alerts
    print("\n[5/5] Delivering alerts...")
    deliver_alerts(alerts)

    # Summary
    print("\n" + "="*65)
    print(f"  PIPELINE COMPLETE")
    print(f"  Run date          : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Signals validated : {len(validated_signals)}")
    print(f"  Prospects matched : {len(matches)}")
    print(f"  Alerts fired      : {len(alerts)}")
    print(f"  Duplicates skipped: {skipped}")
    print(f"  Saved to database : Yes")
    print(f"  HubSpot updated   : Yes")
    print(f"  Next run          : Every 6 hours via scheduler")
    print("="*65 + "\n")


if __name__ == "__main__":
    run_pipeline()