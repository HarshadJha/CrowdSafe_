"""
main.py — CrowdSafe AI Dashboard Entry Point
=============================================
Orchestrates the Streamlit application.  All business logic lives in
``app.modules.*``; all UI rendering lives in ``app.ui.*``.  This file
wires everything together.

Run with:
    streamlit run app/main.py
"""

import sys
import time
from pathlib import Path
from collections import deque

import cv2
import streamlit as st

# ── Ensure project root is on sys.path so ``app.*`` imports resolve ──
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── Application imports ──────────────────────────────────────────────
from app.config import VIDEO_PATH
from app.utils.logging_utils import get_logger
from app.utils.video_utils import get_video_capture, release_capture
from app.utils.detection_utils import generate_heatmap, draw_bounding_boxes

from app.modules.detection import load_yolo_model, run_detection
from app.modules.crowd_analysis import (
    analyze_crowd_density,
    analyze_zones,
    get_alert_level,
    detect_surge,
)
from app.modules.ack_system import (
    create_incident,
    acknowledge_incident,
    resolve_incident,
    mark_escalated,
)
from app.modules.alert_system import trigger_initial_alert, trigger_escalation_alert
from app.modules.prediction import init_firebase, push_status_to_firebase

from app.ui.dashboard import inject_css, render_header
from app.ui.controls import (
    render_source_selector,
    render_mobile_panel,
    render_sidebar_controls,
)
from app.ui.visualizations import (
    render_alert_banner,
    render_stats,
    render_surge_warning,
    render_zones,
    render_suggestions,
    render_chart,
    render_incidents,
)

logger = get_logger(__name__)

# =====================================================================
#  PAGE CONFIG  (must be the first Streamlit call)
# =====================================================================
st.set_page_config(page_title="CrowdSafe Dashboard", page_icon="🚨", layout="wide")

# =====================================================================
#  SESSION STATE INITIALISATION
# =====================================================================
_DEFAULTS = {
    "is_running": False,
    "stop": False,
    "incident_log": [],
    "active_incident": None,
    "cap": None,
    "model": None,
    "tracking": {
        "count_history": deque(maxlen=100),
        "peak_count": 0,
        "total_sum": 0,
        "frame_num": 0,
    },
    "last_fb_update_time": time.time(),
    "mobile_url": "",
    "mobile_connected": False,
}
for key, default in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

# =====================================================================
#  CSS + HEADER
# =====================================================================
inject_css()
render_header()

# =====================================================================
#  SOURCE SELECTION
# =====================================================================
source_selection = render_source_selector()

if source_selection == "Live Mobile Camera (IP Stream)":
    render_mobile_panel()

st.markdown("---")

# =====================================================================
#  SIDEBAR CONTROLS
# =====================================================================
controls = render_sidebar_controls()
firebase_initialized = init_firebase()

# =====================================================================
#  INCIDENT MANAGEMENT PANEL
# =====================================================================
st.header("⚡ Incident Management")

inc = st.session_state.active_incident
col_a, col_r = st.columns(2)

ack_disabled = not (inc and not inc["acknowledged"])
res_disabled = not (inc and inc["acknowledged"] and not inc["resolved"])

if col_a.button("✅ Acknowledge Alert", disabled=ack_disabled, width="stretch"):
    if inc:
        st.session_state.active_incident = acknowledge_incident(inc)
        st.rerun()

if col_r.button("✔️ Mark as Resolved", disabled=res_disabled, width="stretch"):
    if inc:
        resolve_incident(inc)
        st.session_state.active_incident = None
        st.rerun()

status_msg = st.empty()

if inc:
    if inc["resolved"]:
        status_msg.success(f"✅ Situation handled by authorities (Incident {inc['id']})")
    elif inc["acknowledged"]:
        status_msg.success(
            f"✅ Alert acknowledged in {round(inc['response_time'], 1)} seconds. Awaiting resolution..."
        )
    elif inc["escalation_sent"]:
        status_msg.error(f"⚠️ No response from authorities! ESCALATION TRIGGERED for {inc['id']}")
    else:
        status_msg.warning(f"🚨 Active Crowd Alert: Incident {inc['id']} requires acknowledgement!")
else:
    status_msg.info("✅ System Normal. No active incidents.")

st.markdown("---")

# =====================================================================
#  DASHBOARD LAYOUT — Placeholders
# =====================================================================
col_feed, col_stats = st.columns([3, 2])

with col_feed:
    st.header("📹 Live Feed")
    frame_placeholder = st.empty()

with col_stats:
    st.header("📊 Real-Time Analytics")
    alert_ph = st.empty()
    stats_ph = st.empty()
    surge_ph = st.empty()
    zones_ph = st.empty()
    suggest_ph = st.empty()

st.markdown("---")
col_chart, col_inc = st.columns([3, 2])

with col_chart:
    st.header("📈 Crowd Trend")
    chart_ph = st.empty()

with col_inc:
    st.header("📋 Recent Incidents")
    incidents_ph = st.empty()

# =====================================================================
#  START / STOP CONTROLS
# =====================================================================
col_start, col_stop = st.columns(2)

if col_start.button(f"🚀 Start {source_selection}", type="primary"):
    st.session_state.is_running = True
    st.session_state.stop = False

if col_stop.button("🛑 Stop Analysis"):
    st.session_state.is_running = False
    st.session_state.stop = True
    release_capture(st.session_state.cap)
    st.session_state.cap = None

