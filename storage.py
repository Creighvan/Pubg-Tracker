"""
Minimal JSON-file storage for per-Discord-server settings.

No database needed. Everything lives in data.json next to the bot, which
persists as long as the disk under it persists (fine for a small VM; if you
redeploy to a platform with an ephemeral filesystem, mount a persistent
volume for this file or swap this module for SQLite/Postgres later).
"""

import copy
import json
import os
import threading

DATA_PATH = os.path.join(os.path.dirname(__file__), "data.json")
_lock = threading.Lock()

_DEFAULT_GUILD = {
    "players": [],  # list of PUBG player names tracked for this server's clan
    "game_mode": "squad-fpp",
    "post_channel_id": None,
    "post_interval_hours": 6,  # how often the auto digest posts (used only if digest_hour_est is None)
    "digest_enabled": True,
    "digest_hour_est": None,  # 0-23, Eastern time; if set, posts once/day at this time instead of by interval
    "digest_minute_est": 0,  # 0, 15, 30, or 45
    "last_post_at": None,  # ISO timestamp of the last auto digest post
    "last_activity_channel_id": None,  # where the 24h "last active" report posts
    "activity_enabled": True,
    "activity_hour_est": None,  # 0-23, Eastern time; if set, posts once/day at this time
    "activity_minute_est": 0,  # 0, 15, 30, or 45
    "last_activity_posted_at": None,  # ISO timestamp of the last activity report
    "ranked_channel_id": None,  # where the 24h ranked TPP report posts
    "ranked_enabled": True,
    "ranked_hour_est": None,  # 0-23, Eastern time; if set, posts once/day at this time
    "ranked_minute_est": 0,  # 0, 15, 30, or 45
    "ranked_posted_at": None,  # ISO timestamp of the last ranked report
    "ranked_queue": "squad",  # squad, duo, or solo — TPP (no '-fpp' suffix)
    "ranked_known_players": {},  # game mode -> players previously found with ranked activity
    "highlights_channel_id": None,  # where the 24h "daily highlights" report posts
    "highlights_enabled": True,
    "highlights_hour_est": None,  # 0-23, Eastern time; if set, posts once/day at this time
    "highlights_minute_est": 0,  # 0, 15, 30, or 45
    "highlights_posted_at": None,  # ISO timestamp of the last highlights report
    "clan_name": None,
    "pubg_clan_name": None,  # exact PUBG clan name used by the clan-level report
    "pubg_clan_id": None,  # official clan ID, resolved from a clan member
    "clan_channel_id": None,  # destination for the weekly clan-level report
    "clan_level_enabled": True,
    "clan_weekday_est": None,  # Monday=0 through Sunday=6; None disables scheduling
    "clan_hour_est": 0,
    "clan_minute_est": 0,
    "clan_posted_at": None,
    "clan_last_level": None,  # most recent successfully scheduled snapshot
    "clan_last_member_count": None,
    "survival_channel_id": None,  # destination for the weekly Survival Mastery report
    "survival_enabled": True,
    "survival_weekday_est": None,  # Monday=0 through Sunday=6; None disables scheduling
    "survival_hour_est": 12,
    "survival_minute_est": 0,
    "survival_posted_at": None,
    "donation_channel_id": None,  # opt-in channel for the weekly donation message
    "donation_enabled": True,
    "donation_hour_est": 12,  # Sunday noon Eastern by default
    "donation_minute_est": 0,
    "donation_posted_at": None,
    "discord_links": {},  # pubg_name.lower() -> discord user id (int), for @mentions/congrats
    "leaderboard_shard": "pc-na",  # platform-REGION shard, only used by the leaderboards endpoint
    "leaderboard_queue": "squad",  # squad, duo, or solo — TPP
}


def _load() -> dict:
    if not os.path.exists(DATA_PATH):
        return {}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save(data: dict):
    tmp_path = DATA_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, DATA_PATH)


def get_guild(guild_id: int) -> dict:
    with _lock:
        data = _load()
        guild = data.get(str(guild_id))
        # deepcopy, not a plain dict() copy: the defaults contain mutable
        # lists/dicts (players, discord_links, ranked_known_players). A
        # shallow copy shares those with _DEFAULT_GUILD itself, so the first
        # mutation for a brand-new guild (e.g. /addplayer appending) rewrote
        # the module-level defaults and the NEXT new guild inherited the
        # previous one's roster and links.
        if guild is None:
            guild = copy.deepcopy(_DEFAULT_GUILD)
        else:
            merged = copy.deepcopy(_DEFAULT_GUILD)
            merged.update(guild)
            guild = merged
        return guild


def save_guild(guild_id: int, guild_data: dict):
    with _lock:
        data = _load()
        data[str(guild_id)] = guild_data
        _save(data)


def all_guild_ids() -> list[int]:
    with _lock:
        data = _load()
        return [int(g) for g in data.keys()]


def add_player(guild_id: int, name: str) -> bool:
    guild = get_guild(guild_id)
    lowered = [p.lower() for p in guild["players"]]
    if name.lower() in lowered:
        return False
    guild["players"].append(name)
    guild["ranked_known_players"] = {}
    save_guild(guild_id, guild)
    return True


def add_players(guild_id: int, names: list[str]) -> tuple[list[str], list[str]]:
    """
    Bulk-add many players in a single save. Returns (added, duplicates).
    Preserves the casing of the first occurrence for duplicates within the
    input list itself.
    """
    guild = get_guild(guild_id)
    existing_lower = {p.lower() for p in guild["players"]}
    added: list[str] = []
    duplicates: list[str] = []
    seen_this_batch: set[str] = set()

    for name in names:
        name = name.strip()
        if not name:
            continue
        lowered = name.lower()
        if lowered in existing_lower or lowered in seen_this_batch:
            duplicates.append(name)
            continue
        guild["players"].append(name)
        existing_lower.add(lowered)
        seen_this_batch.add(lowered)
        added.append(name)

    if added:
        guild["ranked_known_players"] = {}
        save_guild(guild_id, guild)
    return added, duplicates


def remove_player(guild_id: int, name: str) -> bool:
    guild = get_guild(guild_id)
    before = len(guild["players"])
    guild["players"] = [p for p in guild["players"] if p.lower() != name.lower()]
    changed = len(guild["players"]) != before
    if changed:
        guild["ranked_known_players"] = {}
        save_guild(guild_id, guild)
    return changed


def link_discord_account(guild_id: int, pubg_name: str, discord_user_id: int):
    """Links a PUBG name to a Discord user ID for this server, so reports
    can @mention the right person. Overwrites any existing link for that
    name."""
    guild = get_guild(guild_id)
    guild["discord_links"][pubg_name.lower()] = discord_user_id
    save_guild(guild_id, guild)


def unlink_discord_account(guild_id: int, pubg_name: str) -> bool:
    guild = get_guild(guild_id)
    existed = guild["discord_links"].pop(pubg_name.lower(), None) is not None
    if existed:
        save_guild(guild_id, guild)
    return existed


def get_discord_id(guild_id: int, pubg_name: str) -> int | None:
    guild = get_guild(guild_id)
    return guild["discord_links"].get(pubg_name.lower())
