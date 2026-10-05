"""
Leaderboard command implementations for PUBG Tracker bot.
"""

import storage
import translations
from pubg_api import PubgApiError


async def leaderboardstats_impl(interaction, pubg):
    """Implementation of leaderboardstats command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    await interaction.response.defer()
    try:
        result = await pubg.get_leaderboard_report(interaction.guild_id)
    except PubgApiError as e:
        await interaction.followup.send(f"❌ {translations.get_translation(lang, 'api_error')}: {str(e)}")
        return
    
    if result:
        embed, _ = result
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(translations.get_translation(lang, "no_leaderboard_data"))


async def setleaderboardregion_impl(interaction, region):
    """Implementation of setleaderboardregion command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["leaderboard_region"] = region.value
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(translations.get_translation(lang, "leaderboard_region_set").format(region=region.value))


async def setleaderboardqueue_impl(interaction, queue):
    """Implementation of setleaderboardqueue command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["leaderboard_queue"] = queue.value
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(translations.get_translation(lang, "leaderboard_queue_set").format(queue=queue.value))
