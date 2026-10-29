"""Tests for the first-run setup guide (modules/onboarding.py)."""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import discord
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DISCORD_TOKEN", "test")
os.environ.setdefault("PUBG_API_KEY", "test")

import storage  # noqa: E402
from modules import onboarding  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_PATH", str(tmp_path / "data.json"))
    storage.reset_corruption_state()
    monkeypatch.delenv("SETUP_GUIDE_ENABLED", raising=False)
    monkeypatch.delenv("SETUP_GUIDE_SWEEP_EXISTING", raising=False)
    monkeypatch.setattr(onboarding, "SEND_DELAY_SECONDS", 0)
    monkeypatch.setattr(onboarding, "_sweep_started", False)
    yield


# ------------------------------------------------------------------------------ fakes
def _forbidden():
    return discord.Forbidden(SimpleNamespace(status=403, reason="Missing Permissions"), "Missing Permissions")


class FakeChannel:
    def __init__(self, cid, name, *, can_send=True, public=True, position=0, send_error=None):
        self.id, self.name, self.position = cid, name, position
        self._can_send, self._public, self._send_error = can_send, public, send_error
        self.sent = []

    def permissions_for(self, who):
        if who is DEFAULT_ROLE:
            return discord.Permissions(view_channel=self._public)
        return discord.Permissions(view_channel=True, send_messages=self._can_send, embed_links=self._can_send)

    async def send(self, **kw):
        if self._send_error:
            raise self._send_error
        self.sent.append(kw)


DEFAULT_ROLE = object()


class FakeOwner:
    def __init__(self, dm_error=None):
        self.dms, self._dm_error = [], dm_error

    async def send(self, **kw):
        if self._dm_error:
            raise self._dm_error
        self.dms.append(kw)


class FakeGuild:
    def __init__(self, gid, channels, system_channel=None, name="Test Server", owner=None):
        self.id, self.name = gid, name
        self.text_channels = channels
        self.system_channel = system_channel
        self.me = object()
        self.default_role = DEFAULT_ROLE
        self.owner_id = 4242
        self._owner = owner


class FakeClient:
    def __init__(self, guilds=(), owner=None):
        self.guilds = list(guilds)
        self.user = SimpleNamespace(id=1)
        self._owner = owner or FakeOwner()

    async def fetch_user(self, uid):
        return self._owner


def make_guild(gid=1, **kw):
    ch = FakeChannel(10, "general")
    return FakeGuild(gid, [ch], **kw), ch


# ------------------------------------------------------------------------------ state detection
def test_unconfigured_defaults():
    assert onboarding.is_unconfigured(dict(storage._DEFAULT_GUILD))


@pytest.mark.parametrize("change", [
    {"players": ["Abc"]},
    {"post_channel_id": 5},
    {"last_activity_channel_id": 5},
    {"ranked_channel_id": 5},
    {"audit_log_channel_id": 5},
    {"clan_name": "X"},
    {"pubg_clan_id": "clan.abc"},
])
def test_any_setup_marks_configured(change):
    cfg = dict(storage._DEFAULT_GUILD)
    cfg.update(change)
    assert not onboarding.is_unconfigured(cfg)


def test_default_guild_has_tracking_keys():
    assert "setup_guide_sent_at" in storage._DEFAULT_GUILD and "setup_guide_failed_at" in storage._DEFAULT_GUILD


# ------------------------------------------------------------------------------ the message
def test_embed_within_discord_limits_and_mentions_real_commands():
    e = onboarding.build_setup_embed("Some Server").to_dict()
    total = len(e["title"]) + len(e["description"]) + len(e["footer"]["text"])
    for f in e["fields"]:
        assert len(f["name"]) <= 256 and 0 < len(f["value"]) <= 1024
        total += len(f["name"]) + len(f["value"])
    assert len(e["fields"]) <= 25 and total <= 6000
    import re
    mentioned = set(re.findall(r"`/(\w+)", " ".join(f["value"] for f in e["fields"])))
    # every command named in the guide must really exist
    os.environ.setdefault("DISCORD_TOKEN", "x")
    import bot
    registered = {c.name for c in bot.bot.tree.get_commands()}
    assert mentioned <= registered, f"guide names commands that do not exist: {sorted(mentioned - registered)}"


