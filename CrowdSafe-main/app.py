import streamlit as st
import cv2
import numpy as np
from ultralytics import YOLO
import time
import datetime
import firebase_admin
from firebase_admin import credentials, db
from math import sqrt
import os
import pandas as pd
import random
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
from collections import deque


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Page Configuration ---
st.set_page_config(
    page_title="CrowdSafe Dashboard",
    page_icon="🚨",
    layout="wide"
)

# --- State Initialization ---
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'stop' not in st.session_state:
    st.session_state.stop = False
if 'incident_log' not in st.session_state:
    st.session_state.incident_log = []
if 'active_incident' not in st.session_state:
    st.session_state.active_incident = None
if 'cap' not in st.session_state:
    st.session_state.cap = None
if 'model' not in st.session_state:
    st.session_state.model = None
if 'tracking' not in st.session_state:
    st.session_state.tracking = {
        'count_history': deque(maxlen=100),
        'peak_count': 0,
        'total_sum': 0,
        'frame_num': 0
    }
if 'last_fb_update_time' not in st.session_state:
    st.session_state.last_fb_update_time = time.time()
if 'mobile_url' not in st.session_state:
    st.session_state.mobile_url = ""
if 'mobile_connected' not in st.session_state:
    st.session_state.mobile_connected = False

# --- Custom CSS ---
st.markdown("""
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
""", unsafe_allow_html=True)

# --- Configuration ---
VIDEO_PATH = "local_train.mp4"
FIREBASE_KEY_PATH = "firebase-credentials.json"
LOCATION_NAME = ""
FIREBASE_DB_URL = "YOUR_FIREBASE_DB_URL_HERE"

EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

ALERT_LEVELS = {
    "SAFE":     {"color": "alert-safe",     "icon": "✅", "multiplier": 0.0},
    "MODERATE": {"color": "alert-moderate", "icon": "⚠️", "multiplier": 0.5},
    "HIGH":     {"color": "alert-high",     "icon": "🔴", "multiplier": 1.0},
    "CRITICAL": {"color": "alert-critical", "icon": "🚨", "multiplier": 1.5},
}

SUGGESTIONS = {
    "HIGH": [
        "📢 Deploy additional security personnel to the area",
        "🚪 Open additional exit gates to improve crowd flow",
        "📡 Increase monitoring frequency on adjacent zones",
    ],
    "CRITICAL": [
        "🚨 Immediately redirect crowd to less dense zones",
        "🚪 Open ALL emergency exits now",
        "📞 Alert local law enforcement and medical teams",
        "🔊 Activate public announcement system for crowd dispersal",
        "🚧 Set up physical barriers to control crowd movement",
    ],
}

# ==========================================
#  SERVICE INITIALIZATION
# ==========================================
@st.cache_resource
def init_firebase():
    if FIREBASE_DB_URL == "YOUR_FIREBASE_DB_URL_HERE" or not os.path.exists(FIREBASE_KEY_PATH):
        return False
    try:
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
        return True
    except Exception as e:
        return False

@st.cache_resource
def load_yolo_model():
    try:
        return YOLO("yolov8n.pt")
    except Exception as e:
        st.error(f"Failed to load YOLO model: {e}")
        return None

# ==========================================
#  CORE FUNCTIONS
# ==========================================

def get_video_capture(source_type, ip_url=None):
    """Modular video source initializer. Returns a cv2.VideoCapture or None."""
    try:
        if source_type == "Video File":
            if os.path.exists(VIDEO_PATH):
                return cv2.VideoCapture(VIDEO_PATH)
            return None
        elif source_type == "Live Mobile Camera (IP Stream)":
            if ip_url:
                cap = cv2.VideoCapture(ip_url)
                return cap if cap.isOpened() else None
            return None
    except Exception:
        return None
    return None

def get_alert_level(dense_count, threshold):
    if dense_count >= threshold * 1.5: return "CRITICAL"
    elif dense_count >= threshold: return "HIGH"
    elif dense_count >= threshold * 0.5: return "MODERATE"
    return "SAFE"

def render_alert_banner(level):
    info = ALERT_LEVELS[level]
    st.markdown(f"<div class='{info['color']}'>{info['icon']} Alert Level: {level}</div>", unsafe_allow_html=True)

