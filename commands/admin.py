"""
Admin command implementations for PUBG Tracker bot.
"""

import logging
import storage
import translations
from pubg_api import PubgApiError
from datetime import datetime, timezone
import discord

logger = logging.getLogger(__name__)


class StatisticalAnomalyReportModal(discord.ui.Modal, title="Report Statistical Anomaly"):
    player_name = discord.ui.TextInput(
        label="Player Name",
        placeholder="Enter the PUBG player name to report",
        required=True,
    )
    
    anomaly_type = discord.ui.TextInput(
        label="Anomaly Type",
        placeholder="e.g., High K/D, Unusual win rate, Suspicious headshot rate",
        required=True,
    )
    
    description = discord.ui.TextInput(
        label="Description",
        style=discord.TextStyle.long,
        placeholder="Describe the statistical anomalies and any context for manual review",
        required=True,
        max_length=1000,
    )
    
    match_id = discord.ui.TextInput(
        label="Match ID (optional)",
        placeholder="Enter match ID if available",
        required=False,
    )
    
    evidence_urls = discord.ui.TextInput(
        label="Evidence URLs (optional)",
        style=discord.TextStyle.long,
        placeholder="Paste URLs to screenshots/video clips (one per line)",
        required=False,
        max_length=1000,
    )
    
    async def on_submit(self, interaction: discord.Interaction, pubg, _detect_statistical_anomalies):
        reporter_name = interaction.user.display_name
        player_name = self.player_name.value
        anomaly_type = self.anomaly_type.value
        description = self.description.value
        match_id = self.match_id.value or None
        evidence_urls = [url.strip() for url in self.evidence_urls.value.split('\n') if url.strip()] if self.evidence_urls.value else None
        
        await interaction.response.defer()
        
        try:
            report_id = await storage.add_cheat_report(
                interaction.guild_id,
                reporter_name,
                player_name,
                anomaly_type,
                description,
                match_id,
                evidence_urls,
            )
            
            # Auto-detect if player has statistical anomalies
            guild_cfg = await storage.get_guild(interaction.guild_id)
            players, _ = await pubg.get_players_and_stats([player_name], game_mode=guild_cfg.get("game_mode", "squad-fpp"))
            if players:
                player = players[0]
                stats = player.get("stats", {})
                flags = _detect_statistical_anomalies(stats)
                if flags:
                    await storage.update_statistical_anomaly(interaction.guild_id, player_name, stats, flags)
            
            embed = discord.Embed(
                title="📊 Statistical Anomaly Report Submitted",
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="Report ID", value=report_id, inline=False)
            embed.add_field(name="Player", value=player_name, inline=True)
            embed.add_field(name="Anomaly Type", value=anomaly_type, inline=True)
            embed.add_field(name="Reporter", value=reporter_name, inline=True)
            embed.add_field(name="Description", value=description[:500] + "..." if len(description) > 500 else description, inline=False)
            if match_id:
                embed.add_field(name="Match ID", value=match_id, inline=False)
            if evidence_urls:
                embed.add_field(name="Evidence", value=f"{len(evidence_urls)} file(s) attached", inline=False)
            
            await interaction.followup.send(embed=embed)
            
            # Notify admin channel if configured
            channel_id = guild_cfg.get("cheat_report_channel_id")
            if channel_id:
                channel = interaction.guild.get_channel(channel_id)
                if channel:
                    await channel.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error submitting report: {str(e)}")


async def reportcheater_impl(interaction, pubg, _detect_statistical_anomalies):
    """Implementation of reportcheater command."""
    modal = StatisticalAnomalyReportModal()
    # Store callbacks in the modal
    modal._pubg = pubg
    modal._detect_statistical_anomalies = _detect_statistical_anomalies
    
    # Override on_submit to pass the callbacks
    original_on_submit = modal.on_submit
    async def on_submit_with_callbacks(interaction):
        await original_on_submit(interaction, pubg, _detect_statistical_anomalies)
    modal.on_submit = on_submit_with_callbacks
    
    await interaction.response.send_modal(modal)


async def askfeedback_impl(interaction, channel, secret_key, BOT_ADMIN_KEY):
    """Implementation of askfeedback command."""
    from modules.config import SUPPORT_FEEDBACK_CHANNEL_ID, SUPPORT_SERVER_ID

    if secret_key != BOT_ADMIN_KEY:
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

    import discord
    embed = discord.Embed(
        title=f"Bot Servers ({len(bot.guilds)})",
        description="\n".join(servers) or "No servers",
        color=discord.Color.blue(),
    )
    await interaction.followup.send(embed=embed)
