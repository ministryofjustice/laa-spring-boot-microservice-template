#!/usr/bin/env python3
"""
LAA Spring Boot Microservice Template — Initialisation Script
=============================================================
This script renames all template placeholder values to your new service name,
renames subproject directories, and optionally switches the database from
H2 to PostgreSQL (RDS-ready).

Usage
-----
  python3 initialise-service.py                   # fully interactive
  python3 initialise-service.py laa-my-service    # skip the first prompt
  python3 initialise-service.py --dry-run         # preview only, no changes

Requirements: Python 3.9+, no third-party packages needed.

Implementation lives in .initialise-service-tools/template_tools/
"""
import sys
from pathlib import Path

# Add .initialise-service-tools to the path so the package can be imported
sys.path.insert(0, str(Path(__file__).parent / ".initialise-service-tools"))

from template_tools.cli import main  # noqa: E402

if __name__ == "__main__":
    main()