def detect_surge(count_history, window=5, rate_threshold=3):
    if len(count_history) < window: return False
    recent = list(count_history)[-window:]
    avg_increase = (recent[-1] - recent[0]) / max(window - 1, 1)
    return avg_increase >= rate_threshold

def generate_heatmap(frame, boxes):
    heat = np.zeros(frame.shape[:2], dtype=np.float32)
    for box in boxes:
        cx, cy = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2
        cv2.circle(heat, (cx, cy), 60, 1.0, -1)
    heat = cv2.GaussianBlur(heat, (99, 99), 0)
    if heat.max() > 0: heat = heat / heat.max()
    heatmap_color = cv2.applyColorMap((heat * 255).astype(np.uint8), cv2.COLORMAP_JET)
    return cv2.addWeighted(frame, 0.6, heatmap_color, 0.4, 0)

def create_incident(level, crowd_count):
    incident = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": time.time(),
        "timestamp_str": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "crowd_count": crowd_count,
        "alert_level": level,
        "acknowledged": False,
        "ack_time": None,
        "response_time": None,
        "resolved": False,
        "resolution_time": None,
        "escalation_sent": False,
        "location": LOCATION_NAME
    }
    st.session_state.incident_log.insert(0, incident)
    st.session_state.incident_log = st.session_state.incident_log[:50]
    return incident

def analyze_zones(boxes, frame_width):
    zone_width = frame_width // 3
    zones = {"Left": 0, "Center": 0, "Right": 0}
    for box in boxes:
        cx = (box[0] + box[2]) // 2
        if cx < zone_width: zones["Left"] += 1
        elif cx < zone_width * 2: zones["Center"] += 1
        else: zones["Right"] += 1
    return zones

def analyze_crowd_density(boxes, proximity_threshold, cluster_threshold):
    centers = [((box[0] + box[2]) / 2, (box[1] + box[3]) / 2) for box in boxes]
    num_people = len(centers)
    if num_people < 2: return 0, [False] * num_people
    neighbor_counts = [0] * num_people
    for i in range(num_people):
        for j in range(i + 1, num_people):
            dist = sqrt((centers[i][0] - centers[j][0])**2 + (centers[i][1] - centers[j][1])**2)
            if dist < proximity_threshold:
                neighbor_counts[i] += 1
                neighbor_counts[j] += 1
    in_cluster = [count >= cluster_threshold for count in neighbor_counts]
    return sum(in_cluster), in_cluster

def send_email_alert(subject, message):
    if not EMAIL_SENDER or not EMAIL_RECEIVER or not EMAIL_PASSWORD:
        return
    def send():
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_SENDER
            msg['To'] = EMAIL_RECEIVER
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            print(f"Email Error: {e}")
    threading.Thread(target=send).start()

def trigger_initial_alert(incident):
    message = (
        f"🚨 CROWDSAFE ALERT\n\n"
        f"Incident ID : {incident['id']}\n"
        f"Alert Level : {incident['alert_level']}\n"
        f"Location    : {LOCATION_NAME}\n"
        f"Crowd Count : {incident['crowd_count']}\n"
        f"Time        : {incident['timestamp_str']}\n\n"
        f"Please log in to the dashboard to acknowledge and resolve this alert."
    )
    send_email_alert(f"🚨 CrowdSafe Initial Alert: {LOCATION_NAME}", message)


# ==========================================
#  MAIN APPLICATION UI
# ==========================================

st.markdown("<div class='dashboard-title'>🚨 CrowdSafe AI Dashboard</div>", unsafe_allow_html=True)
st.markdown(f"<div class='dashboard-subtitle'>Real-Time Crowd Monitoring {LOCATION_NAME}</div>", unsafe_allow_html=True)
st.markdown("")

source_selection = st.selectbox("**Select Data Source**", (
    "Live Mobile Camera (IP Stream)",
    "Video File"
))

