import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import sqlite3
import json
import pandas as pd
import streamlit as st
from datetime import datetime

DB_PATH = "mandatemind.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def load_events():
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM payment_events ORDER BY timestamp DESC", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def load_compliance():
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM compliance_decisions ORDER BY timestamp DESC", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def load_retries():
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM retry_actions ORDER BY timestamp DESC", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def load_simulations():
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM simulation_results ORDER BY timestamp DESC LIMIT 10", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def load_notifications():
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM notifications ORDER BY timestamp DESC", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def render_metric_card(icon, label, value, delta=None, delta_type="positive", is_gold=False):
    delta_html = ""
    if delta is not None:
        delta_class = "positive" if delta_type == "positive" else "negative"
        arrow = "+" if delta_type == "positive" else ""
        delta_html = f'<div class="delta {delta_class}">{arrow}{delta}</div>'

    value_class = "value gold" if is_gold else "value"

    return f"""
    <div class="metric-card">
        <div class="icon">{icon}</div>
        <div class="label">{label}</div>
        <div class="{value_class}">{value}</div>
        {delta_html}
    </div>
    """


def render_progress_ring(percentage, size=200, stroke_width=8):
    radius = (size - stroke_width) / 2
    circumference = 2 * 3.14159 * radius
    offset = circumference - (percentage / 100) * circumference

    if percentage >= 80:
        color = "#00ff88"
    elif percentage >= 50:
        color = "#00d68f"
    elif percentage >= 25:
        color = "#ffd700"
    else:
        color = "#ff4757"

    return f"""
    <div style="position: relative; display: flex; justify-content: center; align-items: center; padding: 2rem;">
        <svg class="progress-ring" width="{size}" height="{size}">
            <defs>
                <linearGradient id="ringGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#00d68f;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#ffd700;stop-opacity:1" />
                </linearGradient>
            </defs>
            <circle class="progress-ring-bg" cx="{size/2}" cy="{size/2}" r="{radius}" />
            <circle class="progress-ring-fill" cx="{size/2}" cy="{size/2}" r="{radius}"
                style="stroke: {color}; --progress-offset: {offset};" />
        </svg>
        <div style="position: absolute; text-align: center;">
            <div style="font-size: 2.5rem; font-weight: 800; color: {color};">{percentage:.1f}%</div>
            <div style="font-size: 0.75rem; color: #7a9a7a;">RECOVERY RATE</div>
        </div>
    </div>
    """


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    st.set_page_config(
        page_title="MandateMind",
        page_icon="\U0001f6e1",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    # Hero Header
    st.markdown("""
    <div class="hero-header">
        <div style="display: flex; justify-content: space-between; align-items: center; position: relative; z-index: 1;">
            <div>
                <h1 class="hero-title">MandateMind</h1>
                <p class="hero-subtitle">AI-Powered Payment Recovery Engine with RBI Compliance</p>
                <div class="hero-badge">
                    <span class="dot"></span>
                    <span>Razorpay AI Buildathon 2026</span>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.7rem; color: #7a9a7a; text-transform: uppercase; letter-spacing: 0.1em;">Status</div>
                <div style="font-size: 0.9rem; color: #00d68f; font-weight: 600;">&#9679; SYSTEM ONLINE</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "  Overview",
        "  Events",
        "  Compliance",
        "  Notifications",
        "  Simulations"
    ])

    with tab1:
        render_overview()
    with tab2:
        render_events()
    with tab3:
        render_compliance()
    with tab4:
        render_notifications()
    with tab5:
        render_simulations()


# ═══════════════════════════════════════════════════════════════════════════════
# OVERVIEW TAB
# ═══════════════════════════════════════════════════════════════════════════════
def render_overview():
    events = load_events()
    compliance = load_compliance()
    retries = load_retries()

    total_events = len(events)
    allowed_count = len(compliance[compliance["allowed"] == True]) if not compliance.empty else 0
    blocked_count = len(compliance[compliance["allowed"] == False]) if not compliance.empty else 0
    recovery_rate = round((allowed_count / total_events * 100), 1) if total_events > 0 else 0
    total_amount = events["amount"].sum() if not events.empty else 0

    cols = st.columns(4)
    with cols[0]:
        st.markdown(render_metric_card("\U0001f4e5", "Total Events", f"{total_events:,}", "processed"), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(render_metric_card("\u2705", "Compliance Allowed", f"{allowed_count:,}", f"{blocked_count} blocked"), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(render_metric_card("\U0001f6ab", "Blocked", f"{blocked_count:,}", "violations prevented", delta_type="negative"), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(render_metric_card("\U0001f4b0", "Total Amount", f"Rs.{total_amount:,.0f}", "at risk", is_gold=True), unsafe_allow_html=True)

    col_ring, col_charts = st.columns([1, 2])

    with col_ring:
        st.markdown('<div class="section-header">  Recovery Rate</div>', unsafe_allow_html=True)
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.markdown(render_progress_ring(recovery_rate), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_charts:
        st.markdown('<div class="section-header">  Compliance Breakdown</div>', unsafe_allow_html=True)
        if not compliance.empty:
            import plotly.graph_objects as go
            action_counts = compliance["action"].value_counts()
            fig = go.Figure(data=[
                go.Bar(
                    x=action_counts.index,
                    y=action_counts.values,
                    marker=dict(color=["#00d68f", "#ffd700", "#ff4757"][:len(action_counts)], line=dict(width=0)),
                    text=action_counts.values,
                    textposition="auto",
                )
            ])
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e8f0e8"), margin=dict(l=0, r=0, t=0, b=0),
                height=300, xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="rgba(0,214,143,0.1)"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No compliance data yet.")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<div class="section-header">  Retry Actions</div>', unsafe_allow_html=True)
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        if not retries.empty:
            import plotly.graph_objects as go
            action_counts = retries["action_taken"].value_counts()
            fig = go.Figure(data=[
                go.Pie(labels=action_counts.index, values=action_counts.values, hole=0.6,
                       marker=dict(colors=["#00d68f", "#ffd700", "#ff4757", "#00ff88"]),
                       textfont=dict(color="#e8f0e8"))
            ])
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e8f0e8"),
                showlegend=True, legend=dict(font=dict(color="#e8f0e8")),
                margin=dict(l=0, r=0, t=0, b=0), height=300,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No retry data yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="section-header">  Amount Distribution</div>', unsafe_allow_html=True)
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        if not events.empty:
            import plotly.graph_objects as go
            fig = go.Figure(data=[
                go.Histogram(x=events["amount"], nbinsx=30,
                             marker=dict(color="rgba(0,214,143,0.6)", line=dict(width=1, color="#00d68f")))
            ])
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e8f0e8"), margin=dict(l=0, r=0, t=0, b=0),
                height=300, xaxis=dict(title="Amount (paise)", showgrid=False),
                yaxis=dict(title="Count", showgrid=True, gridcolor="rgba(0,214,143,0.1)"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No event data yet.")
        st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# EVENTS TAB
# ═══════════════════════════════════════════════════════════════════════════════
def render_events():
    st.markdown('<div class="section-header">  Payment Events</div>', unsafe_allow_html=True)
    events = load_events()
    if events.empty:
        st.markdown('<div class="glass-panel"><p style="color: #7a9a7a;">No events yet. Run: <code>python run_recovery.py</code></p></div>', unsafe_allow_html=True)
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        failure_filter = st.selectbox("Filter by failure code", ["All"] + list(events["failure_code"].unique()))
    with col2:
        min_amount = st.number_input("Min amount", value=0, step=100)
    with col3:
        max_amount = st.number_input("Max amount", value=int(events["amount"].max()) + 1000, step=100)

    filtered = events.copy()
    if failure_filter != "All":
        filtered = filtered[filtered["failure_code"] == failure_filter]
    filtered = filtered[(filtered["amount"] >= min_amount) & (filtered["amount"] <= max_amount)]

    st.markdown(f'<div style="color: #7a9a7a; font-size: 0.85rem;">Showing {len(filtered)} of {len(events)} events</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
    st.dataframe(filtered[["id", "subscription_id", "customer_id", "amount", "failure_code", "merchant_category", "timestamp"]].head(100), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE TAB
# ═══════════════════════════════════════════════════════════════════════════════
def render_compliance():
    st.markdown('<div class="section-header">  Compliance Decisions</div>', unsafe_allow_html=True)
    compliance = load_compliance()
    if compliance.empty:
        st.markdown('<div class="glass-panel"><p style="color: #7a9a7a;">No compliance decisions yet.</p></div>', unsafe_allow_html=True)
        return

    import plotly.graph_objects as go

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        allowed = len(compliance[compliance["allowed"] == True])
        blocked = len(compliance[compliance["allowed"] == False])
        fig = go.Figure(data=[go.Bar(x=["Allowed", "Blocked"], y=[allowed, blocked],
                                     marker=dict(color=["#00d68f", "#ff4757"]),
                                     text=[allowed, blocked], textposition="auto", textfont=dict(color="#e8f0e8"))])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(color="#e8f0e8"), margin=dict(l=0, r=0, t=10, b=0),
                          height=300, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(0,214,143,0.1)"))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        blocked_df = compliance[compliance["allowed"] == False]
        if not blocked_df.empty:
            reason_counts = blocked_df["reason"].value_counts().head(5)
            fig = go.Figure(data=[go.Bar(y=reason_counts.index, x=reason_counts.values, orientation="h",
                                         marker=dict(color="#ff4757"), text=reason_counts.values, textposition="auto", textfont=dict(color="#e8f0e8"))])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(color="#e8f0e8"), margin=dict(l=0, r=0, t=10, b=0),
                              height=300, xaxis=dict(showgrid=True, gridcolor="rgba(0,214,143,0.1)"), yaxis=dict(showgrid=False))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No blocks recorded.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-header">  Recent Decisions</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
    st.dataframe(compliance[["event_id", "subscription_id", "allowed", "action", "reason", "timestamp"]].head(50), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS TAB
# ═══════════════════════════════════════════════════════════════════════════════
def render_notifications():
    st.markdown('<div class="section-header">  WhatsApp Notifications</div>', unsafe_allow_html=True)
    notifications = load_notifications()
    if notifications.empty:
        st.markdown('<div class="glass-panel"><p style="color: #7a9a7a;">No notifications yet. Run: <code>python run_whatsapp_sim.py</code></p></div>', unsafe_allow_html=True)
        return

    cols = st.columns(3)
    with cols[0]:
        st.markdown(render_metric_card("\U0001f4e9", "Total Sent", f"{len(notifications):,}"), unsafe_allow_html=True)
    with cols[1]:
        templates = notifications["template"].value_counts()
        st.markdown(render_metric_card("\U0001f4dd", "Template Types", f"{len(templates):,}"), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(render_metric_card("\U0001f464", "Recipients", f"{notifications['recipient'].nunique():,}"), unsafe_allow_html=True)

    col_phone, col_chart = st.columns([1, 2])

    with col_phone:
        st.markdown('<div class="section-header">  Message Preview</div>', unsafe_allow_html=True)
        latest = notifications.head(3)
        msgs_html = ""
        for _, row in latest.iterrows():
            try:
                payload = json.loads(row["payload"]) if row["payload"] else {}
            except Exception:
                payload = {}
            body = payload.get("body", "No content")
            if len(body) > 120:
                body = body[:120] + "..."
            body_escaped = body.replace("\n", "<br>").replace("<", "&lt;").replace(">", "&gt;")
            ts = str(row["timestamp"])[:16]
            msgs_html += f'<div class="whatsapp-msg">{body_escaped}<div class="time">{ts}</div></div>'

        st.markdown(f"""
        <div class="phone-mockup">
            <div class="phone-screen">
                <div class="phone-header">
                    <div class="app-name">MandateMind</div>
                    <div style="font-size: 0.65rem; color: #7a9a7a;">WhatsApp Business</div>
                </div>
                {msgs_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_chart:
        st.markdown('<div class="section-header">  Notification Analytics</div>', unsafe_allow_html=True)
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        if not notifications.empty:
            import plotly.graph_objects as go
            template_counts = notifications["template"].value_counts()
            fig = go.Figure(data=[go.Bar(x=template_counts.index, y=template_counts.values,
                                         marker=dict(color=["#00d68f", "#ffd700", "#ff4757", "#00ff88"][:len(template_counts)]),
                                         text=template_counts.values, textposition="auto", textfont=dict(color="#e8f0e8"))])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(color="#e8f0e8"), margin=dict(l=0, r=0, t=0, b=0),
                              height=350, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(0,214,143,0.1)"))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-header">  Notification History</div>', unsafe_allow_html=True)
    template_filter = st.selectbox("Filter by template", ["All"] + list(notifications["template"].unique()))
    filtered = notifications.copy()
    if template_filter != "All":
        filtered = filtered[filtered["template"] == template_filter]

    for _, row in filtered.head(10).iterrows():
        try:
            payload = json.loads(row["payload"]) if row["payload"] else {}
        except Exception:
            payload = {}
        body = payload.get("body", "No content")
        template = row["template"]
        recipient = row["recipient"]
        badge_class = {"pre_debit_notice": "info", "retry_notification": "success",
                       "stepup_link": "warning", "mandate_exhausted": "danger"}.get(template, "info")
        with st.expander(f"  [{template}] {recipient}"):
            st.markdown(f'<span class="badge {badge_class}">{template}</span>', unsafe_allow_html=True)
            st.code(body, language=None)


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATIONS TAB
# ═══════════════════════════════════════════════════════════════════════════════
def render_simulations():
    st.markdown('<div class="section-header">  Simulation Results</div>', unsafe_allow_html=True)
    simulations = load_simulations()
    if simulations.empty:
        st.markdown('<div class="glass-panel"><p style="color: #7a9a7a;">No simulation results yet. Run: <code>python run_recovery.py</code></p></div>', unsafe_allow_html=True)
        return

    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
    st.dataframe(simulations, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if len(simulations) > 1:
        st.markdown('<div class="section-header">  Recovery Rate Over Time</div>', unsafe_allow_html=True)
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        import plotly.graph_objects as go
        chart_data = simulations[["timestamp", "recovery_rate"]].copy()
        chart_data["timestamp"] = pd.to_datetime(chart_data["timestamp"])
        chart_data = chart_data.sort_values("timestamp")
        fig = go.Figure(data=[go.Scatter(x=chart_data["timestamp"], y=chart_data["recovery_rate"],
                                         mode="lines+markers", line=dict(color="#00d68f", width=3, shape="spline"),
                                         marker=dict(size=8, color="#ffd700", line=dict(width=2, color="#00d68f")),
                                         fill="tozeroy", fillcolor="rgba(0,214,143,0.1)")])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(color="#e8f0e8"), margin=dict(l=0, r=0, t=0, b=0),
                          height=300, xaxis=dict(showgrid=False),
                          yaxis=dict(title="Recovery %", showgrid=True, gridcolor="rgba(0,214,143,0.1)"))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ═══════════════════════════════════════════════════════════════════════════════
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg-dark: #0a1a0f;
    --bg-card: rgba(0, 214, 143, 0.06);
    --emerald: #00d68f;
    --emerald-dim: rgba(0, 214, 143, 0.3);
    --gold: #ffd700;
    --text: #e8f0e8;
    --text-dim: #7a9a7a;
    --danger: #ff4757;
    --success: #00ff88;
    --warning: #ffa502;
}

.stApp {
    background: linear-gradient(135deg, #0a1a0f 0%, #0d2818 50%, #0a1a0f 100%) !important;
    font-family: 'Inter', sans-serif !important;
}

.particles {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    pointer-events: none; z-index: 0; overflow: hidden;
}
.particle {
    position: absolute; width: 4px; height: 4px;
    background: #00d68f; border-radius: 50%; opacity: 0.15;
    animation: float 15s infinite ease-in-out;
}
.particle:nth-child(1) { left: 10%; animation-delay: 0s; animation-duration: 12s; }
.particle:nth-child(2) { left: 25%; animation-delay: 2s; animation-duration: 18s; }
.particle:nth-child(3) { left: 40%; animation-delay: 4s; animation-duration: 14s; }
.particle:nth-child(4) { left: 55%; animation-delay: 1s; animation-duration: 20s; }
.particle:nth-child(5) { left: 70%; animation-delay: 3s; animation-duration: 16s; }
.particle:nth-child(6) { left: 85%; animation-delay: 5s; animation-duration: 13s; }
.particle:nth-child(7) { left: 15%; animation-delay: 6s; animation-duration: 17s; }
.particle:nth-child(8) { left: 60%; animation-delay: 7s; animation-duration: 15s; }

@keyframes float {
    0%, 100% { transform: translateY(100vh) scale(0); opacity: 0; }
    10% { opacity: 0.15; }
    90% { opacity: 0.15; }
    50% { transform: translateY(-10vh) scale(1); }
}

.hero-header {
    background: linear-gradient(135deg, rgba(0,214,143,0.15) 0%, rgba(255,215,0,0.08) 50%, rgba(0,214,143,0.15) 100%);
    border: 1px solid rgba(0,214,143,0.2); border-radius: 20px;
    padding: 2rem 2.5rem; margin-bottom: 2rem;
    position: relative; overflow: hidden;
    animation: slideInDown 0.8s ease-out;
}
.hero-header::before {
    content: ''; position: absolute; top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(ellipse at center, rgba(0,214,143,0.08) 0%, transparent 70%);
    animation: rotateGradient 20s linear infinite;
}
@keyframes rotateGradient {
    0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); }
}
.hero-title {
    font-size: 2.5rem; font-weight: 800;
    background: linear-gradient(135deg, #00d68f 0%, #ffd700 50%, #00d68f 100%);
    background-size: 200% auto;
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    animation: shimmer 3s ease-in-out infinite; margin: 0;
    position: relative; z-index: 1;
}
@keyframes shimmer {
    0%, 100% { background-position: 0% center; }
    50% { background-position: 200% center; }
}
.hero-subtitle {
    color: #7a9a7a; font-size: 1rem; margin-top: 0.5rem;
    position: relative; z-index: 1;
}
.hero-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(0,214,143,0.15); border: 1px solid rgba(0,214,143,0.3);
    border-radius: 20px; padding: 4px 12px; font-size: 0.75rem;
    color: #00d68f; margin-top: 0.75rem;
    position: relative; z-index: 1;
}
.hero-badge .dot {
    width: 6px; height: 6px; background: #00d68f; border-radius: 50%;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(0,214,143,0.4); }
    50% { box-shadow: 0 0 0 8px rgba(0,214,143,0); }
}

.metric-card {
    background: rgba(0, 214, 143, 0.06); backdrop-filter: blur(20px);
    border: 1px solid rgba(0,214,143,0.15); border-radius: 16px;
    padding: 1.5rem; position: relative; overflow: hidden;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    transform-style: preserve-3d; perspective: 1000px;
    animation: slideInUp 0.6s ease-out backwards;
}
.metric-card:nth-child(1) { animation-delay: 0.1s; }
.metric-card:nth-child(2) { animation-delay: 0.2s; }
.metric-card:nth-child(3) { animation-delay: 0.3s; }
.metric-card:nth-child(4) { animation-delay: 0.4s; }
.metric-card:hover {
    transform: translateY(-8px) rotateX(2deg) rotateY(-2deg);
    border-color: rgba(0,214,143,0.4);
    box-shadow: 0 20px 60px rgba(0,214,143,0.15), 0 0 40px rgba(0,214,143,0.1);
}
.metric-card::before {
    content: ''; position: absolute; top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(0,214,143,0.05), transparent);
    transition: left 0.5s ease;
}
.metric-card:hover::before { left: 100%; }
.metric-card .icon { font-size: 2rem; margin-bottom: 0.75rem; filter: drop-shadow(0 0 10px rgba(0,214,143,0.5)); }
.metric-card .label {
    font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.1em; color: #7a9a7a; margin-bottom: 0.25rem;
}
.metric-card .value { font-size: 2rem; font-weight: 800; color: #00d68f; line-height: 1; }
.metric-card .value.gold { color: #ffd700; }
.metric-card .delta { font-size: 0.8rem; margin-top: 0.5rem; display: flex; align-items: center; gap: 4px; }
.metric-card .delta.positive { color: #00ff88; }
.metric-card .delta.negative { color: #ff4757; }

@keyframes slideInUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
@keyframes slideInDown { from { opacity: 0; transform: translateY(-30px); } to { opacity: 1; transform: translateY(0); } }

.section-header {
    font-size: 1.25rem; font-weight: 700; color: #e8f0e8;
    margin: 2rem 0 1rem 0; display: flex; align-items: center; gap: 10px;
}
.section-header::after {
    content: ''; flex: 1; height: 1px;
    background: linear-gradient(90deg, rgba(0,214,143,0.3), transparent);
}

.glass-panel {
    background: rgba(0, 214, 143, 0.06); backdrop-filter: blur(20px);
    border: 1px solid rgba(0,214,143,0.12); border-radius: 16px;
    padding: 1.5rem; margin-bottom: 1.5rem; animation: fadeIn 0.6s ease-out;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

.badge {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 4px 10px; border-radius: 12px; font-size: 0.7rem;
    font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
}
.badge.success { background: rgba(0,255,136,0.15); color: #00ff88; border: 1px solid rgba(0,255,136,0.3); }
.badge.danger { background: rgba(255,71,87,0.15); color: #ff4757; border: 1px solid rgba(255,71,87,0.3); }
.badge.warning { background: rgba(255,165,2,0.15); color: #ffa502; border: 1px solid rgba(255,165,2,0.3); }
.badge.info { background: rgba(0,214,143,0.15); color: #00d68f; border: 1px solid rgba(0,214,143,0.3); }

.progress-ring { transform: rotate(-90deg); }
.progress-ring-bg { fill: none; stroke: rgba(0,214,143,0.1); stroke-width: 8; }
.progress-ring-fill {
    fill: none; stroke-width: 8; stroke-linecap: round;
    stroke-dasharray: 440; stroke-dashoffset: 440;
    animation: progressFill 2s ease-out forwards;
    filter: drop-shadow(0 0 8px rgba(0,214,143,0.5));
}
@keyframes progressFill { to { stroke-dashoffset: var(--progress-offset); } }

.phone-mockup {
    width: 320px; margin: 0 auto; background: #1a1a2e;
    border-radius: 36px; padding: 12px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 40px rgba(0,214,143,0.1);
    border: 2px solid rgba(0,214,143,0.2);
}
.phone-screen { background: #0d1117; border-radius: 28px; padding: 16px; min-height: 400px; }
.phone-header {
    text-align: center; padding: 8px 0 16px 0;
    border-bottom: 1px solid rgba(0,214,143,0.1); margin-bottom: 12px;
}
.phone-header .app-name { font-size: 0.9rem; font-weight: 700; color: #00d68f; }
.whatsapp-msg {
    background: rgba(0,214,143,0.1); border: 1px solid rgba(0,214,143,0.15);
    border-radius: 12px 12px 12px 0; padding: 10px 14px; margin-bottom: 8px;
    font-size: 0.75rem; color: #e8f0e8; line-height: 1.4;
    animation: slideInLeft 0.4s ease-out backwards;
}
.whatsapp-msg:nth-child(2) { animation-delay: 0.2s; }
.whatsapp-msg:nth-child(3) { animation-delay: 0.4s; }
.whatsapp-msg .time { font-size: 0.6rem; color: #7a9a7a; text-align: right; margin-top: 4px; }
@keyframes slideInLeft { from { opacity: 0; transform: translateX(-20px); } to { opacity: 1; transform: translateX(0); } }

[data-testid="stMetric"] {
    background: rgba(0, 214, 143, 0.06); border: 1px solid rgba(0,214,143,0.15);
    border-radius: 12px; padding: 1rem; transition: all 0.3s ease;
}
[data-testid="stMetric"]:hover { border-color: rgba(0,214,143,0.4); box-shadow: 0 0 30px rgba(0,214,143,0.1); }
[data-testid="stMetricValue"] { color: #00d68f !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #7a9a7a !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; }
[data-testid="stTab"] {
    background: transparent !important; border-radius: 8px !important;
    color: #7a9a7a !important; border: 1px solid transparent !important;
}
[data-testid="stTab"][aria-selected="true"] {
    background: rgba(0,214,143,0.1) !important; color: #00d68f !important;
    border-color: rgba(0,214,143,0.3) !important;
}
[data-testid="stDataFrame"] { border: 1px solid rgba(0,214,143,0.12) !important; border-radius: 12px !important; overflow: hidden !important; }
.stSelectbox > div > div { background: rgba(0,214,143,0.06) !important; border-color: rgba(0,214,143,0.2) !important; color: #e8f0e8 !important; }
.stNumberInput > div > div > input { background: rgba(0,214,143,0.06) !important; border-color: rgba(0,214,143,0.2) !important; color: #e8f0e8 !important; }
.stExpander { background: rgba(0,214,143,0.06) !important; border: 1px solid rgba(0,214,143,0.12) !important; border-radius: 12px !important; }
h1, h2, h3, h4, h5, h6 { color: #e8f0e8 !important; }
.stMarkdown { color: #e8f0e8; }
.stSelectbox label, .stNumberInput label { color: #7a9a7a !important; }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0a1a0f; }
::-webkit-scrollbar-thumb { background: rgba(0,214,143,0.3); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #00d68f; }
</style>

<div class="particles">
    <div class="particle"></div><div class="particle"></div><div class="particle"></div>
    <div class="particle"></div><div class="particle"></div><div class="particle"></div>
    <div class="particle"></div><div class="particle"></div>
</div>
"""


if __name__ == "__main__":
    main()
