"""Tests for modules/maintenance.py: detection, restart-safe state, scheduled reminder, posting."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

import modules.maintenance as m


@pytest.fixture(autouse=True)
def fresh_state(tmp_path, monkeypatch):
    # modules.scheduler (imported lazily by some tests) reads these when first imported
    monkeypatch.setenv("DISCORD_TOKEN", "test-token")
    monkeypatch.setenv("PUBG_API_KEY", "test-key")
    monkeypatch.setattr(m, "STATE_FILE", str(tmp_path / "maintenance_state.json"))
    m.MAINTENANCE_STATE.update(
        is_maintenance=False, down_since=None, consecutive_failures=0,
        consecutive_successes=0, last_check=None, scheduled_maintenance=None,
    )
    yield


def run(coro):
    return asyncio.run(coro)


def _signals(monkeypatch, steam, status_ok=True, data_ok=True):
    async def _steam(): return steam
    async def _status(): return status_ok
    async def _data(): return data_ok
    monkeypatch.setattr(m, "get_steam_player_count", _steam)
    monkeypatch.setattr(m, "check_pubg_api_status", _status)
    monkeypatch.setattr(m, "check_pubg_api_data", _data)


# ---------- detection ----------
@pytest.mark.parametrize("steam,status_ok,data_ok,expected", [
    (240_000, True, True, False),    # normal small-hours count
    (700_000, True, True, False),    # peak
    (18_009, True, True, True),      # real maintenance reading, API still answering
    (80_000, True, True, True),      # partial recovery: still treated as down
    (240_000, False, False, False),  # API trouble alone, Steam normal: not maintenance
    (None, False, False, True),      # Steam unavailable AND API down
    (None, True, True, False),       # Steam unavailable but API fine
])
def test_detection(monkeypatch, steam, status_ok, data_ok, expected):
    _signals(monkeypatch, steam, status_ok, data_ok)
    is_down, _ = run(m.check_maintenance_status())
    assert is_down is expected


# ---------- state survives a restart ----------
def test_state_round_trip():
    start = datetime(2026, 11, 8, 22, 0, tzinfo=timezone.utc)
    m.MAINTENANCE_STATE.update(is_maintenance=True, down_since=start, scheduled_maintenance={
        "start_time": start, "end_time": start + timedelta(hours=8.5),
        "source": "Manual", "announced": True, "reminded": True})
    m._save_state()
    m.MAINTENANCE_STATE.update(is_maintenance=False, down_since=None, scheduled_maintenance=None)
    m._load_state()
    assert m.MAINTENANCE_STATE["is_maintenance"] is True
    assert m.MAINTENANCE_STATE["down_since"] == start
    assert m.MAINTENANCE_STATE["scheduled_maintenance"]["reminded"] is True
    assert m.MAINTENANCE_STATE["scheduled_maintenance"]["end_time"] == start + timedelta(hours=8.5)


def test_corrupt_state_file_is_ignored():
    with open(m.STATE_FILE, "w") as f:
        f.write("{not json")
    m._load_state()
    assert m.MAINTENANCE_STATE["is_maintenance"] is False


def test_restart_during_maintenance_still_posts_back_online(monkeypatch):
    """Bot restarts mid-maintenance; when servers return it must post 'back online' with the real downtime."""
    down_since = datetime.now(timezone.utc) - timedelta(hours=3, minutes=5)
    m.MAINTENANCE_STATE.update(is_maintenance=True, down_since=down_since)
    m._save_state()
    m.MAINTENANCE_STATE.update(is_maintenance=False, down_since=None)   # what a restart does
    m._load_state()

    posts = []
    async def _post(embed, scheduled=False): posts.append(embed.title)
    monkeypatch.setattr(m, "post_maintenance_notification", _post)
    _signals(monkeypatch, 250_000)

    import modules.scheduler as sched
    async def _recover(): pass
    monkeypatch.setattr(sched, "trigger_maintenance_recovery", _recover)

    run(m._maintenance_tick()); run(m._maintenance_tick())
    assert posts == ["✅ PUBG Servers Back Online"]
    assert m.MAINTENANCE_STATE["is_maintenance"] is False
    assert run(m.calculate_downtime(down_since)).startswith("3h")


def test_restart_during_maintenance_does_not_repost_detected(monkeypatch):
    m.MAINTENANCE_STATE.update(is_maintenance=True, down_since=datetime.now(timezone.utc) - timedelta(hours=1))
    m._save_state(); m._load_state()
    posts = []
    async def _post(embed, scheduled=False): posts.append(embed.title)
    monkeypatch.setattr(m, "post_maintenance_notification", _post)
    _signals(monkeypatch, 18_000)
    for _ in range(5):
        run(m._maintenance_tick())
    assert posts == []   # already in maintenance: no second "detected" notice


# ---------- scheduled maintenance ----------
def test_reminder_posts_once_and_schedule_expires(monkeypatch):
    posts = []
    async def _post(embed, scheduled=False): posts.append((embed.title, scheduled))
    monkeypatch.setattr(m, "post_maintenance_notification", _post)
    _signals(monkeypatch, 250_000)

    start = datetime.now(timezone.utc) + timedelta(minutes=20)
    m.MAINTENANCE_STATE["scheduled_maintenance"] = {
        "start_time": start, "end_time": start + timedelta(hours=8), "source": "Manual",
        "announced": True, "reminded": False}
    run(m._maintenance_tick()); run(m._maintenance_tick())
    assert posts == [("⏰ PUBG Maintenance Starting Soon", True)]     # once, not every tick

    past = datetime.now(timezone.utc) - timedelta(hours=10)
    m.MAINTENANCE_STATE["scheduled_maintenance"] = {
        "start_time": past, "end_time": past + timedelta(hours=8), "source": "Manual",
        "announced": True, "reminded": True}
    run(m._maintenance_tick())
    assert m.MAINTENANCE_STATE["scheduled_maintenance"] is None


def test_no_reminder_when_far_in_the_future(monkeypatch):
    posts = []
    async def _post(embed, scheduled=False): posts.append(embed.title)
    monkeypatch.setattr(m, "post_maintenance_notification", _post)
    _signals(monkeypatch, 250_000)
    start = datetime.now(timezone.utc) + timedelta(hours=5)
    m.MAINTENANCE_STATE["scheduled_maintenance"] = {
        "start_time": start, "end_time": start + timedelta(hours=8), "source": "Manual",
        "announced": True, "reminded": False}
    run(m._maintenance_tick())
    assert posts == []


# ---------- detected / posting ----------
def test_detected_after_three_failures_posts_once(monkeypatch):
    posts = []
    async def _post(embed, scheduled=False): posts.append(embed.title)
    monkeypatch.setattr(m, "post_maintenance_notification", _post)
    _signals(monkeypatch, 18_009)
    for _ in range(6):
        run(m._maintenance_tick())
    assert posts == ["⚠️ PUBG Servers Under Maintenance"]
    assert m.MAINTENANCE_STATE["is_maintenance"] is True


class _Chan:
    def __init__(self, fail=False): self.sent, self.fail = [], fail
    async def send(self, embed=None):
        if self.fail: raise RuntimeError("403")
        self.sent.append(embed)


def test_post_uses_channel_lookup_and_reports_skips(monkeypatch):
    import discord
    import modules.scheduler as sched
    cfgs = {1: {"maintenance_channel_id": 11}, 2: {"maintenance_channel_id": 22},
            3: {"maintenance_channel_id": 33}, 4: {}}
    chans = {11: _Chan(), 22: None, 33: _Chan(fail=True)}

    async def _ids(): return list(cfgs)
    async def _get(gid): return cfgs[gid]
    async def _lookup(channel_id, guild_id=None): return chans[channel_id]
    monkeypatch.setattr(m.storage, "all_guild_ids", _ids)
    monkeypatch.setattr(m.storage, "get_guild", _get)
    monkeypatch.setattr(sched, "_get_channel_cached", _lookup)

    run(m.post_maintenance_notification(discord.Embed(title="x")))
    assert len(chans[11].sent) == 1          # posted
    assert chans[33].sent == []              # send failed, did not crash the loop