def test_embed_shows_progress_only_when_given_config():
    assert "Your progress" not in str(onboarding.build_setup_embed("S").to_dict())
    cfg = dict(storage._DEFAULT_GUILD, players=["Abc"])
    d = onboarding.build_setup_embed("S", cfg=cfg).to_dict()
    assert "Your progress" in str(d) and "✅ Players added (1)" in str(d)
    assert "isn't set up yet" not in d["description"]  # configured server gets neutral wording


# ------------------------------------------------------------------------------ channel choice
def test_prefers_system_channel_then_public_chatty_channels():
    sysch = FakeChannel(1, "welcome-mat", position=5)
    other = FakeChannel(2, "general", position=1)
    g = FakeGuild(1, [other, sysch], system_channel=sysch)
    assert onboarding.candidate_channels(FakeClient(), g)[0] is sysch
    g2 = FakeGuild(2, [FakeChannel(3, "random", position=0), FakeChannel(4, "bot-commands", position=9)])
    assert onboarding.candidate_channels(FakeClient(), g2)[0].name == "bot-commands"


def test_skips_channels_bot_cannot_post_in_and_prefers_public():
    g = FakeGuild(1, [FakeChannel(1, "locked", can_send=False), FakeChannel(2, "staff", public=False, position=0),
                      FakeChannel(3, "lobby", public=True, position=7)])
    names = [c.name for c in onboarding.candidate_channels(FakeClient(), g)]
    assert "locked" not in names and names[0] == "lobby"


# ------------------------------------------------------------------------------ delivery
async def test_sends_once_and_never_again():
    g, ch = make_guild()
    c = FakeClient([g])
    assert await onboarding.send_setup_guide(c, g) == onboarding.SENT_CHANNEL
    assert await onboarding.send_setup_guide(c, g) == onboarding.SKIPPED
    assert len(ch.sent) == 1
    assert ch.sent[0]["allowed_mentions"].everyone is False and ch.sent[0]["allowed_mentions"].roles is False
    assert (await storage.get_guild(1))["setup_guide_sent_at"]


async def test_configured_server_is_never_messaged():
    g, ch = make_guild(gid=7)
    await storage.add_player(7, "Alpha_One")
    assert await onboarding.send_setup_guide(FakeClient([g]), g) == onboarding.SKIPPED
    assert ch.sent == []


async def test_a_channel_setting_alone_counts_as_configured():
    g, ch = make_guild(gid=8)
    await storage.modify_guild(8, lambda cfg: cfg.update(post_channel_id=123))
    assert await onboarding.send_setup_guide(FakeClient([g]), g) == onboarding.SKIPPED
    assert ch.sent == []


async def test_concurrent_join_and_sweep_send_exactly_once():
    g, ch = make_guild(gid=9)
    c = FakeClient([g])
    results = await asyncio.gather(*(onboarding.send_setup_guide(c, g) for _ in range(10)))
    assert results.count(onboarding.SENT_CHANNEL) == 1 and len(ch.sent) == 1


async def test_falls_through_to_next_channel_when_first_send_is_forbidden():
    bad = FakeChannel(1, "general", send_error=_forbidden(), position=0)
    good = FakeChannel(2, "chat", position=1)
    g = FakeGuild(1, [bad, good])
    assert await onboarding.send_setup_guide(FakeClient([g]), g) == onboarding.SENT_CHANNEL
    assert len(good.sent) == 1


async def test_dm_fallback_when_no_channel_works():
    owner = FakeOwner()
    g = FakeGuild(1, [FakeChannel(1, "locked", can_send=False)])
    assert await onboarding.send_setup_guide(FakeClient([g], owner), g) == onboarding.SENT_DM
    assert len(owner.dms) == 1 and owner.dms[0]["allowed_mentions"].everyone is False


async def test_failure_rolls_back_and_is_not_retried_for_a_week():
    g = FakeGuild(1, [FakeChannel(1, "locked", can_send=False)])
    c = FakeClient([g], FakeOwner(dm_error=_forbidden()))
    assert await onboarding.send_setup_guide(c, g) == onboarding.FAILED
    cfg = await storage.get_guild(1)
    assert cfg["setup_guide_sent_at"] is None and cfg["setup_guide_failed_at"]
    assert await onboarding.send_setup_guide(c, g) == onboarding.SKIPPED  # inside the retry window

    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    await storage.modify_guild(1, lambda x: x.update(setup_guide_failed_at=old))
    g.text_channels.append(FakeChannel(2, "now-open"))
    assert await onboarding.send_setup_guide(c, g) == onboarding.SENT_CHANNEL  # retried after the window


