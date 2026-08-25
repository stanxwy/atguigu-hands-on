"""Pytest fixtures & path bootstrap for the KBMS backend test suite.

Makes the backend project root importable so that ``from app.domain...``
resolves when tests are run from ``backend/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
