"""Launcher for the ACE AMR Fleet Control Streamlit Dashboard.

Usage:
    python run_dashboard.py
"""

import sys
from pathlib import Path
from streamlit.web import cli as stcli


def run():
    app_path = str(Path(__file__).parent / "dashboard" / "app.py")
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.address=localhost",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    run()
