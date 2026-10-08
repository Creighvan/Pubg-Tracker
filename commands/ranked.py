"""
Ranked stats command implementations for PUBG Tracker bot.
"""

import logging
import storage
import translations
from storage import DatabaseCorruptionError
from pubg_api import PubgApiError
import discord

logger = logging.getLogger(__name__)


async def rankedsquad_impl(interaction, pubg):
    """Implementation of rankedsquad command."""
    await _run_ranked_command_impl(interaction, pubg, "squad", "Squad TPP")


async def rankedduo_impl(interaction, pubg):
    """Implementation of rankedduo command."""
    await _run_ranked_command_impl(interaction, pubg, "duo", "Duo TPP")


async def rankedsolo_impl(interaction, pubg):
    """Implementation of rankedsolo command."""
    await _run_ranked_command_impl(interaction, pubg, "solo", "Solo TPP")


async def rankedsquadfpp_impl(interaction, pubg):
    """Implementation of rankedsquadfpp command."""
    await _run_ranked_command_impl(interaction, pubg, "squad-fpp", "Squad FPP")


async def rankedduofpp_impl(interaction, pubg):
    """Implementation of rankedduofpp command."""
    await _run_ranked_command_impl(interaction, pubg, "duo-fpp", "Duo FPP")


async def rankedsolofpp_impl(interaction, pubg):
    """Implementation of rankedsolofpp command."""
    await _run_ranked_command_impl(interaction, pubg, "solo-fpp", "Solo FPP")


async def refreshranked_impl(interaction, pubg):
    """Implementation of refreshranked command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["ranked_refresh"] = True
    await storage.modify_guild(interaction.guild_id, modifier)
    
    await interaction.followup.send(translations.get_translation(lang, "ranked_refresh_queued"))


async def updateranked_impl(interaction, pubg):
    """Implementation of updateranked command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["ranked_update"] = True
    await storage.modify_guild(interaction.guild_id, modifier)
    
    await interaction.followup.send(translations.get_translation(lang, "ranked_update_queued"))


async def _run_ranked_command_impl(interaction, pubg, mode, mode_label):
    """Helper to run ranked commands."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    try:
        result = await pubg.get_ranked_report(interaction.guild_id, mode)
    except PubgApiError as e:
        await interaction.followup.send(f"❌ {translations.get_translation(lang, 'api_error')}: {str(e)}")
        return
    
    if result:
        embed, _ = result
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(translations.get_translation(lang, "no_ranked_data"))
