"""
alert_delivery.py — The Delivery Layer (Layer 5)
1. Terminal output with date stamps
2. HubSpot note — written automatically to company record
3. Past alert summary when no new signals
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

HUBSPOT_KEY = os.environ.get("HUBSPOT_API_KEY")


def print_alert(alert, is_past=False):
    """Prints a formatted alert to terminal with date stamp."""
    width = 65
    border = "═" * width
    label = "📋 PAST ALERT — FOLLOW UP" if is_past else "🚨 REVENUE ALERT — GTM INTELLIGENCE ENGINE"

    print(f"\n╔{border}╗")
    print(f"║  {label:<63}║")
    print(f"╠{border}╣")
    print(f"║  COMPANY   : {alert.get('company', ''):<51}║")
    print(f"║  SIGNAL    : {str(alert.get('signal_type', '')).replace('_',' ').title():<51}║")
    print(f"║  KEYWORD   : {alert.get('keyword', ''):<51}║")
    print(f"║  STAGE     : {alert.get('pipeline_stage', 'cold'):<51}║")

    # Date stamp
    date_str = alert.get('fired_at', alert.get('detected_at',
               datetime.now().strftime('%Y-%m-%d %H:%M')))
    print(f"║  DATE      : {date_str:<51}║")
    print(f"║  URGENCY   : {alert.get('urgency', 'MEDIUM'):<51}║")
    print(f"║  PRIMARY   : {alert.get('primary_action', 'EMAIL'):<51}║")
    print(f"╠{border}╣")

    def wrap(title, text):
        if not text:
            return
        print(f"║  {title}:{' '*(width-len(title)-2)}║")
        words = str(text).split()
        line = "║  "
        for word in words:
            if len(line) + len(word) + 1 > width + 2:
                print(f"{line:<{width+3}}║")
                line = "║  " + word + " "
            else:
                line += word + " "
        if line.strip():
            print(f"{line:<{width+3}}║")
        print(f"╠{border}╣")

    wrap("HEADLINE", alert.get('headline', ''))
    wrap("EMAIL DRAFT", alert.get('email_draft', ''))
    wrap("TALKING POINT", alert.get('talking_point', ''))

    # Insight — last section no divider after
    insight = alert.get('insight', '')
    if insight:
        print(f"║  INSIGHT TO SHARE:{' '*(width-19)}║")
        words = str(insight).split()
        line = "║  "
        for word in words:
            if len(line) + len(word) + 1 > width + 2:
                print(f"{line:<{width+3}}║")
                line = "║  " + word + " "
            else:
                line += word + " "
        if line.strip():
            print(f"{line:<{width+3}}║")

    print(f"╚{border}╝\n")


def get_hubspot_company_id(company_name):
    """Finds HubSpot company ID by name."""
    if not HUBSPOT_KEY:
        return None
    try:
        url = "https://api.hubapi.com/crm/v3/objects/companies/search"
        headers = {
            "Authorization": f"Bearer {HUBSPOT_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "name",
                    "operator": "EQ",
                    "value": company_name
                }]
            }],
            "properties": ["name"]
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                return results[0]["id"]
    except Exception as e:
        print(f"[Delivery] HubSpot search error: {e}")
    return None


def write_hubspot_note(company_id, alert):
    """Writes alert as a note on the HubSpot company record."""
    if not HUBSPOT_KEY or not company_id:
        return False
    try:
        date_str = alert.get('fired_at',
                   datetime.now().strftime('%Y-%m-%d %H:%M'))

        note_body = f"""🚨 GTM INTELLIGENCE ENGINE ALERT

Date: {date_str}
Signal: {str(alert.get('signal_type','')).replace('_', ' ').title()}
Keyword: {alert.get('keyword', '')}
Headline: {alert.get('headline', '')}
Pipeline Stage: {alert.get('pipeline_stage', 'cold')}

EMAIL DRAFT:
{alert.get('email_draft', '')}

TALKING POINT:
{alert.get('talking_point', '')}

INSIGHT TO SHARE:
{alert.get('insight', '')}"""

        url = "https://api.hubapi.com/crm/v3/objects/notes"
        headers = {
            "Authorization": f"Bearer {HUBSPOT_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "properties": {
                "hs_note_body":  note_body,
                "hs_timestamp":  str(int(
                    datetime.now().timestamp() * 1000))
            }
        }
        note_response = requests.post(url, headers=headers, json=payload)

        if note_response.status_code == 201:
            note_id = note_response.json()["id"]
            assoc_url = (
                f"https://api.hubapi.com/crm/v3/objects/notes/"
                f"{note_id}/associations/companies/"
                f"{company_id}/note_to_company"
            )
            requests.put(assoc_url,
                headers={"Authorization": f"Bearer {HUBSPOT_KEY}"})
            print(f"[Delivery] ✓ HubSpot note — {alert.get('company')}")
            return True
        else:
            print(f"[Delivery] HubSpot error {note_response.status_code}")
            return False
    except Exception as e:
        print(f"[Delivery] HubSpot note error: {e}")
        return False


def deliver_alerts(alerts):
    """Delivers new alerts — terminal + HubSpot notes."""
    if not alerts:
        print("[Delivery] No new alerts to deliver today.")
        return

    print(f"[Delivery] Firing {len(alerts)} new alert(s)...\n")

    for alert in alerts:
        print_alert(alert, is_past=False)
        company_id = get_hubspot_company_id(alert.get('company', ''))
        if company_id:
            write_hubspot_note(company_id, alert)
        else:
            print(f"[Delivery] Could not find "
                  f"{alert.get('company')} in HubSpot")

    print(f"\n[Delivery] Done — {len(alerts)} alert(s) delivered.")
    print("[Delivery] All alerts visible in HubSpot company records.")


def deliver_past_alerts(past_alerts):
    """
    Shows past alerts when no new signals today.
    Gives reps context for follow up.
    """
    if not past_alerts:
        print("[Delivery] No past alerts in last 90 days.")
        print("[Delivery] Pipeline is quiet — no signals detected.")
        return

    print(f"[Delivery] Showing {len(past_alerts)} past alert(s) "
          f"from last 90 days for follow up:\n")

    for alert in past_alerts[:10]:  # Show max 10 past alerts
        print_alert(alert, is_past=True)

    if len(past_alerts) > 10:
        print(f"[Delivery] ... and {len(past_alerts)-10} more in database.")
    print("[Delivery] Review past alerts and follow up with prospects.")