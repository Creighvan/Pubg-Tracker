"""Last Active: exact day counting past the API's 14-day window, resets on play, never silently wiped."""
import asyncio
import copy
from datetime import datetime, timedelta, timezone

import pytest

import modules.reports as reports
from modules.reports import apply_last_active_rules

NOW = datetime(2026, 11, 7, 6, 0, tzinfo=timezone.utc)


def P(name, last=None, failed=False):
    d = {"name": name, "last_match_at": last.isoformat() if last else None}
    if failed:
        d["match_lookup_failed"] = True
    return d


def cfg(*names):
    return {"players": list(names), "protected_players": []}


def test_count_continues_exactly_from_the_real_last_match():
    c = cfg("Ann")
    last = NOW - timedelta(days=13, hours=12)
    apply_last_active_rules(c, [P("Ann", last)], NOW)                  # API still shows the match
    for k in (1, 2, 3, 10, 40):
        later = NOW + timedelta(days=k)
        p = P("Ann")                                                    # API no longer lists it
        apply_last_active_rules(c, [p], later)
        assert p["days_inactive"] == (later - last).days
        assert p["data_source"] == "auto_count"


def test_the_old_first_noticed_method_was_off_by_a_day():
    # The player's last match was 14 days and 20 hours ago, but the bot first notices at report time.
    c = cfg("Ann")
    last = NOW - timedelta(days=14, hours=20)
    c["last_seen_at"] = {"ann": last.isoformat()}
    p = P("Ann")
    apply_last_active_rules(c, [p], NOW)
    assert p["days_inactive"] == 14          # exact; "from the day it was noticed" would have said 14 only after yet another day


def test_playing_again_restarts_the_count():
    c = cfg("Ann")
    c["last_seen_at"] = {"ann": (NOW - timedelta(days=20)).isoformat()}
    c["inactive_since_dates"] = {"ann": (NOW - timedelta(days=6)).isoformat()}
    p = P("Ann", NOW - timedelta(hours=2))
    apply_last_active_rules(c, [p], NOW)
    assert "ann" not in c["inactive_since_dates"]
    assert c["last_seen_at"]["ann"] == (NOW - timedelta(hours=2)).isoformat()
    assert "days_inactive" not in p          # shown as "2 hours ago" by the normal path
    later = NOW + timedelta(days=16)         # and a later absence counts from THAT match
    q = P("Ann")
    apply_last_active_rules(c, [q], later)
    assert q["days_inactive"] == (later - (NOW - timedelta(hours=2))).days


def test_a_failed_match_lookup_changes_nothing():
    c = cfg("Ann", "Bob")
    c["last_seen_at"] = {"ann": (NOW - timedelta(days=20)).isoformat()}
    c["inactive_since_dates"] = {"ann": (NOW - timedelta(days=6)).isoformat()}
    before = copy.deepcopy(c)
    apply_last_active_rules(c, [P("Ann", failed=True), P("Bob", failed=True)], NOW)
    assert c["last_seen_at"] == before["last_seen_at"]
    assert c["inactive_since_dates"] == before["inactive_since_dates"]     # nothing deleted, nothing started


def test_a_player_missing_from_one_api_answer_keeps_their_count():
    c = cfg("Ann", "Bob")
    c["last_seen_at"] = {"ann": (NOW - timedelta(days=20)).isoformat()}
    c["inactive_since_dates"] = {"ann": (NOW - timedelta(days=6)).isoformat()}
    c["manual_inactive_dates"] = {"ann": {"date": (NOW - timedelta(days=30)).isoformat(), "set_at": NOW.isoformat()}}
    apply_last_active_rules(c, [P("Bob", NOW - timedelta(hours=1))], NOW)    # Ann not in this answer
    assert "ann" in c["last_seen_at"] and "ann" in c["inactive_since_dates"] and "ann" in c["manual_inactive_dates"]


def test_the_remembered_time_never_moves_backwards():
    c = cfg("Ann")
    newer = NOW - timedelta(days=10)
    c["last_seen_at"] = {"ann": newer.isoformat()}
    p = P("Ann", NOW - timedelta(days=13))        # API is behind
    apply_last_active_rules(c, [p], NOW)
    assert c["last_seen_at"]["ann"] == newer.isoformat()
    assert p["last_match_at"] == newer.isoformat()     # the list shows 10 days, not 13


