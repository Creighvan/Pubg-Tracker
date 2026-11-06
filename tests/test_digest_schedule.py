"""The digest must post once per day shortly after its set time, and say so in the log."""
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

import discord
import pytest


@pytest.fixture
def sched(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "x.y.z")
    monkeypatch.setenv("PUBG_API_KEY", "k")
    import modules.scheduler as s
    import modules.utils as u
    import modules.maintenance as m
    m.MAINTENANCE_STATE["is_maintenance"] = False
    return s, u


def _run_ticks(sched, monkeypatch, cfg, ticks):
    s, u = sched
    posted = []

    class Chan:
        async def send(self, embed=None): posted.append(embed)

    async def ids(): return [111]
    async def get(gid): return cfg
    async def modify(gid, fn): fn(cfg)
    async def lookup(cid, gid=None): return Chan()
    async def report(gid, _, game_mode=None): return discord.Embed(title="Clan Digest"), [1, 2, 3]
    async def audit(*a, **k): pass
    monkeypatch.setattr(s.storage, "all_guild_ids", ids)
    monkeypatch.setattr(s.storage, "get_guild", get)
    monkeypatch.setattr(s.storage, "modify_guild", modify)
    monkeypatch.setattr(s, "_get_channel_cached", lookup)
    monkeypatch.setattr(s, "fetch_clan_report", report)
    monkeypatch.setattr(s, "send_audit_log", audit)

    counts = {}
    for hhmm in ticks:
        h, m = map(int, hhmm.split(":"))
        fixed = datetime(2026, 11, 6, h, m, 7, tzinfo=timezone.utc)

        class D(datetime):
            @classmethod
            def now(cls, tz=None, _fixed=fixed): return _fixed
        monkeypatch.setattr(s, "datetime", D)
        monkeypatch.setattr(u, "datetime", D)
        before = len(posted)
        asyncio.run(s.auto_digest.coro())
        counts[hhmm] = len(posted) - before
    return counts


CFG = {"post_channel_id": 5, "digest_enabled": True, "digest_hour_utc": 10,
       "digest_minute_utc": 0, "last_post_at": "2026-11-05T10:13:00+00:00"}


def test_digest_posts_once_on_the_first_tick_after_its_time(sched, monkeypatch):
    counts = _run_ticks(sched, monkeypatch, dict(CFG), ["09:48", "10:03", "10:18", "10:33"])
    assert counts == {"09:48": 0, "10:03": 1, "10:18": 0, "10:33": 0}


def test_digest_catches_up_when_a_tick_is_late(sched, monkeypatch):
    counts = _run_ticks(sched, monkeypatch, dict(CFG), ["10:48", "11:03"])
    assert counts == {"10:48": 1, "11:03": 0}      # old 15-minute window would have skipped the day


def test_digest_success_is_logged(sched, monkeypatch, caplog):
    with caplog.at_level(logging.INFO):
        _run_ticks(sched, monkeypatch, dict(CFG), ["10:03"])
    text = caplog.text
    assert "Digest is due, fetching report" in text
    assert "Clan digest posted successfully (3 players)" in text
