"""
Minimal JSON-file storage for per-Discord-server settings.

No database needed. Everything lives in data.json next to the bot, which
persists as long as the disk under it persists (fine for a small VM; if you
redeploy to a platform with an ephemeral filesystem, mount a persistent
volume for this file or swap this module for SQLite/Postgres later).
"""

import asyncio
import copy
import json
import os
from datetime import datetime, timezone

DATA_PATH = os.path.join(os.path.dirname(__file__), "data.json")
_lock = asyncio.Lock()

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
    "last_activity_message_id": None,  # message ID for live-updating last active report
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
    "language": "en",  # preferred language code (en, zh, hi, es, ar, fr, bn, pt, id, ur)
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
    "last_feedback_prompt_at": None,  # ISO timestamp of the last 14-day feedback prompt
    "chicken_dinner_channel_id": None,  # destination for automatic win alerts (defaults to post_channel_id)
    "chicken_dinner_enabled": True,
    "chicken_dinner_posted_matches": {},  # pubg_name.lower() -> match_id already alerted, so the same win isn't reposted every 15-min tick
    "status_channel_id": None,  # destination for the live bot-status embed
    "status_message_id": None,  # id of the persistent status message this bot edits in place (None = post a fresh one next update)
    "mentions_enabled": True,  # whether linked Discord accounts get @mentioned in reports (default True)
    "cheat_reports": [],  # list of cheat report dicts
    "suspicious_players": {},  # pubg_name.lower() -> {stats, flags, last_checked}
    "cheat_report_channel_id": None,  # destination for cheat report notifications
    "protected_players": [],  # list of PUBG player names protected from inactivity removal
    "manual_inactive_dates": {},  # pubg_name.lower() -> {"date": iso_date, "set_at": iso_timestamp}
    "inactive_since_dates": {},  # pubg_name.lower() -> iso date when player first hit 14-day mark
    "audit_log_channel_id": None,  # custom channel for this server's audit logs (overrides default)
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


async def get_guild(guild_id: int) -> dict:
    async with _lock:
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


async def save_guild(guild_id: int, guild_data: dict):
    async with _lock:
        data = _load()
        data[str(guild_id)] = guild_data
        _save(data)


async def modify_guild(guild_id: int, modifier):
    """
    Atomically read, modify, and save a guild config.
    
    This prevents lost-update race conditions: the modifier callback
    receives the guild dict and can mutate it, then the changes are
    saved immediately while still holding the lock.
    
    Example:
        await modify_guild(guild_id, lambda g: g["players"].append(name))
    """
    async with _lock:
        data = _load()
        guild = data.get(str(guild_id))
        if guild is None:
            guild = copy.deepcopy(_DEFAULT_GUILD)
        else:
            merged = copy.deepcopy(_DEFAULT_GUILD)
            merged.update(guild)
            guild = merged
        modifier(guild)
        data[str(guild_id)] = guild
        _save(data)


async def all_guild_ids() -> list[int]:
    async with _lock:
        data = _load()
        return [int(g) for g in data.keys()]


async def add_player(guild_id: int, name: str) -> bool:
    guild = await get_guild(guild_id)
    lowered = [p.lower() for p in guild["players"]]
    if name.lower() in lowered:
        return False
    guild["players"].append(name)
    guild["ranked_known_players"] = {}
    await save_guild(guild_id, guild)
    return True


async def add_players(guild_id: int, names: list[str]) -> tuple[list[str], list[str]]:
    """
    Bulk-add many players in a single save. Returns (added, duplicates).
    Preserves the casing of the first occurrence for duplicates within the
    input list itself.
    """
    guild = await get_guild(guild_id)
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
        await save_guild(guild_id, guild)
    return added, duplicates


async def remove_player(guild_id: int, name: str) -> bool:
    guild = await get_guild(guild_id)
    before = len(guild["players"])
    guild["players"] = [p for p in guild["players"] if p.lower() != name.lower()]
    changed = len(guild["players"]) != before
    if changed:
        guild["ranked_known_players"] = {}
        await save_guild(guild_id, guild)
    return changed


