"""
ack_system.py — Incident Lifecycle Management
"""

import time
import datetime
import uuid

import streamlit as st

from app.config import LOCATION_NAME
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

MAX_INCIDENTS = 50  # Rolling incident log cap


def create_incident(level: str, crowd_count: int) -> dict:
    """Create a new incident record and prepend it to session state.

    Returns the newly created incident dict.
    """
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
        "location": LOCATION_NAME,
    }
    st.session_state.incident_log.insert(0, incident)
    st.session_state.incident_log = st.session_state.incident_log[:MAX_INCIDENTS]
    logger.info("Incident %s created — level=%s, count=%d", incident["id"], level, crowd_count)
    return incident


def acknowledge_incident(incident: dict) -> dict:
    """Mark *incident* as acknowledged and compute response time."""
    incident["acknowledged"] = True
    incident["ack_time"] = time.time()
    incident["response_time"] = incident["ack_time"] - incident["timestamp"]
    _sync_to_log(incident)
    logger.info("Incident %s acknowledged in %.1fs", incident["id"], incident["response_time"])
    return incident


def resolve_incident(incident: dict) -> dict:
    """Mark *incident* as resolved."""
    incident["resolved"] = True
    incident["resolution_time"] = time.time()
    _sync_to_log(incident)
    logger.info("Incident %s resolved", incident["id"])
    return incident


def mark_escalated(incident: dict) -> dict:
    """Flag *incident* as escalated (no ACK received in time)."""
    incident["escalation_sent"] = True
    _sync_to_log(incident)
    logger.warning("Incident %s escalated", incident["id"])
    return incident


def _sync_to_log(incident: dict) -> None:
    """Sync updated incident back into ``st.session_state.incident_log``."""
    for i, item in enumerate(st.session_state.incident_log):
        if item["id"] == incident["id"]:
            st.session_state.incident_log[i] = incident
            break
