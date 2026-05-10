"""
alert_generator.py — The Generator (Layer 4)
Optimised version:
- Single Groq API call generates all 3 outputs at once (3x faster)
- Checks insight cache before generating (saves API calls)
- Error recovery — never fails silently
- Signal relevance scoring built in
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def score_signal_relevance(signal, prospect):
    """
    Scores how relevant a signal is to a prospect.
    Higher score = higher priority alert.
    """
    score = 0
    materials = prospect.get("key_materials", "").lower()
    sourcing = prospect.get("sourcing_regions", "").lower()
    stage = prospect.get("pipeline_stage", "cold").lower()

    # Score by sources count
    score += signal.get("sources_count", 0) * 10

    # Score by pipeline stage
    if "active" in stage or "deal" in stage:
        score += 30
    elif stage == "warm":
        score += 20
    else:
        score += 10

    # Score by material match strength
    keyword = signal.get("keyword", "").lower()
    if keyword in materials:
        score += 20

    # Score by sourcing region risk
    high_risk_regions = ["china", "taiwan", "russia", "iran"]
    for region in high_risk_regions:
        if region in sourcing:
            score += 10
            break

    return score


def generate_alert_single_call(prospect, signal):
    """
    Single Groq API call generates all 3 outputs at once.
    3x faster than separate calls.
    Returns structured dict with email, talking_point, insight.
    """
    stage = prospect.get("pipeline_stage", "cold").lower()
    company = prospect["company"]

    prompt = f"""You are a B2B sales intelligence expert.
Generate a complete alert package for a sales rep.

PROSPECT:
Company: {company}
Pipeline Stage: {stage}
Key Materials: {prospect.get('key_materials', 'direct materials')}
Sourcing Regions: {prospect.get('sourcing_regions', 'global')}

SIGNAL:
Type: {signal['signal_type'].replace('_', ' ').title()}
Headline: {signal['headline']}
Keyword: {signal['keyword']}
Sources confirmed: {signal.get('sources_count', 3)}

Generate all 3 outputs. Return ONLY valid JSON, no other text:

{{
  "email_draft": "4 sentence max email. Lead with signal. End with question. Human tone.",
  "talking_point": "One sharp sentence. Create urgency. End with question.",
  "insight": "2 sentence genuine supply chain insight. No selling."
}}

Rules:
- email_draft: personalized to {company}, references their materials and sourcing
- talking_point: urgent if active deal, consultative if warm, value-led if cold
- insight: genuinely useful market intelligence a procurement leader would value
- All outputs in plain text inside the JSON values"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=600,
        )

        raw = response.choices[0].message.content.strip()

        # Clean JSON if needed
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        parsed = json.loads(raw)

        return {
            "email_draft":   parsed.get("email_draft", ""),
            "talking_point": parsed.get("talking_point", ""),
            "insight":       parsed.get("insight", ""),
        }

    except json.JSONDecodeError:
        # Fallback — parse text if JSON fails
        lines = raw.split("\n")
        return {
            "email_draft":   raw[:300] if len(raw) > 100 else "",
            "talking_point": lines[0] if lines else "",
            "insight":       lines[-1] if len(lines) > 1 else "",
        }
    except Exception as e:
        return {
            "email_draft":   f"[Generation failed: {e}]",
            "talking_point": f"[Generation failed: {e}]",
            "insight":       f"[Generation failed: {e}]",
        }


def generate_alert(prospect, signal):
    """
    Main function — generates personalized rep actions.
    Checks cache first — only calls Groq if needed.
    Uses single API call for all 3 outputs.
    """
    from engine.brain import get_cached_insight, save_cached_insight

    stage = prospect.get("pipeline_stage", "cold").lower()
    company = prospect["company"]
    signal_type = signal["signal_type"]
    keyword = signal["keyword"]

    # Score signal relevance
    relevance_score = score_signal_relevance(signal, prospect)

    # Check insight cache first
    cached = get_cached_insight(company, signal_type, keyword, max_age_hours=6)

    if cached:
        print(f"[Generator] Cache hit — {company} ({relevance_score} score)")
        return {
            "company":        company,
            "signal_type":    signal_type,
            "keyword":        keyword,
            "headline":       signal["headline"],
            "pipeline_stage": stage,
            "primary_action": get_primary_action(stage),
            "urgency":        get_urgency(stage, relevance_score),
            "relevance_score": relevance_score,
            "email_draft":    cached["email_draft"],
            "talking_point":  cached["talking_point"],
            "insight":        cached["insight"],
            "cache_hit":      True,
            "fired_at":       datetime.now().strftime("%Y-%m-%d %H:%M"),
            "last_generated": cached["generated_at"],
        }

    # Generate fresh — single API call
    print(f"[Generator] Generating — {company} ({relevance_score} score)")
    outputs = generate_alert_single_call(prospect, signal)

    # Save to cache
    save_cached_insight(
        company, signal_type, keyword,
        outputs["email_draft"],
        outputs["talking_point"],
        outputs["insight"]
    )

    return {
        "company":         company,
        "signal_type":     signal_type,
        "keyword":         keyword,
        "headline":        signal["headline"],
        "pipeline_stage":  stage,
        "primary_action":  get_primary_action(stage),
        "urgency":         get_urgency(stage, relevance_score),
        "relevance_score": relevance_score,
        "email_draft":     outputs["email_draft"],
        "talking_point":   outputs["talking_point"],
        "insight":         outputs["insight"],
        "cache_hit":       False,
        "fired_at":        datetime.now().strftime("%Y-%m-%d %H:%M"),
        "last_generated":  datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def get_primary_action(stage):
    """Returns primary action based on pipeline stage."""
    if "active" in stage or "deal" in stage:
        return "TALKING POINT"
    elif stage == "warm":
        return "EMAIL"
    else:
        return "INSIGHT"


def get_urgency(stage, relevance_score):
    """Returns urgency based on stage and relevance score."""
    if "active" in stage or relevance_score >= 60:
        return "HIGH"
    elif stage == "warm" or relevance_score >= 40:
        return "MEDIUM"
    else:
        return "LOW"


if __name__ == "__main__":
    test_prospect = {
        "company":         "Tesla",
        "pipeline_stage":  "active deal",
        "key_materials":   "Rare Earth; Lithium; Copper; Aluminum",
        "sourcing_regions": "China; Australia; Chile; DRC"
    }
    test_signal = {
        "signal_type":  "commodity_shock",
        "keyword":      "rare earth",
        "headline":     "China tightens rare earth export controls",
        "sources_count": 4,
        "sources":      ["Reuters", "FT", "WSJ", "Mining.com"]
    }

    alert = generate_alert(test_prospect, test_signal)
    print(f"\nCompany: {alert['company']}")
    print(f"Score: {alert['relevance_score']}")
    print(f"Primary: {alert['primary_action']}")
    print(f"Urgency: {alert['urgency']}")
    print(f"Cache hit: {alert['cache_hit']}")
    print(f"\nEmail:\n{alert['email_draft']}")
    print(f"\nTalking Point:\n{alert['talking_point']}")
    print(f"\nInsight:\n{alert['insight']}")