async def link_discord_account(guild_id: int, pubg_name: str, discord_user_id: int):
    """Links a PUBG name to a Discord user ID for this server, so reports
    can @mention the right person. Overwrites any existing link for that
    name."""
    guild = await get_guild(guild_id)
    guild["discord_links"][pubg_name.lower()] = discord_user_id
    await save_guild(guild_id, guild)


async def unlink_discord_account(guild_id: int, pubg_name: str) -> bool:
    guild = await get_guild(guild_id)
    existed = guild["discord_links"].pop(pubg_name.lower(), None) is not None
    if existed:
        await save_guild(guild_id, guild)
    return existed


async def get_discord_id(guild_id: int, pubg_name: str) -> int | None:
    guild = await get_guild(guild_id)
    return guild["discord_links"].get(pubg_name.lower())


async def get_mentions_enabled(guild_id: int) -> bool:
    """Check if mentions are enabled for a guild."""
    guild = await get_guild(guild_id)
    return guild.get("mentions_enabled", True)


async def set_mentions_enabled(guild_id: int, enabled: bool):
    """Enable or disable mentions for a guild."""
    guild = await get_guild(guild_id)
    guild["mentions_enabled"] = enabled
    await save_guild(guild_id, guild)


async def add_cheat_report(
    guild_id: int,
    reporter_name: str,
    accused_name: str,
    cheat_type: str,
    description: str,
    match_id: str | None = None,
    evidence_urls: list[str] | None = None,
) -> str:
    """Add a cheat report and return the report ID."""
    guild = await get_guild(guild_id)
    # Use timestamp as primary key to avoid race conditions on length
    timestamp = int(datetime.now(timezone.utc).timestamp())
    report_id = f"report_{timestamp}"
    report = {
        "report_id": report_id,
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "reporter_name": reporter_name,
        "accused_name": accused_name,
        "accused_name_lower": accused_name.lower(),
        "cheat_type": cheat_type,
        "description": description,
        "match_id": match_id,
        "evidence_urls": evidence_urls or [],
        "status": "pending",  # pending, submitted, resolved
        "krafton_ticket_id": None,
    }
    guild["cheat_reports"].append(report)
    await save_guild(guild_id, guild)
    return report_id


async def get_cheat_reports(guild_id: int) -> list[dict]:
    """Get all cheat reports for a guild."""
    guild = await get_guild(guild_id)
    return guild.get("cheat_reports", [])


async def get_cheat_report(guild_id: int, report_id: str) -> dict | None:
    """Get a specific cheat report by ID."""
    guild = await get_guild(guild_id)
    for report in guild.get("cheat_reports", []):
        if report["report_id"] == report_id:
            return report
    return None


async def update_cheat_report_status(guild_id: int, report_id: str, status: str, krafton_ticket_id: str | None = None):
    """Update the status of a cheat report."""
    guild = await get_guild(guild_id)
    for report in guild.get("cheat_reports", []):
        if report["report_id"] == report_id:
            report["status"] = status
            if krafton_ticket_id:
                report["krafton_ticket_id"] = krafton_ticket_id
            await save_guild(guild_id, guild)
            return True
    return False


async def update_suspicious_player(guild_id: int, player_name: str, stats: dict, flags: list[str]):
    """Update or add a suspicious player entry."""
    guild = await get_guild(guild_id)
    player_lower = player_name.lower()
    guild["suspicious_players"][player_lower] = {
        "name": player_name,
        "stats": stats,
        "flags": flags,
        "last_checked": datetime.now(timezone.utc).isoformat(),
        "report_count": guild["suspicious_players"].get(player_lower, {}).get("report_count", 0) + 1,
    }
    await save_guild(guild_id, guild)


