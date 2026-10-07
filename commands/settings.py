"""
Settings command implementations for PUBG Tracker bot.
"""

import logging
import storage
import translations
from storage import DatabaseCorruptionError
from discord import app_commands
from modules.config import bot

logger = logging.getLogger(__name__)


async def setgamemode_impl(interaction, mode):
    """Implementation of setgamemode command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["game_mode"] = mode.value
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(translations.get_translation(lang, "mode_set").format(mode=mode.value))


async def setchannel_impl(interaction):
    """Implementation of setchannel command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["post_channel_id"] = interaction.channel_id
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(translations.get_translation(lang, "channel_set"))


async def setinterval_impl(interaction, hours):
    """Implementation of setinterval command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["post_interval_hours"] = hours
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(translations.get_translation(lang, "interval_set").format(hours=hours))


async def setdigesttime_impl(interaction, hour, minute):
    """Implementation of setdigesttime command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["digest_hour_utc"] = hour
        guild_cfg["digest_minute_utc"] = minute
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(translations.get_translation(lang, "digest_time_set").format(hour=hour, minute=minute))


async def setactivitychannel_impl(interaction):
    """Implementation of setactivitychannel command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["last_activity_channel_id"] = interaction.channel_id
        guild_cfg["activity_enabled"] = True
        guild_cfg["last_activity_message_id"] = None
    await storage.modify_guild(interaction.guild_id, modifier)
    
    await interaction.response.defer()
    await interaction.followup.send(translations.get_translation(lang, "activity_channel_set"))


async def setrankedchannel_impl(interaction):
    """Implementation of setrankedchannel command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["ranked_channel_id"] = interaction.channel_id
        guild_cfg["ranked_enabled"] = True
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(translations.get_translation(lang, "ranked_channel_set"))


async def setrankedqueue_impl(interaction, queue):
    """Implementation of setrankedqueue command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["ranked_queue"] = queue.value
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(translations.get_translation(lang, "ranked_queue_set").format(queue=queue.value))


async def sethighlightschannel_impl(interaction):
    """Implementation of sethighlightschannel command."""
    await interaction.response.defer()
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["highlights_channel_id"] = interaction.channel_id
        guild_cfg["highlights_enabled"] = True
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.followup.send(translations.get_translation(lang, "highlights_channel_set"))


async def sethighlightstime_impl(interaction, hour):
    """Implementation of sethighlightstime command."""
    await interaction.response.defer()
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["highlights_hour_utc"] = hour
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.followup.send(translations.get_translation(lang, "highlights_time_set").format(hour=hour))


async def setsurvivalchannel_impl(interaction):
    """Implementation of setsurvivalchannel command."""
    await interaction.response.defer()
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["survival_channel_id"] = interaction.channel_id
        guild_cfg["survival_enabled"] = True
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.followup.send(translations.get_translation(lang, "survival_channel_set"))


async def setsurvivaltime_impl(interaction, day, hour, minute):
    """Implementation of setsurvivaltime command."""
    await interaction.response.defer()
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["survival_day_utc"] = day
        guild_cfg["survival_hour_utc"] = hour
        guild_cfg["survival_minute_utc"] = minute
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.followup.send(translations.get_translation(lang, "survival_time_set").format(day=day, hour=hour, minute=minute))


async def setstatuschannel_impl(interaction):
    """Implementation of setstatuschannel command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["status_channel_id"] = interaction.channel_id
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(translations.get_translation(lang, "status_channel_set"))


