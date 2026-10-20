"""
Chicken Dinner command implementations for PUBG Tracker bot.
"""

import logging
import storage
import translations
from pubg_api import PubgApiError
import discord

logger = logging.getLogger(__name__)


async def chickendinner_impl(interaction, pubg):
    """Implementation of chickendinner command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    players = guild_cfg.get("players", [])
    
    if not players:
        await interaction.followup.send(translations.get_translation(lang, "no_players_tracked_short"), ephemeral=True)
        return
    
    try:
        from datetime import datetime, timezone
        wins, not_found = await pubg.get_squad_wins(players, matches_to_check=5)
        
        if not wins:
            await interaction.followup.send(translations.get_translation(lang, "no_chicken_dinner"))
            return
        
        # Create embed with recent wins
        embed = discord.Embed(
            title="🍗 Recent Chicken Dinners",
            description="Last 50 matches per player, all game modes",
            color=discord.Color.gold()
        )
        
        for win in wins[:10]:  # Show up to 10 most recent
            player_name = win.get("name", "Unknown")
            match_time = win.get("match_time", "Unknown time")
            embed.add_field(
                name=player_name,
                value=f"🏆 {match_time}",
                inline=False
            )
        
        embed.set_footer(text=f"Updates every 15 minutes • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        await interaction.followup.send(embed=embed)
        
    except PubgApiError as e:
        await interaction.followup.send(f"❌ {translations.get_translation(lang, 'api_error')}: {str(e)}")
        return


async def setchickendinnerchannel_impl(interaction):
    """Implementation of setchickendinnerchannel command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["chicken_dinner_channel_id"] = interaction.channel_id
        guild_cfg["chicken_dinner_enabled"] = True
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.followup.send(translations.get_translation(lang, "chicken_dinner_channel_set"))


async def pingtoggle_impl(interaction):
    """Implementation of pingtoggle command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    current = guild_cfg.get("mentions_enabled", False)
    
    def modifier(guild_cfg):
        guild_cfg["mentions_enabled"] = not current
        return not current
    
    new_state = await storage.modify_guild(interaction.guild_id, modifier)
    status = "enabled" if new_state else "disabled"
    await interaction.followup.send(f"Mention notifications {status}")