async def get_suspicious_players(guild_id: int) -> dict[str, dict]:
    """Get all suspicious players for a guild."""
    guild = await get_guild(guild_id)
    return guild.get("suspicious_players", {})


async def add_protected_player(guild_id: int, player_name: str) -> bool:
    """Add a player to the protected list (immune to inactivity removal). Returns True if added."""
    guild = await get_guild(guild_id)
    # Clean the list first - remove empty entries and duplicates
    guild["protected_players"] = [p for p in guild["protected_players"] if p and p.strip()]
    guild["protected_players"] = list(dict.fromkeys(guild["protected_players"]))  # Remove duplicates while preserving order
    
    lowered = [p.lower() for p in guild["protected_players"]]
    if player_name.lower() in lowered:
        return False
    guild["protected_players"].append(player_name.strip())  # Store cleaned name
    await save_guild(guild_id, guild)
    return True


async def remove_protected_player(guild_id: int, player_name: str) -> bool:
    """Remove a player from the protected list. Returns True if removed."""
    guild = await get_guild(guild_id)
    # Clean the list first
    guild["protected_players"] = [p for p in guild["protected_players"] if p and p.strip()]
    guild["protected_players"] = list(dict.fromkeys(guild["protected_players"]))
    
    before = len(guild["protected_players"])
    guild["protected_players"] = [p for p in guild["protected_players"] if p.lower() != player_name.lower()]
    changed = len(guild["protected_players"]) != before
    if changed:
        await save_guild(guild_id, guild)
    return changed


async def get_protected_players(guild_id: int) -> list[str]:
    """Get all protected players for a guild."""
    guild = await get_guild(guild_id)
    return guild.get("protected_players", [])


async def is_protected_player(guild_id: int, player_name: str) -> bool:
    """Check if a player is on the protected list."""
    guild = await get_guild(guild_id)
    return player_name.lower() in [p.lower() for p in guild.get("protected_players", [])]


async def clean_protected_players(guild_id: int) -> int:
    """Clean up the protected player list (remove duplicates, empty entries). Returns number of entries removed."""
    guild = await get_guild(guild_id)
    before = len(guild["protected_players"])
    # Remove empty entries and duplicates
    guild["protected_players"] = [p for p in guild["protected_players"] if p and p.strip()]
    guild["protected_players"] = list(dict.fromkeys(guild["protected_players"]))
    after = len(guild["protected_players"])
    await save_guild(guild_id, guild)
    return before - after


async def reset_inactive_count(guild_id: int, player_name: str) -> bool:
    """Reset auto-counting for a specific player. Returns True if reset."""
    guild = await get_guild(guild_id)
    if player_name.lower() in guild.get("inactive_since_dates", {}):
        del guild["inactive_since_dates"][player_name.lower()]
        await save_guild(guild_id, guild)
        return True
    return False


async def get_audit_log_channel(guild_id: int) -> int | None:
    """Get the custom audit log channel for a guild (if set)."""
    guild = await get_guild(guild_id)
    return guild.get("audit_log_channel_id")


async def set_audit_log_channel(guild_id: int, channel_id: int | None):
    """Set or clear the custom audit log channel for a guild."""
    guild = await get_guild(guild_id)
    guild["audit_log_channel_id"] = channel_id
    await save_guild(guild_id, guild)


async def get_language(guild_id: int) -> str:
    """Get the preferred language for a guild."""
    guild = await get_guild(guild_id)
    return guild.get("language", "en")


async def set_language(guild_id: int, language_code: str) -> bool:
    """Set the preferred language for a guild. Returns True if valid."""
    # Valid language codes
    VALID_LANGUAGES = {"en", "zh", "hi", "es", "ar", "fr", "bn", "pt", "id", "ur"}
    if language_code not in VALID_LANGUAGES:
        return False
    guild = await get_guild(guild_id)
    guild["language"] = language_code
    await save_guild(guild_id, guild)
    return True
