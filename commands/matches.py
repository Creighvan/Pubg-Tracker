"""
Match history explorer - view recent matches for a player.
"""

import logging
import discord
from discord import app_commands

import storage
import translations
from modules.utils import normalize_player_name

logger = logging.getLogger(__name__)


async def matches_impl(interaction: discord.Interaction, player: str):
    """Show recent matches for a player."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    normalized = normalize_player_name(player)
    tracked_players = [normalize_player_name(p) for p in guild_cfg.get("players", [])]

    if normalized not in tracked_players:
        await interaction.followup.send(
            translations.get_translation(lang, "player_not_tracked").format(name=player),
            ephemeral=True
        )
        return

    # Placeholder - match history requires match-level data from telemetry
    embed = discord.Embed(
        title=f"🪂 {player}'s Recent Matches",
        description="Match history explorer requires match-level telemetry data. This feature will be expanded when detailed match data is available.",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Coming Soon",
        value="Recent match history with kills, damage, placement, and teammates will be available once match telemetry data is collected.",
        inline=False
    )

    await interaction.followup.send(embed=embed)
