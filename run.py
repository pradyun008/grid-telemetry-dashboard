"""Launcher for the Grid Telemetry Dashboard.

Run from the project root:

    python run.py

Then open http://127.0.0.1:8000 in a browser (this script tries to open
it for you). Stop the server with Ctrl+C.
"""

import threading
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def _open_browser():
    # give uvicorn a moment to bind the port before opening the page
    threading.Timer(1.2, lambda: webbrowser.open(URL)).start()


if __name__ == "__main__":
    print(f"\n  Grid Telemetry Dashboard -> {URL}")
    print("  Press Ctrl+C to stop.\n")
    _open_browser()
    uvicorn.run("src.server:app", host=HOST, port=PORT, log_level="info")
