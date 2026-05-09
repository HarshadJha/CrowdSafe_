"""
crowd_analysis.py — Crowd Density & Zone Analysis
===================================================
Provides functions for:

* **Density clustering** — determining which detections are inside a
  dense cluster based on pairwise proximity.
* **Zone analysis** — splitting the frame into three vertical zones
  (Left / Center / Right) and counting detections per zone.
* **Alert-level classification** — mapping dense-count to a severity
  string.
* **Surge detection** — identifying rapid crowd-count increases over
  a sliding window.
"""

from math import sqrt

from app.config import DEFAULT_FRAME_WIDTH


def analyze_crowd_density(
    boxes: list[list[int]],
    proximity_threshold: int = 50,
    cluster_threshold: int = 3,
) -> tuple[int, list[bool]]:
    """Classify each detection as *in-cluster* or not.

    Two people are considered neighbours if the Euclidean distance
    between their bounding-box centres is below *proximity_threshold*.
    A person is *in-cluster* when their neighbour count reaches
    *cluster_threshold*.

    Parameters
    ----------
    boxes : list[list[int]]
        ``[x1, y1, x2, y2]`` bounding boxes.
    proximity_threshold : int
        Maximum pixel distance for two centres to be neighbours.
    cluster_threshold : int
        Minimum neighbour count to be flagged as dense.

    Returns
    -------
    tuple[int, list[bool]]
        ``(dense_count, in_cluster)`` — total number of people in
        dense clusters and a per-box boolean mask.
    """
    centres = [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for b in boxes]
    n = len(centres)
    if n < 2:
        return 0, [False] * n

    neighbour_counts = [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            dist = sqrt(
                (centres[i][0] - centres[j][0]) ** 2
                + (centres[i][1] - centres[j][1]) ** 2
            )
            if dist < proximity_threshold:
                neighbour_counts[i] += 1
                neighbour_counts[j] += 1

    in_cluster = [c >= cluster_threshold for c in neighbour_counts]
    return sum(in_cluster), in_cluster


def analyze_zones(
    boxes: list[list[int]], frame_width: int = DEFAULT_FRAME_WIDTH
) -> dict[str, int]:
    """Count detections per spatial zone (Left / Center / Right).

    The frame is divided into three equal-width vertical strips.

    Parameters
    ----------
    boxes : list[list[int]]
        Bounding boxes.
    frame_width : int
        Width of the video frame in pixels.

    Returns
    -------
    dict[str, int]
        Mapping of zone name → person count.
    """
    zone_width = frame_width // 3
    zones: dict[str, int] = {"Left": 0, "Center": 0, "Right": 0}
    for box in boxes:
        cx = (box[0] + box[2]) // 2
        if cx < zone_width:
            zones["Left"] += 1
        elif cx < zone_width * 2:
            zones["Center"] += 1
        else:
            zones["Right"] += 1
    return zones


def get_alert_level(dense_count: int, threshold: int) -> str:
    """Map a dense-person count to an alert-level string.

    Parameters
    ----------
    dense_count : int
        Number of people currently inside a dense cluster.
    threshold : int
        The *high* alert threshold set by the operator.

    Returns
    -------
    str
        One of ``"SAFE"``, ``"MODERATE"``, ``"HIGH"``, ``"CRITICAL"``.
    """
    if dense_count >= threshold * 1.5:
        return "CRITICAL"
    if dense_count >= threshold:
        return "HIGH"
    if dense_count >= threshold * 0.5:
        return "MODERATE"
    return "SAFE"


def detect_surge(
    count_history, window: int = 5, rate_threshold: int = 3
) -> bool:
    """Return ``True`` if the crowd count is rising rapidly.

    Computes the average per-frame increase over the last *window*
    data-points and compares it against *rate_threshold*.

    Parameters
    ----------
    count_history : collections.deque
        Recent dense-count values.
    window : int
        Number of recent values to consider.
    rate_threshold : int
        Minimum average increase to flag a surge.

    Returns
    -------
    bool
    """
    if len(count_history) < window:
        return False
    recent = list(count_history)[-window:]
    avg_increase = (recent[-1] - recent[0]) / max(window - 1, 1)
    return avg_increase >= rate_threshold