async def setauditchannel_impl(interaction, admin_ids):
    """Implementation of setauditchannel command."""
    # User is already authorized by the decorator check
    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        def modifier(guild_cfg):
            guild_cfg["audit_channel_id"] = interaction.channel_id
        await storage.modify_guild(interaction.guild_id, modifier)
        await interaction.followup.send(translations.get_translation(lang, "audit_channel_set"))
    except Exception as e:
        logger.error(f"Error in setauditchannel_impl: {e}", exc_info=True)
        await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def clearauditchannel_impl(interaction, admin_ids):
    """Implementation of clearauditchannel command."""
    # User is already authorized by the decorator check
    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        def modifier(guild_cfg):
            guild_cfg["audit_channel_id"] = None
        await storage.modify_guild(interaction.guild_id, modifier)
        await interaction.followup.send(translations.get_translation(lang, "audit_channel_cleared"))
    except Exception as e:
        logger.error(f"Error in clearauditchannel_impl: {e}", exc_info=True)
        await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def showauditconfig_impl(interaction, admin_ids):
    """Implementation of showauditconfig command."""
    # User is already authorized by the decorator check
    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        audit_channel_id = guild_cfg.get("audit_channel_id")
        if audit_channel_id:
            channel = interaction.guild.get_channel(audit_channel_id)
            channel_name = channel.mention if channel else translations.get_translation(lang, "unknown_deleted")
            await interaction.followup.send(
                f"{translations.get_translation(lang, 'custom_audit_channel')} {channel_name} (ID: {audit_channel_id})"
            )
        else:
            await interaction.followup.send(translations.get_translation(lang, "using_central_audit"))
    except Exception as e:
        logger.error(f"Error in showauditconfig_impl: {e}", exc_info=True)
        await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def setlanguage_impl(interaction, language):
    """Implementation of setlanguage command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    current_lang = guild_cfg.get("language", "en")
    
    VALID_LANGUAGES = {"en", "zh", "hi", "es", "ar", "fr", "bn", "pt", "id", "ur"}
    LANGUAGE_NAMES = {
        "en": "English",
        "zh": "Mandarin Chinese",
        "hi": "Hindi",
        "es": "Spanish",
        "ar": "Arabic",
        "fr": "French",
        "bn": "Bengali",
        "pt": "Portuguese",
        "id": "Indonesian",
        "ur": "Urdu"
    }
    
    language = language.lower()
    if language not in VALID_LANGUAGES:
        await interaction.response.send_message(
            f"❌ {translations.get_translation(current_lang, 'invalid_language').format(languages=', '.join(VALID_LANGUAGES))}\n"
            f"Example: English (en), Spanish (es), Chinese (zh)"
        )
        return
    
    success = await storage.set_language(interaction.guild_id, language)
    if success:
        language_name = LANGUAGE_NAMES[language]
        await interaction.response.send_message(
            translations.get_translation(language, "language_set").format(language=language_name)
        )
    else:
        await interaction.response.send_message(f"❌ {translations.get_translation(current_lang, 'language_set_failed')}")


async def language_impl(interaction):
    """Implementation of language command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    VALID_LANGUAGES = {"en", "zh", "hi", "es", "ar", "fr", "bn", "pt", "id", "ur"}
    LANGUAGE_NAMES = {
        "en": "English",
        "zh": "Mandarin Chinese",
        "hi": "Hindi",
        "es": "Spanish",
        "ar": "Arabic",
        "fr": "French",
        "bn": "Bengali",
        "pt": "Portuguese",
        "id": "Indonesian",
        "ur": "Urdu"
    }
    
    language_name = LANGUAGE_NAMES.get(lang, lang)
    await interaction.response.send_message(translations.get_translation(lang, "language_current").format(language=language_name))


async def reportstatus_impl(interaction):
    """Implementation of reportstatus command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    # Build status embed
    import discord
    from modules.utils import _next_daily_report, _next_interval_report, _next_weekly_report
    
    embed = discord.Embed(
        title=translations.get_translation(lang, "report_status_title"),
        color=discord.Color.blue(),
    )
    
    # Digest status
    if guild_cfg.get("digest_enabled"):
        if guild_cfg.get("digest_hour_utc") is not None:
            next_run = _next_daily_report(guild_cfg.get("digest_hour_utc"), guild_cfg.get("digest_minute_utc", 0))
            embed.add_field(name=translations.get_translation(lang, "clan_digest"), value=f"{translations.get_translation(lang, 'enabled')}\n{translations.get_translation(lang, 'next')}: {next_run}", inline=False)
        else:
            next_run = _next_interval_report(guild_cfg.get("post_interval_hours", 6))
            embed.add_field(name=translations.get_translation(lang, "clan_digest"), value=f"{translations.get_translation(lang, 'enabled')}\n{translations.get_translation(lang, 'next')}: {next_run}", inline=False)
    else:
        embed.add_field(name=translations.get_translation(lang, "clan_digest"), value=translations.get_translation(lang, "disabled"), inline=False)
    
    # Other reports...
    await interaction.response.send_message(embed=embed)


async def reporttoggle_impl(interaction, report):
    """Implementation of reporttoggle command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    report_key = f"{report.value}_enabled"
    current = guild_cfg.get(report_key, True)
    
    def modifier(guild_cfg):
        guild_cfg[report_key] = not current
        return not current
    
    new_state = await storage.modify_guild(interaction.guild_id, modifier)
    status = translations.get_translation(lang, "enabled") if new_state else translations.get_translation(lang, "disabled")
    await interaction.response.send_message(f"{report.value} {status}")


async def donate_impl(interaction):
    """Implementation of donate command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    from modules.config import DONATION_URL, BUY_ME_A_COFFEE_URL
    message = translations.get_translation(lang, "donate_message").format(
        donation_url=DONATION_URL,
        coffee_url=BUY_ME_A_COFFEE_URL
    )
    await interaction.response.send_message(message)