# --- Mobile Camera (IP Webcam) Panel ---
if source_selection == "Live Mobile Camera (IP Stream)":
    st.info("📱 Mobile Camera Sync Activated")

    st.markdown("""
    **How to connect your smartphone camera:**
    1. Connect your phone and laptop to the **same Wi-Fi network**.
    2. Download the **"IP Webcam"** app from the Google Play Store or iOS App Store.
    3. Open the app, scroll to the bottom, and tap **"Start server"**.
    4. An IPv4 address will appear on your phone screen (e.g., `http://192.168.1.5:8080`).
    5. Enter that exact URL below, adding `/video` at the end.
    """)

    ip_input = st.text_input(
        "✏️ Mobile Camera Stream URL:",
        value=st.session_state.mobile_url or "http://192.168.x.x:8080/video",
        placeholder="http://192.168.1.5:8080/video"
    )
    st.session_state.mobile_url = ip_input

    # Connection status indicator
    if st.session_state.mobile_connected:
        st.success("📡 Mobile Camera Connected")
    elif st.session_state.is_running:
        st.error("❌ Camera not reachable — check URL and Wi-Fi")

st.markdown("---")

# --- Sidebar Controls ---
st.sidebar.header("🔧 Control Panel")
confidence_threshold = st.sidebar.slider("Detection Confidence", 0.0, 1.0, 0.4, 0.05)
st.sidebar.markdown("---")
st.sidebar.subheader("Density Settings")
proximity_threshold = st.sidebar.slider("Proximity Threshold (px)", 10, 150, 50, 5)
cluster_size_threshold = st.sidebar.slider("Cluster Size (neighbors)", 1, 10, 3, 1)
high_alert_threshold = st.sidebar.slider("High Density Alert Trigger", 5, 50, 10, 1)

st.sidebar.markdown("---")
st.sidebar.subheader("Heatmap")
show_heatmap = st.sidebar.checkbox("Enable Heatmap Overlay", value=True)

firebase_initialized = init_firebase()
email_configured = bool(EMAIL_SENDER and EMAIL_RECEIVER and EMAIL_PASSWORD)
st.sidebar.markdown("---")
# st.sidebar.info("Firebase: " + ("✅ Connected" if firebase_initialized else "❌ Not Configured"))
# st.sidebar.info("Email Alerts: " + ("✅ Configured" if email_configured else "❌ Not Configured"))


# --- INCIDENT MANAGEMENT PANEL (NEW) ---
st.header("⚡ Incident Management")

inc = st.session_state.active_incident

col_a, col_r = st.columns(2)
ack_disabled = not (inc and not inc['acknowledged'])
res_disabled = not (inc and inc['acknowledged'] and not inc['resolved'])

if col_a.button("✅ Acknowledge Alert", disabled=ack_disabled, use_container_width=True):
    if inc:
        inc['acknowledged'] = True
        inc['ack_time'] = time.time()
        inc['response_time'] = inc['ack_time'] - inc['timestamp']
        st.session_state.active_incident = inc
        for i, item in enumerate(st.session_state.incident_log):
            if item['id'] == inc['id']:
                st.session_state.incident_log[i] = inc
                break
        st.rerun()

if col_r.button("✔️ Mark as Resolved", disabled=res_disabled, use_container_width=True):
    if inc:
        inc['resolved'] = True
        inc['resolution_time'] = time.time()
        for i, item in enumerate(st.session_state.incident_log):
            if item['id'] == inc['id']:
                st.session_state.incident_log[i] = inc
                break
        st.session_state.active_incident = None 
        st.rerun()

status_msg_placeholder = st.empty()

if inc:
    if inc['resolved']:
        status_msg_placeholder.success(f"✅ Situation handled by authorities (Incident {inc['id']})")
    elif inc['acknowledged']:
        status_msg_placeholder.success(f"✅ Alert acknowledged in {round(inc['response_time'], 1)} seconds. Awaiting resolution...")
    elif inc['escalation_sent']:
        status_msg_placeholder.error(f"⚠️ No response from authorities! ESCALATION TRIGGERED for {inc['id']}")
    else:
        status_msg_placeholder.warning(f"🚨 Active Crowd Alert: Incident {inc['id']} requires acknowledgement!")
else:
    status_msg_placeholder.info("✅ System Normal. No active incidents.")

st.markdown("---")

# --- Dashboard Layout ---
col_feed, col_stats = st.columns([3, 2])

with col_feed:
    st.header("📹 Live Feed")
    frame_placeholder = st.empty()

with col_stats:
    st.header("📊 Real-Time Analytics")
    alert_banner_placeholder = st.empty()
    stats_placeholder = st.empty()
    surge_placeholder = st.empty()
    zones_placeholder = st.empty()
    suggestions_placeholder = st.empty()

