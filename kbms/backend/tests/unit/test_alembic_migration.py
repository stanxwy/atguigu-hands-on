"""Alembic migration test (SPEC §13): ``upgrade head`` → 10 tables, then
``downgrade base`` → empty, against a temporary SQLite file.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

BACKEND_ROOT = Path(__file__).resolve().parents[2]

ALL_TABLES = {
    "users",
    "departments",
    "roles",
    "user_roles",
    "role_permissions",
    "knowledge_units",
    "unit_permissions",
    "qa_access_logs",
    "faqs",
    "knowledge_gaps",
}


def _run_alembic(cmd: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *cmd.split()],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_alembic_upgrade_then_downgrade(tmp_path):
    db_path = tmp_path / "kbms.db"
    url = f"sqlite:///{db_path}"

    env = os.environ.copy()
    env["DATABASE_URL"] = url

    up = _run_alembic("upgrade head", env)
    assert up.returncode == 0, f"upgrade failed:\nSTDOUT:\n{up.stdout}\nSTDERR:\n{up.stderr}"

    def _business_tables(engine) -> set[str]:
        # ``alembic_version`` is Alembic's own bookkeeping table, not a KBMS table.
        return set(inspect(engine).get_table_names()) - {"alembic_version"}

    engine = create_engine(url)
    try:
        assert _business_tables(engine) == ALL_TABLES
    finally:
        engine.dispose()

    down = _run_alembic("downgrade base", env)
    assert down.returncode == 0, f"downgrade failed:\nSTDOUT:\n{down.stdout}\nSTDERR:\n{down.stderr}"

    engine = create_engine(url)
    try:
        assert _business_tables(engine) == set()
    finally:
        engine.dispose()
