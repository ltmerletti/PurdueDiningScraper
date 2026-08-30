#!/usr/bin/env python3
"""
Main entry point for Purdue Dining Scraper & Nutrition Intelligence CLI.
"""
import os
import sys

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from purdue_menu.cli import main

if __name__ == "__main__":
    main()



