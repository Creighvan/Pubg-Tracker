"""Permanent protection (🛡️) versus temporary protection for members who reached out (⏳)."""
import ast
import asyncio
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import storage
from commands.protected import (
    addleadership_impl, addtempprotected_impl, listprotected_impl, removeleadership_impl, removetempprotected_impl,
)
from modules import reports
from modules.embeds import build_last_active_embed
from modules.protection import (
    LEADERSHIP_ICON as L, active_temporary_protected, get_leadership, protection_kind, purge_expired_temporary, set_leadership, set_temporary,
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



# ---------- clan leaders and managers: their own category (👑) ----------
def test_priority_is_leadership_then_permanent_then_temporary():
    cfg = {"protected_players": ["Ann", "Bob"]}
    set_leadership(cfg, "Ann", "Manager")
    set_temporary(cfg, "Bob", days=5, now=NOW)
    set_temporary(cfg, "Cy", days=5, now=NOW)
    assert protection_kind(cfg, "Ann", NOW) == "leadership"
    assert protection_kind(cfg, "Bob", NOW) == "permanent"
    assert protection_kind(cfg, "Cy", NOW) == "temporary"
    assert get_leadership(cfg)["ann"]["role"] == "Manager"


def test_adding_a_leader_moves_them_off_the_other_two_lists(store):
    store.cfg["protected_players"] = ["Cy", "Ann"]
    run(storage.add_temporary_protected(1, "Bob", 10))
    r = run(storage.add_leadership(1, "bob", "Manager"))
    assert r["status"] == "added" and r["moved_from"] == ["temporary"]
    assert "bob" not in store.cfg["temporary_protected_players"]
    r = run(storage.add_leadership(1, "Ann", "Leader"))
    assert r["moved_from"] == ["permanent"] and store.cfg["protected_players"] == ["Cy"]
    assert run(storage.add_leadership(1, "Ann", "Manager"))["status"] == "updated"
    assert run(storage.add_leadership(1, "Stranger"))["status"] == "not_tracked"
    assert set(run(storage.get_leadership_protected(1))) == {"bob", "ann"}
    assert run(storage.remove_leadership(1, "BOB")) is True and run(storage.remove_leadership(1, "Bob")) is False


def test_a_leader_cannot_also_be_made_temporary(store):
    run(storage.add_leadership(1, "Ann", "Leader"))
    assert run(storage.add_temporary_protected(1, "Ann", 5))["status"] == "leadership"


def _embed3(permanent, temp_names, leaders):
    cfg = {"players": ["Ann", "Bob", "Cy", "Di"], "language": "en"}
    for n in temp_names:
        set_temporary(cfg, n, days=7)
    for n, role in leaders:
        set_leadership(cfg, n, role)
    e = build_last_active_embed(1, "T", cfg, [P("Ann"), P("Bob"), P("Cy"), P("Di")], [], permanent,
                                active_temporary_protected(cfg), get_leadership(cfg))
    return e, "\n".join(f.value for f in e.fields if "**" in f.value)


def test_all_three_kinds_are_told_apart_on_the_list():
    e, rows = _embed3(["Bob"], ["Cy"], [("Ann", "Leader")])
    assert f"**Ann** {L}" in rows and "**Bob** 🛡️" in rows and "**Cy** ⏳" in rows and "**Di** —" in rows
    names = [f.name for f in e.fields]
    assert f"{L} Leaders & managers" in names and "🛡️ Permanently protected" in names and "⏳ Temporarily protected" in names
    for legend in (f"{L} = Clan leader or manager", "🛡️ = Permanently protected", "⏳ = Temporarily protected"):
        assert legend in e.footer.text


def test_leaders_only_shows_just_their_legend():
    e, rows = _embed3([], [], [("Ann", "Manager"), ("Bob", "Leader")])
    assert f"**Ann** {L}" in rows and f"**Bob** {L}" in rows and "🛡️" not in e.footer.text and "⏳" not in e.footer.text
    assert f"{L} = Clan leader or manager" in e.footer.text


def test_a_leader_who_is_also_on_the_permanent_list_counts_once_as_a_leader():
    e, rows = _embed3(["Ann", "Bob"], [], [("Ann", "Leader")])
    assert f"**Ann** {L}" in rows and "**Bob** 🛡️" in rows
    counts = {f.name: f.value for f in e.fields}
    assert counts[f"{L} Leaders & managers"] == "1" and counts["🛡️ Permanently protected"] == "1"


def test_leader_commands_and_list(store):
    store.cfg["protected_players"] = ["Cy", "Ann"]
    sent, audits = _call(addleadership_impl, "ann", "Manager")
    assert "recorded as a clan manager" in sent[0][0] and "Moved off the permanent protection list" in sent[0][0] and len(audits) == 1
    sent, _ = _call(addleadership_impl, "Stranger", "Leader")
    assert "not on the tracked player list" in sent[0][0]
    sent, _ = _call(addtempprotected_impl, "Ann", 5, None)
    assert "clan leader or manager" in sent[0][0]

    i = Interaction()
    run(listprotected_impl(i))
    text = i.sent[0][0]
    assert f"{L} **Clan leaders & managers (1)**\n• Ann — Manager" in text
    assert "🛡️ **Permanently protected (1)**\nCy" in text                  # Ann is not listed twice

    sent, audits = _call(removeleadership_impl, "ann")
    assert "Removed **ann**" in sent[0][0] and len(audits) == 1
    sent, _ = _call(removeleadership_impl, "ann")
    assert "not on the clan leaders" in sent[0][0]


def test_leader_commands_are_registered():
    tree = ast.parse((ROOT / "bot.py").read_text(encoding="utf-8"))
    commands = {n.name for n in ast.walk(tree)
                if isinstance(n, ast.AsyncFunctionDef) and any("tree.command" in ast.unparse(d) for d in n.decorator_list)}
    assert {"addleadership", "removeleadership"} <= commands and len(commands) < 100
