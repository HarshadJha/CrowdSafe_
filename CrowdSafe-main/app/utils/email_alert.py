"""
email_alert.py — Asynchronous Email Alert Dispatcher
=====================================================
Sends HTML-capable email alerts via Gmail SMTP in a background thread
so that the main Streamlit event loop is never blocked.
"""

import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import EMAIL_SENDER, EMAIL_RECEIVER, EMAIL_PASSWORD
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


def is_email_configured() -> bool:
    """Return ``True`` if all three email credentials are set."""
    return bool(EMAIL_SENDER and EMAIL_RECEIVER and EMAIL_PASSWORD)


def send_email_alert(subject: str, message: str) -> None:
    """Send an email alert asynchronously via Gmail SMTP.

    If the email credentials are not configured the call is silently
    ignored.

    Parameters
    ----------
    subject : str
        Email subject line.
    message : str
        Plain-text body of the email.
    """
    if not is_email_configured():
        logger.warning("Email alert skipped — credentials not configured.")
        return

    def _send() -> None:
        try:
            msg = MIMEMultipart()
            msg["From"] = EMAIL_SENDER
            msg["To"] = EMAIL_RECEIVER
            msg["Subject"] = subject
            msg.attach(MIMEText(message, "plain"))

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.send_message(msg)

            logger.info("Email alert sent: %s", subject)
        except Exception as exc:
            logger.error("Email dispatch failed: %s", exc)

    threading.Thread(target=_send, daemon=True).start()