st.markdown("---")
col_chart, col_incidents = st.columns([3, 2])

with col_chart:
    st.header("📈 Crowd Trend")
    chart_placeholder = st.empty()

with col_incidents:
    st.header("📋 Recent Incidents")
    incidents_placeholder = st.empty()

# --- Start/Stop Controls ---
col_start, col_stop = st.columns(2)
start_label = f"🚀 Start {source_selection}"
if col_start.button(start_label, type="primary"):
    st.session_state.is_running = True
    st.session_state.stop = False

if col_stop.button('🛑 Stop Analysis'):
    st.session_state.is_running = False
    st.session_state.stop = True
    if st.session_state.cap:
        st.session_state.cap.release()
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
                st.error("❌ Cannot connect to mobile camera. Verify the IP URL and that both devices are on the same Wi-Fi.")
            elif source_selection == "Video File":
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
        if source_selection in ("Live Mobile Camera (IP Stream)", "Video File"):
            # --- Guard: cap must be open ---
            if not cap or not cap.isOpened():
                # Auto-reconnect for mobile camera
                if source_selection == "Live Mobile Camera (IP Stream)" and reconnect_attempts < MAX_RECONNECT:
                    reconnect_attempts += 1
                    frame_placeholder.warning(f"⚠️ Connection lost — reconnecting ({reconnect_attempts}/{MAX_RECONNECT})…")
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
                # For other sources or max retries exceeded — stop
                st.session_state.mobile_connected = False
                break

            ret, frame = cap.read()
            if not ret:
                # Auto-reconnect on frame-read failure for mobile
                if source_selection == "Live Mobile Camera (IP Stream)" and reconnect_attempts < MAX_RECONNECT:
                    reconnect_attempts += 1
                    frame_placeholder.warning(f"⚠️ Frame lost — reconnecting ({reconnect_attempts}/{MAX_RECONNECT})…")
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

            # Reset reconnect counter on successful read
            reconnect_attempts = 0

            # Resize for performance
            frame = cv2.resize(frame, (960, 540))
            results = model.predict(frame, imgsz=640, conf=confidence_threshold, classes=[0], verbose=False)
            boxes = [list(map(int, b.xyxy[0])) for r in results for b in r.boxes if int(b.cls[0]) == 0]
            total_count = len(boxes)
            dense_count, in_cluster = analyze_crowd_density(boxes, proximity_threshold, cluster_size_threshold)

            for i, box in enumerate(boxes):
                color = (0, 0, 255) if in_cluster[i] else (0, 255, 0)
                cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 2)

            display_frame = generate_heatmap(frame, boxes) if (show_heatmap and boxes) else frame
            frame_placeholder.image(display_frame, channels="BGR")

        # Update Tracking State
        tracking['frame_num'] += 1
        tracking['count_history'].append(dense_count)
        tracking['peak_count'] = max(tracking['peak_count'], dense_count)
        tracking['total_sum'] += dense_count

        alert_level = get_alert_level(dense_count, high_alert_threshold)
        surge_detected = detect_surge(tracking['count_history'])
        zones = analyze_zones(boxes, 960) if boxes else {"Left": 0, "Center": 0, "Right": 0}
        most_crowded_zone = max(zones, key=zones.get) if zones else "Center"

        # INCIDENT & ESCALATION LOGIC
        if alert_level in ("HIGH", "CRITICAL"):
            if st.session_state.active_incident is None:
                inc = create_incident(alert_level, dense_count)
                st.session_state.active_incident = inc
                trigger_initial_alert(inc)
                st.rerun() # Refresh to enable action buttons

        inc = st.session_state.active_incident
        if inc:
            if inc['resolved']:
                status_msg_placeholder.success(f"✅ Situation handled by authorities (Incident {inc['id']})")
            elif inc['acknowledged']:
                status_msg_placeholder.success(f"✅ Alert acknowledged in {round(inc['response_time'], 1)} seconds. Awaiting resolution...")
            else:
                if not inc['escalation_sent'] and (time.time() - inc['timestamp'] > 10):
                    inc['escalation_sent'] = True
                    message = (
                        f"⚠️ ESCALATION ALERT\n\n"
                        f"Incident ID : {inc['id']}\n"
                        f"No acknowledgement received for 10 seconds.\n"
                        f"Alert Level : {inc['alert_level']}\n"
                        f"Location    : {LOCATION_NAME}\n"
                        f"Time        : {inc['timestamp_str']}\n\n"
                        f"Immediate action is required!"
                    )
                    send_email_alert(f"⚠️ ESCALATION: No ACK for {inc['id']}", message)
                    for i, item in enumerate(st.session_state.incident_log):
                        if item['id'] == inc['id']:
                            st.session_state.incident_log[i] = inc
                            break
                    status_msg_placeholder.error("⚠️ No acknowledgement received in 10 seconds. Authorities did not act.")
                elif inc['escalation_sent']:
                    status_msg_placeholder.error(f"⚠️ No response from authorities! ESCALATION TRIGGERED for {inc['id']}")
                else:
                    status_msg_placeholder.warning(f"🚨 Active Crowd Alert: Incident {inc['id']} requires acknowledgement!")
        else:
            status_msg_placeholder.info("✅ System Normal. No active incidents.")

        # UPDATE UI PLACEHOLDERS
        with alert_banner_placeholder.container():
            render_alert_banner(alert_level)

        with stats_placeholder.container():
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("👥 Total", total_count)
            c2.metric("🔴 Dense", dense_count)
            c3.metric("📈 Peak", tracking['peak_count'])
            avg_count = round(tracking['total_sum'] / tracking['frame_num'], 1) if tracking['frame_num'] > 0 else 0
            c4.metric("📊 Avg", avg_count)

        with surge_placeholder.container():
            if surge_detected:
                st.markdown("<div class='surge-warning'>⚡ SURGE INCOMING — Crowd count rising rapidly!</div>", unsafe_allow_html=True)

        with zones_placeholder.container():
            if boxes:
                st.markdown("**🗺️ Zone Density**")
                z1, z2, z3 = st.columns(3)
                zone_icons = {"Left": "⬅️", "Center": "⏺️", "Right": "➡️"}
                for col, (zone_name, zone_count) in zip([z1, z2, z3], zones.items()):
                    highlight = "🔴 " if zone_name == most_crowded_zone and zone_count > 0 else ""
                    col.metric(f"{zone_icons[zone_name]} {zone_name}", f"{highlight}{zone_count}")

        with suggestions_placeholder.container():
            if alert_level in ("HIGH", "CRITICAL"):
                st.markdown("**💡 Recommended Actions**")
                for suggestion in SUGGESTIONS.get(alert_level, []):
                    st.markdown(f"<div class='suggestion-box'>{suggestion}</div>", unsafe_allow_html=True)

        with chart_placeholder.container():
            if len(tracking['count_history']) > 1:
                chart_df = pd.DataFrame({
                    "Crowd Count": list(tracking['count_history']),
                    "Threshold": [high_alert_threshold] * len(tracking['count_history'])
                })
                st.line_chart(chart_df, use_container_width=True)

        with incidents_placeholder.container():
            logs = st.session_state.get('incident_log', [])
            if logs:
                for inc_log in logs[:8]:
                    level_emoji = "🔴" if inc_log['alert_level'] == "HIGH" else "🚨"
                    
                    status_text = ""
                    if inc_log.get('resolved'): status_text = " [RESOLVED ✔️]"
                    elif inc_log.get('acknowledged'): status_text = " [ACKNOWLEDGED ✅]"
                    elif inc_log.get('escalation_sent'): status_text = " [ESCALATED ⚠️]"
                    
                    st.markdown(
                        f"<div class='incident-row'>"
                        f"{level_emoji} <strong>{inc_log['alert_level']}</strong> — "
                        f"Count: {inc_log['crowd_count']} — "
                        f"{inc_log['timestamp_str']}{status_text}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.success("No incidents recorded yet.")

        # Firebase Update
        if time.time() - st.session_state.last_fb_update_time > 2 and firebase_initialized:
            try:
                db.reference('current_status').set({
                    'count': dense_count,
                    'status': alert_level,
                    'zones': zones,
                    'surge': surge_detected,
                    'last_update': datetime.datetime.now().isoformat()
                })
                st.session_state.last_fb_update_time = time.time()
            except Exception:
                pass

        time.sleep(0.01)

    if not st.session_state.is_running and st.session_state.stop:
        st.info("Analysis stopped.")