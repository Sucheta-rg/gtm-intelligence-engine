"""
streamlit_app.py — GTM Intelligence Engine
Enterprise-grade dashboard — Clean professional design
"""

import streamlit as st
import sys
import os
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
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

# ── ENTERPRISE CSS ────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

/* Global */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Main background */
.stApp {
    background-color: #F8F9FC;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0F1629;
    border-right: 1px solid #1E2D4A;
}

section[data-testid="stSidebar"] * {
    color: #CBD5E1 !important;
}

section[data-testid="stSidebar"] .stRadio label {
    color: #94A3B8 !important;
    font-size: 14px;
    padding: 8px 12px;
    border-radius: 8px;
    transition: all 0.2s;
}

/* Hero banner */
.hero-banner {
    background: linear-gradient(135deg, #0F1629 0%, #1E3A5F 50%, #1B4F8A 100%);
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 28px;
    border: 1px solid #2A4A7A;
    position: relative;
    overflow: hidden;
}

.hero-banner::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%);
    border-radius: 50%;
}

.hero-title {
    font-size: 28px;
    font-weight: 700;
    color: #FFFFFF;
    margin: 0 0 6px 0;
    letter-spacing: -0.5px;
}

.hero-subtitle {
    font-size: 15px;
    color: #94A3B8;
    margin: 0 0 20px 0;
}

.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(34, 197, 94, 0.15);
    border: 1px solid rgba(34, 197, 94, 0.3);
    color: #22C55E;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin-right: 8px;
}

.hero-badge-blue {
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.3);
    color: #60A5FA;
}

/* KPI Cards */
.kpi-card {
    background: white;
    border-radius: 12px;
    padding: 24px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
}

.kpi-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.kpi-label {
    font-size: 12px;
    font-weight: 600;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 8px;
}

.kpi-value {
    font-size: 36px;
    font-weight: 700;
    color: #0F1629;
    line-height: 1;
    margin-bottom: 4px;
}

.kpi-change {
    font-size: 12px;
    color: #22C55E;
    font-weight: 500;
}

.kpi-change-neutral {
    color: #64748B;
}

/* Signal cards */
.signal-card {
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid #E2E8F0;
    border-left: 4px solid #3B82F6;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.signal-card-high {
    border-left-color: #EF4444;
}

.signal-card-medium {
    border-left-color: #F59E0B;
}

.signal-type {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #3B82F6;
    margin-bottom: 4px;
}

.signal-headline {
    font-size: 15px;
    font-weight: 600;
    color: #0F1629;
    margin-bottom: 8px;
    line-height: 1.4;
}

.signal-meta {
    font-size: 12px;
    color: #64748B;
    font-family: 'DM Mono', monospace;
}

/* Prospect cards */
.prospect-card {
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid #E2E8F0;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.prospect-name {
    font-size: 16px;
    font-weight: 700;
    color: #0F1629;
    margin-bottom: 4px;
}

.tag {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    margin-right: 6px;
    margin-bottom: 8px;
}

.tag-red {
    background: #FEE2E2;
    color: #DC2626;
}

.tag-amber {
    background: #FEF3C7;
    color: #D97706;
}

.tag-blue {
    background: #DBEAFE;
    color: #1D4ED8;
}

.tag-green {
    background: #DCFCE7;
    color: #16A34A;
}

.tag-grey {
    background: #F1F5F9;
    color: #475569;
}

/* Section headers */
.section-header {
    font-size: 20px;
    font-weight: 700;
    color: #0F1629;
    margin: 24px 0 16px 0;
    display: flex;
    align-items: center;
    gap: 10px;
}

.section-divider {
    height: 1px;
    background: #E2E8F0;
    margin: 24px 0;
}

/* Alert history cards */
.alert-history-card {
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid #E2E8F0;
    margin-bottom: 12px;
}

.alert-company {
    font-size: 16px;
    font-weight: 700;
    color: #0F1629;
}

.alert-date {
    font-size: 12px;
    color: #94A3B8;
    font-family: 'DM Mono', monospace;
}

/* Profile cards */
.profile-card {
    background: white;
    border-radius: 12px;
    padding: 24px;
    border: 1px solid #E2E8F0;
    height: 100%;
}

.profile-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #94A3B8;
    margin-bottom: 8px;
}

.profile-value {
    font-size: 14px;
    color: #0F1629;
    line-height: 1.6;
}

.exposure-alert {
    background: #FEF2F2;
    border: 1px solid #FECACA;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
}

.exposure-safe {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: 12px;
    padding: 20px 24px;
}

/* Sidebar navigation */
.nav-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: #475569 !important;
    margin: 20px 0 8px 0;
}

