#!/usr/bin/env python3
"""Launcher kept at the repo root so the existing `ai` alias keeps working.

The real application lives in src/. This just puts src/ on the import path and
runs it — no need to update your alias or re-run install.sh.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import ai_agent  # this resolves to src/ai_agent.py (src/ is first on the path)

if __name__ == "__main__":
    ai_agent.main()
