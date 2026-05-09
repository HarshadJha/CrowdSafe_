"""
visualizations.py — Real-Time Dashboard Widgets
"""

import streamlit as st
import pandas as pd

from app.config import ALERT_LEVELS, SUGGESTIONS


def render_alert_banner(placeholder, level: str) -> None:
    """Display the colour-coded alert banner."""
    info = ALERT_LEVELS[level]
    with placeholder.container():
        st.markdown(
            f"<div class='{info['color']}'>{info['icon']} Alert Level: {level}</div>",
            unsafe_allow_html=True,
        )


def render_stats(placeholder, total: int, dense: int, peak: int, avg: float) -> None:
    """Render the four-column metric cards."""
    with placeholder.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👥 Total", total)
        c2.metric("🔴 Dense", dense)
        c3.metric("📈 Peak", peak)
        c4.metric("📊 Avg", avg)


def render_surge_warning(placeholder, surge_detected: bool) -> None:
    """Show / hide the surge-warning banner."""
    with placeholder.container():
        if surge_detected:
            st.markdown(
                "<div class='surge-warning'>⚡ SURGE INCOMING — Crowd count rising rapidly!</div>",
                unsafe_allow_html=True,
            )


def render_zones(placeholder, boxes: list, zones: dict) -> None:
    """Render the Left / Center / Right zone density cards."""
    with placeholder.container():
        if boxes:
            st.markdown("**🗺️ Zone Density**")
            z1, z2, z3 = st.columns(3)
            zone_icons = {"Left": "⬅️", "Center": "⏺️", "Right": "➡️"}
            most_crowded = max(zones, key=zones.get)
            for col, (name, count) in zip([z1, z2, z3], zones.items()):
                highlight = "🔴 " if name == most_crowded and count > 0 else ""
                col.metric(f"{zone_icons[name]} {name}", f"{highlight}{count}")


def render_suggestions(placeholder, alert_level: str) -> None:
    """Show operator-recommended actions for HIGH / CRITICAL levels."""
    with placeholder.container():
        if alert_level in ("HIGH", "CRITICAL"):
            st.markdown("**💡 Recommended Actions**")
            for s in SUGGESTIONS.get(alert_level, []):
                st.markdown(f"<div class='suggestion-box'>{s}</div>", unsafe_allow_html=True)


def render_chart(placeholder, count_history, threshold: int) -> None:
    """Line chart of crowd-count history vs. threshold."""
    with placeholder.container():
        if len(count_history) > 1:
            df = pd.DataFrame({
                "Crowd Count": list(count_history),
                "Threshold": [threshold] * len(count_history),
            })
            st.line_chart(df, width="stretch")


def render_incidents(placeholder) -> None:
    """Render the rolling incident log."""
    with placeholder.container():
        logs = st.session_state.get("incident_log", [])
        if logs:
            for inc in logs[:8]:
                emoji = "🔴" if inc["alert_level"] == "HIGH" else "🚨"
                status = ""
                if inc.get("resolved"):
                    status = " [RESOLVED ✔️]"
                elif inc.get("acknowledged"):
                    status = " [ACKNOWLEDGED ✅]"
                elif inc.get("escalation_sent"):
                    status = " [ESCALATED ⚠️]"
                st.markdown(
                    f"<div class='incident-row'>"
                    f"{emoji} <strong>{inc['alert_level']}</strong> — "
                    f"Count: {inc['crowd_count']} — "
                    f"{inc['timestamp_str']}{status}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.success("No incidents recorded yet.")
