"""
Player profile command - flagship command showing comprehensive player info.
"""

import discord
from discord import app_commands
from discord.ui import Button, View

import storage
import history
import translations
from modules.utils import normalize_player_name


class ProfileView(View):
    """Button view for profile navigation."""

    def __init__(self, player_name: str, guild_id: int):
        super().__init__(timeout=None)
        self.player_name = player_name
        self.guild_id = guild_id


async def profile_impl(interaction: discord.Interaction, player_name: str):
    """Show comprehensive player profile."""
    await interaction.response.defer()

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    normalized_name = normalize_player_name(player_name)

    # Check if player is tracked
    tracked_players = [normalize_player_name(p) for p in guild_cfg.get("players", [])]
    if normalized_name not in tracked_players:
        await interaction.followup.send(
            translations.get_translation(lang, "player_not_tracked").format(name=player_name),
            ephemeral=True
        )
        return

    # Get latest snapshot for stats
    snapshots = await history.get_player_snapshots(interaction.guild_id, player_name, days=7)
    if not snapshots:
        await interaction.followup.send(
            translations.get_translation(lang, "insufficient_history").format(days=7),
            ephemeral=True
        )
        return

    stats = snapshots[-1]["stats"]

    # Get trend
    trend = await history.calculate_trend(interaction.guild_id, player_name, days=7)

    # Build profile embed
    embed = discord.Embed(
        title=f"👤 {player_name}",
        color=discord.Color.purple()
    )

    # Current stats
    embed.add_field(
        name="📊 Stats",
        value=f"**Matches:** {stats.get('matches', 0):,}\n"
              f"**Wins:** {stats.get('wins', 0):,}\n"
              f"**Kills:** {stats.get('kills', 0):,}\n"
              f"**K/D:** {stats.get('kd', 0):.2f}\n"
              f"**Win Rate:** {stats.get('win_rate', 0):.1f}%\n"
              f"**Avg Placement:** {stats.get('avg_placement', 0):.1f}",
        inline=True
    )

    # Trend indicator
    kd_change = trend.get("percent_change", {}).get("kd", 0)
    if kd_change is not None:
        if kd_change > 0:
            trend_emoji = "📈"
            trend_text = f"+{kd_change:.1f}%"
        elif kd_change < 0:
            trend_emoji = "📉"
            trend_text = f"{kd_change:.1f}%"
        else:
            trend_emoji = "➡️"
            trend_text = "0%"
    else:
        trend_emoji = "❓"
        trend_text = "N/A"

    embed.add_field(
        name="📈 7-Day Trend",
        value=f"{trend_emoji} K/D: {trend_text}\n"
              f"Snapshots: {trend.get('snapshots_count', 0)}",
        inline=True
    )

    # Activity
    this_week_delta = trend.get("delta", {})
    embed.add_field(
        name="🕐 This Week",
        value=f"**Matches:** {this_week_delta.get('matches', 0):+d}\n"
              f"**Kills:** {this_week_delta.get('kills', 0):+d}\n"
              f"**Wins:** {this_week_delta.get('wins', 0):+d}",
        inline=True
    )

    # Mastery info (if available in stats)
    if stats.get('survival_level'):
        embed.add_field(
            name="🛡️ Survival",
            value=f"**Level:** {stats.get('survival_level', 0)}\n"
                  f"**Tier:** {stats.get('survival_tier', 'N/A')}",
            inline=True
        )

    if stats.get('top_weapon'):
        embed.add_field(
            name="🔫 Top Weapon",
            value=stats.get('top_weapon', 'N/A'),
            inline=True
        )

    # Add navigation buttons
    view = ProfileView(player_name, interaction.guild_id)

    await interaction.followup.send(embed=embed, view=view)
