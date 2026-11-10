"""
Protected player management command implementations for PUBG Tracker bot.

These are the actual command functions. They are decorated in bot.py.
"""

import logging
import storage
import translations
from storage import DatabaseCorruptionError
from modules.utils import normalize_player_name, discord_time
from modules.protection import _parse as _parse_iso
import discord

logger = logging.getLogger(__name__)


async def addprotected_impl(interaction, name, send_audit_log):
    """Implementation of addprotected command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        logger.warning("addprotected_impl: Interaction expired before defer")
        return

    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        added = await storage.add_protected_player(interaction.guild_id, name)
        if added:
            await interaction.followup.send(translations.get_translation(lang, "protected_added").format(name=name))
            await send_audit_log(
                interaction.guild_id,
                "Protected Player Added",
                f"Added {name} to protected list",
                user=interaction.user,
                details={"Player": name}
            )
        else:
            await interaction.followup.send(f"**{name}** is already on the protected list.", ephemeral=True)
    except DatabaseCorruptionError as e:
        await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in addprotected_impl: {e}", exc_info=True)
        await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def removeprotected_impl(interaction, name, send_audit_log):
    """Implementation of removeprotected command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        logger.warning("removeprotected_impl: Interaction expired before defer")
        return

    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        removed = await storage.remove_protected_player(interaction.guild_id, name)
        if removed:
            await interaction.followup.send(translations.get_translation(lang, "protected_removed").format(name=name))
            await send_audit_log(
                interaction.guild_id,
                "Protected Player Removed",
                f"Removed {name} from protected list",
                user=interaction.user,
                details={"Player": name}
            )
        else:
            await interaction.followup.send(translations.get_translation(lang, "protected_not_found").format(name=name), ephemeral=True)
    except Exception as e:
        logger.error(f"Error in removeprotected_impl: {e}", exc_info=True)
        await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def listprotected_impl(interaction):
    """Implementation of listprotected command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        logger.warning("listprotected_impl: Interaction expired before defer")
        return

    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        protected = await storage.get_protected_players(interaction.guild_id)
        temporary = await storage.get_temporary_protected(interaction.guild_id)

        if not protected and not temporary:
            await interaction.followup.send(translations.get_translation(lang, "protected_empty"))
            return

        sections = []
        if protected:
            sections.append(f"🛡️ **Permanently protected ({len(protected)})**\n" + ", ".join(protected))
        if temporary:
            lines = []
            for entry in sorted(temporary.values(), key=lambda e: e.get("name", "").lower()):
                until = _parse_iso(entry.get("until"))
                when = f"until {discord_time(until, 'F')} ({discord_time(until, 'R')})" if until else "until removed"
                reason = f" · {entry['reason']}" if entry.get("reason") else ""
                lines.append(f"• {entry.get('name', '?')} — {when}{reason}")
            sections.append(f"⏳ **Temporarily protected ({len(temporary)})**\n" + "\n".join(lines))
        message = "\n\n".join(sections)
        message += ("\n\n🛡️ Permanent: never flagged for inactivity.  ⏳ Temporary: for members who reached out; "
                    "it ends on its date, or when you use /removetempprotected.")
        await interaction.followup.send(message)
    except Exception as e:
        logger.error(f"Error in listprotected_impl: {e}", exc_info=True)
        await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def cleanprotected_impl(interaction):
    """Implementation of cleanprotected command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        logger.warning("cleanprotected_impl: Interaction expired before defer")
        return

    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        removed = await storage.clean_protected_players(interaction.guild_id)
        protected = await storage.get_protected_players(interaction.guild_id)
        await interaction.followup.send(translations.get_translation(lang, "protected_cleaned").format(count=removed))
    except Exception as e:
        logger.error(f"Error in cleanprotected_impl: {e}", exc_info=True)
        await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def resetprotected_impl(interaction):
    """Implementation of resetprotected command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        logger.warning("resetprotected_impl: Interaction expired before defer")
        return

    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        def modifier(guild_cfg):
            guild_cfg["protected_players"] = []
        await storage.modify_guild(interaction.guild_id, modifier)
        await interaction.followup.send(translations.get_translation(lang, "protected_cleared"))
    except Exception as e:
        logger.error(f"Error in resetprotected_impl: {e}", exc_info=True)
        await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def addprotectedbulk_impl(interaction, players):
    """Implementation of addprotectedbulk command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        logger.warning("addprotectedbulk_impl: Interaction expired before defer")
        return

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

    try:
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
        await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def addtempprotected_impl(interaction, name, days, reason, send_audit_log):
    """Implementation of addtempprotected: temporary protection for a member who reached out."""
    try:
        await interaction.response.defer()
    except discord.NotFound:
        logger.warning("addtempprotected_impl: Interaction expired before defer")
        return

    try:
        result = await storage.add_temporary_protected(interaction.guild_id, name, days, reason or "")
        status = result["status"]
        if status == "not_tracked":
            await interaction.followup.send(
                f"❌ **{name}** is not on the tracked player list. Add them first, then mark them temporarily protected.",
                ephemeral=True)
            return
        if status == "permanent":
            await interaction.followup.send(
                f"🛡️ **{name}** is already permanently protected, so no temporary protection is needed.",
                ephemeral=True)
            return

        entry = result["entry"]
        until = _parse_iso(entry.get("until"))
        ends = (f"until {discord_time(until, 'F')} ({discord_time(until, 'R')})" if until
                else "until you remove it with `/removetempprotected`")
        verb = "now" if status == "added" else "still"
        message = f"⏳ **{entry['name']}** is {verb} temporarily protected {ends}."
        if entry.get("reason"):
            message += f"\nReason: {entry['reason']}"
        await interaction.followup.send(message)
        await send_audit_log(
            interaction.guild_id,
            "Temporary Protection Added" if status == "added" else "Temporary Protection Updated",
            f"Temporarily protected {entry['name']}",
            user=interaction.user,
            details={"Player": entry["name"], "Until": entry["until"] or "until removed", "Reason": entry.get("reason") or "-"},
        )
    except DatabaseCorruptionError:
        await interaction.followup.send("❌ Database error. Please try again later.", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in addtempprotected_impl: {e}", exc_info=True)
        await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def removetempprotected_impl(interaction, name, send_audit_log):
    """Implementation of removetempprotected."""
    try:
        await interaction.response.defer()
    except discord.NotFound:
        logger.warning("removetempprotected_impl: Interaction expired before defer")
        return

    try:
        removed = await storage.remove_temporary_protected(interaction.guild_id, name)
        if not removed:
            await interaction.followup.send(f"❌ **{name}** is not temporarily protected.", ephemeral=True)
            return
        await interaction.followup.send(f"✅ Removed **{name}** from the temporary protection list.")
        await send_audit_log(
            interaction.guild_id,
            "Temporary Protection Removed",
            f"Removed {name} from temporary protection",
            user=interaction.user,
            details={"Player": name},
        )
    except Exception as e:
        logger.error(f"Error in removetempprotected_impl: {e}", exc_info=True)
        await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)
