"""
Report fetcher functions for PUBG Clan Tracker Discord Bot.

This module contains all async functions that fetch data from the PUBG API
and storage to generate various reports. These functions are responsible for
data retrieval and pass the results to embed builder functions in bot.embeds.

Functions:
    fetch_clan_report: Fetch clan statistics for a guild
    fetch_clan_level_report: Fetch clan level and weekly progress
    fetch_last_active_report: Fetch player last active times
    fetch_ranked_report: Fetch ranked standings for a game mode
    fetch_highlights_report: Fetch daily highlights with fun titles
    fetch_mastery_report: Fetch weapon and survival mastery
    fetch_survival_mastery_report: Fetch survival mastery grouped by tier
    fetch_leaderboard_report: Fetch official leaderboard placements

Each function returns a tuple containing the embed (or embeds) and additional
data like player lists or metadata, or None if the report cannot be generated.
"""

from datetime import datetime, timedelta, timezone

import discord

import storage
from pubg_api import PubgApiError

from modules.utils import normalize_player_name

# Import storage's modify_guild for atomic operations
modify_guild = storage.modify_guild

# Import pubg client (set by bot.py after initialization)
# This is a late import to avoid circular dependency
def _get_pubg():
    from modules.config import pubg
    return pubg
from modules.embeds import (
    build_clan_embed,
    build_clan_level_embed,
    build_last_active_embed,
    build_ranked_embed,
    build_highlights_embed,
    build_mastery_embed,
    build_survival_mastery_embeds,
    build_leaderboard_embed,
)


async def fetch_clan_report(guild_id: int, guild_name: str | None = None, game_mode: str | None = None) -> tuple[discord.Embed, list[dict]] | None:
    """Fetch clan statistics report for a guild."""
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    mode = game_mode or guild_cfg["game_mode"]
    players, not_found = await _get_pubg().get_players_and_stats(guild_cfg["players"], game_mode=mode)
    embed = build_clan_embed(guild_name, guild_cfg, players, not_found, game_mode=mode)
    return embed, players


async def fetch_clan_level_report(guild_id: int) -> tuple[discord.Embed, dict] | None:
    """Fetch clan level and weekly progress report for a guild."""
    guild_cfg = await storage.get_guild(guild_id)
    clan_id = guild_cfg.get("pubg_clan_id")
    if not clan_id:
        return None
    clan = await _get_pubg().get_clan_by_id(clan_id)
    return build_clan_level_embed(guild_cfg, clan), clan


