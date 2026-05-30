import os

# Firebase Realtime Database URL
# Go to Firebase Console -> Realtime Database -> Create -> Start in Test Mode
# Replace the URL below with your actual database URL
FIREBASE_URL = os.getenv("FIREBASE_URL", "https://crowdsafe-32381-default-rtdb.firebaseio.com/")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "models", "yolov8n.pt")
SIREN_SOUND_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "sounds", "siren.mp3")
