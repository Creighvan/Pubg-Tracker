"""
Streak tracking system for player performance streaks.
"""

import discord
from discord import app_commands

import storage
import history
import translations
from modules.utils import normalize_player_name
from datetime import datetime, timezone, timedelta


STREAK_TYPES = {
    "day_streak": {
        "name": "Day Streak",
        "emoji": "🔥",
        "description": "Consecutive days with activity",
    },
}


async def update_streaks(guild_id: int, player_name: str, stats: dict):
    """
    Update streaks for a player based on current stats.
    This should be called during daily snapshot.
    """
    normalized = normalize_player_name(player_name)

    data = history._load_history()
    guild_id_str = str(guild_id)

    if guild_id_str not in data:
        data[guild_id_str] = {
            "daily_snapshots": {},
            "match_history": [],
            "achievements": {},
            "streaks": {},
        }

    if "streaks" not in data[guild_id_str]:
        data[guild_id_str]["streaks"] = {}

    if normalized not in data[guild_id_str]["streaks"]:
        data[guild_id_str]["streaks"][normalized] = {
            "day_streak": 0,
            "last_snapshot_date": None,
        }

    player_streaks = data[guild_id_str]["streaks"][normalized]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Update day streak
    if player_streaks["last_snapshot_date"]:
        last_date = datetime.strptime(player_streaks["last_snapshot_date"], "%Y-%m-%d")
        today_date = datetime.strptime(today, "%Y-%m-%d")
        days_diff = (today_date - last_date).days

        if days_diff == 1:
            # Consecutive day
            player_streaks["day_streak"] += 1
        elif days_diff > 1:
            # Streak broken
            player_streaks["day_streak"] = 1
        # If days_diff == 0, same day, don't change
    else:
        player_streaks["day_streak"] = 1

    player_streaks["last_snapshot_date"] = today

    history._save_history(data)


async def streaks_impl(interaction: discord.Interaction, player: str = None):
    """Show current streaks for a player (or all players if none specified)."""
    await interaction.response.defer()

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    if player:
        # Show streaks for specific player
        normalized = normalize_player_name(player)
        tracked_players = [normalize_player_name(p) for p in guild_cfg.get("players", [])]

        if normalized not in tracked_players:
            await interaction.followup.send(
                translations.get_translation(lang, "player_not_tracked").format(name=player),
                ephemeral=True
            )
            return

        guild_history = await history.get_guild_history(interaction.guild_id)
        player_streaks = guild_history.get("streaks", {}).get(normalized, {})

        if not player_streaks:
            await interaction.followup.send(
                f"{player} has no streak data yet.",
                ephemeral=True
            )
            return

        # Build embed
        embed = discord.Embed(
            title=f"🔥 {player}'s Streaks",
            color=discord.Color.orange()
        )

        day_streak = player_streaks.get("day_streak", 0)
        embed.add_field(
            name=f"🔥 Day Streak",
            value=f"{day_streak} consecutive days with activity",
            inline=True
        )

        await interaction.followup.send(embed=embed)

    else:
        # Show streaks for all tracked players
        players = guild_cfg.get("players", [])

        if not players:
            await interaction.followup.send(
                translations.get_translation(lang, "no_players_tracked"),
                ephemeral=True
            )
            return

        guild_history = await history.get_guild_history(interaction.guild_id)
        all_streaks = guild_history.get("streaks", {})

        # Find top streaks by type
        top_streaks = {
            "day_streak": [],
        }

        for player in players:
            normalized = normalize_player_name(player)
            player_streaks = all_streaks.get(normalized, {})

            for streak_id in top_streaks.keys():
                count = player_streaks.get(streak_id, 0)
                if count > 0:
                    top_streaks[streak_id].append({
                        "name": player,
                        "count": count
                    })

        # Sort each streak type
        for streak_id in top_streaks:
            top_streaks[streak_id].sort(key=lambda x: x["count"], reverse=True)

        # Build embed
        embed = discord.Embed(
            title="🔥 Clan Streaks",
            color=discord.Color.orange()
        )

        for streak_id, streak_info in STREAK_TYPES.items():
            top_list = top_streaks[streak_id][:5]  # Top 5
            if top_list:
                top_text = "\n".join(
                    f"**{i+1}.** {item['name']} — {item['count']} days"
                    for i, item in enumerate(top_list)
                )
                embed.add_field(
                    name=f"{streak_info['emoji']} {streak_info['name']}",
                    value=top_text,
                    inline=True
                )

        await interaction.followup.send(embed=embed)
