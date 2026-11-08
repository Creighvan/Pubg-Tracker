"""
Inactive date management command implementations for PUBG Tracker bot.
"""

import logging
import storage
import translations
from datetime import datetime, timedelta, timezone
import discord
from modules.utils import normalize_player_name

logger = logging.getLogger(__name__)


async def setinactivedate_impl(interaction, name, days_ago):
    """Implementation of setinactivedate command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    inactive_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    
    def modifier(guild_cfg):
        guild_cfg["manual_inactive_dates"] = guild_cfg.get("manual_inactive_dates", {})
        # same key the report uses to look the player up
        guild_cfg["manual_inactive_dates"][normalize_player_name(name)] = {
            "date": inactive_date,
            "set_at": datetime.now(timezone.utc).isoformat()
        }
    
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.followup.send(
        translations.get_translation(lang, "inactive_date_set").format(name=name, date=days_ago)
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
        # The manual date lives in "manual_inactive_dates" (this used to look in a
        # different, unused key, so a manual date could never be removed here).
        removed = False
        for store in ("manual_inactive_dates", "inactive_dates"):
            entries = guild_cfg.get(store, {})
            for key in {normalize_player_name(name), name, name.lower().replace(" ", "")}:
                if key in entries:
                    del entries[key]
                    removed = True
        return removed
    
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
