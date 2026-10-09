"""
Historical data storage for trend tracking and analytics.

Stores:
- Daily player snapshots (matches, kills, wins, K/D, etc.)
- Match history with participant tracking
- Clan match participants (for chemistry analytics)
- Achievement milestones
- Streaks

Data is kept in a separate JSON file (history.json) to avoid bloating
the main data.json with historical records.

ARCHITECTURAL DECISIONS (Integrity Audit):

1. Canonical Identity:
   - player_id (PUBG account ID) is the canonical identity
   - player_name is presentation data only
   - This handles PUBG name changes correctly

2. Teammate Identification:
   - Critical invariant: match_id + team_id → actual teammates in that match
   - team_id is NOT globally unique (team7 in match A ≠ team7 in match B)
   - Missing team_id = unknown relationship, NOT opponents
   - This prevents false chemistry from incomplete data

3. Idempotency:
   - record_clan_participant() checks (match_id, player_id) before inserting
   - Re-processing the same match does not create duplicates
   - Essential for scheduled jobs and historical backfill

4. Historical Data Semantics:
   - Old match_history records without team_id = unknown, not "never teammates"
   - Chemistry commands must distinguish:
     - 0 shared matches (never played together)
     - 0 usable matches (missing team data)
   - is_tracked = "was tracked when recorded", not "currently tracked"
   - Historical facts are preserved even if clan membership changes

5. Data Flow:
   PUBG match → participant_details (immutable facts)
                → clan membership (current interpretation)
                → analytics layer (chemistry, bestduo, bestsquad)

6. Safety Rules:
   - Missing team_id → no chemistry (conservative)
   - Partial data → no fabricated relationships
   - Historical backfill → unknown ≠ opponent
   - Name changes → player_id wins
   - Duplicate processing → idempotent

This dataset is frozen pending chemistry command implementation.
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
    #         "season_id": Optional[str],
    #         "ranked_status": Optional[str],
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
    #       "participants": [normalize_player_name],  # Legacy - list of names
    #       "participant_details": [  # New - detailed participant data
    #         {
    #           "player_id": str,
    #           "player_name": str,
    #           "team_id": Optional[str],
    #           "kills": int,
    #           "damage": float,
    #           "placement": int,
    #         }
    #       ],
    #       "outside_teammates": [str],  # non-tracked player names
    #       "is_win": bool,
    #       "placement": int,
    #       "total_kills": int,
    #       "total_damage": float,
    #     }
    #   ],
    #   "clan_participants": [  # Canonical clan match participant dataset
    #     {
    #       "match_id": str,
    #       "player_id": str,
    #       "player_name": str,
    #       "team_id": Optional[str],
    #       "map": str,
    #       "placement": int,
    #       "kills": int,
    #       "damage": float,
    #       "created_at": ISO timestamp,
    #       "is_tracked": bool,  # Whether this player is in the clan roster
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
    """Load history data from disk (internal, assumes lock held)."""
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.debug(f"Loaded history from {HISTORY_PATH}")
            return data
    except FileNotFoundError:
        logger.debug(f"History file not found, creating new one: {HISTORY_PATH}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"History file corrupted, starting fresh: {e}")
        return {}


def _save_history(data: dict) -> None:
    """Save history data to disk atomically (internal, assumes lock held)."""
    try:
        tmp_path = HISTORY_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, HISTORY_PATH)
        logger.debug(f"Saved history to {HISTORY_PATH}")
    except Exception as e:
        logger.error(f"Failed to save history: {e}")


async def get_guild_history(guild_id: int) -> dict:
    """Get history data for a specific guild."""
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


async def record_clan_participant(
    guild_id: int,
    match_id: str,
    player_id: str,
    player_name: str,
    team_id: Optional[str],
    map_name: str,
    placement: int,
    kills: int,
    damage: float,
    created_at: str,
    is_tracked: bool,
) -> None:
    """
    Record a clan match participant with team identification for chemistry analytics.

    This is the canonical participant dataset that enables:
    - /clanmatches
    - /chemistry
    - /bestduo
    - /bestsquad
    - Squad win rates
    - Common teammates
    - Team-specific Chicken Dinner stats

    The critical relationship is: match_id + team_id → actual teammates in that match

    IDEMPOTENCY:
    - Checks (match_id, player_id) before inserting
    - Re-processing the same match does not create duplicates
    - Essential for scheduled jobs and historical backfill

    SEMANTICS:
    - player_id: Canonical identity (PUBG account ID)
    - player_name: Presentation data only (handles name changes)
    - team_id: Team identifier within the match (NOT globally unique)
    - is_tracked: "Was tracked when this match was recorded" (NOT "currently tracked")
                Historical facts are preserved even if clan membership changes

    SAFETY:
    - Missing team_id = unknown relationship, NOT opponents
    - Partial data = no fabricated relationships
    - Historical backfill = unknown ≠ opponent
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
                "clan_participants": [],
            }

        if "clan_participants" not in data[guild_id_str]:
            data[guild_id_str]["clan_participants"] = []

        # Check if this participant already recorded for this match
        clan_participants = data[guild_id_str]["clan_participants"]
        for participant in clan_participants:
            if participant.get("match_id") == match_id and participant.get("player_id") == player_id:
                return  # Already recorded (idempotent)

        # Add new participant
        clan_participants.append({
            "match_id": match_id,
            "player_id": player_id,
            "player_name": player_name,
            "team_id": team_id,
            "map": map_name,
            "placement": placement,
            "kills": kills,
            "damage": damage,
            "created_at": created_at,
            "is_tracked": is_tracked,
        })

        # Trim old participants (use same retention as match history)
        if len(clan_participants) > MAX_MATCH_HISTORY * 4:  # Assume ~4 players per match
            data[guild_id_str]["clan_participants"] = clan_participants[-(MAX_MATCH_HISTORY * 4):]

        _save_history(data)
        logger.info(f"Recorded clan participant {player_name} for match {match_id} in guild {guild_id}")


