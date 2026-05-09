"""
config.py — Centralized Configuration Manager
==============================================
Loads environment variables from ``config/.env`` and exposes all
application constants in one place so that no other module needs
to call ``os.getenv`` directly.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Resolve project root (parent of the ``app/`` package) ──────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Load .env from config/ directory ───────────────────────────────────
_env_path = PROJECT_ROOT / "config" / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    # Fallback: try root-level .env (legacy layout)
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# ===================================================================
#  PATHS
# ===================================================================
VIDEO_PATH: str = str(PROJECT_ROOT / "assets" / "videos" / "local_train.mp4")
YOLO_MODEL_PATH: str = str(PROJECT_ROOT / "assets" / "models" / "yolov8n.pt")
FIREBASE_KEY_PATH: str = os.getenv(
    "FIREBASE_KEY_PATH",
    str(PROJECT_ROOT / "config" / "firebase.json"),
)
INCIDENTS_LOG_PATH: str = str(PROJECT_ROOT / "data" / "incidents.json")

# ===================================================================
#  FIREBASE
# ===================================================================
FIREBASE_DB_URL: str = os.getenv("FIREBASE_DB_URL", "YOUR_FIREBASE_DB_URL_HERE")

# ===================================================================
#  EMAIL ALERTS
# ===================================================================
EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "")
EMAIL_RECEIVER: str = os.getenv("EMAIL_RECEIVER", "")
EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")

# ===================================================================
#  APPLICATION SETTINGS
# ===================================================================
LOCATION_NAME: str = os.getenv("LOCATION_NAME", "")

# Alert-level definitions used throughout the dashboard
ALERT_LEVELS: dict = {
    "SAFE":     {"color": "alert-safe",     "icon": "✅", "multiplier": 0.0},
    "MODERATE": {"color": "alert-moderate", "icon": "⚠️", "multiplier": 0.5},
    "HIGH":     {"color": "alert-high",     "icon": "🔴", "multiplier": 1.0},
    "CRITICAL": {"color": "alert-critical", "icon": "🚨", "multiplier": 1.5},
}

# Pre-defined operator suggestions per alert level
SUGGESTIONS: dict = {
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

# ===================================================================
#  FRAME / DISPLAY DEFAULTS
# ===================================================================
DEFAULT_FRAME_WIDTH: int = 960
DEFAULT_FRAME_HEIGHT: int = 540
HEATMAP_BLUR_KERNEL: tuple = (99, 99)
