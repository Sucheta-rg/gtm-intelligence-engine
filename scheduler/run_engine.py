"""
run_engine.py — Master Orchestrator
GTM Intelligence Engine v1.0
Fetches all prospects automatically from HubSpot.
Matches signals to prospects by material keywords.
No hardcoding — fully dynamic.
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
from engine.alert_delivery import deliver_alerts
from engine.brain import setup_database, save_signal, save_alert

HUBSPOT_KEY = os.environ.get("HUBSPOT_API_KEY")

PROPERTY_FIELDS = ["name", "key_materials", "sourcing_regions", "hs_lead_status"]

# Maps signal types to material keywords
# This is the engine's internal intelligence — never changes
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
    """
    Fetches ALL companies from HubSpot automatically.
    Rep adds any company to HubSpot — engine picks it up next run.
    Company materials come from HubSpot — nothing hardcoded here.
    """
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
    """
    Matches validated signals to prospects using material keywords.
    Reads materials from HubSpot — no hardcoding needed.
    New companies added to HubSpot are automatically matched.
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
    """Runs the full GTM engine pipeline end to end."""
    header()

    print("\n[1/5] Setting up database...")
    setup_database()

    print("\n[2/5] Running signal collection...")
    validated_signals = collect_signals()

    if not validated_signals:
        print("\n[Engine] No validated signals today. Pipeline complete.")
        return

    print(f"\n[Engine] {len(validated_signals)} signal(s) passed validation gate")

    print("\n[3/5] Fetching prospects from HubSpot automatically...")
    prospects = get_prospects_from_hubspot()

    if not prospects:
        print("[Engine] No prospects loaded — check HubSpot connection.")
        return

    print(f"[Engine] Matching {len(prospects)} prospects against signals by material...")
    matches = match_prospects_to_signals(validated_signals, prospects)
    print(f"[Engine] {len(matches)} prospect(s) affected by today's signals")

    if not matches:
        print("[Engine] No material matches found — check key_materials in HubSpot.")
        return

    print("\n[4/5] Generating personalized alerts with Groq AI...")
    alerts = []
    for match in matches:
        alert = generate_alert(match["prospect"], match["signal"])
        signal_id = save_signal(
            signal_type=match["signal"]["signal_type"],
            headline=match["signal"]["headline"],
            source=", ".join(match["signal"]["sources"]),
            keyword=match["signal"]["keyword"],
            sources_count=match["signal"]["sources_count"],
            validated=1
        )
        save_alert(
            prospect_id=match["prospect"]["id"],
            signal_id=signal_id,
            email_draft=alert["email_draft"],
            talking_point=alert["talking_point"],
            insight=alert["insight"]
        )
        alerts.append(alert)

    print("\n[5/5] Delivering alerts...")
    deliver_alerts(alerts)

    print("\n" + "="*65)
    print(f"  PIPELINE COMPLETE")
    print(f"  Signals validated : {len(validated_signals)}")
    print(f"  Prospects matched : {len(matches)}")
    print(f"  Alerts fired      : {len(alerts)}")
    print(f"  Saved to database : Yes")
    print(f"  Next run          : Scheduled every 6 hours")
    print("="*65 + "\n")


if __name__ == "__main__":
    run_pipeline()