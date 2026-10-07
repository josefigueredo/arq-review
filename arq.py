#!/usr/bin/env python3
"""Entry point: puts the repo on sys.path and runs the arq CLI (works through a symlink)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from arqlib.cli import main  # noqa: E402

sys.exit(main())
