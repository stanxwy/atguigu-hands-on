"""Settings tests (SPEC §1.4 / §5.5 / §8): the 7 new KBMS config fields."""

from __future__ import annotations

from app.infra.config.settings import Settings


def test_settings_new_field_defaults():
    s = Settings(DATABASE_URL="sqlite:///./kbms-test.db")
    assert s.DATABASE_URL == "sqlite:///./kbms-test.db"
    assert s.DATA_PERM_DEPT_RECURSIVE is True
    assert s.FAQ_SIMILARITY_THRESHOLD == 0.85
    assert s.FAQ_MIN_FREQUENCY == 3
    assert s.GAP_SIMILARITY_THRESHOLD == 0.5


def test_settings_jwt_fields_exist():
    s = Settings(DATABASE_URL="sqlite:///./kbms-test.db")
    assert s.JWT_SECRET
    assert s.JWT_EXPIRE_MINUTES >= 0
