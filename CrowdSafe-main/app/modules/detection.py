"""
detection.py — YOLOv8 Object Detection Module
===============================================
Wraps the Ultralytics YOLO model for person detection.  The model is
loaded once via Streamlit's ``@st.cache_resource`` and reused across
reruns.
"""

import streamlit as st
from ultralytics import YOLO

from app.config import YOLO_MODEL_PATH
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


@st.cache_resource
def load_yolo_model() -> YOLO | None:
    """Load and cache the YOLOv8 model from disk.

    Returns
    -------
    YOLO or None
        The loaded model, or ``None`` if the file is missing / corrupt.
    """
    try:
        model = YOLO(YOLO_MODEL_PATH)
        logger.info("YOLOv8 model loaded from %s", YOLO_MODEL_PATH)
        return model
    except Exception as exc:
        logger.error("Failed to load YOLO model: %s", exc)
        st.error(f"Failed to load YOLO model: {exc}")
        return None


def run_detection(
    model: YOLO,
    frame,
    confidence: float = 0.4,
    imgsz: int = 640,
) -> list[list[int]]:
    """Run person detection on a single *frame*.

    Parameters
    ----------
    model : YOLO
        Pre-loaded YOLOv8 model.
    frame : np.ndarray
        BGR image.
    confidence : float
        Minimum detection confidence.
    imgsz : int
        Inference image size.

    Returns
    -------
    list[list[int]]
        List of ``[x1, y1, x2, y2]`` bounding boxes for detected persons.
    """
    results = model.predict(
        frame, imgsz=imgsz, conf=confidence, classes=[0], verbose=False
    )
    boxes = [
        list(map(int, b.xyxy[0]))
        for r in results
        for b in r.boxes
        if int(b.cls[0]) == 0
    ]
    return boxes
