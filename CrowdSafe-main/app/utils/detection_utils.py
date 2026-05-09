"""
detection_utils.py — Low-level Detection Helpers
==================================================
Pure-function utilities used by the higher-level detection and crowd
analysis modules.  These have **no Streamlit dependency** and can be
unit-tested in isolation.
"""

import cv2
import numpy as np

from app.config import HEATMAP_BLUR_KERNEL


def generate_heatmap(frame: np.ndarray, boxes: list[list[int]]) -> np.ndarray:
    """Overlay a JET-coloured density heatmap on *frame*.

    Parameters
    ----------
    frame : np.ndarray
        BGR image from the video feed.
    boxes : list[list[int]]
        List of ``[x1, y1, x2, y2]`` bounding boxes.

    Returns
    -------
    np.ndarray
        Blended frame with the heatmap overlay.
    """
    heat = np.zeros(frame.shape[:2], dtype=np.float32)

    for box in boxes:
        cx = (box[0] + box[2]) // 2
        cy = (box[1] + box[3]) // 2
        cv2.circle(heat, (cx, cy), 60, 1.0, -1)

    heat = cv2.GaussianBlur(heat, HEATMAP_BLUR_KERNEL, 0)
    if heat.max() > 0:
        heat /= heat.max()

    heatmap_color = cv2.applyColorMap(
        (heat * 255).astype(np.uint8), cv2.COLORMAP_JET
    )
    return cv2.addWeighted(frame, 0.6, heatmap_color, 0.4, 0)


def draw_bounding_boxes(
    frame: np.ndarray,
    boxes: list[list[int]],
    in_cluster: list[bool],
) -> np.ndarray:
    """Draw colour-coded bounding boxes on *frame*.

    Boxes belonging to a dense cluster are drawn in **red**; others in
    **green**.

    Parameters
    ----------
    frame : np.ndarray
        BGR image.
    boxes : list[list[int]]
        Bounding-box coordinates.
    in_cluster : list[bool]
        Whether each corresponding box is inside a dense cluster.

    Returns
    -------
    np.ndarray
        Frame with drawn rectangles (modified in-place).
    """
    for i, box in enumerate(boxes):
        color = (0, 0, 255) if in_cluster[i] else (0, 255, 0)
        cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 2)
    return frame
