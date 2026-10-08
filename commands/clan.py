"""
Clan management command implementations for PUBG Tracker bot.
"""

import logging
import storage
import translations
from storage import DatabaseCorruptionError
import discord

logger = logging.getLogger(__name__)


async def setclan_impl(interaction, name, pubg):
    """Implementation of setclan command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    try:
        clan = await pubg.get_clan_for_player_name(name.strip())
    except PubgApiError as e:
        from bot import send_error_response
        await send_error_response(interaction, e, context="Failed to resolve PUBG clan")
        return
    if clan is None:
        from modules.config import PUBG_SHARD
        await interaction.followup.send(
            translations.get_translation(lang, "clan_not_found").format(name=name.strip(), shard=PUBG_SHARD),
            ephemeral=True,
        )
        return
    def modifier(guild_cfg):
        guild_cfg["pubg_clan_id"] = clan["id"]
        guild_cfg["pubg_clan_name"] = clan["name"]
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.followup.send(
        translations.get_translation(lang, "clan_set").format(name=clan['name'], tag=clan['tag'], level=clan['level']),
        ephemeral=True,
    )


async def clanlevel_impl(interaction, pubg):
    """Implementation of clanlevel command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    try:
        from modules.reports import fetch_clan_level_report
        result = await fetch_clan_level_report(interaction.guild_id)
    except PubgApiError as e:
        from bot import send_error_response
        await send_error_response(interaction, e, context="PUBG API error")
        return
    if result is None:
        await interaction.followup.send(translations.get_translation(lang, "clan_not_set"))
        return
    embed, _ = result
    await interaction.followup.send(embed=embed)


async def setclanchannel_impl(interaction, send_audit_log):
    """Implementation of setclanchannel command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    def modifier(guild_cfg):
        guild_cfg["clan_channel_id"] = interaction.channel_id
        guild_cfg["clan_level_enabled"] = True
        guild_cfg["clan_message_id"] = None
    await storage.modify_guild(interaction.guild_id, modifier)

    # Immediately post the report
    try:
        from modules.reports import fetch_clan_level_report
        result = await fetch_clan_level_report(interaction.guild_id)
        if result:
            embed, clan = result
            new_message = await interaction.channel.send(embed=embed)
            
            def modifier(guild_cfg):
                guild_cfg["clan_message_id"] = new_message.id
                return new_message.id
            
            await storage.modify_guild(interaction.guild_id, modifier)
            
            await interaction.followup.send(
                translations.get_translation(lang, "clan_channel_set").format(channel=interaction.channel.mention)
            )
            
            await send_audit_log(
                interaction.guild_id,
                "Channel Configured & Report Posted",
                f"Clan level report channel set and initial report posted",
                user=interaction.user,
                details={"Channel": interaction.channel_id, "Clan": clan["name"]},
                report_embed=embed
            )
        else:
            await interaction.followup.send(
                f"✅ Weekly clan-level reports will post in {interaction.channel.mention}. "
                f"Choose the weekly time with `/setclantime`."
            )
    except PubgApiError as e:
        from bot import send_error_response
        await send_error_response(interaction, e, context="PUBG API error")
    except Exception as e:
        from bot import send_error_response
        await send_error_response(interaction, e, context="Error")


async def setclantime_impl(interaction, day, hour, minute):
    """Implementation of setclantime command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["clan_day_utc"] = day
        guild_cfg["clan_hour_utc"] = hour
        guild_cfg["clan_minute_utc"] = minute
    
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.followup.send(translations.get_translation(lang, "clan_time_set").format(day=day, hour=hour, minute=minute))
