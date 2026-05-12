"""
alert_delivery.py — The Delivery Layer (Layer 5)
1. Terminal output with date stamps
2. HubSpot note — written automatically to company record
3. Gmail — sends real email to rep inbox
"""

import os
import requests
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("GTM-Engine")

HUBSPOT_KEY    = os.environ.get("HUBSPOT_API_KEY")
GMAIL_SENDER   = os.environ.get("GMAIL_SENDER")
GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GMAIL_RECIPIENT = os.environ.get("GMAIL_RECIPIENT")


def print_alert(alert, is_past=False):
    """Prints formatted alert to terminal with date stamp."""
    width  = 65
    border = "═" * width
    label  = "📋 PAST ALERT — FOLLOW UP" if is_past \
             else "🚨 REVENUE ALERT — GTM INTELLIGENCE ENGINE"

    print(f"\n╔{border}╗")
    print(f"║  {label:<63}║")
    print(f"╠{border}╣")
    print(f"║  COMPANY   : {alert.get('company',''):<51}║")
    print(f"║  SIGNAL    : {str(alert.get('signal_type','')).replace('_',' ').title():<51}║")
    print(f"║  KEYWORD   : {alert.get('keyword',''):<51}║")
    print(f"║  STAGE     : {alert.get('pipeline_stage','cold'):<51}║")
    date_str = alert.get('fired_at', alert.get(
        'detected_at', datetime.now().strftime('%Y-%m-%d %H:%M')))
    print(f"║  DATE      : {date_str:<51}║")
    print(f"║  URGENCY   : {alert.get('urgency','MEDIUM'):<51}║")
    print(f"║  PRIMARY   : {alert.get('primary_action','EMAIL'):<51}║")
    print(f"╠{border}╣")

    def wrap(title, text):
        if not text:
            return
        print(f"║  {title}:{' '*(width-len(title)-2)}║")
        words = str(text).split()
        line  = "║  "
        for word in words:
            if len(line) + len(word) + 1 > width + 2:
                print(f"{line:<{width+3}}║")
                line = "║  " + word + " "
            else:
                line += word + " "
        if line.strip():
            print(f"{line:<{width+3}}║")
        print(f"╠{border}╣")

    wrap("HEADLINE",      alert.get('headline',''))
    wrap("EMAIL DRAFT",   alert.get('email_draft',''))
    wrap("TALKING POINT", alert.get('talking_point',''))

    insight = alert.get('insight','')
    if insight:
        print(f"║  INSIGHT TO SHARE:{' '*(width-19)}║")
        words = str(insight).split()
        line  = "║  "
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
        url     = "https://api.hubapi.com/crm/v3/objects/companies/search"
        headers = {
            "Authorization": f"Bearer {HUBSPOT_KEY}",
            "Content-Type":  "application/json"
        }
        payload = {
            "filterGroups": [{"filters": [{
                "propertyName": "name",
                "operator":     "EQ",
                "value":        company_name
            }]}],
            "properties": ["name"]
        }
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                return results[0]["id"]
    except Exception as e:
        logger.error(f"HubSpot search error: {e}")
    return None


def write_hubspot_note(company_id, alert):
    """Writes alert as a note on the HubSpot company record."""
    if not HUBSPOT_KEY or not company_id:
        return False
    try:
        date_str  = alert.get('fired_at', datetime.now().strftime('%Y-%m-%d %H:%M'))
        note_body = f"""🚨 GTM INTELLIGENCE ENGINE ALERT

Date: {date_str}
Signal: {str(alert.get('signal_type','')).replace('_', ' ').title()}
Keyword: {alert.get('keyword', '')}
Headline: {alert.get('headline', '')}
Pipeline Stage: {alert.get('pipeline_stage', 'cold')}
Urgency: {alert.get('urgency', 'MEDIUM')}
Primary Action: {alert.get('primary_action', 'EMAIL')}

EMAIL DRAFT:
{alert.get('email_draft', '')}

TALKING POINT:
{alert.get('talking_point', '')}

INSIGHT TO SHARE:
{alert.get('insight', '')}"""

        url     = "https://api.hubapi.com/crm/v3/objects/notes"
        headers = {
            "Authorization": f"Bearer {HUBSPOT_KEY}",
            "Content-Type":  "application/json"
        }
        payload = {
            "properties": {
                "hs_note_body": note_body,
                "hs_timestamp": str(int(datetime.now().timestamp() * 1000))
            }
        }
        note_response = requests.post(url, headers=headers, json=payload, timeout=10)

        if note_response.status_code == 201:
            note_id  = note_response.json()["id"]
            assoc_url = (
                f"https://api.hubapi.com/crm/v3/objects/notes/"
                f"{note_id}/associations/companies/"
                f"{company_id}/note_to_company"
            )
            requests.put(assoc_url,
                headers={"Authorization": f"Bearer {HUBSPOT_KEY}"}, timeout=10)
            logger.info(f"HubSpot note written — {alert.get('company')}")
            print(f"[Delivery] ✓ HubSpot note — {alert.get('company')}")
            return True
        else:
            logger.error(f"HubSpot note error {note_response.status_code}")
            return False
    except Exception as e:
        logger.error(f"HubSpot note error: {e}")
        return False


