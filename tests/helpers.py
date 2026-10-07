from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def make_repo() -> Path:
    """An empty team reviews repo in a temp dir."""
    return Path(tempfile.mkdtemp(prefix="arq-test-"))
