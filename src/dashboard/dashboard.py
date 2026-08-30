import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "mandatemind.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def load_events():
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM payment_events", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def load_compliance():
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM compliance_decisions", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def load_retries():
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM retry_actions", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def load_simulation_results():
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM simulation_results ORDER BY timestamp DESC LIMIT 10", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


if __name__ == "__main__":
    try:
        import streamlit as st
        HAS_STREAMLIT = True
    except ImportError:
        HAS_STREAMLIT = False

    if not HAS_STREAMLIT:
        print("Streamlit not installed. Showing console dashboard.\n")
        events = load_events()
        compliance = load_compliance()
        retries = load_retries()
        results = load_simulation_results()

        print(f"=== MandateMind Dashboard ===")
        print(f"Total Events: {len(events)}")
        print(f"Compliance Decisions: {len(compliance)}")
        print(f"Retry Actions: {len(retries)}")

        if not compliance.empty:
            allowed = compliance[compliance["allowed"] == True]
            blocked = compliance[compliance["allowed"] == False]
            print(f"\nCompliance: {len(allowed)} allowed, {len(blocked)} blocked")
            if not blocked.empty:
                print(f"Block reasons:")
                for reason in blocked["reason"].value_counts().head(5).items():
                    print(f"  - {reason[0]}: {reason[1]}")

        if not retries.empty:
            step_ups = retries[retries["action_taken"] == "STEP_UP_LINK_SENT"]
            scheduled = retries[retries["action_taken"] == "RETRY_SCHEDULED"]
            print(f"\nRetries: {len(scheduled)} scheduled, {len(step_ups)} step-up links")

        if not results.empty:
            print(f"\nLast simulation:")
            r = results.iloc[0]
            print(f"  Events: {r['total_events']}")
            print(f"  Recovery Rate: {r['recovery_rate']:.1f}%")
            print(f"  Compliance Blocks: {r['compliance_blocks']}")
        sys.exit(0)

    st.set_page_config(page_title="MandateMind", layout="wide")
    st.title("MandateMind Dashboard")

    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Events", "Compliance", "Simulations"])

    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        events = load_events()
        compliance = load_compliance()
        retries = load_retries()

        col1.metric("Total Events", len(events))
        col2.metric("Compliance Decisions", len(compliance))
        col3.metric("Retry Actions", len(retries))

        allowed_count = len(compliance[compliance["allowed"] == True]) if not compliance.empty else 0
        blocked_count = len(compliance[compliance["allowed"] == False]) if not compliance.empty else 0
        col4.metric("Blocks", blocked_count)

        if not compliance.empty:
            st.subheader("Compliance Breakdown")
            action_counts = compliance["action"].value_counts()
            st.bar_chart(action_counts)

    with tab2:
        st.subheader("Recent Events")
        events = load_events()
        if not events.empty:
            st.dataframe(events.tail(50), use_container_width=True)
        else:
            st.info("No events yet. Run a simulation first.")

    with tab3:
        st.subheader("Compliance Decisions")
        compliance = load_compliance()
        if not compliance.empty:
            st.dataframe(compliance.tail(50), use_container_width=True)
        else:
            st.info("No compliance decisions yet.")

    with tab4:
        st.subheader("Simulation Results")
        results = load_simulation_results()
        if not results.empty:
            st.dataframe(results, use_container_width=True)
        else:
            st.info("No simulation results yet.")
