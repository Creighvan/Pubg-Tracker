"""Times are stored/scheduled in UTC but shown to players in their own time zone."""
from datetime import datetime, timezone

from modules.utils import (
    _format_utc_time, discord_time, next_daily_utc, next_weekly_utc, utc_with_local,
)

NOW = datetime(2026, 11, 5, 5, 0, tzinfo=timezone.utc)   # Thursday


def test_discord_time_uses_unix_seconds_and_style():
    when = datetime(2026, 11, 5, 2, 0, tzinfo=timezone.utc)
    ts = int(when.timestamp())
    assert discord_time(when, "t") == f"<t:{ts}:t>"
    assert discord_time(when) == f"<t:{ts}:F>"
    assert discord_time(when, "R") == f"<t:{ts}:R>"


def test_naive_datetime_is_treated_as_utc():
    naive = datetime(2026, 11, 5, 2, 0)
    aware = naive.replace(tzinfo=timezone.utc)
    assert discord_time(naive) == discord_time(aware)


def test_next_daily_today_or_tomorrow():
    assert next_daily_utc(6, 30, NOW) == datetime(2026, 11, 5, 6, 30, tzinfo=timezone.utc)   # still ahead today
    assert next_daily_utc(2, 0, NOW) == datetime(2026, 11, 6, 2, 0, tzinfo=timezone.utc)     # already passed: tomorrow
    assert next_daily_utc(5, 0, NOW) == datetime(2026, 11, 6, 5, 0, tzinfo=timezone.utc)     # exactly now: tomorrow


def test_next_weekly():
    # Thursday 05:00 now. Friday = 4, Thursday = 3, Monday = 0
    assert next_weekly_utc(4, 1, 0, NOW) == datetime(2026, 11, 6, 1, 0, tzinfo=timezone.utc)
    assert next_weekly_utc(3, 9, 0, NOW) == datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc)   # later today
    assert next_weekly_utc(3, 2, 0, NOW) == datetime(2026, 11, 12, 2, 0, tzinfo=timezone.utc)  # passed: next week
    assert next_weekly_utc(0, 0, 0, NOW) == datetime(2026, 11, 9, 0, 0, tzinfo=timezone.utc)


def test_format_keeps_utc_for_reference_and_adds_local():
    when = datetime(2026, 11, 6, 2, 0, tzinfo=timezone.utc)
    text = _format_utc_time(when)
    assert f"<t:{int(when.timestamp())}:F>" in text
    assert f"<t:{int(when.timestamp())}:R>" in text
    assert text.endswith("02:00 UTC")


def test_confirmation_message_text():
    when = datetime(2026, 11, 6, 3, 0, tzinfo=timezone.utc)
    assert utc_with_local("03:00", when) == f"03:00 UTC · <t:{int(when.timestamp())}:F>"
