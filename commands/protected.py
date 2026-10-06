"""
Protected player management command implementations for PUBG Tracker bot.

These are the actual command functions. They are decorated in bot.py.
"""

import logging
import storage
import translations
from storage import DatabaseCorruptionError
from modules.utils import normalize_player_name

logger = logging.getLogger(__name__)


async def addprotected_impl(interaction, name, send_audit_log):
    """Implementation of addprotected command."""
    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        added = await storage.add_protected_player(interaction.guild_id, name)
        if added:
            await interaction.response.send_message(translations.get_translation(lang, "protected_added").format(name=name))
            await send_audit_log(
                interaction.guild_id,
                "Protected Player Added",
                f"Added {name} to protected list",
                user=interaction.user,
                details={"Player": name}
            )
        else:
            await interaction.response.send_message(f"**{name}** is already on the protected list.", ephemeral=True)
    except DatabaseCorruptionError as e:
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in addprotected_impl: {e}", exc_info=True)
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def removeprotected_impl(interaction, name, send_audit_log):
    """Implementation of removeprotected command."""
    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        removed = await storage.remove_protected_player(interaction.guild_id, name)
        if removed:
            await interaction.response.send_message(translations.get_translation(lang, "protected_removed").format(name=name))
            await send_audit_log(
                interaction.guild_id,
                "Protected Player Removed",
                f"Removed {name} from protected list",
                user=interaction.user,
                details={"Player": name}
            )
        else:
            await interaction.response.send_message(translations.get_translation(lang, "protected_not_found").format(name=name), ephemeral=True)
    except Exception as e:
        logger.error(f"Error in removeprotected_impl: {e}", exc_info=True)
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def listprotected_impl(interaction):
    """Implementation of listprotected command."""
    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        protected = await storage.get_protected_players(interaction.guild_id)

        if not protected:
            await interaction.response.send_message(translations.get_translation(lang, "protected_empty"))
            return

        message = translations.get_translation(lang, "protected_list").format(count=len(protected)) + "\n" + ", ".join(protected)
        message += "\n\n🛡️ These players won't be flagged for removal due to inactivity."
        await interaction.response.send_message(message)
    except Exception as e:
        logger.error(f"Error in listprotected_impl: {e}", exc_info=True)
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def cleanprotected_impl(interaction):
    """Implementation of cleanprotected command."""
    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        removed = await storage.clean_protected_players(interaction.guild_id)
        protected = await storage.get_protected_players(interaction.guild_id)
        await interaction.response.send_message(translations.get_translation(lang, "protected_cleaned").format(count=removed))
    except Exception as e:
        logger.error(f"Error in cleanprotected_impl: {e}", exc_info=True)
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def resetprotected_impl(interaction):
    """Implementation of resetprotected command."""
    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        def modifier(guild_cfg):
            guild_cfg["protected_players"] = []
        await storage.modify_guild(interaction.guild_id, modifier)
        await interaction.response.send_message(translations.get_translation(lang, "protected_cleared"))
    except Exception as e:
        logger.error(f"Error in resetprotected_impl: {e}", exc_info=True)
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def addprotectedbulk_impl(interaction, players):
    """Implementation of addprotectedbulk command."""
    try:
        await interaction.response.defer()
        # Parse the input - handle both comma and newline separators
        player_list = [p.strip() for p in players.replace(',', '\n').split('\n')]
        player_list = [p for p in player_list if p]  # Remove empty entries

        def modifier(guild_cfg):
            current_protected = set(normalize_player_name(p) for p in guild_cfg["protected_players"])
            added = []
            duplicates = []

            for player in player_list:
                if normalize_player_name(player) in current_protected:
                    duplicates.append(player)
                else:
                    guild_cfg["protected_players"].append(player)
                    current_protected.add(normalize_player_name(player))
                    added.append(player)

            return {"added": added, "duplicates": duplicates}

        result = await storage.modify_guild(interaction.guild_id, modifier)
        added = result["added"]
        duplicates = result["duplicates"]

        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        count = len(added)
        unit_key = "player" if count == 1 else "players"
        unit = translations.get_translation(lang, unit_key)

        message = translations.get_translation(lang, "protected_bulk_added").format(count=count) + ":\n" + ", ".join(added)
        if duplicates:
            message += f"\n⚠️ Skipped {len(duplicates)} already protected: " + ", ".join(duplicates)
        await interaction.followup.send(message)
    except Exception as e:
        logger.error(f"Error in addprotectedbulk_impl: {e}", exc_info=True)
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)
