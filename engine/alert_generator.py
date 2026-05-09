"""
alert_generator.py — The Generator (Layer 4)
Uses Groq AI to generate personalized rep actions
for each validated signal + prospect match.
Generates: email draft, talking point, insight.
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def generate_email(prospect, signal):
    """Generates a personalized email draft for the rep."""
    prompt = f"""You are a B2B sales expert writing on behalf of LevaData — 
an AI-powered direct materials sourcing platform.

Write a short, personalized outreach email to a procurement leader at {prospect['company']}.

Context:
- Signal: {signal['signal_type'].replace('_', ' ').title()}
- News: {signal['headline']}
- Their key materials: {prospect.get('key_materials', 'direct materials')}
- Their sourcing regions: {prospect.get('sourcing_regions', 'global')}
- Pipeline stage: {prospect.get('pipeline_stage', 'cold')}

Rules:
- Max 4 sentences
- Lead with the external signal as context
- Position LevaData as a solution — not a pitch
- Sound human — not AI generated
- No subject line needed

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
    """Generates a call talking point for the rep."""
    prompt = f"""You are a B2B sales coach.
Give a sales rep ONE sharp talking point for a call with {prospect['company']}.

Signal: {signal['headline']}
Their materials: {prospect.get('key_materials', 'direct materials')}
Stage: {prospect.get('pipeline_stage', 'cold')}

One sentence only. Start with the business problem. End with a question.
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
    """Generates a relevant insight the rep can share."""
    prompt = f"""You are a supply chain intelligence analyst.
Write one short insight a sales rep can share with {prospect['company']}.

Signal: {signal['headline']}
Their materials: {prospect.get('key_materials', 'direct materials')}

2 sentences max. Make it genuinely useful — something a procurement leader
would find valuable. No fluff."""

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
    Main function — generates all 3 rep actions for one
    prospect + signal combination.
    Returns complete alert package.
    """
    print(f"[Generator] Generating alert for {prospect['company']} — {signal['signal_type']}")

    email = generate_email(prospect, signal)
    talking_point = generate_talking_point(prospect, signal)
    insight = generate_insight(prospect, signal)

    return {
        "company":       prospect["company"],
        "signal_type":   signal["signal_type"],
        "keyword":       signal["keyword"],
        "headline":      signal["headline"],
        "pipeline_stage": prospect.get("pipeline_stage", "cold"),
        "email_draft":   email,
        "talking_point": talking_point,
        "insight":       insight,
    }


if __name__ == "__main__":
    # Test with one prospect and one signal
    test_prospect = {
        "company":        "Tesla",
        "pipeline_stage": "active deal",
        "key_materials":  "Rare Earth, Lithium, Copper, Aluminum",
        "sourcing_regions": "China, Australia, Chile, DRC"
    }

    test_signal = {
        "signal_type": "commodity_shock",
        "keyword":     "rare earth",
        "headline":    "China tightens rare earth export controls citing national security",
        "sources_count": 3
    }

    alert = generate_alert(test_prospect, test_signal)

    print("\n" + "="*60)
    print("  ALERT PACKAGE — GTM INTELLIGENCE ENGINE")
    print("="*60)
    print(f"\nCOMPANY : {alert['company']}")
    print(f"SIGNAL  : {alert['signal_type']} — {alert['keyword']}")
    print(f"STAGE   : {alert['pipeline_stage']}")
    print(f"\nHEADLINE:\n{alert['headline']}")
    print(f"\nEMAIL DRAFT:\n{alert['email_draft']}")
    print(f"\nTALKING POINT:\n{alert['talking_point']}")
    print(f"\nINSIGHT TO SHARE:\n{alert['insight']}")
    print("="*60)