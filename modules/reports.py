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
import translations

from modules.config import VALID_GAME_MODES, RANKED_MODE_LABELS
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
from modules.utils import _as_utc


async def fetch_clan_report(guild_id: int, guild_name: str) -> tuple[discord.Embed, list[dict]] | None:
    """Fetch clan statistics report for a guild."""
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await _get_pubg().get_players_and_stats(guild_cfg["players"], game_mode=guild_cfg["game_mode"])
    embed = build_clan_embed(guild_name, guild_cfg, players, not_found)
    return embed, players


async def fetch_clan_level_report(guild_id: int) -> tuple[discord.Embed, dict] | None:
    """Fetch clan level and weekly progress report for a guild."""
    guild_cfg = await storage.get_guild(guild_id)
    clan_id = guild_cfg.get("pubg_clan_id")
    if not clan_id:
        return None
    clan = await _get_pubg().get_clan_by_id(clan_id)
    return build_clan_level_embed(guild_cfg, clan), clan


async def fetch_last_active_report(guild_id: int, guild_name: str) -> tuple[discord.Embed, list[dict]] | None:
    """Fetch player last active times report for a guild."""
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await _get_pubg().get_last_active_times(guild_cfg["players"])
    
    # Historical data beyond 14 days: automatic day counting from 14-day mark
    # The PUBG API has a hard 14-day limit for match data retention
    protected_players = await storage.get_protected_players(guild_id)
    
    def update_inactive_dates(guild_cfg):
        """Update inactive dates for players with no recent matches."""
        # Clean up protected players who are not in the tracked list to prevent mismatch
        tracked_normalized = [normalize_player_name(p) for p in guild_cfg["players"]]
        guild_cfg["protected_players"] = [
            p for p in guild_cfg.get("protected_players", [])
            if normalize_player_name(p) in tracked_normalized
        ]
        
        # First, clear manual/auto inactivity for players who have recent matches
        for player in players:
            player_normalized = normalize_player_name(player["name"])
            
            if player.get("last_match_at"):
                # Player has recent matches (active within 14 days)
                # Clean up both auto-counting and manual overrides
                if player_normalized in guild_cfg.get("inactive_since_dates", {}):
                    del guild_cfg["inactive_since_dates"][player_normalized]
                if player_normalized in guild_cfg.get("manual_inactive_dates", {}):
                    del guild_cfg["manual_inactive_dates"][player_normalized]
        
        # Then handle players with no recent matches (beyond 14-day API limit)
        for player in players:
            player_normalized = normalize_player_name(player["name"])
            
            if not player.get("last_match_at"):
                # Player has no recent matches (beyond 14-day API limit)
                
                # Check if we have manual override first
                if manual_data := guild_cfg.get("manual_inactive_dates", {}).get(player_normalized):
                    # Increment manual date daily based on when it was set
                    manual_date = datetime.fromisoformat(manual_data["date"])
                    set_at = datetime.fromisoformat(manual_data["set_at"])
                    days_since_set = (datetime.now(timezone.utc) - set_at).days
                    incremented_date = (manual_date + timedelta(days=days_since_set)).isoformat()
                    player["last_match_date"] = incremented_date
                    player["data_source"] = "manual"
                    # Calculate days inactive for manual dates
                    current_manual_date = manual_date + timedelta(days=days_since_set)
                    player["days_inactive"] = (datetime.now(timezone.utc) - current_manual_date).days
                    # Also remove from auto-counting if it exists to avoid conflicts
                    if player_normalized in guild_cfg.get("inactive_since_dates", {}):
                        del guild_cfg["inactive_since_dates"][player_normalized]
                    continue
                
                # Check if we have an inactive_since_date
                if inactive_since := guild_cfg.get("inactive_since_dates", {}).get(player_normalized):
                    # Calculate days from when they first hit 14-day mark
                    inactive_since_date = datetime.fromisoformat(inactive_since)
                    days_inactive = (datetime.now(timezone.utc) - inactive_since_date).days + 14
                    # The last match date is 14 days before they hit the inactive mark
                    calculated_date = (inactive_since_date - timedelta(days=14)).isoformat()
                    player["last_match_date"] = calculated_date
                    player["data_source"] = "auto_count"
                    # Store the actual days inactive for display
                    player["days_inactive"] = days_inactive
                else:
                    # First time hitting 14-day mark - set inactive_since_date
                    # Only set if not already set (to preserve dates during downtime)
                    if player_normalized not in guild_cfg.get("inactive_since_dates", {}):
                        guild_cfg["inactive_since_dates"][player_normalized] = datetime.now(timezone.utc).isoformat()
                    # Start counting from 14 days ago from the inactive_since_date
                    inactive_since_date = datetime.fromisoformat(guild_cfg["inactive_since_dates"][player_normalized])
                    days_inactive = (datetime.now(timezone.utc) - inactive_since_date).days + 14
                    calculated_date = (inactive_since_date - timedelta(days=14)).isoformat()
                    player["last_match_date"] = calculated_date
                    player["data_source"] = "auto_count"
                    player["days_inactive"] = days_inactive
        
        # Also clear manual/auto inactivity for players not found in API results
        # This handles name changes or players who were removed from PUBG API
        for player_name in guild_cfg["players"]:
            player_normalized = normalize_player_name(player_name)
            player_found = any(normalize_player_name(p["name"]) == player_normalized for p in players)
            if not player_found:
                # Player not found in API results - they may have changed names or been removed
                # Clear both manual and auto inactivity to avoid stale data
                if player_normalized in guild_cfg.get("manual_inactive_dates", {}):
                    del guild_cfg["manual_inactive_dates"][player_normalized]
                if player_normalized in guild_cfg.get("inactive_since_dates", {}):
                    del guild_cfg["inactive_since_dates"][player_normalized]
    
    # Apply inactive date updates atomically
    await modify_guild(guild_id, update_inactive_dates)
    
    return build_last_active_embed(guild_id, guild_name, guild_cfg, players, not_found, protected_players), players


