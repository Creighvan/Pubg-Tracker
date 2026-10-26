"""
Highlights command implementations for PUBG Tracker bot.
"""

import logging
import storage
import translations
from pubg_api import PubgApiError
from modules.reports import fetch_highlights_report

logger = logging.getLogger(__name__)


async def dailyhighlights_impl(interaction, pubg):
    """Implementation of dailyhighlights command."""
    # Interaction already deferred by safe_command_wrapper
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    try:
        # Use 6-hour window instead of 24 for faster response
        # Full telemetry processing is very slow - 2+ hours for 77 players
        result = await fetch_highlights_report(interaction.guild_id, None, hours=6, max_matches_checked=20)
    except PubgApiError as e:
        await interaction.followup.send(f"❌ {translations.get_translation(lang, 'api_error')}: {str(e)}")
        return
    
    if result:
        embed, _ = result
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(translations.get_translation(lang, "no_highlights"))