.status-dot {
    width: 8px;
    height: 8px;
    background: #22C55E;
    border-radius: 50%;
    display: inline-block;
    margin-right: 6px;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
</style>
""", unsafe_allow_html=True)

# ── SETUP ─────────────────────────────────────────────────────
setup_database()

# ── CACHED FUNCTIONS ──────────────────────────────────────────
@st.cache_data(ttl=1800)
def get_signals_cached():
    return collect_signals()

@st.cache_data(ttl=3600)
def get_prospects_cached():
    HUBSPOT_KEY = os.environ.get("HUBSPOT_API_KEY")
    if not HUBSPOT_KEY:
        return []
    try:
        url = "https://api.hubapi.com/crm/v3/objects/companies"
        headers = {"Authorization": f"Bearer {HUBSPOT_KEY}"}
        params = {"properties": "name,key_materials,sourcing_regions,hs_lead_status", "limit": 100}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        prospects = []
        if response.status_code == 200:
            for company in response.json().get("results", []):
                props = company.get("properties", {})
                name = props.get("name", "").strip()
                if name:
                    prospects.append({
                        "company": name,
                        "key_materials": props.get("key_materials", ""),
                        "sourcing_regions": props.get("sourcing_regions", ""),
                        "pipeline_stage": props.get("hs_lead_status", "cold") or "cold"
                    })
        return prospects
    except:
        return []

@st.cache_data(ttl=300)
def get_alerts_cached():
    return get_past_alerts(days=90)

@st.cache_data(ttl=3600)
def profile_company_cached(company_name):
    return research_company(company_name)

SIGNAL_MATERIAL_MAP = {
    "commodity_shock": ["copper","steel","aluminum","tin","resin","plastic","lithium","rare earth","cobalt","nickel"],
    "geopolitical":    ["semiconductor","rare earth","lithium","copper","electronics","chip"],
    "supply_chain":    ["plastic","resin","copper","semiconductor","component","steel"],
    "regulatory":      ["steel","aluminum","copper","semiconductor","electronics"]
}

# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 20px 0 10px 0;">
        <div style="font-size: 18px; font-weight: 700; color: #FFFFFF; letter-spacing: -0.3px;">
            GTM Intelligence
        </div>
        <div style="font-size: 12px; color: #64748B; margin-top: 2px;">
            Revenue Engine v1.0
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    page = st.radio("Select Page", [
        "📡 Signal Feed",
        "🎯 Risk Map",
        "📋 Alert History",
        "🔍 Company Profiler"
    ], label_visibility="collapsed")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="padding: 12px 0;">
        <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; 
             letter-spacing: 1px; color: #475569; margin-bottom: 12px;">
            ENGINE STATUS
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 8px;">
            <span class="status-dot"></span>
            <span style="font-size: 13px; color: #22C55E; font-weight: 600;">
                Active — Running
            </span>
        </div>
        <div style="font-size: 12px; color: #475569; margin-bottom: 4px;">
            Schedule: Every 6 hours
        </div>
        <div style="font-size: 11px; color: #334155; font-family: monospace;">
            Last: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="padding: 8px 0;">
        <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; 
             letter-spacing: 1px; color: #475569; margin-bottom: 12px;">
            DATA SOURCES
        </div>
        <div style="font-size: 12px; color: #64748B; line-height: 2;">
            ● Reuters Business<br>
            ● Financial Times<br>
            ● Wall Street Journal<br>
            ● Supply Chain Dive<br>
            ● Spend Matters<br>
            ● Mining.com
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── HERO BANNER ───────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">🚨 GTM Intelligence Engine</div>
    <div class="hero-subtitle">
        Proactive revenue intelligence for B2B sales teams — 
        alerting reps before prospects know they have a problem.
    </div>
    <span class="hero-badge">● Live</span>
    <span class="hero-badge hero-badge-blue">3 Signals Active</span>
    <span class="hero-badge hero-badge-blue">10 Prospects Monitored</span>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE 1 — SIGNAL FEED
# ════════════════════════════════════════════════════════════
if page == "📡 Signal Feed":

    with st.spinner("Loading signals..."):
        signals = get_signals_cached()

    # KPI Row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Signals Validated</div>
            <div class="kpi-value">{len(signals)}</div>
            <div class="kpi-change">● Active now</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Sources Monitored</div>
            <div class="kpi-value">6</div>
            <div class="kpi-change kpi-change-neutral">Tier 1 + Tier 2</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Corroboration Rule</div>
            <div class="kpi-value">3+</div>
            <div class="kpi-change kpi-change-neutral">Sources required</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        high_signals = sum(1 for s in signals if s.get("sources_count", 0) >= 4)
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">High Priority</div>
            <div class="kpi-value" style="color: #EF4444;">{high_signals}</div>
            <div class="kpi-change kpi-change-neutral">4+ sources confirmed</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    if signals:
        st.markdown('<div class="section-header">✅ Validated Signals</div>',
                    unsafe_allow_html=True)

        for signal in signals:
            count = signal.get("sources_count", 0)
            card_class = "signal-card-high" if count >= 4 else \
                        "signal-card-medium" if count == 3 else "signal-card"
            color = "#EF4444" if count >= 4 else \
                   "#F59E0B" if count == 3 else "#3B82F6"
            dot = "🔴" if count >= 4 else "🟡"

            st.markdown(f"""
<div class="signal-card {card_class}">
    <div class="signal-type" style="color: {color};">
        {dot} {signal['signal_type'].replace('_',' ').upper()}
    </div>
    <div class="signal-headline">{signal['headline']}</div>
    <div class="signal-meta">
        Keyword: <strong>{signal['keyword']}</strong> &nbsp;|&nbsp;
        Sources: <strong>{signal['sources_count']} confirmed</strong> — 
        {', '.join(signal['sources'])} &nbsp;|&nbsp;
        Detected: {signal['detected_at']}
    </div>
</div>
""", unsafe_allow_html=True)

        # Signal type distribution chart
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-header">📊 Signal Distribution</div>',
                    unsafe_allow_html=True)

        signal_types = [s["signal_type"].replace("_", " ").title() for s in signals]
        signal_counts = {t: signal_types.count(t) for t in set(signal_types)}

        fig = go.Figure(go.Bar(
            x=list(signal_counts.keys()),
            y=list(signal_counts.values()),
            marker_color=["#1D4ED8", "#DC2626", "#D97706"][:len(signal_counts)],
            text=list(signal_counts.values()),
            textposition='outside'
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_family="DM Sans",
            height=250,
            margin=dict(t=20, b=20, l=20, r=20),
            showlegend=False,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#F1F5F9')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No validated signals at this time.")

# ════════════════════════════════════════════════════════════
# PAGE 2 — RISK MAP
# ════════════════════════════════════════════════════════════
elif page == "🎯 Risk Map":

    with st.spinner("Loading data..."):
        signals = get_signals_cached()
        prospects = get_prospects_cached()

    # Match prospects
    at_risk = []
    seen = set()
    for signal in signals:
        kws = SIGNAL_MATERIAL_MAP.get(signal["signal_type"], [])
        for prospect in prospects:
            materials = prospect.get("key_materials", "").lower()
            for kw in kws:
                if kw in materials and prospect["company"] not in seen:
                    seen.add(prospect["company"])
                    at_risk.append({**prospect, "signal": signal, "keyword": kw})
                    break

    # KPI Row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Prospects Monitored</div>
            <div class="kpi-value">{len(prospects)}</div>
            <div class="kpi-change kpi-change-neutral">From HubSpot CRM</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Active Signals</div>
            <div class="kpi-value" style="color: #1D4ED8;">{len(signals)}</div>
            <div class="kpi-change">3+ sources confirmed</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Prospects At Risk</div>
            <div class="kpi-value" style="color: #EF4444;">{len(at_risk)}</div>
            <div class="kpi-change" style="color: #EF4444;">● Requires action</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        pct = int((len(at_risk) / len(prospects) * 100)) if prospects else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Exposure Rate</div>
            <div class="kpi-value" style="color: #D97706;">{pct}%</div>
            <div class="kpi-change kpi-change-neutral">Of pipeline affected</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    if at_risk:
        # Risk table
        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.markdown('<div class="section-header">⚠️ Affected Prospects</div>',
                        unsafe_allow_html=True)

            for item in at_risk:
                signal = item["signal"]
                stage = item.get("pipeline_stage", "cold").lower()
                stage_tag = "tag-red" if "active" in stage else \
                           "tag-amber" if stage == "warm" else "tag-grey"
                signal_tag = "tag-red" if "commodity" in signal["signal_type"] \
                            else "tag-blue"

                st.markdown(f"""
<div class="prospect-card">
    <div class="prospect-name">🏭 {item['company']}</div>
    <span class="tag {stage_tag}">{stage.title()}</span>
    <span class="tag {signal_tag}">
        {signal['signal_type'].replace('_',' ').title()}
    </span>
    <span class="tag tag-grey">⚡ {item['keyword']}</span>
    <div style="font-size: 13px; color: #475569; margin-top: 8px; line-height: 1.5;">
        <strong>Materials:</strong> {item['key_materials'][:80]}...<br>
        <strong>Sourcing:</strong> {item['sourcing_regions'][:60]}
    </div>
</div>
""", unsafe_allow_html=True)

        with col_right:
            st.markdown('<div class="section-header">📊 Risk Breakdown</div>',
                        unsafe_allow_html=True)

            # Signal type breakdown
            signal_types = [a["signal"]["signal_type"].replace(
                "_"," ").title() for a in at_risk]
            counts = {t: signal_types.count(t) for t in set(signal_types)}

            fig = go.Figure(go.Pie(
                labels=list(counts.keys()),
                values=list(counts.values()),
                hole=0.6,
                marker_colors=["#1D4ED8", "#DC2626", "#D97706", "#16A34A"],
            ))
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                font_family="DM Sans",
                height=280,
                margin=dict(t=10, b=10, l=10, r=10),
                showlegend=True,
                legend=dict(orientation="v", font_size=11)
            )
            fig.update_traces(textinfo='percent', textfont_size=12)
            st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════
# PAGE 3 — ALERT HISTORY
# ════════════════════════════════════════════════════════════
elif page == "📋 Alert History":

    with st.spinner("Loading alert history..."):
        past_alerts = get_alerts_cached()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Alerts Fired</div>
            <div class="kpi-value">{len(past_alerts)}</div>
            <div class="kpi-change kpi-change-neutral">Last 90 days</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        companies = len(set(a.get("company", "") for a in past_alerts))
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Companies Alerted</div>
            <div class="kpi-value">{companies}</div>
            <div class="kpi-change kpi-change-neutral">Unique prospects</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        signal_types = len(set(a.get("signal_type", "") for a in past_alerts))
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Signal Types</div>
            <div class="kpi-value">{signal_types}</div>
            <div class="kpi-change kpi-change-neutral">Categories detected</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    if past_alerts:
        # Alert timeline chart
        st.markdown('<div class="section-header">📈 Alert Timeline</div>',
                    unsafe_allow_html=True)

        df = pd.DataFrame(past_alerts)
        if "alert_date" in df.columns:
            date_counts = df.groupby("alert_date").size().reset_index(name="count")
            fig = go.Figure(go.Scatter(
                x=date_counts["alert_date"],
                y=date_counts["count"],
                mode='lines+markers',
                line=dict(color='#1D4ED8', width=2),
                marker=dict(size=6, color='#1D4ED8'),
                fill='tozeroy',
                fillcolor='rgba(29,78,216,0.08)'
            ))
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_family="DM Sans",
                height=200,
                margin=dict(t=10, b=10, l=10, r=10),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#F1F5F9',
                          title="Alerts fired")
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # Filter
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            companies_list = ["All"] + sorted(set(
                a.get("company", "") for a in past_alerts))
            selected_company = st.selectbox("Filter by company", companies_list)
        with col_f2:
            signal_list = ["All"] + sorted(set(
                a.get("signal_type", "").replace("_"," ").title()
                for a in past_alerts))
            selected_signal = st.selectbox("Filter by signal", signal_list)

        filtered = past_alerts
        if selected_company != "All":
            filtered = [a for a in filtered if a.get("company") == selected_company]
        if selected_signal != "All":
            filtered = [a for a in filtered if
                       a.get("signal_type","").replace("_"," ").title() == selected_signal]

        st.markdown(f"**Showing {len(filtered)} alert(s)**")

        for alert in filtered[:15]:
            stage = alert.get("pipeline_stage", "cold")
            stage_tag = "tag-red" if "active" in stage else \
                       "tag-amber" if stage == "warm" else "tag-grey"

            with st.expander(
                f"🚨 {alert.get('company','—')} — "
                f"{str(alert.get('signal_type','')).replace('_',' ').title()} — "
                f"{alert.get('fired_at','')}"
            ):
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    st.markdown(f"**Signal:** {alert.get('signal_type','')}")
                    st.markdown(f"**Keyword:** {alert.get('keyword','')}")
                    st.markdown(f"**Stage:** {stage}")
                with col_b:
                    st.markdown(f"**Date:** {alert.get('fired_at','')}")

                st.markdown("---")
                st.markdown("**📧 Email Draft**")
                st.info(alert.get('email_draft',''))
                st.markdown("**📞 Talking Point**")
                st.warning(alert.get('talking_point',''))
                st.markdown("**💡 Insight**")
                st.success(alert.get('insight',''))
    else:
        st.info("No alerts in the last 90 days. Run the engine first.")

# ════════════════════════════════════════════════════════════
# PAGE 4 — COMPANY PROFILER
# ════════════════════════════════════════════════════════════
elif page == "🔍 Company Profiler":

    st.markdown("""
    <div style="background: white; border-radius: 12px; padding: 24px; 
         border: 1px solid #E2E8F0; margin-bottom: 24px;">
        <div style="font-size: 18px; font-weight: 700; color: #0F1629; margin-bottom: 6px;">
            🔍 Company Intelligence Profiler
        </div>
        <div style="font-size: 14px; color: #64748B;">
            Type any manufacturer name. The engine researches their 
            supply chain profile and checks their exposure to live signals.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_input, col_btn = st.columns([4, 1])
    with col_input:
        company_input = st.text_input(
            "Company name",
            placeholder="e.g. Bosch, Caterpillar, Samsung, ABB...",
            label_visibility="collapsed"
        )
    with col_btn:
        search = st.button("🔍 Profile", use_container_width=True)

    if search and company_input:
        with st.spinner(f"Researching {company_input}..."):
            profile = profile_company_cached(company_input)
            signals = get_signals_cached()

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="section-header">📊 {company_input} — Intelligence Profile</div>',
                    unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"""
<div class="profile-card">
    <div class="profile-label">Industry</div>
    <div class="profile-value">{profile.get('INDUSTRY','Not found')}</div>
</div>
""", unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
<div class="profile-card">
    <div class="profile-label">Manufacturing Locations</div>
    <div class="profile-value">{profile.get('MANUFACTURING','Not found')}</div>
</div>
""", unsafe_allow_html=True)

        col3, col4 = st.columns(2)

        with col3:
            st.markdown(f"""
<div class="profile-card" style="margin-top: 12px;">
    <div class="profile-label">Key Materials</div>
    <div class="profile-value">{profile.get('KEY_MATERIALS','Not found')}</div>
</div>
""", unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
<div class="profile-card" style="margin-top: 12px;">
    <div class="profile-label">Sourcing Regions</div>
    <div class="profile-value">{profile.get('SOURCING_REGIONS','Not found')}</div>
</div>
""", unsafe_allow_html=True)

        st.markdown(f"""
<div style="background: #FEF9C3; border: 1px solid #FDE047; border-radius: 12px; 
     padding: 20px 24px; margin-top: 12px;">
    <div class="profile-label" style="color: #854D0E;">⚠️ Supply Chain Vulnerability</div>
    <div class="profile-value" style="color: #713F12;">
        {profile.get('URGENCY_SIGNAL','Not found')}
    </div>
</div>
""", unsafe_allow_html=True)

        # Signal exposure check
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-header">⚡ Live Signal Exposure</div>',
                    unsafe_allow_html=True)

        materials = profile.get("KEY_MATERIALS", "").lower()
        exposures = []

        for signal in signals:
            kws = SIGNAL_MATERIAL_MAP.get(signal["signal_type"], [])
            for kw in kws:
                if kw in materials:
                    exposures.append({"signal": signal, "keyword": kw})
                    break

        if exposures:
            st.markdown(f"""
<div class="exposure-alert">
    <div style="font-size: 15px; font-weight: 700; color: #DC2626; margin-bottom: 12px;">
        ⚠️ {company_input} is exposed to {len(exposures)} live signal(s)
    </div>
""", unsafe_allow_html=True)

            for exp in exposures:
                s = exp["signal"]
                st.markdown(f"""
    <div style="margin-bottom: 12px; padding: 12px; background: white; 
         border-radius: 8px; border: 1px solid #FECACA;">
        <span class="tag tag-red">{s['signal_type'].replace('_',' ').title()}</span>
        <span class="tag tag-grey">⚡ {exp['keyword']}</span>
        <div style="font-size: 13px; color: #374151; margin-top: 8px;">
            {s['headline']}
        </div>
        <div style="font-size: 11px; color: #9CA3AF; margin-top: 4px; 
             font-family: monospace;">
            {s['sources_count']} sources confirmed
        </div>
    </div>
""", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"""
<div class="exposure-safe">
    <div style="font-size: 15px; font-weight: 700; color: #16A34A;">
        ✅ {company_input} has no direct exposure to current signals
    </div>
</div>
""", unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
st.markdown("""
<div style="text-align: center; padding: 12px 0;">
    <span style="font-size: 13px; color: #94A3B8; font-weight: 500;">
        GTM Intelligence Engine
    </span>
    <span style="font-size: 13px; color: #CBD5E1; margin: 0 8px;">·</span>
    <span style="font-size: 13px; color: #94A3B8;">
        Proactive revenue intelligence for B2B sales teams.
    </span>
</div>
""", unsafe_allow_html=True)