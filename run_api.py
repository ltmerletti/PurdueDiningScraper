#!/usr/bin/env python3
"""
Entry point for running the API server.
"""
import uvicorn
from src.purdue_menu.api import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


