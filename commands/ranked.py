"""
Ranked stats command implementations for PUBG Tracker bot.
"""

import logging
import storage
import translations
from pubg_api import PubgApiError
from modules.reports import fetch_ranked_report
import discord

logger = logging.getLogger(__name__)


# The six queues, in the order Discord shows them. The keys are what the PUBG report code understands.
RANKED_QUEUES = {
    "squad": "Squad TPP",
    "duo": "Duo TPP",
    "solo": "Solo TPP",
    "squad-fpp": "Squad FPP",
    "duo-fpp": "Duo FPP",
    "solo-fpp": "Solo FPP",
}


async def ranked_impl(interaction, pubg, queue=None):
    """Implementation of /ranked: current-season standings for any of the six queues.

    With no queue given it uses the queue this server's daily ranked report tracks
    (/setrankedqueue), which is Squad TPP unless changed.
    """
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    mode = queue if queue in RANKED_QUEUES else guild_cfg.get("ranked_queue", "squad")
    if mode not in RANKED_QUEUES:
        mode = "squad"

    try:
        result = await fetch_ranked_report(interaction.guild_id, interaction.guild.name, mode)
    except PubgApiError as e:
        await interaction.followup.send(f"❌ {translations.get_translation(lang, 'api_error', error=str(e))}")
        return

    if result:
        embed, _ = result
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(translations.get_translation(lang, "no_ranked_data"))
