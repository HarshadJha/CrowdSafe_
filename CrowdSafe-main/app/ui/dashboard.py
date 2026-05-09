"""
dashboard.py — Main Dashboard Layout & CSS
"""

import streamlit as st
from app.config import LOCATION_NAME

# ── Custom CSS (injected once per session) ──────────────────────────
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .alert-safe { background: linear-gradient(135deg, #0d9488, #14b8a6); color: white; padding: 12px 20px; border-radius: 10px; text-align: center; font-weight: 700; font-size: 1.1em; box-shadow: 0 4px 15px rgba(13,148,136,0.4); }
    .alert-moderate { background: linear-gradient(135deg, #d97706, #f59e0b); color: white; padding: 12px 20px; border-radius: 10px; text-align: center; font-weight: 700; font-size: 1.1em; box-shadow: 0 4px 15px rgba(217,119,6,0.4); }
    .alert-high { background: linear-gradient(135deg, #dc2626, #ef4444); color: white; padding: 12px 20px; border-radius: 10px; text-align: center; font-weight: 700; font-size: 1.1em; box-shadow: 0 4px 15px rgba(220,38,38,0.4); }
    .alert-critical { background: linear-gradient(135deg, #7f1d1d, #dc2626); color: white; padding: 12px 20px; border-radius: 10px; text-align: center; font-weight: 700; font-size: 1.2em; animation: pulse 1.5s infinite; box-shadow: 0 4px 20px rgba(127,29,29,0.6); }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
    .surge-warning { background: linear-gradient(135deg, #9333ea, #c026d3); color: white; padding: 14px 20px; border-radius: 10px; text-align: center; font-weight: 700; font-size: 1.1em; animation: pulse 1s infinite; box-shadow: 0 4px 20px rgba(147,51,234,0.5); }
    .zone-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; padding: 15px; text-align: center; margin: 5px 0; }
    .suggestion-box { background: linear-gradient(135deg, #1e3a5f, #2563eb); color: white; padding: 12px 16px; border-radius: 10px; margin: 4px 0; font-size: 0.95em; border-left: 4px solid #60a5fa; }
    .incident-row { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin: 4px 0; font-size: 0.9em; }
    .dashboard-title { text-align: center; font-size: 2.2em; font-weight: 700; background: linear-gradient(90deg, #ef4444, #f59e0b, #14b8a6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0; }
    .dashboard-subtitle { text-align: center; color: #9ca3af; font-size: 0.95em; margin-top: 0; }
</style>
"""


def inject_css() -> None:
    """Inject the custom CSS into the Streamlit page."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header() -> None:
    """Render the dashboard title and subtitle."""
    st.markdown(
        "<div class='dashboard-title'>🚨 CrowdSafe AI Dashboard</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='dashboard-subtitle'>Real-Time Crowd Monitoring {LOCATION_NAME}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("")
