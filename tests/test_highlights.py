"""Daily highlights accuracy: window, match filtering, kill-count consistency, labels."""
import os
import random
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DISCORD_TOKEN", "test")
os.environ.setdefault("PUBG_API_KEY", "test")

import pubg_api  # noqa: E402
import translations  # noqa: E402
from modules.embeds import build_highlights_embed  # noqa: E402

NOW = datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def details(match_id, hours_ago, players, *, mode="squad-fpp", mtype="official", custom=False):
    """players: {account_id: stats dict}"""
    return {
        "created_at": iso(NOW - timedelta(hours=hours_ago)),
        "participants": {pid: {"stats": {"playerId": pid, "winPlace": 5, "boosts": 1, "heals": 1, **st}, "name": pid, "team_id": 1}
                         for pid, st in players.items()},
        "telemetry_url": f"https://telemetry/{match_id}.json",
        "map_name": "Erangel", "game_mode": mode, "match_type": mtype, "is_custom": custom,
    }


def kill_events(killer, human=0, bot=0, self_=0, empty=0):
    ev = []
    for i in range(human):
        ev.append({"_T": "LogPlayerKillV2", "killer": {"accountId": killer}, "victim": {"accountId": f"account.h{i}"}})
    for i in range(bot):
        ev.append({"_T": "LogPlayerKillV2", "killer": {"accountId": killer}, "victim": {"accountId": f"ai.{i}"}})
    for _ in range(self_):
        ev.append({"_T": "LogPlayerKillV2", "killer": {"accountId": killer}, "victim": {"accountId": killer}})
    for _ in range(empty):
        ev.append({"_T": "LogPlayerKillV2", "killer": {"accountId": killer}, "victim": {"accountId": ""}})
    return ev


class World:
    """A fake PUBG: players, their matches (newest first) and telemetry."""

    def __init__(self):
        self.players = {}      # name -> {"id", "match_ids"}
        self.matches = {}      # match_id -> details
        self.telemetry = {}    # match_id -> events

    def add(self, name, pid):
        self.players[name] = {"id": pid, "name": name, "match_ids": []}

    def match(self, mid, hours_ago, per_player, telemetry=(), **kw):
        self.matches[mid] = details(mid, hours_ago, per_player, **kw)
        self.telemetry[mid] = list(telemetry)
        for name, p in self.players.items():
            if p["id"] in per_player:
                p["match_ids"].append(mid)

    def client(self, monkeypatch):
        c = pubg_api.PubgClient("key")

        async def get_players_by_name(names):
            return [dict(self.players[n]) for n in names if n in self.players]

        async def get_match_details(mid):
            return self.matches[mid]

        async def get_telemetry(url):
            return self.telemetry[url.rsplit("/", 1)[1].replace(".json", "")]
        monkeypatch.setattr(c, "get_players_by_name", get_players_by_name)
        monkeypatch.setattr(c, "_get_match_details", get_match_details)
        monkeypatch.setattr(c, "_get_telemetry", get_telemetry)
        return c


def by_name(players):
    return {p["name"]: p["daily"] for p in players}


# ------------------------------------------------------------------ the reported 65 vs 342 case
async def test_zombie_mode_telemetry_cannot_create_342_human_kills(monkeypatch):
    w = World()
    w.add("SoonDuBuSpicy", "account.a")
    w.add("wrckless", "account.b")
    # SoonDuBuSpicy: two normal squad matches, 65 kills total
    w.match("m1", 3, {"account.a": {"kills": 40}}, kill_events("account.a", human=10, bot=30))
    w.match("m2", 5, {"account.a": {"kills": 25}}, kill_events("account.a", human=5, bot=20))
    # wrckless: normal matches with 8 kills total ...
    w.match("m3", 6, {"account.b": {"kills": 5}}, kill_events("account.b", human=2, bot=3))
    w.match("m4", 7, {"account.b": {"kills": 3}}, kill_events("account.b", human=1, bot=2))
    # ... plus a zombie event match where the stats endpoint shows 2 kills but telemetry has 340 events
    w.match("m5", 8, {"account.b": {"kills": 2}}, kill_events("account.b", human=200, bot=40, empty=100),
            mode="zombie-squad-fpp", mtype="event")
    # newest-first order, as the real API returns
    for p in w.players.values():
        p["match_ids"].sort(key=lambda m: w.matches[m]["created_at"], reverse=True)

    found, _ = await w.client(monkeypatch).get_daily_activity_report(["SoonDuBuSpicy", "wrckless"], hours=24)
    d = by_name(found)
    assert d["SoonDuBuSpicy"]["kills"] == 65
    assert d["wrckless"]["kills"] == 8
    assert d["wrckless"]["human_kills"] == 3 and d["wrckless"]["bot_kills"] == 5
    assert d["wrckless"]["skipped_nonstandard"] == 1
    assert d["wrckless"]["matches"] == 2  # the zombie match is not counted at all


