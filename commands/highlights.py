"""
Highlights command implementations for PUBG Tracker bot.
"""

import storage
import translations
from pubg_api import PubgApiError


async def dailyhighlights_impl(interaction, pubg):
    """Implementation of dailyhighlights command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    await interaction.response.defer()
    try:
        result = await pubg.get_highlights_report(interaction.guild_id)
    except PubgApiError as e:
        await interaction.followup.send(f"❌ {translations.get_translation(lang, 'api_error')}: {str(e)}")
        return
    
    if result:
        embed, _ = result
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(translations.get_translation(lang, "no_highlights"))