def send_gmail_alert(alert):
    """
    Sends alert as a real email to the sales rep.
    Uses Gmail SMTP with App Password.
    """
    if not all([GMAIL_SENDER, GMAIL_PASSWORD, GMAIL_RECIPIENT]):
        logger.warning("Gmail not configured — skipping email delivery")
        return False

    try:
        company      = alert.get('company', '')
        signal_type  = str(alert.get('signal_type', '')).replace('_', ' ').title()
        keyword      = alert.get('keyword', '')
        urgency      = alert.get('urgency', 'MEDIUM')
        primary      = alert.get('primary_action', 'EMAIL')
        stage        = alert.get('pipeline_stage', 'cold')
        date_str     = alert.get('fired_at', datetime.now().strftime('%Y-%m-%d %H:%M'))

        subject = f"🚨 [{urgency}] {company} — {signal_type} Signal Detected"

        # HTML email body
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; 
         background: #F8F9FC; margin: 0; padding: 20px; }}
  .container {{ max-width: 640px; margin: 0 auto; 
                background: white; border-radius: 12px; 
                border: 1px solid #E2E8F0; overflow: hidden; }}
  .header {{ background: linear-gradient(135deg, #0F1629, #1B4F8A); 
             padding: 24px 32px; }}
  .header h1 {{ color: white; font-size: 20px; margin: 0 0 4px 0; }}
  .header p {{ color: #94A3B8; font-size: 13px; margin: 0; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px;
            font-size: 11px; font-weight: 700; margin-right: 6px; }}
  .badge-red {{ background: #FEE2E2; color: #DC2626; }}
  .badge-blue {{ background: #DBEAFE; color: #1D4ED8; }}
  .badge-grey {{ background: #F1F5F9; color: #475569; }}
  .body {{ padding: 24px 32px; }}
  .section {{ margin-bottom: 20px; }}
  .section-label {{ font-size: 11px; font-weight: 700; 
                    text-transform: uppercase; letter-spacing: 0.8px;
                    color: #94A3B8; margin-bottom: 8px; }}
  .section-content {{ font-size: 14px; color: #374151; 
                      line-height: 1.6; background: #F8F9FC;
                      border-radius: 8px; padding: 14px 16px;
                      border-left: 3px solid #3B82F6; }}
  .section-content-amber {{ border-left-color: #F59E0B; }}
  .section-content-green {{ border-left-color: #22C55E; }}
  .headline {{ font-size: 15px; font-weight: 600; color: #0F1629;
               background: #EEF2FF; border-radius: 8px; 
               padding: 14px 16px; margin-bottom: 20px;
               border-left: 3px solid #6366F1; }}
  .footer {{ background: #F8F9FC; padding: 16px 32px; 
             border-top: 1px solid #E2E8F0; text-align: center;
             font-size: 12px; color: #94A3B8; }}
  .meta {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🚨 GTM Intelligence Engine Alert</h1>
    <p>Proactive revenue intelligence — automated signal detection</p>
  </div>
  <div class="body">
    <div class="meta">
      <span class="badge badge-red">⚡ {urgency} URGENCY</span>
      <span class="badge badge-blue">{signal_type}</span>
      <span class="badge badge-grey">{stage.title()}</span>
      <span class="badge badge-grey">Primary: {primary}</span>
    </div>

    <div style="font-size: 22px; font-weight: 700; color: #0F1629; 
                margin-bottom: 4px;">🏭 {company}</div>
    <div style="font-size: 13px; color: #64748B; margin-bottom: 16px; 
                font-family: monospace;">
      Signal: {keyword} &nbsp;|&nbsp; Detected: {date_str}
    </div>

    <div class="headline">📰 {alert.get('headline','')}</div>

    <div class="section">
      <div class="section-label">📧 Suggested Email Draft</div>
      <div class="section-content">{alert.get('email_draft','')}</div>
    </div>

    <div class="section">
      <div class="section-label">📞 Call Talking Point</div>
      <div class="section-content section-content-amber">
        {alert.get('talking_point','')}
      </div>
    </div>

    <div class="section">
      <div class="section-label">💡 Insight to Share</div>
      <div class="section-content section-content-green">
        {alert.get('insight','')}
      </div>
    </div>
  </div>
  <div class="footer">
    GTM Intelligence Engine v1.0 &nbsp;·&nbsp; 
    Proactive revenue intelligence for B2B sales teams
  </div>
</div>
</body>
</html>"""

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = GMAIL_SENDER
        msg['To']      = GMAIL_RECIPIENT
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_SENDER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_SENDER, GMAIL_RECIPIENT, msg.as_string())

        logger.info(f"Gmail sent — {company} alert to {GMAIL_RECIPIENT}")
        print(f"[Delivery] ✓ Gmail sent — {company}")
        return True

    except Exception as e:
        logger.error(f"Gmail error for {alert.get('company')}: {e}")
        print(f"[Delivery] Gmail failed — {alert.get('company')}: {e}")
        return False


def deliver_alerts(alerts):
    """Delivers all alerts — terminal + HubSpot + Gmail."""
    if not alerts:
        print("[Delivery] No new alerts to deliver today.")
        return

    print(f"[Delivery] Firing {len(alerts)} alert(s)...\n")
    gmail_sent = 0

    for alert in alerts:
        # 1. Terminal
        print_alert(alert, is_past=False)

        # 2. HubSpot note
        company_id = get_hubspot_company_id(alert.get('company', ''))
        if company_id:
            write_hubspot_note(company_id, alert)

        # 3. Gmail
        if send_gmail_alert(alert):
            gmail_sent += 1

    print(f"\n[Delivery] Done — {len(alerts)} alert(s) delivered.")
    print(f"[Delivery] HubSpot notes written to all company records.")
    print(f"[Delivery] Gmail sent: {gmail_sent}/{len(alerts)}")


def deliver_past_alerts(past_alerts):
    """Shows past alerts when no new signals today."""
    if not past_alerts:
        print("[Delivery] No past alerts in last 90 days.")
        return

    print(f"[Delivery] Showing {len(past_alerts)} past alert(s) "
          f"from last 90 days:\n")

    for alert in past_alerts[:10]:
        print_alert(alert, is_past=True)

    if len(past_alerts) > 10:
        print(f"[Delivery] ... and {len(past_alerts)-10} more in database.")