async def test_standard_match_with_inflated_telemetry_is_clamped_to_stats(monkeypatch):
    w = World()
    w.add("P", "account.p")
    w.match("m1", 2, {"account.p": {"kills": 4}}, kill_events("account.p", human=300, bot=40))
    found, _ = await w.client(monkeypatch).get_daily_activity_report(["P"], hours=24)
    d = by_name(found)["P"]
    assert d["human_kills"] + d["bot_kills"] <= d["kills"] == 4


async def test_victims_without_an_account_id_are_not_human_kills(monkeypatch):
    w = World()
    w.add("P", "account.p")
    w.match("m1", 2, {"account.p": {"kills": 6}}, kill_events("account.p", human=2, bot=1, empty=50))
    d = by_name((await w.client(monkeypatch).get_daily_activity_report(["P"], hours=24))[0])["P"]
    assert (d["human_kills"], d["bot_kills"]) == (2, 1)


@pytest.mark.parametrize("mtype,mode,custom", [
    ("custom", "squad-fpp", False), ("event", "squad", False), ("training", "squad-fpp", False),
    ("arcade", "tdm", False), ("official", "tdm", False), ("official", "war-squad", False),
    ("official", "zombie-duo-fpp", False), ("official", "lab-fpp", False), ("official", "squad-fpp", True),
])
async def test_non_standard_matches_are_excluded(monkeypatch, mtype, mode, custom):
    w = World()
    w.add("P", "account.p")
    w.match("m1", 2, {"account.p": {"kills": 9}}, kill_events("account.p", human=9), mode=mode, mtype=mtype, custom=custom)
    d = by_name((await w.client(monkeypatch).get_daily_activity_report(["P"], hours=24))[0])["P"]
    assert d["matches"] == 0 and d["kills"] == 0 and d["skipped_nonstandard"] == 1


@pytest.mark.parametrize("mtype,mode", [
    ("official", "squad-fpp"), ("official", "solo"), ("official", "duo-fpp"), ("competitive", "squad"),
    ("official", "normal-squad-fpp"), ("official", "esports-squad"), ("", ""),
])
async def test_standard_matches_are_kept(monkeypatch, mtype, mode):
    w = World()
    w.add("P", "account.p")
    w.match("m1", 2, {"account.p": {"kills": 3}}, kill_events("account.p", human=3), mode=mode, mtype=mtype)
    d = by_name((await w.client(monkeypatch).get_daily_activity_report(["P"], hours=24))[0])["P"]
    assert d["matches"] == 1 and d["kills"] == 3


# ------------------------------------------------------------------ the 24 hour window
async def test_only_the_last_24_hours_count(monkeypatch):
    w = World()
    w.add("P", "account.p")
    w.match("new1", 0.5, {"account.p": {"kills": 1}})
    w.match("new2", 23.5, {"account.p": {"kills": 2}})
    w.match("old1", 24.5, {"account.p": {"kills": 50}})
    w.match("old2", 40, {"account.p": {"kills": 50}})
    w.players["P"]["match_ids"].sort(key=lambda m: w.matches[m]["created_at"], reverse=True)
    d = by_name((await w.client(monkeypatch).get_daily_activity_report(["P"], hours=24))[0])["P"]
    assert d["kills"] == 3 and d["matches"] == 2
    d6 = by_name((await w.client(monkeypatch).get_daily_activity_report(["P"], hours=6))[0])["P"]
    assert d6["kills"] == 1 and d6["matches"] == 1


async def test_window_metadata_matches_the_requested_hours(monkeypatch):
    w = World()
    w.add("P", "account.p")
    w.match("m1", 1, {"account.p": {"kills": 1}})
    d = by_name((await w.client(monkeypatch).get_daily_activity_report(["P"], hours=24))[0])["P"]
    start, end = datetime.fromisoformat(d["window_start"]), datetime.fromisoformat(d["window_end"])
    assert end - start == timedelta(hours=24)
    assert abs((end - datetime.now(timezone.utc)).total_seconds()) < 60


