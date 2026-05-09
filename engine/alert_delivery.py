"""
alert_delivery.py — The Delivery Layer (Layer 5)
Formats and delivers alerts to sales reps.
Currently: terminal output (portfolio demo).
Future: email via Gmail SMTP, Slack webhook.
"""

from datetime import datetime


def print_alert(alert):
    """Prints a beautifully formatted alert to terminal."""
    width = 65
    border = "═" * width

    print(f"\n╔{border}╗")
    print(f"║  🚨 REVENUE ALERT — GTM INTELLIGENCE ENGINE{' ' * 20}║")
    print(f"╠{border}╣")
    print(f"║  COMPANY   : {alert['company']:<51}║")
    print(f"║  SIGNAL    : {alert['signal_type'].replace('_',' ').title():<51}║")
    print(f"║  KEYWORD   : {alert['keyword']:<51}║")
    print(f"║  STAGE     : {alert['pipeline_stage']:<51}║")
    print(f"║  DETECTED  : {datetime.now().strftime('%Y-%m-%d %H:%M'):<51}║")
    print(f"╠{border}╣")
    print(f"║  HEADLINE:{'  ' * 28}║")

    # Word wrap headline
    words = alert['headline'].split()
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
    print(f"║  EMAIL DRAFT:{'  ' * 27}║")
    words = alert['email_draft'].split()
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
    print(f"║  TALKING POINT:{'  ' * 26}║")
    words = alert['talking_point'].split()
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
    print(f"║  INSIGHT TO SHARE:{'  ' * 23}║")
    words = alert['insight'].split()
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


def deliver_alerts(alerts):
    """Delivers all alerts to reps."""
    if not alerts:
        print("[Delivery] No alerts to deliver today.")
        return

    print(f"[Delivery] Firing {len(alerts)} alert(s)...\n")
    for alert in alerts:
        print_alert(alert)

    print(f"[Delivery] Done — {len(alerts)} alert(s) delivered.")
    print("[Delivery] Next step: connect Gmail/Slack for live delivery.")


if __name__ == "__main__":
    # Test with sample alert
    test_alert = {
        "company":       "Tesla",
        "signal_type":   "commodity_shock",
        "keyword":       "rare earth",
        "headline":      "China tightens rare earth export controls citing national security",
        "pipeline_stage": "active deal",
        "email_draft":   "Given China's rare earth export controls, Tesla's supply chain faces immediate risk. LevaData helps procurement teams identify alternative suppliers fast.",
        "talking_point": "With China restricting rare earths, how is Tesla protecting motor magnet supply for Q3 production?",
        "insight":       "Australia and Canada are emerging as alternative rare earth suppliers — companies moving now are securing 12-month contracts before prices spike further."
    }

    deliver_alerts([test_alert])