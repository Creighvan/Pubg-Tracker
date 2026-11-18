"""The award/notification features and the useless commands are gone, and the maintenance commands are owner-only."""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT = ast.parse((ROOT / "bot.py").read_text(encoding="utf-8"))

REMOVED = {
    # useless: placeholders, duplicates, or commands that saved a setting nothing reads
    "bestsquad", "matches", "refreshranked", "updateranked", "postnow", "posthighlights",
    # awards, achievement pings and Discord-account linking
    "achievements", "streaks", "weeklyawards", "pingtoggle", "linkme", "linkplayer", "unlinkme", "links",
}


def _commands():
    out = {}
    for n in BOT.body:
        if isinstance(n, ast.AsyncFunctionDef):
            decorators = [ast.unparse(d) for d in n.decorator_list]
            if any("tree.command" in d for d in decorators):
                out[n.name] = (n, decorators)
    return out


def test_removed_commands_are_not_registered():
    assert not REMOVED & set(_commands())


def test_the_commands_that_stay_are_still_there():
    keep = {"clanstats", "dailyhighlights", "lastactive", "reportstatus", "runallreports", "chickendinner",
            "addprotected", "addtempprotected", "addleadership", "listprotected", "ranked", "leaderboardstats",
            "setinactivedate", "setclan", "clanlevel", "survivalstats"}
    assert keep <= set(_commands())


def test_the_removed_modules_are_gone():
    for name in ("achievements", "streaks", "weeklyawards", "links", "matches"):
        assert not (ROOT / "commands" / f"{name}.py").exists()


def test_nothing_in_production_code_still_refers_to_them():
    gone = re.compile(r"commands\.(achievements|streaks|weeklyawards|links|matches)\b|check_achievements|update_streaks"
                      r"|link_discord_account|get_mentions_enabled|set_mentions_enabled|bestsquad_impl|postnow_impl"
                      r"|posthighlights_impl|refreshranked_impl|updateranked_impl|pingtoggle_impl|\bdiscord_links\b")
    hits = []
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(("tests/", "venv/", ".git/")) or rel.startswith("test_") or rel == "verify_deployment.py":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if gone.search(line):
                hits.append(f"{rel}:{number}")
    assert not hits, hits


def test_maintenance_commands_are_owner_only():
    commands = _commands()
    for name in ("schedulemaintenance", "clearmaintenance", "forcemaintenance"):
        node, decorators = commands[name]
        assert any("default_permissions" in d and "administrator=True" in d for d in decorators), name
        assert not any("has_permissions(manage_guild" in d for d in decorators), name
        assert "_is_admin_authorized" in ast.unparse(node.body[0]), f"{name}: the owner check must be the first thing it does"
        assert "[Admin]" in next(d for d in decorators if "tree.command" in d)


def test_server_level_settings_stay_available_to_server_admins():
    commands = _commands()
    for name in ("setmaintenancechannel", "setscheduledmaintenancechannel"):
        _, decorators = commands[name]
        assert any("has_permissions(manage_guild" in d for d in decorators), name       # these only affect the admin's own server


def test_the_leaderboard_no_longer_turns_names_into_mentions():
    import os
    os.environ.setdefault("DISCORD_TOKEN", "x.y.z")
    os.environ.setdefault("PUBG_API_KEY", "k")
    from modules.embeds import build_leaderboard_embed
    cfg = {"discord_links": {"ann": 123}, "mentions_enabled": True, "language": "en", "players": ["Ann"]}   # old saved data
    found = {"ann": {"name": "Ann", "rank": 5}}
    embed = build_leaderboard_embed(1, "T", cfg, found, 100, 1, "squad")
    text = " ".join(f.value for f in embed.fields)
    assert "**Ann**" in text and "<@123>" not in text
