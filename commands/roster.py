"""
Roster management command implementations for PUBG Tracker bot.

These are the actual command functions. They are decorated in bot.py.
"""

import storage
import translations
from storage import DatabaseCorruptionError


async def addplayer_impl(interaction, name, send_audit_log, _refresh_last_active_report):
    """Implementation of addplayer command."""
    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")
        
        added = await storage.add_player(interaction.guild_id, name)
        if added:
            await interaction.response.send_message(translations.get_translation(lang, "player_added_success").format(name=name))
            await send_audit_log(
                interaction.guild_id,
                "Player Added",
                f"Added {name} to roster",
                user=interaction.user,
                details={"Player": name}
            )
            # Refresh last active report if configured
            await _refresh_last_active_report(interaction.guild_id, interaction.guild.name)
        else:
            await interaction.response.send_message(translations.get_translation(lang, "player_already_on_roster").format(name=name), ephemeral=True)
    except DatabaseCorruptionError as e:
        await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)


async def addplayers_impl(interaction, names, send_audit_log, _refresh_last_active_report):
    """Implementation of addplayers command."""
    raw = names.replace("\n", ",").split(",")
    candidates = [n.strip() for n in raw if n.strip()]
    if not candidates:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")
        await interaction.response.send_message(translations.get_translation(lang, "no_names_found"), ephemeral=True)
        return

    try:
        added, duplicates = await storage.add_players(interaction.guild_id, candidates)
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")
        
        count = len(added)
        unit_key = "player" if count == 1 else "players"
        unit = translations.get_translation(lang, unit_key)
        
        lines = [translations.get_translation(lang, "added_players_count").format(count=count)]
        if added:
            lines.append(", ".join(added))
        if duplicates:
            lines.append(translations.get_translation(lang, "skipped_duplicates").format(count=len(duplicates)) + ", ".join(duplicates))
        await interaction.response.send_message("\n".join(lines))
        
        # Refresh last active report if configured
        if added:
            await _refresh_last_active_report(interaction.guild_id, interaction.guild.name)
    except DatabaseCorruptionError as e:
        await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)


async def removeplayer_impl(interaction, name, send_audit_log, _refresh_last_active_report):
    """Implementation of removeplayer command."""
    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")
        
        removed = await storage.remove_player(interaction.guild_id, name)
        if removed:
            await interaction.response.send_message(translations.get_translation(lang, "player_removed_success").format(name=name))
            await send_audit_log(
                interaction.guild_id,
                "Player Removed",
                f"Removed {name} from roster",
                user=interaction.user,
                details={"Player": name}
            )
            # Refresh last active report if configured
            await _refresh_last_active_report(interaction.guild_id, interaction.guild.name)
        else:
            await interaction.response.send_message(translations.get_translation(lang, "player_not_on_roster").format(name=name), ephemeral=True)
    except DatabaseCorruptionError as e:
        await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)


async def roster_impl(interaction):
    """Implementation of roster command."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    players = guild_cfg["players"]
    if not players:
        await interaction.response.send_message(translations.get_translation(lang, "no_players_tracked"))
        return
    await interaction.response.send_message(
        translations.get_translation(lang, "tracked_roster").format(count=len(players)) + "\n" + ", ".join(players)
    )