# ------------------------------------------------------------------ randomised invariant
async def test_invariants_hold_for_random_worlds(monkeypatch):
    rng = random.Random(1234)
    for _ in range(25):
        w = World()
        names = [f"P{i}" for i in range(rng.randint(1, 6))]
        for i, n in enumerate(names):
            w.add(n, f"account.{i}")
        for m in range(rng.randint(1, 10)):
            who = {f"account.{i}": {"kills": rng.randint(0, 12)} for i in range(len(names)) if rng.random() < 0.7}
            if not who:
                continue
            tele = []
            for pid, st in who.items():
                tele += kill_events(pid, human=rng.randint(0, 80), bot=rng.randint(0, 80), self_=rng.randint(0, 2), empty=rng.randint(0, 80))
            w.match(f"m{m}", rng.uniform(0, 30), who, tele,
                    mode=rng.choice(["squad-fpp", "duo", "zombie-squad", "tdm"]), mtype=rng.choice(["official", "event", "custom"]))
        for p in w.players.values():
            p["match_ids"].sort(key=lambda m: w.matches[m]["created_at"], reverse=True)
        found, _ = await w.client(monkeypatch).get_daily_activity_report(names, hours=24)
        for d in by_name(found).values():
            assert d["human_kills"] + d["bot_kills"] <= d["kills"]
            assert d["best_match_kills"] <= d["kills"]
            assert d["stooge_kills"] == d["self_kills"] + d["team_kills"]


# ------------------------------------------------------------------ the match payload parser
async def test_match_details_expose_mode_and_type(monkeypatch):
    c = pubg_api.PubgClient("key")

    async def fake_request(path, params=None, rate_limited=True):
        return {"data": {"attributes": {"createdAt": iso(NOW), "mapName": "Baltic_Main", "gameMode": "zombie-squad-fpp",
                                         "matchType": "event", "isCustomMatch": False}}, "included": []}
    monkeypatch.setattr(c, "_request", fake_request)
    d = await c._get_match_details("x")
    assert (d["game_mode"], d["match_type"], d["is_custom"]) == ("zombie-squad-fpp", "event", False)
    assert pubg_api.is_standard_match(d) is False


# ------------------------------------------------------------------ the embed
def fake_players():
    d = {"kills": 65, "damageDealt": 7000.0, "headshotKills": 5, "revives": 1, "assists": 2, "wins": 1, "matches": 8,
         "human_kills": 10, "bot_kills": 30, "self_kills": 0, "team_kills": 0, "stooge_kills": 0, "boosts": 3, "heals": 4,
         "road_kills": 0, "swim_distance": 0.0, "weapons_acquired": 100, "loot_ratio": 1.5, "best_zero_kill_placement": None,
         "best_match_kills": 21, "best_match_damage": 1900.0, "best_match_headshots": 2, "longestKill": 100,
         "window_start": (NOW - timedelta(hours=24)).isoformat(), "window_end": NOW.isoformat(), "skipped_nonstandard": 0}
    return [{"name": "Alpha", "id": "a", "daily": d}]


@pytest.mark.parametrize("lang", list(translations.TRANSLATIONS))
def test_embed_text_is_correct_in_every_language(lang):
    e = build_highlights_embed("Clan", {"language": lang}, fake_players(), [], 24, live=True).to_dict()
    desc = e["description"]
    assert "24" in desc and "<t:" in desc and "→" in desc  # exact window shown
    assert "02:00" not in desc  # no more "since daily reset"
    top = next(f for f in e["fields"] if f["name"] == translations.get_translation(lang, "top_5"))["value"]
    allfields = " ".join(f["value"] + f["name"] for f in e["fields"]) + desc
    assert "Recent matches" not in allfields and "Players:" not in allfields and "match:" not in allfields
    assert "**" not in desc.replace("<t:", "")  # unit words are plain words, not bold headings
    assert "top_5" not in allfields and "unit_" not in allfields
    assert "8" in top


def test_english_wording_and_footers():
    live = build_highlights_embed("Clan", {"language": "en"}, fake_players(), [], 24, live=True).to_dict()
    assert live["description"].startswith("Based on 1 player who played in the last 24 hours.")
    assert "live-updating" in live["footer"]["text"]
    ondemand = build_highlights_embed("Clan", {"language": "en"}, fake_players(), [], 6, live=False).to_dict()
    assert ondemand["description"].startswith("Based on 1 player who played in the last 6 hours.")
    assert "last 6 hours" in ondemand["footer"]["text"] and "live-updating" not in ondemand["footer"]["text"]
    line = next(f["value"] for f in live["fields"] if f["name"] == "Top 5")
    assert "8 matches" in line and "10 human / 30 bot" in line


def test_embed_works_without_window_metadata():
    pl = fake_players()
    for k in ("window_start", "window_end"):
        pl[0]["daily"].pop(k)
    e = build_highlights_embed("Clan", {"language": "en"}, pl, [], 24).to_dict()
    assert "<t:" not in e["description"] and e["description"].endswith("24 hours.")
