"""
admin_dashboard/app.py
=============================================
Orchestrates the Streamlit application for the Admin panel.
"""

import sys
import time
import os
from datetime import datetime
from pathlib import Path
from collections import deque
import threading
import cv2
import streamlit as st

# Ensure project root is on sys.path
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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

# NEW FIREBASE IMPORT
from shared import firebase_client

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

st.set_page_config(page_title="CrowdSafe Dashboard", page_icon="🚨", layout="wide")

_fb_cache = {}

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

inject_css()
render_header()

source_selection = render_source_selector()

if source_selection == "Live Mobile Camera (IP Stream)":
    render_mobile_panel()

st.markdown("---")

controls = render_sidebar_controls()

st.header("⚡ Incident Management")

inc = st.session_state.active_incident

status_msg = st.empty()

if inc:
    if inc.get("resolved"):
        status_msg.success(f"✅ Situation handled by authorities (Incident {inc['id']})")
    elif inc.get("acknowledged"):
        status_msg.success(
            f"✅ Alert acknowledged in {round(inc.get('response_time', 0), 1)} seconds. Awaiting resolution..."
        )
    elif inc.get("escalation_sent"):
        status_msg.error(f"⚠️ No response from authorities! ESCALATION TRIGGERED for {inc['id']}")
    else:
        status_msg.warning(f"🚨 Active Crowd Alert: Incident {inc['id']} requires acknowledgement!")
else:
    status_msg.info("✅ System Normal. No active incidents.")

st.markdown("---")

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

col_start, col_stop = st.columns(2)

if col_start.button(f"🚀 Start {source_selection}", type="primary"):
    st.session_state.is_running = True
    st.session_state.stop = False

if col_stop.button("🛑 Stop Analysis"):
    st.session_state.is_running = False
    st.session_state.stop = True
    release_capture(st.session_state.cap)
    st.session_state.cap = None

if st.session_state.is_running and not st.session_state.stop:
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

        frame = cv2.resize(frame, (960, 540))
        boxes = run_detection(model, frame, controls["confidence"])
        total_count = len(boxes)
        dense_count, in_cluster = analyze_crowd_density(
            boxes, controls["proximity"], controls["cluster_size"]
        )

        draw_bounding_boxes(frame, boxes, in_cluster)
        display = generate_heatmap(frame, boxes) if (controls["show_heatmap"] and boxes) else frame
        
        # Streamlit requires RGB color space
        display_rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(display_rgb, channels="RGB")

        tracking["frame_num"] += 1
        tracking["count_history"].append(dense_count)
        tracking["peak_count"] = max(tracking["peak_count"], dense_count)
        tracking["total_sum"] += dense_count

        alert_level = get_alert_level(dense_count, controls["high_alert"])
        surge_detected = detect_surge(tracking["count_history"])
        zones = analyze_zones(boxes, 960) if boxes else {"Left": 0, "Center": 0, "Right": 0}

        if alert_level in ("HIGH", "CRITICAL"):
            if st.session_state.active_incident is None:
                new_inc = create_incident(alert_level, dense_count)
                
                # Push to Firebase
                alert_data = {
                    "level": alert_level,
                    "count": dense_count,
                    "timestamp": datetime.now().isoformat(),
                    "location": "Main Hall",
                    "risk_score": round((dense_count / 20) * 100, 2),
                    "status": "ACTIVE"
                }
                fb_res = firebase_client.push_alert(alert_data)
                if fb_res and "name" in fb_res:
                    new_inc["firebase_id"] = fb_res["name"]
                
                st.session_state.active_incident = new_inc
                trigger_initial_alert(new_inc)
                st.rerun()

        # Firebase Sync
        current_time = time.time()
        
        # 1. Start the fetch thread every 1 second
        if current_time - st.session_state.last_fb_update_time > 1.0:
            st.session_state.last_fb_update_time = current_time
            if st.session_state.active_incident and "firebase_id" in st.session_state.active_incident:
                fb_id = st.session_state.active_incident["firebase_id"]
                
                def fetch_fb():
                    try:
                        fb_alerts = firebase_client.get_active_alerts()
                        if fb_alerts and fb_id in fb_alerts:
                            _fb_cache[fb_id] = fb_alerts[fb_id].get("status")
                    except Exception:
                        pass
                
                threading.Thread(target=fetch_fb, daemon=True).start()
                
        # 2. Check the cache EVERY FRAME so it responds the millisecond the thread finishes
        if st.session_state.active_incident and "firebase_id" in st.session_state.active_incident:
            fb_id = st.session_state.active_incident["firebase_id"]
            fb_status = _fb_cache.get(fb_id)
            if fb_status == "ACKNOWLEDGED" and not st.session_state.active_incident.get("acknowledged"):
                st.session_state.active_incident = acknowledge_incident(st.session_state.active_incident)
                _fb_cache[fb_id] = None
                st.rerun()
            elif fb_status == "RESOLVED" and not st.session_state.active_incident.get("resolved"):
                resolve_incident(st.session_state.active_incident)
                st.session_state.active_incident = None
                _fb_cache[fb_id] = None
                st.rerun()

        inc = st.session_state.active_incident
        if current_time - st.session_state.get("last_ui_update", 0) > 1.0:
            st.session_state["last_ui_update"] = current_time
            if inc:
                if inc.get("resolved"):
                    status_msg.success(f"✅ Situation handled (Incident {inc['id']})")
                elif inc.get("acknowledged"):
                    status_msg.success(
                        f"✅ Acknowledged in {round(inc.get('response_time', 0), 1)}s. Awaiting resolution…"
                    )
                else:
                    if not inc.get("escalation_sent") and (time.time() - inc.get("timestamp", time.time()) > 30):
                        mark_escalated(inc)
                        trigger_escalation_alert(inc)
                        status_msg.error("⚠️ No ACK in 30s. Authorities did not act.")
                    elif inc.get("escalation_sent"):
                        status_msg.error(f"⚠️ ESCALATION active for {inc['id']}")
                    else:
                        status_msg.warning(f"🚨 Incident {inc['id']} requires ACK!")
            else:
                status_msg.info("✅ System Normal. No active incidents.")

            render_alert_banner(alert_ph, alert_level)
            avg = round(tracking["total_sum"] / tracking["frame_num"], 1) if tracking["frame_num"] else 0
            render_stats(stats_ph, total_count, dense_count, tracking["peak_count"], avg)
            render_surge_warning(surge_ph, surge_detected)
            render_zones(zones_ph, boxes, zones)
            render_suggestions(suggest_ph, alert_level)
            render_chart(chart_ph, tracking["count_history"], controls["high_alert"])
            render_incidents(incidents_ph)

        time.sleep(0.01)

    if not st.session_state.is_running and st.session_state.stop:
        st.info("Analysis stopped.")
