"""
alert_system.py — Alert Dispatch & Escalation Logic
"""

from app.config import LOCATION_NAME
from app.utils.email_alert import send_email_alert
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


def trigger_initial_alert(incident: dict) -> None:
    """Send the first email notification for a new incident."""
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
    logger.info("Initial alert dispatched for incident %s", incident["id"])


def trigger_escalation_alert(incident: dict) -> None:
    """Send an escalation email when an incident goes unacknowledged."""
    message = (
        f"⚠️ ESCALATION ALERT\n\n"
        f"Incident ID : {incident['id']}\n"
        f"No acknowledgement received for 10 seconds.\n"
        f"Alert Level : {incident['alert_level']}\n"
        f"Location    : {LOCATION_NAME}\n"
        f"Time        : {incident['timestamp_str']}\n\n"
        f"Immediate action is required!"
    )
    send_email_alert(f"⚠️ ESCALATION: No ACK for {incident['id']}", message)
    logger.warning("Escalation alert sent for incident %s", incident["id"])
