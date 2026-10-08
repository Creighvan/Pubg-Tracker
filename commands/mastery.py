"""
Mastery command implementations for PUBG Tracker bot.
"""

import logging
import storage
import translations
from pubg_api import PubgApiError
import discord

logger = logging.getLogger(__name__)


async def masterystats_impl(interaction, pubg):
    """Implementation of masterystats command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    try:
        result = await pubg.get_mastery_report(interaction.guild_id)
    except PubgApiError as e:
        await interaction.followup.send(f"❌ {translations.get_translation(lang, 'api_error')}: {str(e)}")
        return

    if result:
        embed, _ = result
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(translations.get_translation(lang, "no_mastery_data"))


async def survivalstats_impl(interaction, pubg):
    """Implementation of survivalstats command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    try:
        result = await pubg.get_survival_mastery_report(interaction.guild_id)
    except PubgApiError as e:
        await interaction.followup.send(f"❌ {translations.get_translation(lang, 'api_error')}: {str(e)}")
        return

    if result:
        embed, _ = result
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(translations.get_translation(lang, "no_survival_data"))
