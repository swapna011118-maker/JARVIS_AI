"""Web-based entry point for JARVIS.
Runs a local web server with Web Speech API for the best speech recognition.
Open http://localhost:8000 in Chrome/Edge to use.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from Backend.WebServer import app

if __name__ == "__main__":
    print("JARVIS web interface starting on http://localhost:8000")
    print("Open Chrome/Edge and go to http://localhost:8000")
    print("Press Ctrl+C to stop.")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
