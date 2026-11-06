"""/reportstatus must list every configured report, not just the Clan Digest."""
import asyncio
from types import SimpleNamespace

import pytest

import storage
from commands.settings import reportstatus_impl


class _FakeInteraction:
    def __init__(self):
        self.guild_id = 123
        self.sent = []
        self.response = SimpleNamespace(defer=self._defer)
        self.followup = SimpleNamespace(send=self._send)

    async def _defer(self, *a, **k): pass
    async def _send(self, **kwargs): self.sent.append(kwargs)


CFG = {
    "post_channel_id": 11, "digest_hour_utc": 3,
    "last_activity_channel_id": 12,
    "ranked_channel_id": 13, "ranked_hour_utc": 4, "ranked_minute_utc": 30,
    "highlights_channel_id": 14,
    "clan_channel_id": 15, "clan_weekday_utc": 0,
    "survival_channel_id": 16, "survival_weekday_utc": 6,
}


def _run(cfg, monkeypatch):
    async def _get(guild_id): return dict(cfg)
    monkeypatch.setattr(storage, "get_guild", _get)
    inter = _FakeInteraction()
    asyncio.run(reportstatus_impl(inter))
    return inter.sent[0]["embed"]


def test_lists_all_configured_reports(monkeypatch):
    embed = _run(CFG, monkeypatch)
    names = " | ".join(f.name for f in embed.fields)
    for expected in ("Clan Digest", "Last Active", "Ranked", "Highlights", "Clan Level", "Survival"):
        assert expected in names, f"{expected} missing from /reportstatus: {names}"


def test_next_run_is_shown_as_local_time(monkeypatch):
    embed = _run(CFG, monkeypatch)
    for f in embed.fields:
        if f.name == "⛔ Disabled":
            continue
        # a Discord timestamp (shown in each reader's own time zone), or "due now"
        assert "<t:" in f.value or "scheduler check" in f.value, f"{f.name}: {f.value}"
    assert any("<t:" in f.value for f in embed.fields)


def test_disabled_report_is_listed_as_disabled(monkeypatch):
    embed = _run(dict(CFG, ranked_enabled=False), monkeypatch)
    disabled = [f for f in embed.fields if f.name == "⛔ Disabled"]
    assert disabled and "Ranked" in disabled[0].value
