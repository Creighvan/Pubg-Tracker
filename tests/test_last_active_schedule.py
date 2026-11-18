"""Last Active updates once a day, shortly after its UTC time, editing one message in place.

The time itself lives in ONE place (modules.utils.LAST_ACTIVE_RUN_UTC). These tests read it from there,
so changing the time (for example 02:30 -> 03:00) never needs a test change.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import discord
import pytest

import translations
from modules.embeds import build_last_active_embed, build_report_status_embed
from modules.utils import LAST_ACTIVE_RUN_UTC, most_recent_slot, next_last_active_report

H, M = LAST_ACTIVE_RUN_UTC
HHMM = f"{H:02d}:{M:02d}"


def slot(day=8):
    return datetime(2026, 11, day, H, M, 0, tzinfo=timezone.utc)


def at(minutes, day=8):
    """A scheduler tick `minutes` after (negative: before) that day's run time."""
    return slot(day) + timedelta(minutes=minutes, seconds=7)


def test_the_run_time_is_a_valid_utc_time():
    assert isinstance(H, int) and isinstance(M, int) and 0 <= H <= 23 and 0 <= M <= 59


def test_most_recent_slot():
    assert most_recent_slot(H, M, at(-1)) == slot(7)           # not yet reached today: yesterday's
    assert most_recent_slot(H, M, slot(8)) == slot(8)
    assert most_recent_slot(H, M, at(60)) == slot(8)


@pytest.fixture
def sched(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "x.y.z")
    monkeypatch.setenv("PUBG_API_KEY", "k")
    import modules.scheduler as s
    return s


def _ticks(sched, monkeypatch, cfg, ticks):
    import modules.utils as utils
    edits = []

    class Msg:
        async def edit(self, embed=None): edits.append(clock["now"])

    class Chan:
        async def fetch_message(self, mid): return Msg()
        async def send(self, embed=None): raise AssertionError("Last Active must edit its one message, not repost")

    async def ids(): return [111]
    async def get(gid): return cfg
    async def modify(gid, fn): fn(cfg)
    async def lookup(cid, gid=None): return Chan()
    async def report(gid, name=None): return discord.Embed(title="Last Active"), [1, 2, 3]
    async def audit(*a, **k): pass

    for name, value in (("all_guild_ids", ids), ("get_guild", get), ("modify_guild", modify)):
        monkeypatch.setattr(sched.storage, name, value)
    monkeypatch.setattr(sched, "_get_channel_cached", lookup)
    monkeypatch.setattr(sched, "fetch_last_active_report", report)
    monkeypatch.setattr(sched, "send_audit_log", audit)

    clock = {"now": None}

    class D(datetime):
        @classmethod
        def now(cls, tz=None): return clock["now"]

    monkeypatch.setattr(sched, "datetime", D)
    monkeypatch.setattr(utils, "datetime", D)
    done = []
    for when in ticks:
        clock["now"] = when
        before = len(edits)
        asyncio.run(sched.auto_last_active.coro())
        done.append(len(edits) - before)
    return done


def CFG(posted):
    cfg = {"last_activity_channel_id": 5, "activity_enabled": True, "last_activity_message_id": 99}
    if posted is not None:
        cfg["last_activity_posted_at"] = posted.isoformat()
    return cfg


def test_updates_on_the_first_check_after_its_time_and_only_once(sched, monkeypatch):
    cfg = CFG(slot(7) + timedelta(minutes=3))                        # yesterday's update
    ticks = [at(-27), at(-12), at(3), at(18), at(33), at(12 * 60)]
    assert _ticks(sched, monkeypatch, cfg, ticks) == [0, 0, 1, 0, 0, 0]


def test_switch_over_day_gives_one_extra_update(sched, monkeypatch):
    cfg = CFG(slot(8) - timedelta(minutes=25))                        # posted today, but before the new time
    assert _ticks(sched, monkeypatch, cfg, [at(-12), at(3), at(18)]) == [0, 1, 0]


def test_first_ever_run_waits_for_its_time(sched, monkeypatch):
    assert _ticks(sched, monkeypatch, CFG(None), [at(-12), at(3)]) == [0, 1]


def test_a_missed_day_is_caught_up(sched, monkeypatch):
    cfg = CFG(slot(6) + timedelta(minutes=3))                          # nothing posted yesterday
    assert _ticks(sched, monkeypatch, cfg, [at(6 * 60), at(6 * 60 + 15)]) == [1, 0]


def test_next_update_text():
    now = at(6 * 60)
    assert "next scheduler check" in next_last_active_report((slot(7) + timedelta(minutes=3)).isoformat(), now)
    text = next_last_active_report((slot(8) + timedelta(minutes=5)).isoformat(), now)
    assert "<t:" in text and text.endswith(f"{HHMM} UTC")             # tomorrow's time, shown in local time too


def test_reportstatus_describes_the_real_schedule():
    cfg = {"post_channel_id": 5, "last_activity_channel_id": 6,
           "last_activity_posted_at": (slot(8) + timedelta(minutes=5)).isoformat()}
    fields = {f.name: f.value for f in build_report_status_embed(cfg).fields}
    value = next(v for n, v in fields.items() if "Last Active" in n)
    assert f"Daily at {HHMM} UTC (updates in place)" in value


def test_the_texts_in_every_language_carry_the_current_time():
    en = translations.TRANSLATIONS["en"]
    assert HHMM in en["updates_daily"] and HHMM in en["activity_channel_set"]
    assert "02:00" in translations.get_translation("en", "highlights_footer")      # Highlights has its own time


def test_embed_footer_shows_the_time():
    embed = build_last_active_embed(1, "Test", {"players": ["Ann"]}, [{"name": "Ann", "last_match_at": None}], [], [])
    assert f"{HHMM} UTC" in embed.footer.text