async def get_clan_participants(
    guild_id: int,
    days: Optional[int] = None,
    player_filter: Optional[str] = None,
    tracked_only: bool = True,
) -> list[dict]:
    """
    Get clan match participants for analytics.

    Args:
        guild_id: Discord guild ID
        days: Optional time filter (None = all history)
        player_filter: Optional player name filter
        tracked_only: If True, only return tracked clan members

    Returns:
        List of participant records with team_id for chemistry analysis
    """
    async with _lock:
        data = _load_history()
        guild_id_str = str(guild_id)

        if guild_id_str not in data:
            return []

        clan_participants = data[guild_id_str].get("clan_participants", [])

        # Apply filters
        if days is not None:
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            clan_participants = [p for p in clan_participants if p.get("created_at", "") >= cutoff_date]

        if player_filter is not None:
            normalized = normalize_player_name(player_filter)
            clan_participants = [p for p in clan_participants if normalize_player_name(p.get("player_name", "")) == normalized]

        if tracked_only:
            clan_participants = [p for p in clan_participants if p.get("is_tracked", False)]

        return clan_participants


def are_teammates(participant_a: dict, participant_b: dict) -> bool:
    """
    Determine if two participants were teammates in the same match.

    CRITICAL INVARIANT: match_id + team_id → actual teammates in that match

    IMPORTANT: team_id is NOT globally unique
    - team7 in match A ≠ team7 in match B
    - Must check BOTH match_id AND team_id

    MISSING DATA HANDLING:
    - Missing team_id = unknown relationship, NOT opponents
    - Conservative approach: if unsure, not teammates
    - This prevents false chemistry from incomplete data

    HISTORICAL DATA:
    - Old matches without team_id = unknown, not "never teammates"
    - Chemistry commands must distinguish:
      - 0 shared matches (never played together)
      - 0 usable matches (missing team data)

    Args:
        participant_a: First participant record
        participant_b: Second participant record

    Returns:
        True if same match AND same team_id, False otherwise
    """
    # Must be same match
    if participant_a.get("match_id") != participant_b.get("match_id"):
        return False

    # Must have valid team_ids
    team_a = participant_a.get("team_id")
    team_b = participant_b.get("team_id")

    if not team_a or not team_b:
        return False

    # Must be same team
    return team_a == team_b


