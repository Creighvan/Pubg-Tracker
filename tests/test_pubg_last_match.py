"""PubgClient.get_last_active_times: newest of the first three matches, failures flagged not guessed."""
import asyncio

from pubg_api import PubgClient


def _client(monkeypatch, players, created):
    c = PubgClient("key", shard="steam")

    async def by_name(names):
        return [dict(p) for p in players]

    async def created_at(match_id):
        v = created.get(match_id)
        if v == "ERR":
            return None
        return v

    monkeypatch.setattr(c, "get_players_by_name", by_name)
    monkeypatch.setattr(c, "get_match_created_at", created_at)
    return c


def _run(c, names):
    found, _ = asyncio.run(c.get_last_active_times(names))
    return {p["name"]: p for p in found}


def test_takes_the_newest_of_the_first_three_matches(monkeypatch):
    players = [{"name": "Ann", "id": "1", "match_ids": ["a", "b", "c", "d"]}]
    created = {"a": "2026-11-01T10:00:00Z", "b": "2026-11-05T10:00:00Z", "c": "2026-11-03T10:00:00Z", "d": "2026-11-09T10:00:00Z"}
    ann = _run(_client(monkeypatch, players, created), ["Ann"])["Ann"]
    assert ann["last_match_at"] == "2026-11-05T10:00:00Z" and ann["match_lookup_failed"] is False


def test_one_failed_request_does_not_hide_the_others(monkeypatch):
    players = [{"name": "Ann", "id": "1", "match_ids": ["a", "b", "c"]}]
    created = {"a": "ERR", "b": "2026-11-05T10:00:00Z", "c": "ERR"}
    ann = _run(_client(monkeypatch, players, created), ["Ann"])["Ann"]
    assert ann["last_match_at"] == "2026-11-05T10:00:00Z" and ann["match_lookup_failed"] is False


def test_all_requests_failing_is_flagged_not_treated_as_inactive(monkeypatch):
    players = [{"name": "Ann", "id": "1", "match_ids": ["a", "b"]}]
    ann = _run(_client(monkeypatch, players, {"a": "ERR", "b": "ERR"}), ["Ann"])["Ann"]
    assert ann["last_match_at"] is None and ann["match_lookup_failed"] is True


def test_no_matches_in_the_window_is_genuinely_none(monkeypatch):
    players = [{"name": "Ann", "id": "1", "match_ids": []}]
    ann = _run(_client(monkeypatch, players, {}), ["Ann"])["Ann"]
    assert ann["last_match_at"] is None and ann["match_lookup_failed"] is False
