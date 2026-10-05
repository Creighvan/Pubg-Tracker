"""
Weapon analytics - per-weapon performance tracking.
"""

import discord
from discord import app_commands

import storage
import translations
from modules.utils import normalize_player_name
from pubg_api import PubgClient
from modules.config import pubg


async def weaponstats_impl(interaction: discord.Interaction, player: str):
    """Show weapon statistics for a player."""
    await interaction.response.defer()

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

    # Fetch weapon mastery
    try:
        mastery = await pubg.get_weapon_mastery(player)
    except Exception as e:
        await interaction.followup.send(
            f"Error fetching weapon mastery: {e}",
            ephemeral=True
        )
        return

    if not mastery:
        await interaction.followup.send(
            f"No weapon mastery data available for {player}.",
            ephemeral=True
        )
        return

    # Build embed
    embed = discord.Embed(
        title=f"🔫 {player}'s Weapon Stats",
        color=discord.Color.red()
    )

    # Sort by kills
    sorted_weapons = sorted(mastery.items(), key=lambda x: x[1].get("kills", 0), reverse=True)

    # Show top 5 weapons
    for weapon_name, weapon_data in sorted_weapons[:5]:
        kills = weapon_data.get("kills", 0)
        damage = weapon_data.get("damage", 0)
        level = weapon_data.get("level", 0)

        matches = weapon_data.get("matches", 1)
        kills_per_match = kills / max(matches, 1)

        embed.add_field(
            name=f"**{weapon_name}** (Level {level})",
            value=f"Kills: {kills:,}\nDamage: {int(damage):,}\nKills/Match: {kills_per_match:.2f}",
            inline=True
        )

    # Find favorite weapon
    if sorted_weapons:
        favorite = sorted_weapons[0]
        fav_name = favorite[0]
        fav_kills = favorite[1].get("kills", 0)
        embed.set_footer(text=f"Favorite weapon: {fav_name} ({fav_kills:,} kills)")

    await interaction.followup.send(embed=embed)
