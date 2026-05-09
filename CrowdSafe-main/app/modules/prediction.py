"""
prediction.py — Firebase Real-Time Data Push
"""

import datetime
import time

import streamlit as st
import firebase_admin
from firebase_admin import credentials, db

from app.config import FIREBASE_DB_URL, FIREBASE_KEY_PATH
from app.utils.logging_utils import get_logger
import os

logger = get_logger(__name__)


@st.cache_resource
def init_firebase() -> bool:
    """Initialize Firebase Admin SDK (cached, runs only once).

    Returns True on success, False otherwise.
    """
    if FIREBASE_DB_URL == "YOUR_FIREBASE_DB_URL_HERE" or not os.path.exists(FIREBASE_KEY_PATH):
        logger.warning("Firebase not configured — skipping init.")
        return False
    try:
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})
        logger.info("Firebase initialized successfully.")
        return True
    except Exception as exc:
        logger.error("Firebase init failed: %s", exc)
        return False


def push_status_to_firebase(
    dense_count: int,
    alert_level: str,
    zones: dict,
    surge_detected: bool,
) -> None:
    """Push the current crowd status to Firebase (rate-limited to 2 s)."""
    now = time.time()
    if now - st.session_state.get("last_fb_update_time", 0) < 2:
        return
    try:
        db.reference("current_status").set({
            "count": dense_count,
            "status": alert_level,
            "zones": zones,
            "surge": surge_detected,
            "last_update": datetime.datetime.now().isoformat(),
        })
        st.session_state.last_fb_update_time = now
    except Exception as exc:
        logger.error("Firebase push failed: %s", exc)
