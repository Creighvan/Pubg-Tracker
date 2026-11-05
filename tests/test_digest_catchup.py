"""Regression tests: a fixed-time daily report must still post if the scheduler tick is late."""
from datetime import datetime, timezone
from unittest.mock import patch

import modules.utils as utils


def _due_at(hour, minute, cfg):
    fake_now = datetime(2026, 11, 5, hour, minute, tzinfo=timezone.utc)

    class _FakeDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return fake_now

    with patch.object(utils, "datetime", _FakeDT):
        return utils._is_due(cfg, "digest_hour_utc", "digest_minute_utc", "last_post_at", 6)


CFG = {"digest_hour_utc": 18, "digest_minute_utc": 0}


def test_not_due_before_target():
    assert _due_at(17, 59, CFG) is False


def test_due_at_target():
    assert _due_at(18, 0, CFG) is True


def test_due_when_tick_is_20_minutes_late():
    # Old 15-minute window returned False here, silently skipping the day.
    assert _due_at(18, 20, CFG) is True


def test_due_when_delayed_by_hours_but_within_catchup():
    assert _due_at(22, 30, CFG) is True


def test_not_due_after_catchup_window():
    assert _due_at(0, 5, CFG) is False  # next UTC day, window closed


def test_not_due_after_catchup_expires_same_day():
    assert _due_at(23, 59, {"digest_hour_utc": 10, "digest_minute_utc": 0}) is False


def test_not_due_if_already_posted_today():
    cfg = dict(CFG, last_post_at="2026-11-05T18:02:00+00:00")
    assert _due_at(18, 30, cfg) is False


def test_due_again_next_day_after_posting_yesterday():
    cfg = dict(CFG, last_post_at="2026-11-04T18:02:00+00:00")
    assert _due_at(18, 5, cfg) is True
