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


def main():
    st.set_page_config(
        page_title="MandateMind Dashboard",
        page_icon=":shield:",
        layout="wide",
    )

    st.title("MandateMind Dashboard")
    st.caption("AI-Powered Payment Recovery Engine with RBI Compliance")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Events", "Compliance", "Notifications", "Simulations"])

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


def render_overview():
    st.header("Overview")

    events = load_events()
    compliance = load_compliance()
    retries = load_retries()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Events", len(events))

    with col2:
        st.metric("Compliance Decisions", len(compliance))

    with col3:
        allowed_count = len(compliance[compliance["allowed"] == True]) if not compliance.empty else 0
        st.metric("Allowed", allowed_count)

    with col4:
        blocked_count = len(compliance[compliance["allowed"] == False]) if not compliance.empty else 0
        st.metric("Blocked", blocked_count)

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Compliance Breakdown")
        if not compliance.empty:
            action_counts = compliance["action"].value_counts()
            st.bar_chart(action_counts)
        else:
            st.info("No compliance data yet.")

    with col_right:
        st.subheader("Retry Actions")
        if not retries.empty:
            action_counts = retries["action_taken"].value_counts()
            st.bar_chart(action_counts)
        else:
            st.info("No retry data yet.")

    st.divider()

    st.subheader("Key Metrics")
    if not events.empty and not compliance.empty:
        total = len(events)
        allowed = len(compliance[compliance["allowed"] == True])
        blocked = len(compliance[compliance["allowed"] == False])
        recovery_rate = round((allowed / total * 100), 1) if total > 0 else 0

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Recovery Rate", f"{recovery_rate}%")
        col_b.metric("Total Amount", f"Rs.{events['amount'].sum():,.0f}")
        col_c.metric("Avg Amount", f"Rs.{events['amount'].mean():,.0f}")
        col_d.metric("Success Rate", f"{round(allowed/max(len(compliance),1)*100, 1)}%")


def render_events():
    st.header("Payment Events")

    events = load_events()

    if events.empty:
        st.info("No events yet. Run a simulation first.")
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

    st.write(f"Showing {len(filtered)} of {len(events)} events")

    st.dataframe(
        filtered[["id", "subscription_id", "customer_id", "amount", "failure_code", "merchant_category", "timestamp"]].head(100),
        use_container_width=True,
    )


def render_compliance():
    st.header("Compliance Decisions")

    compliance = load_compliance()

    if compliance.empty:
        st.info("No compliance decisions yet.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Decision Distribution")
        allowed = len(compliance[compliance["allowed"] == True])
        blocked = len(compliance[compliance["allowed"] == False])
        st.bar_chart({"Allowed": allowed, "Blocked": blocked})

    with col2:
        st.subheader("Block Reasons")
        blocked_df = compliance[compliance["allowed"] == False]
        if not blocked_df.empty:
            reason_counts = blocked_df["reason"].value_counts().head(10)
            st.dataframe(reason_counts.reset_index().rename(columns={"reason": "Reason", "count": "Count"}))
        else:
            st.info("No blocks recorded.")

    st.divider()

    st.subheader("Recent Decisions")
    st.dataframe(
        compliance[["event_id", "subscription_id", "allowed", "action", "reason", "timestamp"]].head(50),
        use_container_width=True,
    )


def render_simulations():
    st.header("Simulation Results")

    simulations = load_simulations()

    if simulations.empty:
        st.info("No simulation results yet. Run: python run_recovery.py")
        return

    st.dataframe(simulations, use_container_width=True)

    if len(simulations) > 1:
        st.divider()
        st.subheader("Recovery Rate Over Time")
        chart_data = simulations[["timestamp", "recovery_rate"]].copy()
        chart_data["timestamp"] = pd.to_datetime(chart_data["timestamp"])
        chart_data = chart_data.sort_values("timestamp")
        st.line_chart(chart_data.set_index("timestamp")["recovery_rate"])


def render_notifications():
    st.header("WhatsApp Notifications")

    notifications = load_notifications()

    if notifications.empty:
        st.info("No notifications yet. Run: python run_whatsapp_sim.py")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Sent", len(notifications))

    with col2:
        templates = notifications["template"].value_counts()
        st.metric("Template Types", len(templates))

    with col3:
        st.metric("Recipients", notifications["recipient"].nunique())

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("By Template")
        if not notifications.empty:
            template_counts = notifications["template"].value_counts()
            st.bar_chart(template_counts)

    with col_right:
        st.subheader("By Channel")
        if not notifications.empty:
            channel_counts = notifications["channel"].value_counts()
            st.bar_chart(channel_counts)

    st.divider()

    st.subheader("Notification History")

    template_filter = st.selectbox(
        "Filter by template",
        ["All"] + list(notifications["template"].unique()),
    )

    filtered = notifications.copy()
    if template_filter != "All":
        filtered = filtered[filtered["template"] == template_filter]

    st.write(f"Showing {len(filtered)} of {len(notifications)} notifications")

    for _, row in filtered.head(20).iterrows():
        try:
            payload = json.loads(row["payload"]) if row["payload"] else {}
        except Exception:
            payload = {}

        body = payload.get("body", "No content")
        template = row["template"]
        recipient = row["recipient"]
        timestamp = row["timestamp"]

        with st.expander(f"[{template}] {recipient} - {timestamp}"):
            st.code(body, language=None)


if __name__ == "__main__":
    main()
