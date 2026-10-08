"""
Weekly clan awards - weekly performance summary and awards.
"""

import logging
import discord
from discord import app_commands

import storage
import history
import translations
from modules.utils import normalize_player_name
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


AWARD_CATEGORIES = {
    "most_wins": {
        "name": "Most Wins",
        "emoji": "🏆",
        "description": "Most match wins this week",
    },
    "most_kills": {
        "name": "Top Fragger",
        "emoji": "💀",
        "description": "Most kills this week",
    },
    "most_damage": {
        "name": "Most Damage",
        "emoji": "💥",
        "description": "Highest damage output this week",
    },
    "best_kd": {
        "name": "Best K/D",
        "emoji": "🎯",
        "description": "Highest kill/death ratio this week",
    },
    "best_win_rate": {
        "name": "Best Win Rate",
        "emoji": "📈",
        "description": "Highest win percentage this week",
    },
    "most_active": {
        "name": "Most Active",
        "emoji": "🔥",
        "description": "Most matches played this week",
    },
    "most_improved": {
        "name": "Most Improved",
        "emoji": "📊",
        "description": "Biggest K/D improvement this week",
    },
}


async def calculate_weekly_awards(guild_id: int, days: int = 7) -> dict:
    """Calculate weekly awards based on historical data."""
    guild_cfg = await storage.get_guild(guild_id)
    players = guild_cfg.get("players", [])

    if not players:
        return {}

    # Get start and end dates
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # Get snapshots for the period
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    awards = {
        "most_wins": None,
        "most_kills": None,
        "most_damage": None,
        "best_kd": None,
        "best_win_rate": None,
        "most_active": None,
        "most_improved": None,
    }

    # Calculate stats for each player
    player_stats = {}
    for player in players:
        normalized = normalize_player_name(player)
        snapshots = await history.get_player_snapshots(guild_id, player, days=days)

        if len(snapshots) < 2:
            continue

        first_snapshot = snapshots[0]
        last_snapshot = snapshots[-1]

        # Calculate week totals
        wins_delta = last_snapshot.get("wins", 0) - first_snapshot.get("wins", 0)
        kills_delta = last_snapshot.get("kills", 0) - first_snapshot.get("kills", 0)
        damage_delta = last_snapshot.get("damage", 0) - first_snapshot.get("damage", 0)
        matches_delta = last_snapshot.get("matches", 0) - first_snapshot.get("matches", 0)

        # Calculate rates
        deaths_delta = last_snapshot.get("deaths", 0) - first_snapshot.get("deaths", 0)
        kd = kills_delta / max(deaths_delta, 1) if deaths_delta > 0 else kills_delta
        win_rate = (wins_delta / max(matches_delta, 1)) * 100 if matches_delta > 0 else 0

        # Calculate improvement (K/D change)
        kd_start = first_snapshot.get("kd", 0)
        kd_end = last_snapshot.get("kd", 0)
        kd_improvement = kd_end - kd_start

        player_stats[normalized] = {
            "name": player,
            "wins": wins_delta,
            "kills": kills_delta,
            "damage": damage_delta,
            "kd": kd,
            "win_rate": win_rate,
            "matches": matches_delta,
            "kd_improvement": kd_improvement,
        }

    if not player_stats:
        return awards

    # Find winners for each category
    for stat_key, award_key in [
        ("wins", "most_wins"),
        ("kills", "most_kills"),
        ("damage", "most_damage"),
        ("kd", "best_kd"),
        ("win_rate", "best_win_rate"),
        ("matches", "most_active"),
        ("kd_improvement", "most_improved"),
    ]:
        best_player = max(player_stats.items(), key=lambda x: x[1][stat_key] if x[1][stat_key] > 0 else -1)
        if best_player[1][stat_key] > 0:
            awards[award_key] = best_player[1]

    return awards


async def weeklyawards_impl(interaction: discord.Interaction, days: int = 7):
    """Show weekly clan awards."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    players = guild_cfg.get("players", [])

    if not players:
        await interaction.followup.send(
            translations.get_translation(lang, "no_players_tracked"),
            ephemeral=True
        )
        return

    awards = await calculate_weekly_awards(interaction.guild_id, days)

    if not any(awards.values()):
        await interaction.followup.send(
            "Not enough historical data for weekly awards. Need at least 2 days of snapshots.",
            ephemeral=True
        )
        return

    # Build embed
    embed = discord.Embed(
        title=f"🏆 Weekly Clan Awards ({days} Days)",
        color=discord.Color.gold()
    )

    for award_id, player_data in awards.items():
        if player_data:
            award_info = AWARD_CATEGORIES[award_id]
            player_name = player_data["name"]

            # Get the value based on award type
            if award_id == "most_wins":
                value = f"{player_data['wins']} wins"
            elif award_id == "most_kills":
                value = f"{player_data['kills']} kills"
            elif award_id == "most_damage":
                value = f"{int(player_data['damage']):,} damage"
            elif award_id == "best_kd":
                value = f"{player_data['kd']:.2f} K/D"
            elif award_id == "best_win_rate":
                value = f"{player_data['win_rate']:.1f}% win rate"
            elif award_id == "most_active":
                value = f"{player_data['matches']} matches"
            elif award_id == "most_improved":
                value = f"+{player_data['kd_improvement']:.2f} K/D"
            else:
                value = "N/A"

            embed.add_field(
                name=f"{award_info['emoji']} {award_info['name']}",
                value=f"**{player_name}**\n{value}",
                inline=True
            )

    embed.set_footer(text=f"Based on {days} days of historical data")

    await interaction.followup.send(embed=embed)
