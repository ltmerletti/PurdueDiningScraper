#!/usr/bin/env python3
"""
Purdue Dining FastMCP Server entrypoint.
Runs the Model Context Protocol server over stdio for Claude Desktop, Claude Code, Cursor, and LM Studio.
"""
import os
import sys

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from purdue_menu.mcp.server import mcp

if __name__ == "__main__":
    mcp.run()

