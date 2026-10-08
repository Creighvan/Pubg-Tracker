"""
Inactive date management command implementations for PUBG Tracker bot.
"""

import logging
import storage
import translations
from storage import DatabaseCorruptionError
from datetime import datetime, timedelta, timezone
import discord

logger = logging.getLogger(__name__)


async def setinactivedate_impl(interaction, name, days_ago):
    """Implementation of setinactivedate command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    from datetime import datetime, timedelta, timezone
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    inactive_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    def modifier(guild_cfg):
        guild_cfg["inactive_dates"] = guild_cfg.get("inactive_dates", {})
        guild_cfg["inactive_dates"][name] = inactive_date.isoformat()
    
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.followup.send(
        translations.get_translation(lang, "inactive_date_set").format(name=name, days=days_ago)
    )


async def removeinactivedate_impl(interaction, name):
    """Implementation of removeinactivedate command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["inactive_dates"] = guild_cfg.get("inactive_dates", {})
        if name in guild_cfg["inactive_dates"]:
            del guild_cfg["inactive_dates"][name]
            return True
        return False
    
    removed = await storage.modify_guild(interaction.guild_id, modifier)
    if removed:
        await interaction.followup.send(translations.get_translation(lang, "inactive_date_removed").format(name=name))
    else:
        await interaction.followup.send(translations.get_translation(lang, "inactive_date_not_found").format(name=name), ephemeral=True)


async def resetinactivecount_impl(interaction, name):
    """Implementation of resetinactivecount command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["inactive_dates"] = guild_cfg.get("inactive_dates", {})
        guild_cfg["inactive_dates"][name] = datetime.now(timezone.utc).isoformat()
    
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.followup.send(translations.get_translation(lang, "inactive_count_reset").format(name=name))
