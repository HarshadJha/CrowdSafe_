"""
video_utils.py — Video Source Helpers
======================================
Handles creation and management of :class:`cv2.VideoCapture` objects
for different input sources (local file, IP webcam stream).
"""

import os
import cv2

from app.config import VIDEO_PATH
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


def get_video_capture(source_type: str, ip_url: str | None = None) -> cv2.VideoCapture | None:
    """Create and return an opened :class:`cv2.VideoCapture` for the
    requested *source_type*.

    Parameters
    ----------
    source_type : str
        One of ``"Video File"`` or ``"Live Mobile Camera (IP Stream)"``.
    ip_url : str, optional
        URL of the IP Webcam stream (required for mobile camera).

    Returns
    -------
    cv2.VideoCapture or None
        An opened capture object, or ``None`` on failure.
    """
    try:
        if source_type == "Video File":
            if os.path.exists(VIDEO_PATH):
                logger.info("Opening video file: %s", VIDEO_PATH)
                return cv2.VideoCapture(VIDEO_PATH)
            logger.error("Video file not found: %s", VIDEO_PATH)
            return None

        if source_type == "Live Mobile Camera (IP Stream)":
            if ip_url:
                logger.info("Connecting to IP stream: %s", ip_url)
                cap = cv2.VideoCapture(ip_url)
                if cap.isOpened():
                    return cap
                logger.error("IP stream could not be opened: %s", ip_url)
            return None

    except Exception as exc:
        logger.error("get_video_capture error: %s", exc)

    return None


def release_capture(cap: cv2.VideoCapture | None) -> None:
    """Safely release a :class:`cv2.VideoCapture` if it is not ``None``."""
    if cap is not None:
        cap.release()
        logger.info("Video capture released.")