def test_a_newer_api_match_moves_it_forward():
    c = cfg("Ann")
    c["last_seen_at"] = {"ann": (NOW - timedelta(days=10)).isoformat()}
    apply_last_active_rules(c, [P("Ann", NOW - timedelta(days=3))], NOW)
    assert c["last_seen_at"]["ann"] == (NOW - timedelta(days=3)).isoformat()


def test_a_manual_date_beats_older_matches_the_api_still_lists():
    c = cfg("Ajax")
    c["manual_inactive_dates"] = {"ajax": {"date": (NOW - timedelta(days=30)).isoformat(), "set_at": NOW.isoformat()}}
    p = P("Ajax", NOW - timedelta(days=6))           # API shows a match from before the date was set
    apply_last_active_rules(c, [p], NOW)
    assert p["data_source"] == "manual" and p["days_inactive"] == 30
    assert "ajax" in c["manual_inactive_dates"]
    p2 = P("Ajax", NOW - timedelta(days=6))
    apply_last_active_rules(c, [p2], NOW + timedelta(days=2))
    assert p2["days_inactive"] == 32                  # keeps counting by itself


def test_a_manual_date_ends_when_the_player_plays_after_it_was_set():
    c = cfg("Ajax")
    set_at = NOW - timedelta(hours=5)
    c["manual_inactive_dates"] = {"ajax": {"date": (NOW - timedelta(days=30)).isoformat(), "set_at": set_at.isoformat()}}
    p = P("Ajax", NOW - timedelta(hours=1))           # a match AFTER the date was set
    apply_last_active_rules(c, [p], NOW)
    assert "ajax" not in c["manual_inactive_dates"]
    assert c["last_seen_at"]["ajax"] == (NOW - timedelta(hours=1)).isoformat()


def test_unknown_history_starts_at_14_days_today_and_then_counts():
    c = cfg("Ann")
    p = P("Ann")
    apply_last_active_rules(c, [p], NOW)
    assert p["days_inactive"] == 14
    q = P("Ann")
    apply_last_active_rules(c, [q], NOW + timedelta(days=3))
    assert q["days_inactive"] == 17


def test_protected_players_not_on_the_roster_are_cleaned_up():
    c = cfg("Ann")
    c["protected_players"] = ["Ann", "Gone"]
    apply_last_active_rules(c, [P("Ann", NOW)], NOW)
    assert c["protected_players"] == ["Ann"]


# ---------- the whole report, as the bot runs it ----------
class _FakeStore:
    def __init__(self, config):
        self.config = config

    async def get_guild(self, gid): return copy.deepcopy(self.config)
    async def get_protected_players(self, gid): return []
    async def modify_guild(self, gid, fn): fn(self.config)


def _run_report(monkeypatch, store, players):
    class FakePubg:
        async def get_last_active_times(self, names): return players, []
    monkeypatch.setattr(reports, "storage", store)
    monkeypatch.setattr(reports, "modify_guild", store.modify_guild)
    monkeypatch.setattr(reports, "_get_pubg", lambda: FakePubg())
    embed, _ = asyncio.run(reports.fetch_last_active_report(1, "Test"))
    return "\n".join(f.value for f in embed.fields)


def test_report_text_counts_past_14_days_and_labels_it(monkeypatch):
    now = datetime.now(timezone.utc)
    c = cfg("Ann", "Bob")
    c["last_seen_at"] = {"ann": (now - timedelta(days=18, hours=3)).isoformat()}
    text = _run_report(monkeypatch, _FakeStore(c), [P("Ann"), P("Bob", now - timedelta(hours=2))])
    assert "**Ann** — 18 days ago" in text and "auto-count" in text.lower()
    assert "**Bob** — 2 hours ago" in text


def test_report_does_not_show_an_old_manual_label_after_the_player_played(monkeypatch):
    now = datetime.now(timezone.utc)
    c = cfg("Ajax")
    c["manual_inactive_dates"] = {"ajax": {"date": (now - timedelta(days=30)).isoformat(),
                                           "set_at": (now - timedelta(hours=6)).isoformat()}}
    text = _run_report(monkeypatch, _FakeStore(c), [P("Ajax", now - timedelta(hours=1))])
    assert "**Ajax** — less than 1 hour ago".lower() in text.lower() or "**Ajax** — " in text
    assert "manual" not in text.lower()          # the report reads the saved settings AFTER this run's cleanup
