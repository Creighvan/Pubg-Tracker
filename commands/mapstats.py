"""
Map analytics - map-specific performance tracking.
"""

import discord
from discord import app_commands

import storage
import history
import translations
from modules.utils import normalize_player_name


async def mapstats_impl(interaction: discord.Interaction):
    """Show clan map performance statistics."""
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

    # For now, this is a placeholder since map data requires match telemetry
    # This will be expanded when match history with map data is available
    embed = discord.Embed(
        title="🗺️ Map Analytics",
        description="Map-specific performance tracking requires match-level data. This feature will be expanded when match history with map telemetry is available.",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Coming Soon",
        value="Map performance statistics (Erangel, Miramar, Taego, etc.) will be available once match history with map data is collected.",
        inline=False
    )

    await interaction.followup.send(embed=embed)
