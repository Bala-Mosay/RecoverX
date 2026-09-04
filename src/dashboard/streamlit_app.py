import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import sqlite3
import json
import pandas as pd
import streamlit as st
from datetime import datetime
import plotly.graph_objects as go

DB_PATH = os.getenv("DB_PATH", "mandatemind.db")

# ═══════════════════════════════════════════════════════════════════════════════
# SVG ICONS
# ═══════════════════════════════════════════════════════════════════════════════
ICONS = {
    "events": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    "check": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    "block": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>',
    "amount": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
    "mail": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
    "template": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
    "users": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "inbox": '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>',
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _query(sql, params=None):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return pd.read_sql_query(sql, conn, params=params)
    except Exception:
        return pd.DataFrame()


def load_events():
    return _query("SELECT * FROM payment_events ORDER BY timestamp DESC")


def load_compliance():
    return _query("SELECT * FROM compliance_decisions ORDER BY timestamp DESC")


def load_retries():
    return _query("SELECT * FROM retry_actions ORDER BY timestamp DESC")


def load_simulations():
    return _query("SELECT * FROM simulation_results ORDER BY timestamp DESC LIMIT 10")


def load_notifications():
    return _query("SELECT * FROM notifications ORDER BY timestamp DESC")


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════════
def metric_card(icon_key, label, value, delta=None, delta_type="positive"):
    icon_svg = ICONS.get(icon_key, "")
    delta_html = ""
    if delta:
        cls = "mc-delta mc-pos" if delta_type == "positive" else "mc-delta mc-neg"
        arrow = "+" if delta_type == "positive" else ""
        delta_html = f'<div class="{cls}">{arrow}{delta}</div>'
    return f"""<div class="mc" tabindex="0">
        <div class="mc-inner">
            <div class="mc-icon">{icon_svg}</div>
            <div class="mc-label">{label}</div>
            <div class="mc-val">{value}</div>
            {delta_html}
        </div>
    </div>"""


def empty_state(title, hint):
    return f"""<div class="empty">
        <div class="empty-icon">{ICONS.get("inbox", "")}</div>
        <div class="empty-title">{title}</div>
        <div class="empty-hint">{hint}</div>
    </div>"""


def progress_ring(pct, size=200, stroke=8):
    r = (size - stroke) / 2
    c = 2 * 3.14159 * r
    offset = c - (pct / 100) * c
    if pct >= 80:
        color = "#5ee0a8"
    elif pct >= 50:
        color = "#4a9e7a"
    elif pct >= 25:
        color = "#d4a843"
    else:
        color = "#e05555"
    return f"""<div class="ring-wrap">
        <svg class="ring-svg" width="{size}" height="{size}">
            <circle class="ring-bg" cx="{size/2}" cy="{size/2}" r="{r}" stroke-width="{stroke}"/>
            <circle class="ring-fill" cx="{size/2}" cy="{size/2}" r="{r}" stroke-width="{stroke}"
                stroke="{color}" stroke-dasharray="{c}" stroke-dashoffset="{offset}"/>
        </svg>
        <div class="ring-center">
            <div class="ring-pct" style="color:{color}">{pct:.1f}%</div>
            <div class="ring-label">Recovery rate</div>
        </div>
    </div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════════════
STYLE = """<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }

/* ── Grain Overlay ── */
.stApp {
    background: #0c1310 !important;
    font-family: 'Outfit', sans-serif !important;
    color: #c8d8cc !important;
}
html::after {
    content: '';
    position: fixed;
    inset: 0;
    z-index: 9999;
    pointer-events: none;
    opacity: 0.03;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    background-repeat: repeat;
    background-size: 128px 128px;
}

/* ── Container ── */
.main .block-container {
    max-width: 1400px !important;
    padding-top: 2rem !important;
}