async def test_kill_switch(monkeypatch):
    monkeypatch.setenv("SETUP_GUIDE_ENABLED", "false")
    g, ch = make_guild(gid=3)
    assert await onboarding.send_setup_guide(FakeClient([g]), g) == onboarding.SKIPPED
    assert ch.sent == []


async def test_blocked_database_means_nobody_is_messaged(monkeypatch):
    g, ch = make_guild(gid=5)

    async def boom(*a, **k):
        raise storage.DatabaseCorruptionError("blocked")
    monkeypatch.setattr(storage, "modify_guild", boom)
    assert await onboarding.send_setup_guide(FakeClient([g]), g) == onboarding.SKIPPED
    assert ch.sent == []


# ------------------------------------------------------------------------------ sweep
async def test_sweep_messages_only_unconfigured_servers():
    g1, c1 = make_guild(gid=11)
    g2, c2 = make_guild(gid=12)
    g3, c3 = make_guild(gid=13)
    await storage.add_player(12, "Alpha_One")
    stats = await onboarding.sweep_existing_guilds(FakeClient([g1, g2, g3]))
    assert (len(c1.sent), len(c2.sent), len(c3.sent)) == (1, 0, 1)
    assert stats[onboarding.SENT_CHANNEL] == 2 and stats[onboarding.SKIPPED] == 1
    again = await onboarding.sweep_existing_guilds(FakeClient([g1, g2, g3]))  # restart: nothing new sent
    assert again[onboarding.SENT_CHANNEL] == 0 and len(c1.sent) == 1


async def test_one_broken_server_does_not_stop_the_sweep(monkeypatch):
    g1, c1 = make_guild(gid=21)
    g2, c2 = make_guild(gid=22)
    real = onboarding.send_setup_guide

    async def flaky(client, guild):
        if guild.id == 21:
            raise RuntimeError("boom")
        return await real(client, guild)
    monkeypatch.setattr(onboarding, "send_setup_guide", flaky)
    stats = await onboarding.sweep_existing_guilds(FakeClient([g1, g2]))
    assert stats["error"] == 1 and len(c2.sent) == 1


async def test_sweep_starts_once_per_process_and_respects_flags(monkeypatch):
    started = []
    import modules.scheduler as sched
    monkeypatch.setattr(sched, "_spawn", lambda coro, name, loop=None: (started.append(name), coro.close()))
    c = FakeClient([])
    onboarding.start_setup_guide_sweep(c)
    onboarding.start_setup_guide_sweep(c)  # on_ready fired again after a reconnect
    assert started == ["setup_guide_sweep"]

    monkeypatch.setattr(onboarding, "_sweep_started", False)
    monkeypatch.setenv("SETUP_GUIDE_SWEEP_EXISTING", "false")
    onboarding.start_setup_guide_sweep(c)
    assert started == ["setup_guide_sweep"]  # unchanged: sweep disabled


# ------------------------------------------------------------------------------ /setupguide
async def test_setupguide_command_is_ephemeral_and_shows_progress():
    await storage.add_player(31, "Alpha_One")
    sent = {}

    async def send_message(**kw):
        sent.update(kw)
    it = SimpleNamespace(guild_id=31, guild=SimpleNamespace(name="S"), response=SimpleNamespace(send_message=send_message))
    await onboarding.setupguide_impl(it)
    assert sent["ephemeral"] is True and "✅ Players added (1)" in str(sent["embed"].to_dict())


def test_log_style_channels_are_skipped_but_lookalike_words_are_not():
    g = FakeGuild(1, [FakeChannel(1, "mod-logs", position=0), FakeChannel(2, "audit_log", position=1),
                      FakeChannel(3, "auditlog", position=2), FakeChannel(4, "technology", position=3),
                      FakeChannel(5, "catalog", position=4)])
    names = [c.name for c in onboarding.candidate_channels(FakeClient(), g)]
    assert names == ["technology", "catalog"]