async def get_teammate_pairs(
    guild_id: int,
    days: Optional[int] = None,
    min_matches: int = 1,
) -> dict:
    """
    Get all teammate pairs and their match history for chemistry analytics.

    DISTINCTION PRESERVED:
    - shared_matches: Both players appeared in the same match
    - usable_shared_matches: Both have valid team data
    - same_team_matches: Confirmed teammates (same match + same team_id)
    This preserves the unknown vs zero distinction from the integrity audit.

    Returns:
        Dict where key is "player1_player2" (sorted alphabetically) and value is:
        {
            "shared_matches": int,        # Both appeared in match
            "usable_shared_matches": int,  # Both have team data
            "same_team_matches": int,      # Confirmed teammates
            "wins": int,
            "top10": int,
            "combined_kills": int,
            "combined_damage": float,
            "avg_placement": float,
            "win_rate": float,
            "player_a_kills": int,
            "player_b_kills": int,
            "last_played": str,  # ISO timestamp
        }
    """
    participants = await get_clan_participants(guild_id, days=days, tracked_only=True)

    # Group by match
    matches: dict[str, list[dict]] = {}
    for p in participants:
        match_id = p.get("match_id")
        if match_id not in matches:
            matches[match_id] = []
        matches[match_id].append(p)

    # Find all pairs (shared matches) and track team confirmation
    pairs: dict[str, dict] = {}

    for match_id, match_participants in matches.items():
        # Group by team
        teams: dict[str, list[dict]] = {}
        for p in match_participants:
            team_id = p.get("team_id")
            if team_id:
                if team_id not in teams:
                    teams[team_id] = []
                teams[team_id].append(p)

        # Generate all pairs (all participants in match, regardless of team)
        # This tracks shared_matches first
        for i in range(len(match_participants)):
            for j in range(i + 1, len(match_participants)):
                p1 = match_participants[i]
                p2 = match_participants[j]

                # Create pair key (sorted alphabetically)
                names = sorted([p1.get("player_name", ""), p2.get("player_name", "")])
                pair_key = f"{names[0]}_{names[1]}"

                if pair_key not in pairs:
                    pairs[pair_key] = {
                        "shared_matches": 0,
                        "usable_shared_matches": 0,
                        "same_team_matches": 0,
                        "wins": 0,
                        "top10": 0,
                        "combined_kills": 0,
                        "combined_damage": 0.0,
                        "placements": [],
                        "player_a_kills": 0,
                        "player_b_kills": 0,
                        "last_played": None,
                    }

                # Always count as shared match
                pairs[pair_key]["shared_matches"] += 1

                # Check if both have team data (usable)
                if p1.get("team_id") and p2.get("team_id"):
                    pairs[pair_key]["usable_shared_matches"] += 1

                    # Check if same team (confirmed teammates)
                    if p1.get("team_id") == p2.get("team_id"):
                        pairs[pair_key]["same_team_matches"] += 1
                        pairs[pair_key]["combined_kills"] += p1.get("kills", 0) + p2.get("kills", 0)
                        pairs[pair_key]["combined_damage"] += p1.get("damage", 0) + p2.get("damage", 0)

                        placement = p1.get("placement", 0)
                        pairs[pair_key]["placements"].append(placement)

                        if placement == 1:
                            pairs[pair_key]["wins"] += 1
                        if placement <= 10:
                            pairs[pair_key]["top10"] += 1

                        # Track individual kills per player
                        pairs[pair_key]["player_a_kills"] += p1.get("kills", 0)
                        pairs[pair_key]["player_b_kills"] += p2.get("kills", 0)

                        # Update last played time
                        created_at = p1.get("created_at")
                        if created_at:
                            if pairs[pair_key]["last_played"] is None or created_at > pairs[pair_key]["last_played"]:
                                pairs[pair_key]["last_played"] = created_at

    # Calculate derived stats (only from confirmed same_team_matches)
    for pair_key, stats in pairs.items():
        same_team_matches = stats["same_team_matches"]
        
        if same_team_matches >= min_matches:
            stats["win_rate"] = (stats["wins"] / same_team_matches * 100) if same_team_matches > 0 else 0
            stats["avg_placement"] = (sum(stats["placements"]) / len(stats["placements"])) if stats["placements"] else 0
            stats["avg_combined_kills"] = (stats["combined_kills"] / same_team_matches) if same_team_matches > 0 else 0
            stats["avg_combined_damage"] = (stats["combined_damage"] / same_team_matches) if same_team_matches > 0 else 0
        else:
            stats["win_rate"] = 0
            stats["avg_placement"] = 0
            stats["avg_combined_kills"] = 0
            stats["avg_combined_damage"] = 0

    return pairs


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


