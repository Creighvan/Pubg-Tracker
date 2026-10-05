"""
Historical data storage for trend tracking and analytics.

Stores:
- Daily player snapshots (matches, kills, wins, K/D, etc.)
- Match history with participant tracking
- Achievement milestones
- Streaks

Data is kept in a separate JSON file (history.json) to avoid bloating
the main data.json with historical records.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from modules.utils import normalize_player_name

logger = logging.getLogger(__name__)

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "history.json")
_lock = asyncio.Lock()

# Maximum history to retain (days)
MAX_DAILY_SNAPSHOTS = 90  # 3 months
MAX_MATCH_HISTORY = 1000  # matches per guild

# Achievement definitions (shared with commands/achievements.py)
ACHIEVEMENTS = {
    "first_win": {
        "name": "First Chicken Dinner",
        "emoji": "🏆",
        "description": "Won your first match",
    },
    "wins_10": {
        "name": "10 Wins",
        "emoji": "🏆",
        "description": "Reached 10 total wins",
    },
    "wins_50": {
        "name": "50 Wins",
        "emoji": "🏆",
        "description": "Reached 50 total wins",
    },
    "wins_100": {
        "name": "100 Wins",
        "emoji": "🏆",
        "description": "Reached 100 total wins",
    },
    "kills_100": {
        "name": "100 Kills",
        "emoji": "💀",
        "description": "Reached 100 total kills",
    },
    "kills_500": {
        "name": "500 Kills",
        "emoji": "💀",
        "description": "Reached 500 total kills",
    },
    "kills_1000": {
        "name": "1000 Kills",
        "emoji": "💀",
        "description": "Reached 1000 total kills",
    },
    "kills_5000": {
        "name": "5000 Kills",
        "emoji": "💀",
        "description": "Reached 5000 total kills",
    },
    "survival_tier5": {
        "name": "Survival Tier 5",
        "emoji": "🛡️",
        "description": "Reached Survival Mastery Tier 5",
    },
    "survival_level30": {
        "name": "Survival Level 30",
        "emoji": "🛡️",
        "description": "Reached Survival Mastery Level 30",
    },
}


_DEFAULT_HISTORY = {
    # guild_id -> {
    #   "daily_snapshots": {
    #     "YYYY-MM-DD": {
    #       normalize_player_name -> {
    #         "matches": int,
    #         "wins": int,
    #         "kills": int,
    #         "deaths": int,
    #         "damage": float,
    #         "top10": int,
    #         "win_rate": float,
    #         "kd": float,
    #         "avg_placement": float,
    #         "survival_level": int,
    #         "survival_tier": int,
    #         "top_weapon": str,
    #         "ranked_points": Optional[int],
    #         "ranked_tier": Optional[str],
    #       }
    #     }
    #   },
    #   "match_history": [
    #     {
    #       "match_id": str,
    #       "date": "YYYY-MM-DD",
    #       "timestamp": ISO timestamp,
    #       "map": str,
    #       "game_mode": str,
    #       "participants": [normalize_player_name],
    #       "outside_teammates": [str],  # non-tracked player names
    #       "is_win": bool,
    #       "placement": int,
    #       "total_kills": int,
    #       "total_damage": float,
    #     }
    #   ],
    #   "achievements": {
    #     normalize_player_name -> {
    #       "first_win": ISO timestamp,
    #       "wins_10": ISO timestamp,
    #       "wins_50": ISO timestamp,
    #       "wins_100": ISO timestamp,
    #       "kills_100": ISO timestamp,
    #       "kills_500": ISO timestamp,
    #       "kills_1000": ISO timestamp,
    #       "survival_tier5": ISO timestamp,
    #       # ... more achievements
    #     }
    #   },
    #   "streaks": {
    #     normalize_player_name -> {
    #       "top10_streak": int,
    #       "top10_streak_start": ISO timestamp,
    #       "win_streak": int,
    #       "win_streak_start": ISO timestamp,
    #       "kills_streak": int,
    #       "kills_streak_start": ISO timestamp,
    #       "day_streak": int,
    #       "day_streak_start": ISO timestamp,
    #     }
    #   },
    # }
}


def _load_history() -> dict:
    """Load history data from disk."""
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"Loaded history from {HISTORY_PATH}")
            return data
    except FileNotFoundError:
        logger.info(f"History file not found, creating new one: {HISTORY_PATH}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"History file corrupted, starting fresh: {e}")
        return {}


def _save_history(data: dict) -> None:
    """Save history data to disk."""
    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug(f"Saved history to {HISTORY_PATH}")
    except Exception as e:
        logger.error(f"Failed to save history: {e}")


async def get_guild_history(guild_id: int) -> dict:
    """Get history data for a specific guild."""
    data = _load_history()
    guild_id_str = str(guild_id)
    if guild_id_str not in data:
        data[guild_id_str] = {
            "daily_snapshots": {},
            "match_history": [],
            "achievements": {},
            "streaks": {},
        }
        _save_history(data)
    return data[guild_id_str]


async def record_daily_snapshot(
    guild_id: int,
    date: str,  # YYYY-MM-DD
    player_stats: dict,  # normalize_player_name -> stats dict
) -> None:
    """
    Record a daily snapshot for tracked players.

    player_stats should contain:
    - matches
    - wins
    - kills
    - deaths
    - damage
    - top10
    - win_rate
    - kd
    - avg_placement
    - survival_level (optional)
    - survival_tier (optional)
    - top_weapon (optional)
    - ranked_points (optional)
    - ranked_tier (optional)
    """
    async with _lock:
        data = _load_history()
        guild_id_str = str(guild_id)

        if guild_id_str not in data:
            data[guild_id_str] = {
                "daily_snapshots": {},
                "match_history": [],
                "achievements": {},
                "streaks": {},
            }

        if "daily_snapshots" not in data[guild_id_str]:
            data[guild_id_str]["daily_snapshots"] = {}

        # Clean up old snapshots beyond retention period
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=MAX_DAILY_SNAPSHOTS)).strftime("%Y-%m-%d")
        data[guild_id_str]["daily_snapshots"] = {
            k: v for k, v in data[guild_id_str]["daily_snapshots"].items()
            if k >= cutoff_date
        }

        # Record today's snapshot
        data[guild_id_str]["daily_snapshots"][date] = player_stats

        _save_history(data)
        logger.info(f"Recorded daily snapshot for guild {guild_id} on {date}: {len(player_stats)} players")


async def get_player_snapshots(
    guild_id: int,
    player_name: str,
    days: int = 30,
) -> list[dict]:
    """
    Get daily snapshots for a player over the last N days.

    Returns list of (date, stats) tuples, sorted chronologically.
    """
    async with _lock:
        data = _load_history()
        guild_id_str = str(guild_id)

        if guild_id_str not in data:
            return []

        daily_snapshots = data[guild_id_str].get("daily_snapshots", {})
        normalized_name = normalize_player_name(player_name)

        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        snapshots = []
        for date, players in daily_snapshots.items():
            if date >= cutoff_date and normalized_name in players:
                snapshots.append({"date": date, "stats": players[normalized_name]})

        # Sort chronologically
        snapshots.sort(key=lambda x: x["date"])
        return snapshots


async def record_match(
    guild_id: int,
    match_id: str,
    date: str,
    timestamp: str,
    map_name: str,
    game_mode: str,
    participants: list[str],  # normalized player names
    outside_teammates: list[str],  # non-tracked names
    is_win: bool,
    placement: int,
    total_kills: int,
    total_damage: float,
) -> None:
    """Record a match with participant tracking."""
    async with _lock:
        data = _load_history()
        guild_id_str = str(guild_id)

        if guild_id_str not in data:
            data[guild_id_str] = {
                "daily_snapshots": {},
                "match_history": [],
                "achievements": {},
                "streaks": {},
            }

        if "match_history" not in data[guild_id_str]:
            data[guild_id_str]["match_history"] = []

        # Check if match already recorded
        match_history = data[guild_id_str]["match_history"]
        for match in match_history:
            if match.get("match_id") == match_id:
                return  # Already recorded

        # Add new match
        match_history.append({
            "match_id": match_id,
            "date": date,
            "timestamp": timestamp,
            "map": map_name,
            "game_mode": game_mode,
            "participants": participants,
            "outside_teammates": outside_teammates,
            "is_win": is_win,
            "placement": placement,
            "total_kills": total_kills,
            "total_damage": total_damage,
        })

        # Trim old matches beyond retention
        if len(match_history) > MAX_MATCH_HISTORY:
            data[guild_id_str]["match_history"] = match_history[-MAX_MATCH_HISTORY:]

        _save_history(data)
        logger.info(f"Recorded match {match_id} for guild {guild_id}: {len(participants)} participants")


async def get_guild_matches(
    guild_id: int,
    days: int = 7,
    player_filter: Optional[str] = None,
) -> list[dict]:
    """
    Get matches for a guild over the last N days.

    If player_filter is provided, only return matches where that player participated.
    """
    async with _lock:
        data = _load_history()
        guild_id_str = str(guild_id)

        if guild_id_str not in data:
            return []

        match_history = data[guild_id_str].get("match_history", [])
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        matches = []
        for match in match_history:
            if match["date"] >= cutoff_date:
                if player_filter is None or normalize_player_name(player_filter) in match["participants"]:
                    matches.append(match)

        # Sort by timestamp descending (most recent first)
        matches.sort(key=lambda x: x["timestamp"], reverse=True)
        return matches


async def calculate_trend(
    guild_id: int,
    player_name: str,
    days: int = 7,
) -> dict:
    """
    Calculate trend statistics for a player over the last N days.

    Returns dict with:
    - stats_start: stats at start of period
    - stats_end: stats at end of period
    - delta: change in each stat
    - percent_change: percentage change for key stats
    """
    snapshots = await get_player_snapshots(guild_id, player_name, days)

    if len(snapshots) < 2:
        return {
            "error": "insufficient_data",
            "message": f"Need at least 2 snapshots over {days} days to calculate trend",
        }

    stats_start = snapshots[0]["stats"]
    stats_end = snapshots[-1]["stats"]

    delta = {}
    percent_change = {}

    for key in ["matches", "wins", "kills", "deaths", "damage", "top10"]:
        start_val = stats_start.get(key, 0)
        end_val = stats_end.get(key, 0)
        delta[key] = end_val - start_val

        if start_val > 0:
            percent_change[key] = ((end_val - start_val) / start_val) * 100
        else:
            percent_change[key] = None

    # For rate-based stats, compare the values directly
    for key in ["win_rate", "kd", "avg_placement"]:
        start_val = stats_start.get(key, 0)
        end_val = stats_end.get(key, 0)
        delta[key] = end_val - start_val

        if start_val > 0:
            percent_change[key] = ((end_val - start_val) / start_val) * 100
        else:
            percent_change[key] = None

    return {
        "stats_start": stats_start,
        "stats_end": stats_end,
        "delta": delta,
        "percent_change": percent_change,
        "period_days": days,
        "snapshots_count": len(snapshots),
    }
