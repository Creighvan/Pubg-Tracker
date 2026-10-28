"""
Mastery command implementations for PUBG Tracker bot.
"""

import logging
import random
import string
import storage
import translations
from pubg_api import PubgApiError
from modules.reports import fetch_survival_mastery_report, fetch_mastery_report
import discord

logger = logging.getLogger(__name__)

async def safe_command_wrapper(interaction, func, *args, **kwargs):
    """Universal command wrapper to ensure all commands work perfectly."""
    try:
        await interaction.response.defer()
    except discord.NotFound:
        logger.warning(f"[command_wrapper] Interaction {interaction.id} already expired")
        return

    try:
        await func(interaction, *args, **kwargs)
    except discord.NotFound:
        logger.error(f"[command_wrapper] Interaction {interaction.id} expired before response could be sent")
    except discord.HTTPException as e:
        if "Invalid Webhook Token" in str(e):
            logger.error(f"[command_wrapper] Discord webhook token expired for interaction {interaction.id}")
        else:
            error_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            logger.error(f"[{error_id}] HTTPException in command: {e}", exc_info=e)
            try:
                await interaction.followup.send(f"❌ Something went wrong. Error reference: {error_id}")
            except:
                pass
    except Exception as e:
        error_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        logger.error(f"[{error_id}] Unexpected error in command: {e}", exc_info=e)
        try:
            await interaction.followup.send(f"❌ Something went wrong. Error reference: {error_id}")
        except:
            pass


async def masterystats_impl(interaction, pubg):
    """Implementation of masterystats command."""
    await _masterystats_impl(interaction, pubg)

async def _masterystats_impl(interaction, pubg):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    try:
        result = await fetch_mastery_report(interaction.guild_id, None)
    except PubgApiError as e:
        await interaction.followup.send(f"❌ {translations.get_translation(lang, 'api_error', error=str(e))}")
        return

    if result:
        embed, _ = result
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(translations.get_translation(lang, "no_mastery_data"))


async def survivalstats_impl(interaction, pubg):
    """Implementation of survivalstats command."""
    await _survivalstats_impl(interaction, pubg)

async def _survivalstats_impl(interaction, pubg):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    try:
        result = await fetch_survival_mastery_report(interaction.guild_id, None)
    except PubgApiError as e:
        await interaction.followup.send(f"❌ {translations.get_translation(lang, 'api_error', error=str(e))}")
        return

    if result:
        embeds, files = result
        await interaction.followup.send(embeds=embeds[:10], files=files)
    else:
        await interaction.followup.send(translations.get_translation(lang, "no_survival_data"))
