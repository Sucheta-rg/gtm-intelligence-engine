"""
signal_collector.py — The Listener (Layer 1)
Scans news signals for trigger keywords.
Applies 3-source corroboration rule before validating.

NOTE: Uses mock feed for prototype demo.
In production: replace MOCK_HEADLINES with live RSS feed scanner.
"""

from datetime import datetime
from collections import defaultdict

# ── MOCK NEWS FEED ────────────────────────────────────────────
# Simulates real headlines from credible sources — May 2026
# In production: replace with feedparser.parse(rss_url)

MOCK_HEADLINES = [
    # Signal 1 — Middle East Energy Shock
    {"source": "Reuters Business",   "title": "Oil prices surge 50% as Strait of Hormuz disruptions worsen"},
    {"source": "Financial Times",    "title": "Energy price shock hits manufacturers as oil tops record high"},
    {"source": "Wall Street Journal","title": "Middle East conflict drives largest oil supply shock on record"},
    {"source": "Supply Chain Dive",  "title": "Resin and plastics costs spike as oil price surge hits supply chains"},

    # Signal 2 — Copper and Metals Spike
    {"source": "Reuters Business",   "title": "Copper hits all-time high driven by EV and data center demand"},
    {"source": "Financial Times",    "title": "Metal prices rise 17% in 2026 — copper aluminum tin reach records"},
    {"source": "Mining.com",         "title": "Copper price surge creating BOM cost pressure for electronics makers"},
    {"source": "Wall Street Journal","title": "Base metals at record highs as industrial demand outpaces supply"},

    # Signal 3 — US-China Tariffs
    {"source": "Reuters Business",   "title": "US launches Section 301 investigations against Taiwan South Korea"},
    {"source": "Wall Street Journal","title": "New US-China tariffs force abrupt supply chain shifts for tech sector"},
    {"source": "Financial Times",    "title": "Semiconductor tariff escalation threatens Asia-Pacific supply chains"},
    {"source": "Supply Chain Dive",  "title": "Contract manufacturers scramble as US-China trade tensions escalate"},

    # Signal 4 — Rare Earth Restrictions
    {"source": "Reuters Business",   "title": "China tightens rare earth export controls citing national security"},
    {"source": "Financial Times",    "title": "Rare earth restrictions threaten EV motor magnet supply globally"},
    {"source": "Mining.com",         "title": "China rare earth export curbs hit 85% of global refining capacity"},
    {"source": "Wall Street Journal","title": "EV manufacturers face supply risk as China restricts critical minerals"},

    # Non-trigger headlines — should NOT fire alerts
    {"source": "Reuters Business",   "title": "Federal Reserve holds interest rates steady at May meeting"},
    {"source": "Financial Times",    "title": "Tech earnings beat expectations for Q2 2026"},
]

# ── SIGNAL KEYWORDS ───────────────────────────────────────────
SIGNAL_KEYWORDS = {
    "commodity_shock": [
        "copper", "steel tariff", "aluminum price", "metal prices",
        "raw material shortage", "lithium", "rare earth", "resin",
        "oil price", "commodity", "base metals"
    ],
    "geopolitical": [
        "trade war", "sanctions", "taiwan", "iran",
        "export restriction", "trade tension", "geopolitical",
        "strait of hormuz", "red sea", "china tariff",
        "section 301", "national security"
    ],
    "supply_chain": [
        "supply chain", "port strike", "shipping delay",
        "container shortage", "factory closure", "logistics",
        "supply shortage", "chip shortage", "semiconductor shortage",
        "contract manufacturer"
    ],
    "regulatory": [
        "import tariff", "export ban", "trade policy",
        "section 301", "trade regulation", "customs duty",
        "investigation", "compliance"
    ]
}

CORROBORATION_THRESHOLD = 3


def scan_feeds():
    """Returns mock headlines simulating live RSS feed."""
    print(f"[Listener] {len(MOCK_HEADLINES)} headlines loaded from mock feed")
    return MOCK_HEADLINES


def match_keywords(headlines):
    """Checks headlines against signal keywords."""
    matches = []
    for item in headlines:
        text = item["title"].lower()
        for signal_type, keywords in SIGNAL_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text:
                    matches.append({
                        "signal_type": signal_type,
                        "keyword":     kw,
                        "headline":    item["title"],
                        "source":      item["source"],
                        "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    break
    return matches


def apply_corroboration(matches):
    """Only validates signals confirmed by 3+ sources."""
    grouped = defaultdict(list)
    for match in matches:
        key = (match["signal_type"], match["keyword"])
        grouped[key].append(match)

    validated = []
    watching  = []

    for (signal_type, keyword), sources in grouped.items():
        unique = list({s["source"]: s for s in sources}.values())
        count  = len(unique)
        signal = {
            "signal_type":  signal_type,
            "keyword":      keyword,
            "sources_count": count,
            "sources":      [s["source"] for s in unique],
            "headline":     unique[0]["headline"],
            "detected_at":  unique[0]["detected_at"],
            "validated":    count >= CORROBORATION_THRESHOLD
        }
        if count >= CORROBORATION_THRESHOLD:
            validated.append(signal)
        else:
            watching.append(signal)

    return validated, watching


def run():
    """Main pipeline — returns validated signals."""
    print("[Listener] Starting signal scan...")
    headlines = scan_feeds()
    matches   = match_keywords(headlines)
    print(f"[Listener] {len(matches)} keyword matches found")

    validated, watching = apply_corroboration(matches)
    print(f"[Listener] {len(validated)} signals VALIDATED (3+ sources)")
    print(f"[Listener] {len(watching)} signals WATCHING (below threshold)")

    return validated


if __name__ == "__main__":
    signals = run()
    if signals:
        print(f"\n--- VALIDATED SIGNALS ---")
        for s in signals:
            print(f"\n  TYPE    : {s['signal_type']}")
            print(f"  KEYWORD : {s['keyword']}")
            print(f"  SOURCES : {s['sources_count']} — {s['sources']}")
            print(f"  HEADLINE: {s['headline']}")
    else:
        print("\n[Listener] No validated signals at this time")