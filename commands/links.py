"""
Discord-to-PUBG linking command implementations for PUBG Tracker bot.
"""

import logging
import storage
import translations
import discord

logger = logging.getLogger(__name__)


async def linkme_impl(interaction, pubg_name):
    """Implementation of linkme command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["player_links"] = guild_cfg.get("player_links", {})
        guild_cfg["player_links"][pubg_name] = interaction.user.id
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.followup.send(translations.get_translation(lang, "link_success").format(pubg_name=pubg_name))


async def linkplayer_impl(interaction, member, pubg_name):
    """Implementation of linkplayer command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["player_links"] = guild_cfg.get("player_links", {})
        guild_cfg["player_links"][pubg_name] = member.id
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.followup.send(translations.get_translation(lang, "link_player_success").format(member=member.mention, pubg_name=pubg_name))


async def unlinkme_impl(interaction, pubg_name):
    """Implementation of unlinkme command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    def modifier(guild_cfg):
        guild_cfg["player_links"] = guild_cfg.get("player_links", {})
        if pubg_name in guild_cfg["player_links"]:
            del guild_cfg["player_links"][pubg_name]
            return True
        return False
    
    removed = await storage.modify_guild(interaction.guild_id, modifier)
    if removed:
        await interaction.followup.send(translations.get_translation(lang, "unlink_success").format(pubg_name=pubg_name))
    else:
        await interaction.followup.send(translations.get_translation(lang, "unlink_not_found").format(pubg_name=pubg_name), ephemeral=True)


async def links_impl(interaction):
    """Implementation of links command."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    links = guild_cfg.get("player_links", {})
    if not links:
        await interaction.followup.send(translations.get_translation(lang, "no_links"))
        return
    
    lines = [f"**{pubg_name}** → <@{user_id}>" for pubg_name, user_id in links.items()]
    await interaction.followup.send(translations.get_translation(lang, "links_list").format(count=len(links)) + "\n" + "\n".join(lines))
