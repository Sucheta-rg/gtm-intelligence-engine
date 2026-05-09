"""
alert_generator.py — The Generator (Layer 4)
Uses Groq AI to generate personalized rep actions.
Personalizes by pipeline stage:
- Cold: insight only — lead with value
- Warm: full email draft
- Active Deal: urgent talking point
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def generate_email(prospect, signal):
    """Generates personalized email — for WARM prospects."""
    stage = prospect.get("pipeline_stage", "cold").lower()

    prompt = f"""You are a B2B sales expert writing to a procurement leader.
Company: {prospect['company']}
Pipeline stage: {stage}
Signal: {signal['signal_type'].replace('_', ' ').title()}
News: {signal['headline']}
Their materials: {prospect.get('key_materials', 'direct materials')}
Their sourcing: {prospect.get('sourcing_regions', 'global')}

Write a SHORT personalized email. Rules:
- Max 4 sentences
- Lead with the external signal as context
- Position our solution as genuinely helpful — not a pitch
- Sound human — not AI generated
- No subject line needed
- End with one specific question

Write only the email body."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Email generation failed: {e}]"


def generate_talking_point(prospect, signal):
    """Generates urgent talking point — for ACTIVE DEAL prospects."""
    prompt = f"""You are a B2B sales coach.
Give ONE sharp urgent talking point for a call with {prospect['company']}.
They are in active deal stage — this signal directly affects their decision.

Signal: {signal['headline']}
Their materials: {prospect.get('key_materials', 'direct materials')}

One sentence only. Create urgency. End with a question.
No preamble."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=100,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Talking point generation failed: {e}]"


def generate_insight(prospect, signal):
    """Generates valuable insight — for COLD prospects."""
    prompt = f"""You are a supply chain intelligence analyst.
Write one SHORT insight a sales rep can share with {prospect['company']}.
This prospect is cold — they don't know us yet.
Lead with genuine value. No selling.

Signal: {signal['headline']}
Their materials: {prospect.get('key_materials', 'direct materials')}

2 sentences max. Make it genuinely useful."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Insight generation failed: {e}]"


def generate_alert(prospect, signal):
    """
    Main function — generates personalized rep actions
    based on pipeline stage.

    Cold     → insight only (lead with value)
    Warm     → email draft (personal and specific)
    Active   → talking point (urgent, decision focused)
    All      → get all 3 but primary action highlighted
    """
    stage = prospect.get("pipeline_stage", "cold").lower()
    company = prospect["company"]

    print(f"[Generator] {company} — {stage} — {signal['signal_type']}")

    # Generate all 3 actions
    email = generate_email(prospect, signal)
    talking_point = generate_talking_point(prospect, signal)
    insight = generate_insight(prospect, signal)

    # Set primary action based on pipeline stage
    if "active" in stage or "deal" in stage:
        primary_action = "TALKING POINT"
        urgency = "HIGH"
    elif stage == "warm":
        primary_action = "EMAIL"
        urgency = "MEDIUM"
    else:
        primary_action = "INSIGHT"
        urgency = "LOW"

    return {
        "company":        company,
        "signal_type":    signal["signal_type"],
        "keyword":        signal["keyword"],
        "headline":       signal["headline"],
        "pipeline_stage": stage,
        "primary_action": primary_action,
        "urgency":        urgency,
        "email_draft":    email,
        "talking_point":  talking_point,
        "insight":        insight,
        "fired_at":       __import__("datetime").datetime.now().strftime(
                          "%Y-%m-%d %H:%M"),
    }


if __name__ == "__main__":
    # Test with 3 different pipeline stages
    test_signal = {
        "signal_type": "commodity_shock",
        "keyword":     "rare earth",
        "headline":    "China tightens rare earth export controls",
        "sources_count": 3
    }

    stages = [
        {"company": "Tesla",     "pipeline_stage": "active deal",
         "key_materials": "Rare Earth, Lithium, Copper",
         "sourcing_regions": "China, Australia"},
        {"company": "Honeywell", "pipeline_stage": "warm",
         "key_materials": "Copper, Steel, Aluminum",
         "sourcing_regions": "China, Canada"},
        {"company": "Dyson",     "pipeline_stage": "cold",
         "key_materials": "Plastics, Resins, Copper",
         "sourcing_regions": "China, Southeast Asia"},
    ]

    for prospect in stages:
        alert = generate_alert(prospect, test_signal)
        print(f"\n{'='*50}")
        print(f"COMPANY : {alert['company']}")
        print(f"STAGE   : {alert['pipeline_stage']}")
        print(f"PRIMARY : {alert['primary_action']} ({alert['urgency']})")
        print(f"\nEMAIL:\n{alert['email_draft'][:200]}...")
        print(f"\nTALKING POINT:\n{alert['talking_point']}")
        print(f"\nINSIGHT:\n{alert['insight'][:200]}...")