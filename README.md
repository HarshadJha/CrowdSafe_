# CrowdSafe: Real-Time Crowd Monitoring Dashboard

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red.svg)](https://streamlit.io)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-purple.svg)](https://docs.ultralytics.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An AI-powered real-time crowd detection, density analysis, and alerting dashboard built with **YOLOv8**, **Streamlit**, **Firebase**, and **SMTP**.

---

## 📋 Features

| Feature | Description |
|---|---|
| **YOLO Person Detection** | Real-time person detection using YOLOv8 on video streams |
| **Mobile Camera Support** | Connect your smartphone via IP Webcam for live monitoring |
| **Crowd Density Analysis** | Proximity-based clustering to identify dense zones |
| **Zone Analysis** | Frame split into Left / Center / Right zones with per-zone counts |
| **Surge Detection** | Alerts when crowd count rises rapidly over a sliding window |
| **Heatmap Overlay** | JET-coloured density heatmap rendered on the live feed |
| **Incident Management** | Create, acknowledge, resolve, and escalate incidents |
| **Email Alerts** | Automatic SMTP alerts with escalation on no-ACK |
| **Firebase Integration** | Push real-time status to Firebase Realtime Database |
| **Logging System** | Rotating file + console logs under `data/logs/` |

---

## 🏗️ Project Structure

```
CrowdSafe/
│
├── app/                          # Main application logic
│   ├── main.py                  # Entry point (Streamlit app)
│   ├── config.py                # Centralised config & env loading
│   ├── utils/                   # Helper functions
│   │   ├── email_alert.py       # Async email dispatcher
│   │   ├── video_utils.py       # Video capture factory
│   │   ├── detection_utils.py   # Heatmap & bounding-box helpers
│   │   └── logging_utils.py     # Rotating-file logger
│   │
│   ├── modules/                 # Core system modules
│   │   ├── detection.py         # YOLOv8 model loading & inference
│   │   ├── crowd_analysis.py    # Density, zones, alerts, surge
│   │   ├── alert_system.py      # Email alert composition
│   │   ├── ack_system.py        # Incident lifecycle management
│   │   ├── prediction.py        # Firebase init & data push
│   │   └── iot_simulation.py    # IoT sensor simulator
│   │
│   └── ui/                      # Streamlit UI components
│       ├── dashboard.py         # CSS injection & header
│       ├── controls.py          # Sidebar & source selection
│       └── visualizations.py    # Real-time analytics widgets
│
├── assets/                      # Static files
│   ├── videos/
│   │   └── local_train.mp4
│   └── models/
│       └── yolov8n.pt
│
├── config/                      # Environment & credentials
│   ├── .env                     # Secret keys (git-ignored)
│   └── firebase.json            # Firebase service account key
│
├── data/                        # Runtime data
│   ├── incidents.json
│   └── logs/
│       └── crowdsafe.log
│
├── docs/                        # Documentation
│   ├── firebase_setup_guide.md
│   ├── report/
│   └── diagrams/
│
├── .gitignore
├── requirements.txt
├── README.md
└── run.py                       # Convenience launcher
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Dashboard | Streamlit 1.35 |
| AI / Detection | YOLOv8, PyTorch, OpenCV |
| Backend / DB | Firebase Realtime Database |
| Alerting | SMTP (Gmail) |
| Data | Pandas, NumPy |
| Mobile | IP Webcam App |
| Logging | Python `logging` (rotating file) |

---

## 🚀 Getting Started

### Prerequisites

* Python 3.9+
* Git

### 1. Clone the Repository

```bash
git clone https://github.com/samulya896/CROWDSAFE.git
cd CROWDSAFE
```

### 2. Set Up a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Edit `config/.env` with your credentials:

```env
EMAIL_SENDER=your_email@gmail.com
EMAIL_RECEIVER=authority@email.com
EMAIL_PASSWORD=your_app_password

FIREBASE_KEY_PATH=config/firebase.json
FIREBASE_DB_URL=https://your-project-id.firebaseio.com

LOCATION_NAME=Main Plaza
```

### 5. Add Local Files

1. Place your Firebase service-account JSON at `config/firebase.json`.
2. Place your video file at `assets/videos/local_train.mp4`.
3. The YOLOv8 model is already at `assets/models/yolov8n.pt`.

---

## ▶️ Usage

```bash
# Option 1 — Streamlit directly
streamlit run app/main.py

# Option 2 — Convenience launcher
python run.py
```

---

## 📊 Data Flow

```text
CCTV / Mobile Camera → YOLOv8 → People Count → Firebase
                                                 ↓
Firebase ← Real-time Updates ← Dashboard
                                 ↓
High Crowd / Escalation → Incident Management → Email Alert
```

---

## 📝 License

This project is licensed under the MIT License.
