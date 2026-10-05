"""
Achievement system for tracking player milestones.
"""

import discord
from discord import app_commands

import storage
import history
import translations
from modules.utils import normalize_player_name

# Import achievement definitions from history module
from history import ACHIEVEMENTS


async def check_achievements(guild_id: int, player_name: str, stats: dict) -> list:
    """
    Check if player has earned any new achievements based on current stats.
    Returns list of newly earned achievement IDs.
    """
    normalized = normalize_player_name(player_name)
    new_achievements = []

    # Get existing achievements
    guild_history = await history.get_guild_history(guild_id)
    existing = guild_history.get("achievements", {}).get(normalized, {})

    # Check each achievement
    # Win milestones
    wins = stats.get("wins", 0)
    if wins >= 1 and "first_win" not in existing:
        new_achievements.append("first_win")
    if wins >= 10 and "wins_10" not in existing:
        new_achievements.append("wins_10")
    if wins >= 50 and "wins_50" not in existing:
        new_achievements.append("wins_50")
    if wins >= 100 and "wins_100" not in existing:
        new_achievements.append("wins_100")

    # Kill milestones
    kills = stats.get("kills", 0)
    if kills >= 100 and "kills_100" not in existing:
        new_achievements.append("kills_100")
    if kills >= 500 and "kills_500" not in existing:
        new_achievements.append("kills_500")
    if kills >= 1000 and "kills_1000" not in existing:
        new_achievements.append("kills_1000")
    if kills >= 5000 and "kills_5000" not in existing:
        new_achievements.append("kills_5000")

    # Survival mastery
    survival_tier = stats.get("survival_tier", 0)
    if survival_tier >= 5 and "survival_tier5" not in existing:
        new_achievements.append("survival_tier5")

    survival_level = stats.get("survival_level", 0)
    if survival_level >= 30 and "survival_level30" not in existing:
        new_achievements.append("survival_level30")

    return new_achievements


async def record_achievement(guild_id: int, player_name: str, achievement_id: str):
    """Record an achievement for a player."""
    normalized = normalize_player_name(player_name)

    async with history._lock:
        data = history._load_history()
        guild_id_str = str(guild_id)

        if guild_id_str not in data:
            data[guild_id_str] = {
                "daily_snapshots": {},
                "match_history": [],
                "achievements": {},
                "streaks": {},
            }

        if "achievements" not in data[guild_id_str]:
            data[guild_id_str]["achievements"] = {}

        if normalized not in data[guild_id_str]["achievements"]:
            data[guild_id_str]["achievements"][normalized] = {}

        from datetime import datetime, timezone
        data[guild_id_str]["achievements"][normalized][achievement_id] = datetime.now(timezone.utc).isoformat()

        history._save_history(data)


async def achievements_impl(interaction: discord.Interaction, player: str = None):
    """Show achievements for a player (or all players if none specified)."""
    await interaction.response.defer()

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    if player:
        # Show achievements for specific player
        normalized = normalize_player_name(player)
        tracked_players = [normalize_player_name(p) for p in guild_cfg.get("players", [])]

        if normalized not in tracked_players:
            await interaction.followup.send(
                translations.get_translation(lang, "player_not_tracked").format(name=player),
                ephemeral=True
            )
            return

        guild_history = await history.get_guild_history(interaction.guild_id)
        player_achievements = guild_history.get("achievements", {}).get(normalized, {})

        if not player_achievements:
            await interaction.followup.send(
                f"{player} hasn't earned any achievements yet.",
                ephemeral=True
            )
            return

        # Build embed
        embed = discord.Embed(
            title=f"🏆 {player}'s Achievements",
            color=discord.Color.gold()
        )

        for achievement_id, timestamp in player_achievements.items():
            achievement = ACHIEVEMENTS.get(achievement_id)
            if achievement:
                embed.add_field(
                    name=f"{achievement['emoji']} {achievement['name']}",
                    value=f"{achievement['description']}\n*Earned: {timestamp[:10]}*",
                    inline=True
                )

        await interaction.followup.send(embed=embed)

    else:
        # Show achievements for all tracked players
        players = guild_cfg.get("players", [])

        if not players:
            await interaction.followup.send(
                translations.get_translation(lang, "no_players_tracked"),
                ephemeral=True
            )
            return

        guild_history = await history.get_guild_history(interaction.guild_id)
        all_achievements = guild_history.get("achievements", {})

        # Count achievements per player
        achievement_counts = []
        for player in players:
            normalized = normalize_player_name(player)
            player_achievements = all_achievements.get(normalized, {})
            if player_achievements:
                achievement_counts.append({
                    "name": player,
                    "count": len(player_achievements),
                    "achievements": player_achievements
                })

        if not achievement_counts:
            await interaction.followup.send(
                "No achievements earned yet by any tracked players.",
                ephemeral=True
            )
            return

        # Sort by achievement count
        achievement_counts.sort(key=lambda x: x["count"], reverse=True)

        # Build embed
        embed = discord.Embed(
            title="🏆 Clan Achievements",
            color=discord.Color.gold()
        )

        for item in achievement_counts[:10]:  # Top 10
            player = item["name"]
            count = item["count"]
            achievements = item["achievements"]

            # Show top 3 achievements
            achievement_names = []
            for achievement_id in list(achievements.keys())[:3]:
                achievement = ACHIEVEMENTS.get(achievement_id)
                if achievement:
                    achievement_names.append(f"{achievement['emoji']} {achievement['name']}")

            if len(achievements) > 3:
                achievement_names.append(f"+{len(achievements) - 3} more")

            embed.add_field(
                name=f"{player} ({count})",
                value=", ".join(achievement_names),
                inline=True
            )

        embed.set_footer(text=f"Showing top {min(len(achievement_counts), 10)} players")

        await interaction.followup.send(embed=embed)
