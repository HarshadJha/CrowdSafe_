import requests
import json
from config.settings import FIREBASE_URL

def get_db_url(path):
    # Strip trailing slashes
    base = FIREBASE_URL.rstrip('/')
    return f"{base}/{path}.json"

def push_alert(alert_data):
    """Pushes a new alert to Firebase and returns its ID."""
    if "your-project-id" in FIREBASE_URL:
        print("WARNING: Firebase URL not configured. Using Mock.")
        return None
        
    try:
        res = requests.post(get_db_url("alerts"), json=alert_data)
        return res.json()
    except Exception as e:
        print(f"Firebase Error: {e}")
        return None

def update_alert_status(alert_id, status):
    """Updates the status of a specific alert."""
    if "your-project-id" in FIREBASE_URL: return None
    try:
        res = requests.patch(get_db_url(f"alerts/{alert_id}"), json={"status": status})
        return res.json()
    except Exception as e:
        print(f"Firebase Error: {e}")
        return None

def get_active_alerts():
    """Gets all alerts from Firebase."""
    if "your-project-id" in FIREBASE_URL: return {}
    try:
        res = requests.get(get_db_url("alerts"))
        if res.status_code == 200 and res.json():
            return res.json()
    except Exception as e:
        print(f"Firebase Error: {e}")
    return {}