async def fetch_ranked_report(guild_id: int, guild_name: str, game_mode: str | None = None) -> tuple[discord.Embed, list[dict]] | None:
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
        guild_cfg["ranked_known_players"] = dict(known_by_mode)
        guild_cfg["ranked_known_players"][game_mode] = [
            p["name"] for p in players if p.get("ranked", {}).get("currentTier") is not None
        ]
        await storage.save_guild(guild_id, guild_cfg)
    embed = build_ranked_embed(guild_name, guild_cfg, players, not_found, game_mode)
    return embed, players


async def fetch_highlights_report(guild_id: int, guild_name: str, hours: int = 24) -> tuple[discord.Embed, list[dict]] | None:
    """Fetch daily highlights report for a guild."""
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    try:
        players, not_found = await _get_pubg().get_daily_activity_report(guild_cfg["players"], hours=hours)
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
    embed = build_highlights_embed(guild_name, guild_cfg, players, not_found, hours)
    return embed, players


async def fetch_mastery_report(guild_id: int, guild_name: str) -> tuple[discord.Embed, list[dict]] | None:
    """Fetch weapon and survival mastery report for a guild."""
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await _get_pubg().get_mastery_report(guild_cfg["players"])
    return build_mastery_embed(guild_name, guild_cfg, players, not_found), players


async def fetch_survival_mastery_report(
    guild_id: int, guild_name: str
) -> tuple[list[discord.Embed], list[discord.File]] | None:
    """Fetch survival mastery report grouped by tier for a guild."""
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await _get_pubg().get_mastery_report(guild_cfg["players"])
    return build_survival_mastery_embeds(guild_cfg, guild_name, players, not_found)


async def fetch_leaderboard_report(
    guild_id: int, guild_name: str, max_pages: int = 4
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
