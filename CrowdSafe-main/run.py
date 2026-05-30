"""
run.py — Optional Launcher Script
===================================
Allows running the project from the project root via:
    python run.py
"""

import subprocess
import sys
from pathlib import Path

ENTRY_POINT = Path(__file__).parent / "app" / "main.py"


def main():
    """Launch the Streamlit application."""
    cmd = [sys.executable, "-m", "streamlit", "run", str(ENTRY_POINT)]
    print(f"Starting CrowdSafe AI Dashboard …")
    print(f"   Command: {' '.join(cmd)}\n")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
