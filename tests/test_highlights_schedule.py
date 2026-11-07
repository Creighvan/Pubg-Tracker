"""Daily highlights: posts right after the 02:00 UTC reset, once a day, and retries after a failure."""
import asyncio
from datetime import datetime, timedelta, timezone

import discord
import pytest

from pubg_api import PubgApiError


@pytest.fixture
def sched(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "x.y.z")
    monkeypatch.setenv("PUBG_API_KEY", "k")
    import modules.scheduler as s
    s._highlights_retry_after.clear()
    return s


def _simulate(sched, monkeypatch, start, hours, fetch_results, posted_at):
    """Run auto_highlights on a fake clock. fetch_results: list of 'ok' / 'error' / 'none' per attempt."""
    import modules.utils as utils

    clock = {"now": start}

    class D(datetime):
        @classmethod
        def now(cls, tz=None): return clock["now"]

    monkeypatch.setattr(sched, "datetime", D)
    monkeypatch.setattr(utils, "datetime", D)

    cfg = {"highlights_channel_id": 99, "highlights_enabled": True,
           "highlights_message_id": 555, "highlights_posted_at": posted_at}
    events, attempts = [], []

    class Msg:
        async def edit(self, embed=None): events.append(clock["now"])

    class Chan:
        async def fetch_message(self, mid): return Msg()
        async def send(self, embed=None): raise AssertionError("should edit the existing message")

    async def ids(): return [111]
    async def get(gid): return cfg
    async def modify(gid, fn): fn(cfg)
    async def lookup(cid, gid=None): return Chan()
    async def audit(*a, **k): pass
    async def status(*a, **k): pass

    async def report(gid, _, **kw):
        kind = fetch_results[min(len(attempts), len(fetch_results) - 1)]
        attempts.append((clock["now"], kind))
        if kind == "error":
            raise PubgApiError("429 rate limited")
        if kind == "none":
            return None
        return discord.Embed(title="Clan - Daily Highlights"), [1] * 74

    monkeypatch.setattr(sched.storage, "all_guild_ids", ids)
    monkeypatch.setattr(sched.storage, "get_guild", get)
    monkeypatch.setattr(sched.storage, "modify_guild", modify)
    monkeypatch.setattr(sched, "_get_channel_cached", lookup)
    monkeypatch.setattr(sched, "fetch_highlights_report", report)
    monkeypatch.setattr(sched, "send_audit_log", audit)
    monkeypatch.setattr(sched, "_record_status_event", status)

    end = start + timedelta(hours=hours)
    real_sleep = asyncio.sleep

    async def fake_sleep(seconds):
        clock["now"] += timedelta(seconds=seconds)
        if clock["now"] > end:
            raise asyncio.CancelledError
        await real_sleep(0)

    monkeypatch.setattr(sched.asyncio, "sleep", fake_sleep)
    try:
        asyncio.run(sched.auto_highlights())
    except asyncio.CancelledError:
        pass
    return events, attempts


START = datetime(2026, 11, 5, 19, 48, 7, tzinfo=timezone.utc)      # bot (re)started here
POSTED = "2026-11-05T02:00:04+00:00"                                 # yesterday's scheduled post


def test_posts_once_just_after_the_reset(sched, monkeypatch):
    events, attempts = _simulate(sched, monkeypatch, START, 14, ["ok"], POSTED)
    assert len(events) == 1 and len(attempts) == 1
    assert events[0].strftime("%d %H:%M") == "06 02:03"             # first 15-minute check after 02:00 UTC


def test_does_not_repost_when_already_posted_today(sched, monkeypatch):
    posted_today = "2026-11-06T02:00:30+00:00"
    events, attempts = _simulate(sched, monkeypatch, datetime(2026, 11, 6, 3, 0, 7, tzinfo=timezone.utc), 10, ["ok"], posted_today)
    assert events == [] and attempts == []


def test_retries_after_an_api_error(sched, monkeypatch):
    events, attempts = _simulate(sched, monkeypatch, START, 14, ["error", "ok"], POSTED)
    assert [kind for _, kind in attempts] == ["error", "ok"]
    gap = attempts[1][0] - attempts[0][0]
    assert timedelta(minutes=60) <= gap < timedelta(minutes=80)       # cooldown, then retry; no hammering
    assert len(events) == 1                                          # and it does post in the end


def test_retries_after_no_data(sched, monkeypatch):
    events, attempts = _simulate(sched, monkeypatch, START, 14, ["none", "ok"], POSTED)
    assert [kind for _, kind in attempts] == ["none", "ok"]
    assert len(events) == 1


def test_old_behaviour_would_have_given_up_for_the_day(sched, monkeypatch):
    # three failures in a row still only cost one attempt per hour, never a flood
    events, attempts = _simulate(sched, monkeypatch, START, 9, ["error"], POSTED)
    assert 1 <= len(attempts) <= 4 and events == []