def _parse_iso(value) -> datetime | None:
    """Parse an ISO timestamp (accepts a trailing Z); None if missing or unreadable."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def apply_last_active_rules(guild_cfg: dict, players: list[dict], now: datetime | None = None) -> None:
    """Decide each player's "last active" time and keep the saved counts correct.

    The PUBG API only remembers 14 days of matches. The rules, in plain terms:

    * The bot remembers each player's latest known match (guild_cfg["last_seen_at"]).
      That value only ever moves FORWARD, so a slow or glitchy API answer can never
      make a player look less recently active than they already were.
    * When the API has no match for a player any more (past 14 days), the count
      keeps going from that remembered match: 15 days, 16 days, ... exact, not
      "from the day the bot noticed".
    * The moment the player plays again, the API shows a newer match, the count
      stops and restarts from that match.
    * A manual date (/setinactivedate) is kept until the player plays a match
      AFTER it was set. Older matches the API still lists do not undo it.
    * A failed lookup, or a player missing from one API answer, never deletes or
      restarts anything: nothing is changed for that player until the next report.
    """
    now = now or datetime.now(timezone.utc)
    last_seen = guild_cfg.setdefault("last_seen_at", {})
    manual_all = guild_cfg.setdefault("manual_inactive_dates", {})
    since_all = guild_cfg.setdefault("inactive_since_dates", {})

    # Clean up protected players who are not in the tracked list to prevent mismatch
    tracked_normalized = [normalize_player_name(p) for p in guild_cfg["players"]]
    guild_cfg["protected_players"] = [
        p for p in guild_cfg.get("protected_players", [])
        if normalize_player_name(p) in tracked_normalized
    ]

    for player in players:
        norm = normalize_player_name(player["name"])
        api_time = _parse_iso(player.get("last_match_at"))

        # 1) A manual date wins until the player plays a match after it was set.
        manual = manual_all.get(norm)
        if manual:
            raw_date = manual.get("date") if isinstance(manual, dict) else manual
            manual_date = _parse_iso(raw_date)
            set_at = _parse_iso(manual.get("set_at")) if isinstance(manual, dict) else None
            played_again = api_time is not None and set_at is not None and api_time > set_at
            if manual_date is not None and not played_again:
                player["last_match_date"] = manual_date.isoformat()
                player["data_source"] = "manual"
                player["days_inactive"] = max(0, (now - manual_date).days)
                since_all.pop(norm, None)
                continue
            del manual_all[norm]          # they played again (or the entry is unusable)
            since_all.pop(norm, None)

        stored = _parse_iso(last_seen.get(norm))

        # 2) The API knows a recent match: remember it, and never go backwards.
        if api_time is not None:
            if stored is None or api_time > stored:
                last_seen[norm] = api_time.isoformat()
            elif stored > api_time:
                player["last_match_at"] = stored.isoformat()   # API is behind: show the newer, remembered time
            since_all.pop(norm, None)                          # active again: the count restarts
            continue

        # 3) The match times could not be read this time: unknown, not inactive.
        if player.get("match_lookup_failed"):
            continue

        # 4) No match in the API's 14-day window: keep counting from the real last match.
        since = _parse_iso(since_all.get(norm))
        if stored is not None:
            since = stored + timedelta(days=14)               # exact
            since_all[norm] = since.isoformat()
        elif since is None:
            since = now                                       # never seen before: count starts at 14 days today
            since_all[norm] = since.isoformat()
        last_match = since - timedelta(days=14)
        player["last_match_date"] = last_match.isoformat()
        player["data_source"] = "auto_count"
        player["days_inactive"] = max(0, (now - last_match).days)


async def fetch_last_active_report(guild_id: int, guild_name: str | None = None) -> tuple[discord.Embed, list[dict]] | None:
    """Fetch player last active times report for a guild."""
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await _get_pubg().get_last_active_times(guild_cfg["players"])

    protected_players = await storage.get_protected_players(guild_id)

    # Apply the last-active rules and save them atomically
    await modify_guild(guild_id, lambda cfg: apply_last_active_rules(cfg, players))

    # modify_guild works on its own copy, so read the saved settings back; otherwise the
    # list would be drawn from the settings as they were BEFORE this run's updates.
    guild_cfg = await storage.get_guild(guild_id)

    return build_last_active_embed(guild_id, guild_name, guild_cfg, players, not_found, protected_players), players


async def fetch_ranked_report(guild_id: int, guild_name: str | None = None, game_mode: str | None = None) -> tuple[discord.Embed, list[dict]] | None:
    """Fetch ranked standings report for a guild and game mode."""
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    game_mode = game_mode or guild_cfg.get("ranked_queue", "squad")
    known_by_mode = guild_cfg.get("ranked_known_players", {})
    # The first report for a queue must scan the roster because PUBG has no
    # ranked-player filter. Later reports only recheck players previously
    # found in that queue, keeping a large clan roster fast and API-friendly.
    names_to_check = known_by_mode.get(game_mode)
    if names_to_check is None:
        names_to_check = guild_cfg["players"]
    players, not_found = await _get_pubg().get_ranked_report(names_to_check, game_mode)
    if game_mode not in known_by_mode:
        known_by_mode[game_mode] = [
            p["name"] for p in players if p.get("ranked", {}).get("currentTier") is not None
        ]

        def modifier(g):
            g["ranked_known_players"] = known_by_mode
        await storage.modify_guild(guild_id, modifier)
    embed = build_ranked_embed(guild_name, guild_cfg, players, not_found, game_mode)
    return embed, players


async def fetch_highlights_report(guild_id: int, guild_name: str | None = None, hours: int = 24, max_matches_checked: int = None, live: bool = False) -> tuple[discord.Embed, list[dict]] | None:
    """Fetch daily highlights report for a guild."""
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    try:
        players, not_found = await _get_pubg().get_daily_activity_report(guild_cfg["players"], hours=hours, max_matches_checked=max_matches_checked)
    except PubgApiError as e:
        # Provide better error message for telemetry availability issues
        if "telemetry" in str(e).lower() or "404" in str(e):
            embed = discord.Embed(
                title=f"{guild_name} — Highlights Unavailable",
                description="No matches found in the last 14 days. PUBG match telemetry is only available for the last 14 days, so highlights reports cannot be generated for older matches.",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc),
            )
            return embed, []
        raise
    embed = build_highlights_embed(guild_name, guild_cfg, players, not_found, hours, live=live)
    return embed, players


async def fetch_mastery_report(guild_id: int, guild_name: str | None = None) -> tuple[discord.Embed, list[dict]] | None:
    """Fetch weapon and survival mastery report for a guild."""
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await _get_pubg().get_mastery_report(guild_cfg["players"])
    return build_mastery_embed(guild_name, guild_cfg, players, not_found), players


async def fetch_survival_mastery_report(
    guild_id: int, guild_name: str | None
) -> tuple[list[discord.Embed], list[discord.File]] | None:
    """Fetch survival mastery report grouped by tier for a guild."""
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await _get_pubg().get_mastery_report(guild_cfg["players"])
    return build_survival_mastery_embeds(guild_cfg, guild_name, players, not_found)


async def fetch_leaderboard_report(
    guild_id: int, guild_name: str | None, max_pages: int = 4
) -> tuple[discord.Embed, dict[str, dict]] | None:
    """Fetch official leaderboard placements for a guild."""
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    queue = guild_cfg.get("leaderboard_queue", "squad")
    season_id = await _get_pubg().get_current_season_id()
    found, checked = await _get_pubg().get_leaderboard_placements(
        guild_cfg["players"], season_id, game_mode=queue,
        max_pages=max_pages, leaderboard_shard=guild_cfg.get("leaderboard_shard", "pc-na"),
    )
    mentions_enabled = guild_cfg.get("mentions_enabled", True)
    embed = build_leaderboard_embed(guild_id, guild_name, guild_cfg, found, checked, max_pages, queue, mentions_enabled)
    return embed, found