/* ── Hero ── */
.hero {
    background: #111c16;
    border-left: 3px solid #5ee0a8;
    border-radius: 8px;
    padding: 2rem 2.5rem;
    margin-bottom: 2.5rem;
}
.hero h1 {
    font-size: 2rem;
    font-weight: 700;
    color: #e0ece4 !important;
    margin: 0;
    letter-spacing: -0.03em;
    line-height: 1.1;
    text-wrap: balance;
}
.hero p {
    color: #6a8a7a;
    font-size: 0.9rem;
    margin: 0.35rem 0 0 0;
    line-height: 1.5;
}
.hero-badge {
    display: inline-block;
    background: #1a2e22;
    border: 1px solid #243d2b;
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 0.7rem;
    font-weight: 500;
    color: #5ee0a8;
    margin-top: 0.75rem;
}
.hero-right {
    text-align: right;
    flex-shrink: 0;
}
.hero-status {
    font-size: 0.75rem;
    font-weight: 500;
    color: #6a8a7a;
}
.hero-status strong {
    color: #5ee0a8;
}

/* ── Metric Cards ── */
.mc {
    background: #0e1812;
    border: 1px solid #1a2e22;
    border-radius: 10px;
    padding: 5px;
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.25s ease;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}
.mc:hover {
    transform: translateY(-2px);
    border-color: #2a4a35;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}
.mc:active {
    transform: scale(0.98);
}
.mc:focus-visible {
    outline: 2px solid #5ee0a8;
    outline-offset: 2px;
}
.mc-inner {
    background: #111c16;
    border-radius: 7px;
    padding: 1.25rem 1.25rem 1.35rem;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}
.mc-icon {
    color: #5ee0a8;
    margin-bottom: 0.75rem;
}
.mc-label {
    font-size: 0.8rem;
    font-weight: 500;
    color: #6a8a7a;
    margin-bottom: 0.25rem;
}
.mc-val {
    font-size: 1.8rem;
    font-weight: 700;
    color: #e0ece4;
    line-height: 1;
    font-variant-numeric: tabular-nums;
}
.mc-delta {
    font-size: 0.75rem;
    margin-top: 0.5rem;
}
.mc-pos { color: #5ee0a8; }
.mc-neg { color: #e05555; }

/* ── Cards Grid (2+2) ── */
.cards-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 1.5rem;
}

/* ── Section Headers ── */
.sec {
    font-size: 1rem;
    font-weight: 600;
    color: #c8d8cc;
    margin: 2.5rem 0 1rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #1a2e22;
    letter-spacing: -0.01em;
}

/* ── Panels ── */
.panel {
    background: #0e1812;
    border: 1px solid #1a2e22;
    border-radius: 10px;
    padding: 5px;
    margin-bottom: 1.25rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}
.panel-inner {
    background: #111c16;
    border-radius: 7px;
    padding: 1.25rem;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

/* ── Progress Ring ── */
.ring-wrap {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 1.5rem;
}
.ring-svg { transform: rotate(-90deg); }
.ring-bg { fill: none; stroke: #1a2e22; }
.ring-fill {
    fill: none;
    stroke-linecap: round;
    transition: stroke-dashoffset 1s ease-out;
}
.ring-center {
    position: absolute;
    text-align: center;
}
.ring-pct {
    font-size: 2.2rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}
.ring-label {
    font-size: 0.8rem;
    font-weight: 500;
    color: #6a8a7a;
    margin-top: 0.15rem;
}

/* ── Badges ── */
.badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.badge-ok { background: #1a2e22; color: #5ee0a8; }
.badge-err { background: #2e1a1a; color: #e05555; }
.badge-warn { background: #2e2a1a; color: #d4a843; }
.badge-info { background: #1a2a2e; color: #5ea8d4; }

/* ── Empty States ── */
.empty {
    text-align: center;
    padding: 3.5rem 2rem;
    background: #111c16;
    border: 1px solid #1a2e22;
    border-radius: 10px;
}
.empty-icon {
    color: #2a4a35;
    margin-bottom: 1rem;
}
.empty-title {
    font-size: 1rem;
    font-weight: 600;
    color: #8aaa8a;
    margin-bottom: 0.4rem;
}
.empty-hint {
    font-size: 0.8rem;
    color: #5a7a5a;
    line-height: 1.5;
}
.empty-hint code {
    background: #1a2e22;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 0.75rem;
    color: #5ee0a8;
}

/* ── Phone Mockup ── */
.phone {
    width: 320px;
    max-width: 100%;
    margin: 0 auto;
    background: #1a1a24;
    border-radius: 28px;
    padding: 10px;
    border: 1px solid #2a2a36;
}
.phone-inner {
    background: #0e0e16;
    border-radius: 22px;
    padding: 14px;
    min-height: 380px;
}
.phone-top {
    text-align: center;
    padding: 6px 0 14px 0;
    border-bottom: 1px solid #1a1a24;
    margin-bottom: 10px;
}
.phone-top strong {
    font-size: 0.85rem;
    color: #5ee0a8;
}
.phone-top small {
    display: block;
    font-size: 0.6rem;
    color: #6a7a7a;
    margin-top: 2px;
}
.wa-msg {
    background: #1a2420;
    border: 1px solid #243d2b;
    border-radius: 10px 10px 10px 2px;
    padding: 8px 12px;
    margin-bottom: 6px;
    font-size: 0.7rem;
    color: #c8d8cc;
    line-height: 1.4;
}
.wa-msg .wa-time {
    font-size: 0.55rem;
    color: #6a8a7a;
    text-align: right;
    margin-top: 3px;
}

/* ── Streamlit Overrides ── */
[data-testid="stMetric"] {
    display: none !important;
}
[data-testid="stTab"] {
    background: transparent !important;
    color: #6a8a7a !important;
    border-radius: 4px !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.2s ease, border-color 0.2s ease !important;
}
[data-testid="stTab"][aria-selected="true"] {
    background: #1a2e22 !important;
    color: #5ee0a8 !important;
    border-bottom: 2px solid #5ee0a8 !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid #1a2e22 !important;
    border-radius: 8px !important;
}
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: #111c16 !important;
    border-color: #1a2e22 !important;
    color: #c8d8cc !important;
}
.stSelectbox label,
.stNumberInput label,
.stTextInput label {
    color: #6a8a7a !important;
}
.stExpander {
    background: #111c16 !important;
    border: 1px solid #1a2e22 !important;
    border-radius: 8px !important;
}
h1, h2, h3, h4, h5, h6 { color: #e0ece4 !important; }
.stMarkdown { color: #c8d8cc; }
.stSpinner > div { color: #5ee0a8 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #0c1310; }
::-webkit-scrollbar-thumb { background: #2a4a35; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #3a6a4a; }

/* ── Responsive ── */
@media (max-width: 768px) {
    .hero { padding: 1.25rem 1.5rem; }
    .hero h1 { font-size: 1.5rem; }
    .hero-right { text-align: left; margin-top: 0.5rem; }
    .cards-grid { grid-template-columns: 1fr; }
    .mc-val { font-size: 1.4rem; }
    .ring-pct { font-size: 1.6rem; }
    .phone { width: 100%; }
    .sec { margin-top: 1.5rem; }
}
</style>"""


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    st.set_page_config(page_title="MandateMind", page_icon=" ", layout="wide", initial_sidebar_state="collapsed")
    st.markdown(STYLE, unsafe_allow_html=True)

    # Hero
    st.markdown("""<div class="hero">
        <div>
            <h1>MandateMind</h1>
            <p>Payment recovery engine enforcing RBI e-mandate rules for recurring payments.</p>
            <div class="hero-badge">Razorpay AI Buildathon 2026</div>
        </div>
        <div class="hero-right">
            <div class="hero-status"><strong>3</strong> compliance rules enforced</div>
        </div>
    </div>""", unsafe_allow_html=True)

    tabs = st.tabs(["  Overview", "  Events", "  Compliance", "  Notifications", "  Simulations"])
    with tabs[0]: tab_overview()
    with tabs[1]: tab_events()
    with tabs[2]: tab_compliance()
    with tabs[3]: tab_notifications()
    with tabs[4]: tab_simulations()


# ═══════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
def tab_overview():
    with st.spinner("Loading..."):
        events = load_events()
        compliance = load_compliance()
        retries = load_retries()

    n_events = len(events)
    n_allowed = len(compliance[compliance["allowed"] == True]) if not compliance.empty else 0
    n_blocked = len(compliance[compliance["allowed"] == False]) if not compliance.empty else 0
    rate = round((n_allowed / n_events * 100), 1) if n_events > 0 else 0
    total_amt = events["amount"].sum() if not events.empty else 0

    # 2+2 grid instead of 4 equal columns
    st.markdown("""<div class="cards-grid">
        {card1}{card2}
    </div>
    <div class="cards-grid">
        {card3}{card4}
    </div>""".format(
        card1=metric_card("events", "Total events", f"{n_events:,}", "processed"),
        card2=metric_card("check", "Compliance allowed", f"{n_allowed:,}", f"{n_blocked} blocked"),
        card3=metric_card("block", "Blocked", f"{n_blocked:,}", "violations stopped", "negative"),
        card4=metric_card("amount", "Total amount at risk", f"Rs.{total_amt:,.0f}", "across all events"),
    ), unsafe_allow_html=True)

    left, right = st.columns([1, 2])
    with left:
        st.markdown('<div class="sec">Recovery rate</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel"><div class="panel-inner">', unsafe_allow_html=True)
        st.markdown(progress_ring(rate), unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="sec">Compliance breakdown</div>', unsafe_allow_html=True)
        if not compliance.empty:
            vc = compliance["action"].value_counts()
            fig = go.Figure(go.Bar(x=vc.index, y=vc.values, marker_color="#5ee0a8", text=vc.values, textposition="auto"))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#c8d8cc", size=12, family="Outfit"), margin=dict(l=0, r=0, t=0, b=0), height=280, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#1a2e22"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown(empty_state("No compliance data yet", "Run a simulation to see compliance decisions."), unsafe_allow_html=True)

    left2, right2 = st.columns(2)
    with left2:
        st.markdown('<div class="sec">Retry actions</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel"><div class="panel-inner">', unsafe_allow_html=True)
        if not retries.empty:
            vc = retries["action_taken"].value_counts()
            fig = go.Figure(go.Pie(labels=vc.index, values=vc.values, hole=0.55, marker=dict(colors=["#5ee0a8", "#d4a843", "#e05555", "#5ea8d4"]), textfont=dict(color="#c8d8cc")))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#c8d8cc", family="Outfit"), showlegend=True, legend=dict(font=dict(color="#c8d8cc", size=11)), margin=dict(l=0, r=0, t=0, b=0), height=280)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown(empty_state("No retry data yet", "Retry actions appear after failed payment attempts."), unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    with right2:
        st.markdown('<div class="sec">Amount distribution</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel"><div class="panel-inner">', unsafe_allow_html=True)
        if not events.empty:
            fig = go.Figure(go.Histogram(x=events["amount"], nbinsx=25, marker_color="#5ee0a8", marker_line=dict(width=1, color="#3a6a4a")))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#c8d8cc", family="Outfit"), margin=dict(l=0, r=0, t=0, b=0), height=280, xaxis=dict(title="Amount (paise)", showgrid=False), yaxis=dict(title="Count", showgrid=True, gridcolor="#1a2e22"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown(empty_state("No event data yet", "Payment events appear when simulations run."), unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# EVENTS
# ═══════════════════════════════════════════════════════════════════════════════
def tab_events():
    st.markdown('<div class="sec">Payment events</div>', unsafe_allow_html=True)
    with st.spinner("Loading events..."):
        events = load_events()
    if events.empty:
        st.markdown(empty_state("No events yet", "Run <code>python run_recovery.py</code> to generate payment events."), unsafe_allow_html=True)
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        fail_filter = st.selectbox("Failure code", ["All"] + list(events["failure_code"].unique()))
    with c2:
        min_amt = st.number_input("Min amount", value=0, step=100)
    with c3:
        max_amt = st.number_input("Max amount", value=int(events["amount"].max()) + 1000, step=100)

    df = events.copy()
    if fail_filter != "All":
        df = df[df["failure_code"] == fail_filter]
    df = df[(df["amount"] >= min_amt) & (df["amount"] <= max_amt)]

    st.caption(f"Showing {len(df)} of {len(events)} events")
    st.markdown('<div class="panel"><div class="panel-inner">', unsafe_allow_html=True)
    st.dataframe(df[["id", "subscription_id", "customer_id", "amount", "failure_code", "merchant_category", "timestamp"]].head(100), use_container_width=True)
    st.markdown('</div></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════════════
def tab_compliance():
    st.markdown('<div class="sec">Compliance decisions</div>', unsafe_allow_html=True)
    with st.spinner("Loading compliance data..."):
        compliance = load_compliance()
    if compliance.empty:
        st.markdown(empty_state("No compliance decisions yet", "Decisions appear after running payment simulations."), unsafe_allow_html=True)
        return

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="panel"><div class="panel-inner">', unsafe_allow_html=True)
        allowed = len(compliance[compliance["allowed"] == True])
        blocked = len(compliance[compliance["allowed"] == False])
        fig = go.Figure(go.Bar(x=["Allowed", "Blocked"], y=[allowed, blocked], marker_color=["#5ee0a8", "#e05555"], text=[allowed, blocked], textposition="auto", textfont=dict(color="#c8d8cc")))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#c8d8cc", family="Outfit"), margin=dict(l=0, r=0, t=10, b=0), height=280, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#1a2e22"))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel"><div class="panel-inner">', unsafe_allow_html=True)
        blocked_df = compliance[compliance["allowed"] == False]
        if not blocked_df.empty:
            rc = blocked_df["reason"].value_counts().head(5)
            fig = go.Figure(go.Bar(y=rc.index, x=rc.values, orientation="h", marker_color="#e05555", text=rc.values, textposition="auto", textfont=dict(color="#c8d8cc")))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#c8d8cc", family="Outfit"), margin=dict(l=0, r=0, t=10, b=0), height=280, xaxis=dict(showgrid=True, gridcolor="#1a2e22"), yaxis=dict(showgrid=False))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown(empty_state("No blocks recorded", "All compliance checks passed so far."), unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="sec">Recent decisions</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><div class="panel-inner">', unsafe_allow_html=True)
    st.dataframe(compliance[["event_id", "subscription_id", "allowed", "action", "reason", "timestamp"]].head(50), use_container_width=True)
    st.markdown('</div></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════
def tab_notifications():
    st.markdown('<div class="sec">WhatsApp notifications</div>', unsafe_allow_html=True)
    with st.spinner("Loading notifications..."):
        notifications = load_notifications()
    if notifications.empty:
        st.markdown(empty_state("No notifications yet", "Run <code>python run_whatsapp_sim.py</code> to send test notifications."), unsafe_allow_html=True)
        return

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(metric_card("mail", "Total sent", f"{len(notifications):,}"), unsafe_allow_html=True)
    with c2: st.markdown(metric_card("template", "Templates", f"{notifications['template'].nunique():,}"), unsafe_allow_html=True)
    with c3: st.markdown(metric_card("users", "Recipients", f"{notifications['recipient'].nunique():,}"), unsafe_allow_html=True)

    col_phone, col_chart = st.columns([1, 2])
    with col_phone:
        st.markdown('<div class="sec">Message preview</div>', unsafe_allow_html=True)
        latest = notifications.head(3)
        msgs = ""
        for _, row in latest.iterrows():
            try:
                body = json.loads(row["payload"]).get("body", "") if row["payload"] else ""
            except Exception:
                body = ""
            if len(body) > 100:
                body = body[:100] + "..."
            body = body.replace("\n", "<br>").replace("<", "&lt;").replace(">", "&gt;")
            ts = str(row["timestamp"])[:16]
            msgs += f'<div class="wa-msg">{body}<div class="wa-time">{ts}</div></div>'
        st.markdown(f"""<div class="phone">
            <div class="phone-inner">
                <div class="phone-top"><strong>MandateMind</strong><small>WhatsApp Business</small></div>
                {msgs}
            </div>
        </div>""", unsafe_allow_html=True)

    with col_chart:
        st.markdown('<div class="sec">By template</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel"><div class="panel-inner">', unsafe_allow_html=True)
        tc = notifications["template"].value_counts()
        fig = go.Figure(go.Bar(x=tc.index, y=tc.values, marker_color="#5ee0a8", text=tc.values, textposition="auto", textfont=dict(color="#c8d8cc")))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#c8d8cc", family="Outfit"), margin=dict(l=0, r=0, t=0, b=0), height=320, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#1a2e22"))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="sec">History</div>', unsafe_allow_html=True)
    tpl_filter = st.selectbox("Filter template", ["All"] + list(notifications["template"].unique()))
    filtered = notifications if tpl_filter == "All" else notifications[notifications["template"] == tpl_filter]

    for _, row in filtered.head(10).iterrows():
        try:
            body = json.loads(row["payload"]).get("body", "") if row["payload"] else ""
        except Exception:
            body = ""
        tpl = row["template"]
        badge_cls = {"pre_debit_notice": "badge-info", "retry_notification": "badge-ok", "stepup_link": "badge-warn", "mandate_exhausted": "badge-err"}.get(tpl, "badge-info")
        with st.expander(f"[{tpl}] {row['recipient']}"):
            st.markdown(f'<span class="badge {badge_cls}">{tpl}</span>', unsafe_allow_html=True)
            st.code(body, language=None)


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATIONS
# ═══════════════════════════════════════════════════════════════════════════════
def tab_simulations():
    st.markdown('<div class="sec">Simulation results</div>', unsafe_allow_html=True)
    with st.spinner("Loading simulations..."):
        simulations = load_simulations()
    if simulations.empty:
        st.markdown(empty_state("No simulation results yet", "Run <code>python run_recovery.py</code> to start a simulation."), unsafe_allow_html=True)
        return

    st.markdown('<div class="panel"><div class="panel-inner">', unsafe_allow_html=True)
    st.dataframe(simulations, use_container_width=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

    if len(simulations) > 1:
        st.markdown('<div class="sec">Recovery rate over time</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel"><div class="panel-inner">', unsafe_allow_html=True)
        chart_data = simulations[["timestamp", "recovery_rate"]].copy()
        chart_data["timestamp"] = pd.to_datetime(chart_data["timestamp"])
        chart_data = chart_data.sort_values("timestamp")
        fig = go.Figure(go.Scatter(
            x=chart_data["timestamp"], y=chart_data["recovery_rate"],
            mode="lines+markers", line=dict(color="#5ee0a8", width=2, shape="spline"),
            marker=dict(size=6, color="#5ee0a8", line=dict(width=1, color="#111c16")),
            fill="tozeroy", fillcolor="rgba(94,224,168,0.06)"
        ))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#c8d8cc", family="Outfit"), margin=dict(l=0, r=0, t=0, b=0), height=280, xaxis=dict(showgrid=False), yaxis=dict(title="Recovery %", showgrid=True, gridcolor="#1a2e22"))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div></div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
