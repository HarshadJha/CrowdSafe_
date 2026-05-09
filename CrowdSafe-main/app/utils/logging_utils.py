"""
logging_utils.py — Application-wide Logging Configuration
==========================================================
Provides a pre-configured logger that writes to both **stdout** and
a rotating log file under ``data/logs/``.  Every module should obtain
its logger via::

    from app.utils.logging_utils import get_logger
    logger = get_logger(__name__)
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import PROJECT_ROOT

# ── Log directory & file ───────────────────────────────────────────────
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "crowdsafe.log"

# ── Formatter ──────────────────────────────────────────────────────────
_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"
_formatter = logging.Formatter(_FMT, datefmt=_DATE_FMT)

# ── Shared handlers (created once) ────────────────────────────────────
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(_formatter)

_file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(_formatter)


def get_logger(name: str) -> logging.Logger:
    """Return a pre-configured :class:`logging.Logger` for *name*.

    Parameters
    ----------
    name : str
        Typically ``__name__`` of the calling module.

    Returns
    -------
    logging.Logger
        Logger instance with console + rotating-file handlers attached.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(_console_handler)
        logger.addHandler(_file_handler)
        logger.propagate = False
    return logger