def fix_invalid_snapshots():
    """
    Fix invalid win_rate and kd values in existing snapshots.
    This is a one-time migration to correct data where matches or deaths were 0
    but wins/kills were non-zero, causing infinite ratios.
    Also removes invalid snapshots to prevent trend calculation issues.
    """
    data = _load_history()

    deleted_count = 0

    for guild_id in data.keys():
        if guild_id == "snapshots":
            continue  # Skip old structure if present

        guild_data = data.get(guild_id, {})
        daily_snapshots = guild_data.get("daily_snapshots", {})

        dates_to_delete = []

        for date in daily_snapshots:
            snapshot = daily_snapshots[date]
            all_invalid = True

            for player_name in snapshot:
                player_stats = snapshot[player_name]

                matches = player_stats.get("matches", 0)
                wins = player_stats.get("wins", 0)
                kills = player_stats.get("kills", 0)
                deaths = player_stats.get("deaths", 0)

                # Check if this snapshot has invalid data
                if (matches == 0 and wins > 0) or (deaths == 0 and kills > 0):
                    # Invalid snapshot for this player
                    continue
                else:
                    # At least one player has valid data
                    all_invalid = False

                    # Fix win_rate
                    if matches > 0:
                        player_stats["win_rate"] = round(wins / matches * 100, 2)
                    else:
                        player_stats["win_rate"] = 0.0

                    # Fix kd
                    if deaths > 0:
                        player_stats["kd"] = round(kills / deaths, 2)
                    else:
                        player_stats["kd"] = 0.0

            # If all players in this snapshot have invalid data, delete the entire snapshot
            if all_invalid:
                dates_to_delete.append(date)

        for date in dates_to_delete:
            del daily_snapshots[date]
            deleted_count += 1

    _save_history(data)
    print(f"[fix_invalid_snapshots] Fixed invalid win_rate and kd values in history.json, deleted {deleted_count} invalid snapshots")


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

    # Filter out invalid snapshots (where matches=0 or deaths=0 but has wins/kills)
    valid_snapshots = []
    for snapshot in snapshots:
        stats = snapshot["stats"]
        matches = stats.get("matches", 0)
        deaths = stats.get("deaths", 0)
        wins = stats.get("wins", 0)
        kills = stats.get("kills", 0)

        # Skip snapshots with invalid data (0 matches but wins, or 0 deaths but kills)
        if (matches == 0 and wins > 0) or (deaths == 0 and kills > 0):
            continue
        valid_snapshots.append(snapshot)

    if len(valid_snapshots) < 2:
        return {
            "error": "insufficient_data",
            "message": f"Need at least 2 valid snapshots over {days} days to calculate trend (skipped {len(snapshots) - len(valid_snapshots)} invalid snapshots)",
        }

    stats_start = valid_snapshots[0]["stats"]
    stats_end = valid_snapshots[-1]["stats"]

    delta = {}
    percent_change = {}

    # For raw cumulative stats, calculate percentage change
    for key in ["matches", "wins", "kills", "deaths", "damage", "top10"]:
        start_val = stats_start.get(key, 0)
        end_val = stats_end.get(key, 0)
        delta[key] = end_val - start_val

        if start_val > 0:
            percent_change[key] = ((end_val - start_val) / start_val) * 100
        else:
            percent_change[key] = None

    # For rate-based stats (already percentages/ratios), calculate percentage change correctly
    # win_rate is already a percentage (0-100), kd is a ratio, avg_placement is a number
    for key in ["win_rate", "kd", "avg_placement"]:
        start_val = stats_start.get(key, 0)
        end_val = stats_end.get(key, 0)
        delta[key] = end_val - start_val

        # For rate-based stats, use absolute change in percentage points for win_rate
        # For kd and avg_placement, calculate relative percentage change
        if key == "win_rate":
            # win_rate change in percentage points (e.g., 5.0% -> 6.0% = +1.0%)
            percent_change[key] = delta[key]  # Already in percentage points
        elif start_val > 0:
            percent_change[key] = ((end_val - start_val) / start_val) * 100
        else:
            percent_change[key] = None

    return {
        "stats_start": stats_start,
        "stats_end": stats_end,
        "delta": delta,
        "percent_change": percent_change,
        "period_days": days,
        "snapshots_count": len(valid_snapshots),
    }


def calculate_rank_progression(previous: dict, current: dict) -> dict:
    """
    Calculate rank progression between two snapshots.

    Explicit outcomes:
    - same season + valid RP → delta
    - different season → season_reset
    - missing previous data → insufficient_history
    - missing current RP → unavailable
    - API error → unavailable

    Args:
        previous: dict with ranked_points, ranked_tier, season_id, ranked_status
        current: dict with ranked_points, ranked_tier, season_id, ranked_status

    Returns:
        dict with:
        - status: "delta", "season_reset", "insufficient_history", "unavailable"
        - point_change: int (only if status is "delta")
        - previous_tier: str
        - current_tier: str
        - previous_points: int
        - current_points: int
    """
    prev_points = previous.get("ranked_points")
    curr_points = current.get("ranked_points")
    prev_season = previous.get("season_id")
    curr_season = current.get("season_id")
    prev_status = previous.get("ranked_status")
    curr_status = current.get("ranked_status")

    # Handle API errors or unavailable data
    if curr_status == "error" or prev_status == "error":
        return {
            "status": "unavailable",
            "reason": "ranked data unavailable due to API error"
        }

    # Handle missing data
    if prev_points is None or curr_points is None:
        return {
            "status": "insufficient_history",
            "reason": "missing ranked data in one or both snapshots"
        }

    # Handle season transition
    if prev_season != curr_season:
        return {
            "status": "season_reset",
            "reason": "season changed",
            "previous_season": prev_season,
            "current_season": curr_season,
            "previous_points": prev_points,
            "current_points": curr_points,
            "previous_tier": previous.get("ranked_tier"),
            "current_tier": current.get("ranked_tier"),
        }

    # Same season, valid data - calculate delta
    point_change = curr_points - prev_points
    return {
        "status": "delta",
        "point_change": point_change,
        "previous_points": prev_points,
        "current_points": curr_points,
        "previous_tier": previous.get("ranked_tier"),
        "current_tier": current.get("ranked_tier"),
    }
