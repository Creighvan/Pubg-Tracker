"""
Squad chemistry - analyze team synergy and best squad combinations.
"""

import discord
from discord import app_commands

import storage
import translations
from modules.utils import normalize_player_name


async def chemistry_impl(interaction: discord.Interaction, player1: str, player2: str):
    """Show chemistry between two players."""
    await interaction.response.defer()

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    normalized1 = normalize_player_name(player1)
    normalized2 = normalize_player_name(player2)
    tracked_players = [normalize_player_name(p) for p in guild_cfg.get("players", [])]

    if normalized1 not in tracked_players or normalized2 not in tracked_players:
        await interaction.followup.send(
            "Both players must be tracked to analyze chemistry.",
            ephemeral=True
        )
        return

    # Placeholder - chemistry requires match-level data with participant tracking
    embed = discord.Embed(
        title=f"🤝 {player1} + {player2} Chemistry",
        description="Squad chemistry analysis requires match-level data with participant tracking. This feature will be expanded when detailed match data is available.",
        color=discord.Color.purple()
    )

    embed.add_field(
        name="Coming Soon",
        value="Chemistry analysis (matches played together, win rate, combined performance) will be available once match telemetry with participant data is collected.",
        inline=False
    )

    await interaction.followup.send(embed=embed)


async def bestsquad_impl(interaction: discord.Interaction):
    """Show the best squad combination in the clan."""
    await interaction.response.defer()

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    players = guild_cfg.get("players", [])

    if not players:
        await interaction.followup.send(
            translations.get_translation(lang, "no_players_tracked"),
            ephemeral=True
        )
        return

    # Placeholder - best squad requires match-level data with participant tracking
    embed = discord.Embed(
        title="🏆 Best Squad Combination",
        description="Best squad analysis requires match-level data with participant tracking. This feature will be expanded when detailed match data is available.",
        color=discord.Color.purple()
    )

    embed.add_field(
        name="Coming Soon",
        value="Best squad analysis (most successful combinations, win rates, synergy metrics) will be available once match telemetry with participant data is collected.",
        inline=False
    )

    await interaction.followup.send(embed=embed)
