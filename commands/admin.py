"""
Admin command implementations for PUBG Tracker bot.
"""

import logging
import storage
from datetime import datetime, timezone
import discord

logger = logging.getLogger(__name__)


async def runallreports_impl(interaction):
    """Run all reports immediately for this guild."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")
        
        # Import report functions
        from modules.reports import (
            fetch_clan_report, fetch_last_active_report,
            fetch_ranked_report, fetch_highlights_report,
            fetch_clan_level_report, fetch_survival_mastery_report
        )
        
        results = []
        channel = interaction.channel
        
        # Run digest (uses fetch_clan_report)
        if guild_cfg.get("digest_enabled"):
            try:
                result = await fetch_clan_report(interaction.guild_id, None)
                embed = result[0] if result else None
                if embed:
                    await channel.send(embed=embed)
                    results.append("✅ Digest")
                else:
                    results.append("❌ Digest: No data")
            except Exception as e:
                results.append(f"❌ Digest: {e}")
        
        # Run last active
        if guild_cfg.get("activity_enabled"):
            try:
                result = await fetch_last_active_report(interaction.guild_id, None)
                embed = result[0] if result else None
                if embed:
                    await channel.send(embed=embed)
                    results.append("✅ Last Active")
                else:
                    results.append("❌ Last Active: No data")
            except Exception as e:
                results.append(f"❌ Last Active: {e}")
        
        # Run ranked
        if guild_cfg.get("ranked_enabled"):
            try:
                result = await fetch_ranked_report(interaction.guild_id, None)
                embed = result[0] if result else None
                if embed:
                    await channel.send(embed=embed)
                    results.append("✅ Ranked")
                else:
                    results.append("❌ Ranked: No data")
            except Exception as e:
                results.append(f"❌ Ranked: {e}")
        
        # Run highlights
        if guild_cfg.get("highlights_enabled"):
            try:
                result = await fetch_highlights_report(interaction.guild_id, None)
                embed = result[0] if result else None
                if embed:
                    await channel.send(embed=embed)
                    results.append("✅ Highlights")
                else:
                    results.append("❌ Highlights: No data")
            except Exception as e:
                results.append(f"❌ Highlights: {e}")
        
        # Run clan level
        if guild_cfg.get("clan_level_enabled"):
            try:
                result = await fetch_clan_level_report(interaction.guild_id)
                embed = result[0] if result else None
                if embed:
                    await channel.send(embed=embed)
                    results.append("✅ Clan Level")
                else:
                    results.append("❌ Clan Level: No data")
            except Exception as e:
                results.append(f"❌ Clan Level: {e}")
        
        # Run survival
        if guild_cfg.get("survival_enabled"):
            try:
                survival = await fetch_survival_mastery_report(interaction.guild_id, None)
                embeds, files = survival if survival else (None, None)
                if embeds:
                    await channel.send(embeds=embeds, files=files)
                    results.append("✅ Survival")
                else:
                    results.append("❌ Survival: No data")
            except Exception as e:
                results.append(f"❌ Survival: {e}")
        
        # Send results
        result_text = "\n".join(results) or "No reports are enabled for this server (see /reportstatus)."
        await interaction.followup.send(f"**Report Results:**\n{result_text}")
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[runallreports] Error: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error running reports: {e}")


async def askfeedback_impl(interaction, channel, secret_key, BOT_ADMIN_KEY):
    """Implementation of askfeedback command."""
    from modules.config import SUPPORT_FEEDBACK_CHANNEL_ID, SUPPORT_SERVER_ID
    import hmac

    if not BOT_ADMIN_KEY or secret_key is None:
        await interaction.response.send_message("❌ Admin key not configured", ephemeral=True)
        return
    
    if not hmac.compare_digest(secret_key.encode(), BOT_ADMIN_KEY.encode()):
        await interaction.response.send_message("❌ Invalid secret key", ephemeral=True)
        return

    # Defer after key check
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    if not channel:
        # Use support server channel
        target_guild = interaction.client.get_guild(SUPPORT_SERVER_ID)
        if target_guild:
            target_channel = target_guild.get_channel(SUPPORT_FEEDBACK_CHANNEL_ID)
            if target_channel:
                await target_channel.send(
                    "📝 **Feedback & Suggestions**\n\n"
                    "We'd love to hear your feedback on the PUBG Tracker bot! "
                    "Please share any suggestions, bug reports, or feature requests.\n\n"
                    "Thank you for helping us improve!"
                )
                await interaction.followup.send("✅ Feedback prompt posted to support server")
                return

    await interaction.followup.send("❌ Could not find target channel", ephemeral=True)


async def botservers_impl(interaction, bot, ADMIN_USER_IDS):
    """Implementation of botservers command."""
    if interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    # Defer after auth check
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    servers = []
    for guild in bot.guilds:
        servers.append(f"**{guild.name}** (ID: {guild.id}, Members: {guild.member_count})")

    embed = discord.Embed(
        title=f"Bot Servers ({len(bot.guilds)})",
        description="\n".join(servers) or "No servers",
        color=discord.Color.blue(),
    )
    await interaction.followup.send(embed=embed)
