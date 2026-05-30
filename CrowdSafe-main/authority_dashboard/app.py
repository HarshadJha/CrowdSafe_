import streamlit as st
import time
import sys
import os
import base64
from streamlit_autorefresh import st_autorefresh

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared import firebase_client
from config.settings import SIREN_SOUND_PATH

st.set_page_config(page_title="Authority Dashboard", layout="wide")

# Autorefresh every 1 second
st_autorefresh(interval=1000, key="data_refresh")

st.markdown("""
<style>
.emergency-banner { background-color: #FF0000; color: white; text-align: center; padding: 20px; font-size: 40px; font-weight: bold; animation: blinker 1s linear infinite; border-radius: 10px;}
@keyframes blinker { 50% { opacity: 0; } }
.incident-card { background-color: #1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 10px solid #FF4500; }
.safe-banner { background-color: #006400; color: white; text-align: center; padding: 20px; font-size: 30px; font-weight: bold; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

st.title("🚨 Emergency Response Authority Dashboard")

import threading
from playsound import playsound

_siren_playing = False

def play_siren_bg():
    global _siren_playing
    while _siren_playing:
        try:
            playsound(SIREN_SOUND_PATH, block=True)
        except Exception:
            import time
            time.sleep(1)

def start_siren():
    global _siren_playing
    if not _siren_playing:
        _siren_playing = True
        threading.Thread(target=play_siren_bg, daemon=True).start()

def stop_siren():
    global _siren_playing
    _siren_playing = False

def ack_callback(aid):
    firebase_client.update_alert_status(aid, "ACKNOWLEDGED")

def res_callback(aid):
    firebase_client.update_alert_status(aid, "RESOLVED")

alerts = firebase_client.get_active_alerts()
active_alerts = {k: v for k, v in alerts.items() if v.get('status') in ['ACTIVE', 'ACKNOWLEDGED']}

if not active_alerts:
    stop_siren()
    st.markdown('<div class="safe-banner">✅ ALL CLEAR. No active incidents.</div>', unsafe_allow_html=True)
else:
    # Check if any is ACTIVE (unacknowledged)
    has_unacknowledged = any(a.get('status') == 'ACTIVE' for a in active_alerts.values())
    if has_unacknowledged:
        st.markdown('<div class="emergency-banner">CRITICAL INCIDENT IN PROGRESS</div>', unsafe_allow_html=True)
        start_siren()
    else:
        stop_siren()
        st.warning("⚠️ Incidents are being managed (Acknowledged)")

    st.write("---")
    st.subheader("Active Incidents List")
    
    for aid, alert in reversed(list(active_alerts.items())):
        st.markdown(f"""
        <div class="incident-card">
            <h2 style='margin-top: 0;'>Level: {alert['level']} Alert</h2>
            <p><strong>Location:</strong> {alert.get('location', 'Unknown')}</p>
            <p><strong>Crowd Count:</strong> {alert.get('count', 0)} people (Risk Score: {alert.get('risk_score', 0)}%)</p>
            <p><strong>Time Detected:</strong> {alert.get('timestamp', 'N/A')}</p>
            <p><strong>Current Status:</strong> <span style='color: {"red" if alert['status'] == "ACTIVE" else "orange"};'>{alert['status']}</span></p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if alert['status'] == 'ACTIVE':
                st.button(f"🛡️ Acknowledge Incident", key=f"ack_{aid}", use_container_width=True, on_click=ack_callback, args=(aid,))
        
        with col2:
            if alert['status'] in ['ACTIVE', 'ACKNOWLEDGED']:
                st.button(f"✅ Mark as Resolved", key=f"res_{aid}", use_container_width=True, on_click=res_callback, args=(aid,))
        st.markdown("<hr>", unsafe_allow_html=True)
