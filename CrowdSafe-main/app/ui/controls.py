"""
controls.py — Sidebar Controls & Source Selection
"""

import streamlit as st
from app.utils.email_alert import is_email_configured


def render_source_selector() -> str:
    """Render the video-source dropdown and return the selection."""
    return st.selectbox(
        "**Select Data Source**",
        ("Live Mobile Camera (IP Stream)", "Video File"),
    )


def render_mobile_panel() -> None:
    """Render the IP Webcam connection panel."""
    st.info("📱 Mobile Camera Sync Activated")
    st.markdown(
        """
    **How to connect your smartphone camera:**
    1. Connect your phone and laptop to the **same Wi-Fi network**.
    2. Download the **"IP Webcam"** app from the Google Play Store or iOS App Store.
    3. Open the app, scroll to the bottom, and tap **"Start server"**.
    4. An IPv4 address will appear on your phone screen (e.g., `http://192.168.1.5:8080`).
    5. Enter that exact URL below, adding `/video` at the end.
    """
    )
    ip_input = st.text_input(
        "✏️ Mobile Camera Stream URL:",
        value=st.session_state.mobile_url or "http://192.168.x.x:8080/video",
        placeholder="http://192.168.1.5:8080/video",
    )
    st.session_state.mobile_url = ip_input

    if st.session_state.mobile_connected:
        st.success("📡 Mobile Camera Connected")
    elif st.session_state.is_running:
        st.error("❌ Camera not reachable — check URL and Wi-Fi")


def render_sidebar_controls() -> dict:
    """Render all sidebar sliders/checkboxes and return their values."""
    st.sidebar.header("🔧 Control Panel")
    confidence = st.sidebar.slider("Detection Confidence", 0.0, 1.0, 0.4, 0.05)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Density Settings")
    proximity = st.sidebar.slider("Proximity Threshold (px)", 10, 150, 50, 5)
    cluster_size = st.sidebar.slider("Cluster Size (neighbors)", 1, 10, 3, 1)
    high_alert = st.sidebar.slider("High Density Alert Trigger", 5, 50, 10, 1)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Heatmap")
    show_heatmap = st.sidebar.checkbox("Enable Heatmap Overlay", value=True)

    return {
        "confidence": confidence,
        "proximity": proximity,
        "cluster_size": cluster_size,
        "high_alert": high_alert,
        "show_heatmap": show_heatmap,
    }
