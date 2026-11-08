"""The one-time seeding script turns the corrected list into counts that keep going by themselves."""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import seed_last_active as seed
from modules.reports import apply_last_active_rules

ROOT = Path(__file__).resolve().parent.parent
REF = datetime(2026, 11, 7, 6, 0, tzinfo=timezone.utc)
ENTRIES = seed.parse_list(seed.CORRECT_LIST)


def _cfg():
    return {"players": [name for name, _ in ENTRIES], "protected_players": []}


def P(name, last=None):
    return {"name": name, "last_match_at": last.isoformat() if last else None}


def test_the_whole_list_is_read():
    assert len(ENTRIES) == 74
    assert dict(ENTRIES)["Ajms32xx"] == 146 and dict(ENTRIES)["El_Grundler23"] == 14
    assert dict(ENTRIES)["FreeHelmetChecks"] is None            # "Less than 1 hour ago": left to the API
    assert dict(ENTRIES)["keyuchehun"] == 1


def test_every_player_past_the_api_window_shows_exactly_the_listed_days():
    c = _cfg()
    seed.seed(c, ENTRIES, REF, set())
    old = [(n, d) for n, d in ENTRIES if d is not None and d >= 14]
    assert len(old) == 15
    players = [P(n) for n, _ in old]                              # the API has no matches for them
    apply_last_active_rules(c, players, REF)
    assert {p["name"]: p["days_inactive"] for p in players} == dict(old)


def test_counts_keep_going_one_day_at_a_time_after_seeding():
    c = _cfg()
    seed.seed(c, ENTRIES, REF, set())
    for k in (1, 2, 7, 30):
        players = [P("Ajms32xx"), P("Ellicool")]
        apply_last_active_rules(c, players, REF + timedelta(days=k))
        assert players[0]["days_inactive"] == 146 + k and players[1]["days_inactive"] == 58 + k


def test_a_player_the_api_reports_as_older_than_the_list_shows_the_listed_days():
    c = _cfg()
    seed.seed(c, ENTRIES, REF, set())
    p = P("Luhzayy", REF - timedelta(days=13))                    # API says 13, the list says 10
    apply_last_active_rules(c, [p], REF)
    assert (REF - datetime.fromisoformat(p["last_match_at"])).days == 10


def test_a_forced_player_ignores_a_wrong_older_api_match_until_they_really_play():
    c = _cfg()
    seed.seed(c, ENTRIES, REF, {"Ajax2021"})
    ghost = P("Ajax2021", REF - timedelta(days=6))                # the API wrongly shows 6 days
    apply_last_active_rules(c, [ghost], REF)
    assert ghost["days_inactive"] == 30 and ghost["data_source"] == "manual"
    real = P("Ajax2021", REF + timedelta(hours=3))                # a genuine new match
    apply_last_active_rules(c, [real], REF + timedelta(hours=4))
    assert "ajax2021" not in c["manual_inactive_dates"]


def test_players_not_on_the_roster_are_reported_not_invented():
    c = {"players": ["Ann"], "protected_players": []}
    actions = seed.seed(c, [("Ann", 20), ("Stranger", 5)], REF, set())
    assert any("Stranger" in a and "not in" in a for a in actions)
    assert "stranger" not in c["last_seen_at"]


def test_dry_run_writes_nothing_and_apply_writes_with_a_backup(tmp_path):
    cfg = _cfg()
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"guilds": {"1274149985625182208": cfg}}), encoding="utf-8")
    run = lambda *extra: subprocess.run([sys.executable, str(ROOT / "seed_last_active.py"), "--data", str(path), *extra],
                                        capture_output=True, text=True, cwd=ROOT)
    before = path.read_text(encoding="utf-8")
    preview = run()
    assert preview.returncode == 0 and "PREVIEW ONLY" in preview.stdout
    assert path.read_text(encoding="utf-8") == before and not list(tmp_path.glob("*.bak-*"))
    applied = run("--apply", "--force", "Ajax2021")
    assert applied.returncode == 0, applied.stderr
    saved = json.loads(path.read_text(encoding="utf-8"))["guilds"]["1274149985625182208"]
    assert "ajms32xx" in saved["last_seen_at"] and "ajax2021" in saved["manual_inactive_dates"]
    assert len(list(tmp_path.glob("data.json.bak-before-lastactive-*"))) == 1
