"""
Chicken Dinner command implementations for PUBG Tracker bot.
"""

import storage
import translations
from pubg_api import PubgApiError


async def chickendinner_impl(interaction, pubg):
    """Implementation of chickendinner command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    await interaction.response.defer()
    try:
        result = await pubg.get_chicken_dinner_report(interaction.guild_id)
    except PubgApiError as e:
        await interaction.followup.send(f"❌ {translations.get_translation(lang, 'api_error')}: {str(e)}")
        return
    
    if result:
        embed, _ = result
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(translations.get_translation(lang, "no_chicken_dinner"))


async def setchickendinnerchannel_impl(interaction):
    """Implementation of setchickendinnerchannel command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["chicken_dinner_channel_id"] = interaction.channel_id
        guild_cfg["chicken_dinner_enabled"] = True
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(translations.get_translation(lang, "chicken_dinner_channel_set"))


async def pingtoggle_impl(interaction):
    """Implementation of pingtoggle command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    current = guild_cfg.get("mentions_enabled", False)
    
    def modifier(guild_cfg):
        guild_cfg["mentions_enabled"] = not current
        return not current
    
    new_state = await storage.modify_guild(interaction.guild_id, modifier)
    status = "enabled" if new_state else "disabled"
    await interaction.response.send_message(f"Mention notifications {status}")
