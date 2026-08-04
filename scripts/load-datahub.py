#!/usr/bin/env python3
"""Source-checkout entry point for the datahub-postgres-loader package."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datahub_pg_loader.cli import main


if __name__ == "__main__":
    main()
