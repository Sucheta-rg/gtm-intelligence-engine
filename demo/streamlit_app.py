"""
streamlit_app.py — GTM Intelligence Engine Demo
Live dashboard for LinkedIn portfolio demonstration.

Pages:
1. Live Signals — current validated signals
2. Prospect Risk Map — who is affected right now
3. Alert History — last 90 days
4. Company Profiler — type any company, engine profiles it live
"""

import streamlit as st
import sys
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.signal_collector import run as collect_signals
from engine.company_researcher import research_company
from engine.brain import setup_database, get_past_alerts

# ── PAGE CONFIG ───────────────────────────────────────────────
st.set_page_config(
    page_title="GTM Intelligence Engine",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── STYLING ───────────────────────────────────────────────────
st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #1F3864, #2E5090);
    padding: 2rem;
    border-radius: 12px;
    color: white;
    margin-bottom: 2rem;
}
.signal-card {
    background: #EEF2FF;
    border-left: 4px solid #2E5090;
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
}
.alert-card {
    background: #FFF7ED;
    border-left: 4px solid #EA580C;
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
}
.metric-card {
    background: white;
    border: 1px solid #E5E7EB;
    padding: 1rem;
    border-radius: 8px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🚨 GTM Intelligence Engine</h1>
    <p>Proactive revenue intelligence for B2B sales teams.<br>
    Monitors external signals and alerts reps before prospects 
    know they have a problem.</p>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────
st.sidebar.title("Navigation")
page = st.sidebar.radio("Select Page", [
    "📡 Live Signals",
    "🎯 Prospect Risk Map",
    "📋 Alert History",
    "🔍 Company Profiler"
])

st.sidebar.markdown("---")
st.sidebar.markdown("**Engine Status**")
st.sidebar.success("✓ Engine Active")
st.sidebar.info(f"Last run: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
st.sidebar.markdown("**Data Sources**")
st.sidebar.markdown("- Reuters Business")
st.sidebar.markdown("- Financial Times")
st.sidebar.markdown("- Wall Street Journal")
st.sidebar.markdown("- Supply Chain Dive")
st.sidebar.markdown("- Spend Matters")
st.sidebar.markdown("- Mining.com")

# ── SETUP DATABASE ────────────────────────────────────────────
setup_database()

# ════════════════════════════════════════════════════════════
# PAGE 1 — LIVE SIGNALS
# ════════════════════════════════════════════════════════════
if page == "📡 Live Signals":
    st.header("📡 Live Signal Feed")
    st.markdown("Real-time signals validated by 3+ credible sources.")

    col1, col2, col3 = st.columns(3)

    with st.spinner("Scanning credible sources..."):
        signals = collect_signals()

    col1.metric("Signals Validated", len(signals))
    col2.metric("Sources Monitored", "6")
    col3.metric("Corroboration Rule", "3+ Sources")

    if signals:
        st.markdown("---")
        st.subheader(f"✅ {len(signals)} Validated Signal(s)")

        for signal in signals:
            with st.container():
                st.markdown(f"""
<div class="signal-card">
    <strong>🔴 {signal['signal_type'].replace('_',' ').title()}</strong><br>
    <strong>Keyword:</strong> {signal['keyword']}<br>
    <strong>Headline:</strong> {signal['headline']}<br>
    <strong>Sources:</strong> {signal['sources_count']} confirmed — 
    {', '.join(signal['sources'])}<br>
    <strong>Detected:</strong> {signal['detected_at']}
</div>
""", unsafe_allow_html=True)
    else:
        st.info("No new validated signals at this time. Check back later.")

# ════════════════════════════════════════════════════════════
# PAGE 2 — PROSPECT RISK MAP
# ════════════════════════════════════════════════════════════
elif page == "🎯 Prospect Risk Map":
    st.header("🎯 Prospect Risk Map")
    st.markdown("Which prospects in your pipeline are affected by today's signals.")

    HUBSPOT_KEY = os.environ.get("HUBSPOT_API_KEY")

    SIGNAL_MATERIAL_MAP = {
        "commodity_shock": ["copper", "steel", "aluminum", "tin", "resin",
                           "plastic", "lithium", "rare earth", "cobalt", "nickel"],
        "geopolitical":    ["semiconductor", "rare earth", "lithium", "copper",
                           "electronics", "chip"],
        "supply_chain":    ["plastic", "resin", "copper", "semiconductor",
                           "component", "steel"],
        "regulatory":      ["steel", "aluminum", "copper", "semiconductor",
                           "electronics"]
    }

    with st.spinner("Loading prospects from HubSpot..."):
        try:
            url = "https://api.hubapi.com/crm/v3/objects/companies"
            headers = {"Authorization": f"Bearer {HUBSPOT_KEY}"}
            params = {
                "properties": "name,key_materials,sourcing_regions,hs_lead_status",
                "limit": 100
            }
            response = requests.get(url, headers=headers, params=params)
            prospects = []
            if response.status_code == 200:
                for company in response.json().get("results", []):
                    props = company.get("properties", {})
                    name = props.get("name", "").strip()
                    if name:
                        prospects.append({
                            "company":         name,
                            "key_materials":   props.get("key_materials", ""),
                            "sourcing_regions": props.get("sourcing_regions", ""),
                            "pipeline_stage":  props.get("hs_lead_status", "cold") or "cold"
                        })
        except Exception as e:
            st.error(f"Could not connect to HubSpot: {e}")
            prospects = []

    with st.spinner("Scanning signals..."):
        signals = collect_signals()

    col1, col2, col3 = st.columns(3)
    col1.metric("Prospects Monitored", len(prospects))
    col2.metric("Active Signals", len(signals))

    # Match prospects to signals
    at_risk = []
    for signal in signals:
        kws = SIGNAL_MATERIAL_MAP.get(signal["signal_type"], [])
        for prospect in prospects:
            materials = prospect.get("key_materials", "").lower()
            for kw in kws:
                if kw in materials:
                    at_risk.append({**prospect, "signal": signal, "keyword": kw})
                    break

    col3.metric("Prospects At Risk", len(set(a["company"] for a in at_risk)))

    if at_risk:
        st.markdown("---")
        st.subheader("⚠️ Prospects Affected Right Now")

        seen = set()
        for item in at_risk:
            company = item["company"]
            if company not in seen:
                seen.add(company)
                signal = item["signal"]
                st.markdown(f"""
<div class="alert-card">
    <strong>🏭 {company}</strong><br>
    <strong>Signal:</strong> {signal['signal_type'].replace('_',' ').title()}<br>
    <strong>Matched keyword:</strong> {item['keyword']}<br>
    <strong>Their materials:</strong> {item['key_materials']}<br>
    <strong>Sourcing from:</strong> {item['sourcing_regions']}<br>
    <strong>Pipeline stage:</strong> {item['pipeline_stage']}
</div>
""", unsafe_allow_html=True)
    else:
        st.info("No prospects matched today's signals.")

# ════════════════════════════════════════════════════════════
# PAGE 3 — ALERT HISTORY
# ════════════════════════════════════════════════════════════
elif page == "📋 Alert History":
    st.header("📋 Alert History — Last 90 Days")
    st.markdown("Every alert ever fired by the engine.")

    past_alerts = get_past_alerts(days=90)

    col1, col2 = st.columns(2)
    col1.metric("Total Alerts Fired", len(past_alerts))
    col2.metric("Period", "Last 90 Days")

    if past_alerts:
        st.markdown("---")

        # Filter by company
        companies = list(set(a.get("company", "") for a in past_alerts))
        companies = ["All"] + sorted(companies)
        selected = st.selectbox("Filter by company", companies)

        filtered = past_alerts if selected == "All" else [
            a for a in past_alerts if a.get("company") == selected
        ]

        st.markdown(f"Showing {len(filtered)} alert(s)")

        for alert in filtered[:20]:
            with st.expander(
                f"🚨 {alert.get('company')} — "
                f"{str(alert.get('signal_type','')).replace('_',' ').title()} — "
                f"{alert.get('fired_at', '')}"
            ):
                st.markdown(f"**Signal:** {alert.get('signal_type', '')}")
                st.markdown(f"**Keyword:** {alert.get('keyword', '')}")
                st.markdown(f"**Pipeline Stage:** {alert.get('pipeline_stage', '')}")
                st.markdown(f"**Date:** {alert.get('fired_at', '')}")
                st.markdown("---")
                st.markdown("**📧 Email Draft:**")
                st.info(alert.get('email_draft', ''))
                st.markdown("**📞 Talking Point:**")
                st.warning(alert.get('talking_point', ''))
                st.markdown("**💡 Insight:**")
                st.success(alert.get('insight', ''))
    else:
        st.info("No alerts in the last 90 days. Run the engine first.")

# ════════════════════════════════════════════════════════════
# PAGE 4 — COMPANY PROFILER
# ════════════════════════════════════════════════════════════
elif page == "🔍 Company Profiler":
    st.header("🔍 Company Profiler")
    st.markdown(
        "Type any manufacturer name. "
        "The engine will research and profile them instantly."
    )

    company_input = st.text_input(
        "Enter company name",
        placeholder="e.g. Bosch, Caterpillar, Samsung..."
    )

    if st.button("🔍 Profile This Company") and company_input:
        with st.spinner(f"Researching {company_input}..."):
            profile = research_company(company_input)

        st.markdown("---")
        st.subheader(f"📊 Intelligence Profile — {company_input}")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Industry**")
            st.info(profile.get("INDUSTRY", "Not found"))
            st.markdown("**Key Materials**")
            st.info(profile.get("KEY_MATERIALS", "Not found"))
            st.markdown("**Sourcing Regions**")
            st.info(profile.get("SOURCING_REGIONS", "Not found"))

        with col2:
            st.markdown("**Manufacturing Locations**")
            st.info(profile.get("MANUFACTURING", "Not found"))
            st.markdown("**Supply Chain Vulnerability**")
            st.warning(profile.get("URGENCY_SIGNAL", "Not found"))

        # Check if any current signals affect this company
        st.markdown("---")
        st.subheader("⚡ Signal Exposure Check")

        SIGNAL_MATERIAL_MAP = {
            "commodity_shock": ["copper", "steel", "aluminum", "resin",
                               "plastic", "lithium", "rare earth"],
            "geopolitical":    ["semiconductor", "rare earth", "lithium",
                               "copper", "electronics"],
            "supply_chain":    ["plastic", "resin", "copper", "semiconductor"],
            "regulatory":      ["steel", "aluminum", "copper", "semiconductor"]
        }

        with st.spinner("Checking against live signals..."):
            signals = collect_signals()

        materials = profile.get("KEY_MATERIALS", "").lower()
        exposures = []

        for signal in signals:
            kws = SIGNAL_MATERIAL_MAP.get(signal["signal_type"], [])
            for kw in kws:
                if kw in materials:
                    exposures.append({
                        "signal": signal,
                        "keyword": kw
                    })
                    break

        if exposures:
            st.error(f"⚠️ {company_input} is exposed to "
                     f"{len(exposures)} live signal(s)")
            for exp in exposures:
                st.markdown(f"""
**Signal:** {exp['signal']['signal_type'].replace('_',' ').title()}
**Matched:** {exp['keyword']}
**Headline:** {exp['signal']['headline']}
**Sources:** {exp['signal']['sources_count']} confirmed
""")
        else:
            st.success(f"✅ {company_input} has no direct exposure "
                       f"to current signals")

# ── FOOTER ────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<center><strong>GTM Intelligence Engine</strong><br>"
    "Proactive revenue intelligence for B2B sales teams.</center>",
    unsafe_allow_html=True
)