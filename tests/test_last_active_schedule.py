"""Last Active updates once a day, shortly after 03:00 UTC, editing one message in place."""
import asyncio
from datetime import datetime, timedelta, timezone

import discord
import pytest

import translations
from modules.embeds import build_last_active_embed, build_report_status_embed
from modules.utils import LAST_ACTIVE_RUN_UTC, most_recent_slot, next_last_active_report


def test_the_run_time_is_0300_utc():
    assert LAST_ACTIVE_RUN_UTC == (3, 0)


def test_most_recent_slot():
    at = lambda h, m: datetime(2026, 11, 8, h, m, 7, tzinfo=timezone.utc)
    assert most_recent_slot(3, 0, at(2, 59)) == datetime(2026, 11, 7, 3, 0, tzinfo=timezone.utc)   # not yet today
    assert most_recent_slot(3, 0, at(3, 0)) == datetime(2026, 11, 8, 3, 0, tzinfo=timezone.utc)
    assert most_recent_slot(3, 0, at(23, 0)) == datetime(2026, 11, 8, 3, 0, tzinfo=timezone.utc)


@pytest.fixture
def sched(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "x.y.z")
    monkeypatch.setenv("PUBG_API_KEY", "k")
    import modules.scheduler as s
    return s


def _ticks(sched, monkeypatch, cfg, ticks, day=8):
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
    done = {}
    for hhmm in ticks:
        h, m = map(int, hhmm.split(":"))
        clock["now"] = datetime(2026, 11, day, h, m, 7, tzinfo=timezone.utc)
        before = len(edits)
        asyncio.run(sched.auto_last_active.coro())
        done[hhmm] = len(edits) - before
    return done


CFG = lambda posted: {"last_activity_channel_id": 5, "activity_enabled": True,
                      "last_activity_message_id": 99, "last_activity_posted_at": posted}


def test_updates_on_the_first_check_after_0300_and_only_once(sched, monkeypatch):
    cfg = CFG("2026-11-07T03:03:10+00:00")            # yesterday's update
    done = _ticks(sched, monkeypatch, cfg, ["02:33", "02:48", "03:03", "03:18", "03:33", "14:18"])
    assert done == {"02:33": 0, "02:48": 0, "03:03": 1, "03:18": 0, "03:33": 0, "14:18": 0}


def test_switch_over_day_gives_one_extra_update_after_0300(sched, monkeypatch):
    cfg = CFG("2026-11-08T02:05:00+00:00")            # posted at the OLD 02:00 time today
    done = _ticks(sched, monkeypatch, cfg, ["02:48", "03:03", "03:18"])
    assert done == {"02:48": 0, "03:03": 1, "03:18": 0}


def test_first_ever_run_waits_for_0300(sched, monkeypatch):
    cfg = CFG(None)
    del cfg["last_activity_posted_at"]
    done = _ticks(sched, monkeypatch, cfg, ["02:48", "03:03"])
    assert done == {"02:48": 0, "03:03": 1}


def test_a_missed_day_is_caught_up(sched, monkeypatch):
    cfg = CFG("2026-11-06T03:03:00+00:00")            # bot was down yesterday
    done = _ticks(sched, monkeypatch, cfg, ["09:18", "09:33"])
    assert done == {"09:18": 1, "09:33": 0}


def test_next_update_text():
    now = datetime(2026, 11, 8, 9, 0, tzinfo=timezone.utc)
    assert "next scheduler check" in next_last_active_report("2026-11-07T03:03:00+00:00", now)
    text = next_last_active_report("2026-11-08T03:05:00+00:00", now)
    assert "<t:" in text and text.endswith("03:00 UTC")             # tomorrow 03:00 UTC, shown in local time too


def test_reportstatus_describes_the_real_schedule():
    cfg = {"post_channel_id": 5, "last_activity_channel_id": 6, "last_activity_posted_at": "2026-11-08T03:05:00+00:00"}
    fields = {f.name: f.value for f in build_report_status_embed(cfg).fields}
    value = next(v for n, v in fields.items() if "Last Active" in n)
    assert "Daily at 03:00 UTC (updates in place)" in value and "03:00 UTC" in value


def test_footer_and_confirmation_texts_say_0300_and_highlights_is_unchanged():
    for lang in translations.TRANSLATIONS:
        assert "02:00" not in translations.TRANSLATIONS[lang]["updates_daily"]
    assert "03:00" in translations.get_translation("en", "updates_daily")
    assert "03:00" in translations.get_translation("en", "activity_channel_set", channel="#x")
    assert "02:00" in translations.get_translation("en", "highlights_footer")      # Highlights still runs at 02:00


def test_embed_footer_shows_the_new_time():
    embed = build_last_active_embed(1, "Test", {"players": ["Ann"]}, [{"name": "Ann", "last_match_at": None}], [], [])
    assert "03:00 UTC" in embed.footer.text