# =====================================================================
#  MAIN PROCESSING LOOP
# =====================================================================
if st.session_state.is_running and not st.session_state.stop:
    # ── Initialise capture & model on first run ─────────────────────
    if st.session_state.cap is None:
        model = load_yolo_model()
        cap = get_video_capture(source_selection, st.session_state.mobile_url)
        if model and cap and cap.isOpened():
            st.session_state.cap = cap
            st.session_state.model = model
            if source_selection == "Live Mobile Camera (IP Stream)":
                st.session_state.mobile_connected = True
        else:
            st.session_state.mobile_connected = False
            if source_selection == "Live Mobile Camera (IP Stream)":
                st.error("❌ Cannot connect to mobile camera. Verify the IP URL.")
            else:
                st.error(f"Video file not found at '{VIDEO_PATH}'.")
            st.session_state.is_running = False
            st.stop()

    cap = st.session_state.cap
    model = st.session_state.model
    tracking = st.session_state.tracking

    reconnect_attempts = 0
    MAX_RECONNECT = 3

    while st.session_state.is_running and not st.session_state.stop:
        boxes = []
        dense_count = 0
        total_count = 0
        in_cluster = []

        # ── Guard: capture must be open ─────────────────────────────
        if not cap or not cap.isOpened():
            if source_selection == "Live Mobile Camera (IP Stream)" and reconnect_attempts < MAX_RECONNECT:
                reconnect_attempts += 1
                frame_placeholder.warning(
                    f"⚠️ Connection lost — reconnecting ({reconnect_attempts}/{MAX_RECONNECT})…"
                )
                time.sleep(2)
                cap = get_video_capture(source_selection, st.session_state.mobile_url)
                if cap and cap.isOpened():
                    st.session_state.cap = cap
                    st.session_state.mobile_connected = True
                    reconnect_attempts = 0
                    continue
                else:
                    st.session_state.mobile_connected = False
                    continue
            st.session_state.mobile_connected = False
            break

        ret, frame = cap.read()
        if not ret:
            if source_selection == "Live Mobile Camera (IP Stream)" and reconnect_attempts < MAX_RECONNECT:
                reconnect_attempts += 1
                frame_placeholder.warning(
                    f"⚠️ Frame lost — reconnecting ({reconnect_attempts}/{MAX_RECONNECT})…"
                )
                time.sleep(2)
                cap.release()
                cap = get_video_capture(source_selection, st.session_state.mobile_url)
                if cap and cap.isOpened():
                    st.session_state.cap = cap
                    st.session_state.mobile_connected = True
                    reconnect_attempts = 0
                    continue
                else:
                    st.session_state.mobile_connected = False
                    continue
            break

        reconnect_attempts = 0

        # ── Resize + detect ─────────────────────────────────────────
        frame = cv2.resize(frame, (960, 540))
        boxes = run_detection(model, frame, controls["confidence"])
        total_count = len(boxes)
        dense_count, in_cluster = analyze_crowd_density(
            boxes, controls["proximity"], controls["cluster_size"]
        )

        # ── Draw & display ──────────────────────────────────────────
        draw_bounding_boxes(frame, boxes, in_cluster)
        display = generate_heatmap(frame, boxes) if (controls["show_heatmap"] and boxes) else frame
        frame_placeholder.image(display, channels="BGR")

        # ── Update tracking ─────────────────────────────────────────
        tracking["frame_num"] += 1
        tracking["count_history"].append(dense_count)
        tracking["peak_count"] = max(tracking["peak_count"], dense_count)
        tracking["total_sum"] += dense_count

        alert_level = get_alert_level(dense_count, controls["high_alert"])
        surge_detected = detect_surge(tracking["count_history"])
        zones = analyze_zones(boxes, 960) if boxes else {"Left": 0, "Center": 0, "Right": 0}

        # ── Incident & escalation ───────────────────────────────────
        if alert_level in ("HIGH", "CRITICAL"):
            if st.session_state.active_incident is None:
                new_inc = create_incident(alert_level, dense_count)
                st.session_state.active_incident = new_inc
                trigger_initial_alert(new_inc)
                st.rerun()

        inc = st.session_state.active_incident
        if inc:
            if inc["resolved"]:
                status_msg.success(f"✅ Situation handled (Incident {inc['id']})")
            elif inc["acknowledged"]:
                status_msg.success(
                    f"✅ Acknowledged in {round(inc['response_time'], 1)}s. Awaiting resolution…"
                )
            else:
                if not inc["escalation_sent"] and (time.time() - inc["timestamp"] > 10):
                    mark_escalated(inc)
                    trigger_escalation_alert(inc)
                    status_msg.error("⚠️ No ACK in 10s. Authorities did not act.")
                elif inc["escalation_sent"]:
                    status_msg.error(f"⚠️ ESCALATION active for {inc['id']}")
                else:
                    status_msg.warning(f"🚨 Incident {inc['id']} requires ACK!")
        else:
            status_msg.info("✅ System Normal. No active incidents.")

        # ── Render analytics widgets ────────────────────────────────
        render_alert_banner(alert_ph, alert_level)
        avg = round(tracking["total_sum"] / tracking["frame_num"], 1) if tracking["frame_num"] else 0
        render_stats(stats_ph, total_count, dense_count, tracking["peak_count"], avg)
        render_surge_warning(surge_ph, surge_detected)
        render_zones(zones_ph, boxes, zones)
        render_suggestions(suggest_ph, alert_level)
        render_chart(chart_ph, tracking["count_history"], controls["high_alert"])
        render_incidents(incidents_ph)

        # ── Firebase push ───────────────────────────────────────────
        if firebase_initialized:
            push_status_to_firebase(dense_count, alert_level, zones, surge_detected)

        time.sleep(0.01)

    if not st.session_state.is_running and st.session_state.stop:
        st.info("Analysis stopped.")
