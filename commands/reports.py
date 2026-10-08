"""
Report command implementations for PUBG Tracker bot.
"""

import logging
import storage
import translations
from pubg_api import PubgApiError
import discord

logger = logging.getLogger(__name__)


async def clanstats_impl(interaction, pubg):
    """Implementation of clanstats command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    try:
        result = await pubg.get_clan_report(interaction.guild_id)
    except PubgApiError as e:
        await interaction.followup.send(f"❌ {translations.get_translation(lang, 'api_error')}: {str(e)}")
        return
    
    if result:
        embed, _ = result
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(translations.get_translation(lang, "no_clan_data"))


async def postnow_impl(interaction, pubg):
    """Implementation of postnow command."""
    await clanstats_impl(interaction, pubg)


async def leaderboard_impl(interaction, pubg, sort_by):
    """Implementation of leaderboard command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    stat_key = sort_by.value if sort_by else "kills"
    
    if not guild_cfg["players"]:
        await interaction.followup.send(translations.get_translation(lang, "no_players_tracked"))
        return
    
    try:
        players, not_found = await pubg.get_players_and_stats(guild_cfg["players"], game_mode=guild_cfg["game_mode"])
    except PubgApiError as e:
        await interaction.followup.send(f"❌ {translations.get_translation(lang, 'api_error')}: {str(e)}")
        return
    
    ranked = sorted(players, key=lambda p: p["stats"].get(stat_key, 0), reverse=True)
    lines = [f"{i}. **{p['name']}** — {p['stats'].get(stat_key, 0):,}" for i, p in enumerate(ranked, start=1)]
    
    import discord
    embed = discord.Embed(
        title=f"Leaderboard — {stat_key} ({guild_cfg['game_mode']})",
        description="\n".join(lines) or "No data.",
        color=discord.Color.blue(),
    )
    if not_found:
        embed.set_footer(text=f"Not found: {', '.join(not_found)}")
    await interaction.followup.send(embed=embed)


async def lastactive_impl(interaction, pubg):
    """Implementation of lastactive command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    from modules.reports import fetch_last_active_report
    
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    try:
        result = await fetch_last_active_report(interaction.guild_id, interaction.guild.name)
    except PubgApiError as e:
        await interaction.followup.send(f"❌ {translations.get_translation(lang, 'api_error')}: {str(e)}")
        return
    
    if result:
        embed, _ = result
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(translations.get_translation(lang, "no_active_data"))
