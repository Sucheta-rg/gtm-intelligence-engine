"""
company_researcher.py — The Researcher (Layer 2)
Auto-profiles a company using Wikipedia API + Groq AI.
Extracts key materials, sourcing regions, manufacturing locations.
"""

import requests
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def get_wikipedia_summary(company_name):
    """Fetches company summary from Wikipedia API."""
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + company_name.replace(" ", "_")
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("extract", "")
        return ""
    except Exception as e:
        print(f"[Researcher] Wikipedia error for {company_name}: {e}")
        return ""


def extract_profile_with_ai(company_name, wikipedia_text):
    """Uses Groq AI to extract procurement-relevant info from company text."""
    if not wikipedia_text:
        wikipedia_text = f"{company_name} is a manufacturing company."

    prompt = f"""You are a procurement intelligence analyst.
Based on this company description, extract key supply chain information.

Company: {company_name}
Description: {wikipedia_text[:1000]}

Reply in this EXACT format — no extra text:
INDUSTRY: [one phrase]
KEY_MATERIALS: [comma separated list of raw materials they depend on]
SOURCING_REGIONS: [comma separated list of regions they source from]
MANUFACTURING: [comma separated list of countries where they manufacture]
URGENCY_SIGNAL: [one sentence about their biggest supply chain vulnerability]"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[Researcher] Groq AI error: {e}")
        return None


def parse_ai_response(raw_text):
    """Parses the AI response into a structured dict."""
    profile = {}
    if not raw_text:
        return profile
    for line in raw_text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            profile[key.strip()] = value.strip()
    return profile


def research_company(company_name):
    """
    Main function — researches a company and returns full profile.
    Step 1: Wikipedia API
    Step 2: Groq AI extraction
    Step 3: Return structured profile
    """
    print(f"[Researcher] Researching {company_name}...")

    wiki_text = get_wikipedia_summary(company_name)
    if wiki_text:
        print(f"[Researcher] Wikipedia data found — {len(wiki_text)} chars")
    else:
        print(f"[Researcher] No Wikipedia data — using AI knowledge only")

    raw_profile = extract_profile_with_ai(company_name, wiki_text)
    profile = parse_ai_response(raw_profile)

    profile["company"] = company_name
    profile["researched_at"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")

    return profile


if __name__ == "__main__":
    # Test with 3 of our demo companies
    test_companies = ["Dyson", "Tesla", "Honeywell"]

    for company in test_companies:
        print(f"\n{'='*50}")
        profile = research_company(company)
        for key, value in profile.items():
            print(f"  {key:<20}: {value}")