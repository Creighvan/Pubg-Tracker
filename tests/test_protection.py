"""Permanent protection (🛡️) versus temporary protection for members who reached out (⏳)."""
import ast
import asyncio
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import storage
from commands.protected import addtempprotected_impl, listprotected_impl, removetempprotected_impl
from modules import reports
from modules.embeds import build_last_active_embed
from modules.protection import (
    active_temporary_protected, protection_kind, purge_expired_temporary, set_temporary,
)

NOW = datetime(2026, 11, 8, 6, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parent.parent


# ---------- pure helpers ----------
def test_temporary_protection_with_an_end_date_and_without():
    cfg = {"players": ["Ann", "Bob"]}
    set_temporary(cfg, "Ann", days=7, reason="vacation", now=NOW)
    set_temporary(cfg, "Bob", days=None, now=NOW)
    assert set(active_temporary_protected(cfg, NOW)) == {"ann", "bob"}
    later = NOW + timedelta(days=8)
    assert set(active_temporary_protected(cfg, later)) == {"bob"}       # Ann's has ended, Bob's has no end
    assert cfg["temporary_protected_players"]["ann"]["reason"] == "vacation"


def test_purge_removes_only_ended_protections():
    cfg = {}
    set_temporary(cfg, "Ann", days=1, now=NOW)
    set_temporary(cfg, "Bob", days=30, now=NOW)
    assert purge_expired_temporary(cfg, NOW + timedelta(days=2)) == ["Ann"]
    assert list(cfg["temporary_protected_players"]) == ["bob"]


def test_permanent_wins_when_a_player_is_on_both_lists():
    cfg = {"protected_players": ["Ann"]}
    set_temporary(cfg, "Ann", days=5, now=NOW)
    set_temporary(cfg, "Bob", days=5, now=NOW)
    assert protection_kind(cfg, "ANN", NOW) == "permanent"
    assert protection_kind(cfg, "bob", NOW) == "temporary"
    assert protection_kind(cfg, "Cy", NOW) is None


# ---------- storage (in-memory) ----------
class Store:
    def __init__(self, cfg):
        self.cfg = cfg

    async def get_guild(self, gid): return copy.deepcopy(self.cfg)
    async def modify_guild(self, gid, fn): return fn(self.cfg)
    async def get_protected_players(self, gid): return list(self.cfg.get("protected_players", []))


@pytest.fixture
def store(monkeypatch):
    s = Store({"players": ["Ann", "Bob", "Cy"], "protected_players": ["Cy"], "language": "en"})
    monkeypatch.setattr(storage, "get_guild", s.get_guild)
    monkeypatch.setattr(storage, "modify_guild", s.modify_guild)
    monkeypatch.setattr(storage, "get_protected_players", s.get_protected_players)
    return s


def run(coro):
    return asyncio.run(coro)


def test_storage_add_update_remove(store):
    assert run(storage.add_temporary_protected(1, "ann", 10, "away"))["status"] == "added"
    assert run(storage.add_temporary_protected(1, "Ann", 20, "away longer"))["status"] == "updated"
    assert set(run(storage.get_temporary_protected(1))) == {"ann"}
    assert run(storage.remove_temporary_protected(1, "ANN")) is True
    assert run(storage.remove_temporary_protected(1, "Ann")) is False


def test_storage_refuses_untracked_and_already_permanent(store):
    assert run(storage.add_temporary_protected(1, "Stranger", 5))["status"] == "not_tracked"
    assert run(storage.add_temporary_protected(1, "Cy", 5))["status"] == "permanent"
    assert store.cfg.get("temporary_protected_players", {}) == {}


def test_making_someone_permanent_replaces_their_temporary_protection(store):
    run(storage.add_temporary_protected(1, "Ann", 10))
    assert "ann" in store.cfg["temporary_protected_players"]
    run(storage.add_protected_player(1, "Ann"))
    assert "ann" not in store.cfg["temporary_protected_players"]
    assert "Ann" in store.cfg["protected_players"]


# ---------- the Last Active list ----------
def P(name, hours=2):
    return {"name": name, "last_match_at": (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()}


def _embed(permanent, temp_names):
    cfg = {"players": ["Ann", "Bob", "Cy"], "language": "en"}
    temp = {}
    for n in temp_names:
        set_temporary(cfg, n, days=7)
    temp = active_temporary_protected(cfg)
    e = build_last_active_embed(1, "T", cfg, [P("Ann"), P("Bob"), P("Cy")], [], permanent, temp)
    rows = "\n".join(f.value for f in e.fields if "**" in f.value)
    return e, rows


def test_the_list_marks_the_two_kinds_differently():
    e, rows = _embed(["Cy"], ["Ann"])
    assert "**Cy** 🛡️" in rows and "**Ann** ⏳" in rows and "**Bob** —" in rows
    names = [f.name for f in e.fields]
    assert "🛡️ Permanently protected" in names and "⏳ Temporarily protected" in names
    assert "🛡️ = Permanently protected" in e.footer.text and "⏳ = Temporarily protected" in e.footer.text


def test_with_only_permanent_protection_nothing_changes():
    e, rows = _embed(["Cy"], [])
    assert "⏳" not in rows and "⏳" not in e.footer.text
    assert "🛡️ Protected players" in [f.name for f in e.fields]                   # the original label
    assert e.footer.text.endswith(__import__("translations").get_translation("en", "protected_footer"))


def test_with_only_temporary_protection():
    e, rows = _embed([], ["Ann"])
    assert "**Ann** ⏳" in rows and "🛡️" not in rows
    assert "⏳ = Temporarily protected" in e.footer.text and "🛡️" not in e.footer.text


def test_a_player_on_both_lists_shows_as_permanent():
    e, rows = _embed(["Ann"], ["Ann"])
    assert "**Ann** 🛡️" in rows and "⏳" not in rows


def test_the_whole_report_hides_ended_protections_and_cleans_them_up(monkeypatch):
    cfg = {"players": ["Ann", "Bob"], "protected_players": [], "language": "en"}
    set_temporary(cfg, "Ann", days=7)
    set_temporary(cfg, "Bob", days=1, now=datetime.now(timezone.utc) - timedelta(days=3))     # ended 2 days ago
    s = Store(cfg)

    class FakePubg:
        async def get_last_active_times(self, names): return [P("Ann"), P("Bob")], []

    monkeypatch.setattr(reports, "storage", s)
    monkeypatch.setattr(reports, "modify_guild", s.modify_guild)
    monkeypatch.setattr(reports, "_get_pubg", lambda: FakePubg())
    embed, _ = run(reports.fetch_last_active_report(1, "T"))
    rows = "\n".join(f.value for f in embed.fields if "**" in f.value)
    assert "**Ann** ⏳" in rows and "**Bob** —" in rows
    assert list(cfg["temporary_protected_players"]) == ["ann"]                              # Bob's ended entry was deleted


# ---------- the commands ----------
class Interaction:
    def __init__(self):
        self.guild_id = 1
        self.user = object()
        self.sent = []
        self.response = type("R", (), {"defer": staticmethod(self._defer)})()
        self.followup = type("F", (), {"send": staticmethod(self._send)})()

    async def _defer(self, *a, **k): pass
    async def _send(self, content=None, **kw): self.sent.append((content, kw))


def _call(impl, *args):
    i = Interaction()
    audits = []

    async def audit(*a, **k): audits.append((a, k))

    run(impl(i, *args, audit))
    return i.sent, audits


def test_add_command_messages(store):
    sent, audits = _call(addtempprotected_impl, "Stranger", 7, None)
    assert "not on the tracked player list" in sent[0][0] and sent[0][1].get("ephemeral") and not audits
    sent, _ = _call(addtempprotected_impl, "Cy", 7, None)
    assert "already permanently protected" in sent[0][0]
    sent, audits = _call(addtempprotected_impl, "Ann", 14, "on vacation")
    assert "temporarily protected until <t:" in sent[0][0] and "on vacation" in sent[0][0] and len(audits) == 1
    sent, _ = _call(addtempprotected_impl, "Bob", None, None)
    assert "until you remove it" in sent[0][0]


def test_remove_command(store):
    _call(addtempprotected_impl, "Ann", 14, None)
    sent, audits = _call(removetempprotected_impl, "ann")
    assert "Removed **ann**" in sent[0][0] and len(audits) == 1
    sent, _ = _call(removetempprotected_impl, "ann")
    assert "not temporarily protected" in sent[0][0]


def test_list_command_separates_permanent_and_temporary(store):
    run(storage.add_temporary_protected(1, "Ann", 14, "vacation"))
    i = Interaction()
    run(listprotected_impl(i))
    text = i.sent[0][0]
    assert "🛡️ **Permanently protected (1)**\nCy" in text
    assert "⏳ **Temporarily protected (1)**" in text and "• Ann — until <t:" in text and "vacation" in text


def test_list_command_when_nobody_is_protected(monkeypatch):
    s = Store({"players": ["Ann"], "protected_players": [], "language": "en"})
    for name in ("get_guild", "modify_guild", "get_protected_players"):
        monkeypatch.setattr(storage, name, getattr(s, name))
    i = Interaction()
    run(listprotected_impl(i))
    assert i.sent and "<t:" not in i.sent[0][0]


# ---------- the commands are registered in bot.py ----------
def test_slash_commands_are_registered():
    tree = ast.parse((ROOT / "bot.py").read_text(encoding="utf-8"))
    commands = {n.name for n in ast.walk(tree)
                if isinstance(n, ast.AsyncFunctionDef)
                and any("tree.command" in ast.unparse(d) for d in n.decorator_list)}
    assert {"addtempprotected", "removetempprotected", "addprotected", "removeprotected", "listprotected"} <= commands
    assert len(commands) < 100                                     # Discord's limit for global slash commands
