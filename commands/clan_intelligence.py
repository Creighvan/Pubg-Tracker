"""
Clan intelligence commands - clan-wide analytics and team synergy.
"""

import logging
import discord
from discord import app_commands

import storage
import history
import translations
from modules.utils import normalize_player_name

logger = logging.getLogger(__name__)


async def clantrend_impl(interaction: discord.Interaction, days: int = 7):
    """Show clan-wide trend analysis over the last N days."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    players = guild_cfg.get("players", [])

    if not players:
        await interaction.followup.send(
            translations.get_translation(lang, "no_players_tracked"),
            ephemeral=True
        )
        return

    # Calculate trends for all players
    all_trends = []
    for player in players:
        trend = await history.calculate_trend(interaction.guild_id, player, days)
        if "error" not in trend:
            all_trends.append({
                "name": player,
                "trend": trend
            })

    if not all_trends:
        await interaction.followup.send(
            translations.get_translation(lang, "insufficient_history").format(days=days),
            ephemeral=True
        )
        return

    # Sort by K/D improvement
    all_trends.sort(
        key=lambda x: x["trend"].get("percent_change", {}).get("kd", 0),
        reverse=True
    )

    # Build embed
    embed = discord.Embed(
        title=f"📈 Clan {days}-Day Trend",
        color=discord.Color.blue()
    )

    # Top 5 most improved
    most_improved = all_trends[:5]
    improved_text = ""
    for i, item in enumerate(most_improved, 1):
        name = item["name"]
        kd_change = item["trend"].get("percent_change", {}).get("kd", 0)
        win_rate_change = item["trend"].get("percent_change", {}).get("win_rate", 0)

        if kd_change is not None:
            kd_arrow = "📈" if kd_change > 0 else "📉" if kd_change < 0 else "➡️"
            kd_text = f"{kd_arrow} {kd_change:+.1f}%"
        else:
            kd_text = "N/A"

        if win_rate_change is not None:
            wr_arrow = "📈" if win_rate_change > 0 else "📉" if win_rate_change < 0 else "➡️"
            wr_text = f"{wr_arrow} {win_rate_change:+.1f}%"
        else:
            wr_text = "N/A"

        improved_text += f"**{i}. {name}**\nK/D: {kd_text} | Win Rate: {wr_text}\n"

    embed.add_field(
        name="🔥 Most Improved",
        value=improved_text or "No data",
        inline=False
    )

    # Bottom 5 (declining)
    least_improved = all_trends[-5:][::-1]  # Reverse to show worst first
    declining_text = ""
    for i, item in enumerate(least_improved, 1):
        name = item["name"]
        kd_change = item["trend"].get("percent_change", {}).get("kd", 0)
        win_rate_change = item["trend"].get("percent_change", {}).get("win_rate", 0)

        if kd_change is not None:
            kd_arrow = "📈" if kd_change > 0 else "📉" if kd_change < 0 else "➡️"
            kd_text = f"{kd_arrow} {kd_change:+.1f}%"
        else:
            kd_text = "N/A"

        declining_text += f"**{i}. {name}**\nK/D: {kd_text}\n"

    embed.add_field(
        name="📉 Declining",
        value=declining_text or "No data",
        inline=False
    )

    # Clan aggregate stats
    total_kd_change = sum(
        t.get("percent_change", {}).get("kd", 0) or 0
        for t in [item["trend"] for item in all_trends]
    )
    avg_kd_change = total_kd_change / len(all_trends) if all_trends else 0

    total_wr_change = sum(
        t.get("percent_change", {}).get("win_rate", 0) or 0
        for t in [item["trend"] for item in all_trends]
    )
    avg_wr_change = total_wr_change / len(all_trends) if all_trends else 0

    embed.add_field(
        name="📊 Clan Average Change",
        value=f"**K/D:** {avg_kd_change:+.1f}%\n"
              f"**Win Rate:** {avg_wr_change:+.1f}%\n"
              f"**Players Analyzed:** {len(all_trends)}",
        inline=True
    )

    embed.set_footer(text=f"Based on {days} days of historical data")

    await interaction.followup.send(embed=embed)


async def rosterhealth_impl(interaction: discord.Interaction):
    """Show clan health dashboard with activity and inactivity status."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    players = guild_cfg.get("players", [])
    protected_players = [normalize_player_name(p) for p in guild_cfg.get("protected_players", [])]
    manual_inactive = guild_cfg.get("manual_inactive_dates", {})
    inactive_since = guild_cfg.get("inactive_since_dates", {})

    if not players:
        await interaction.followup.send(
            translations.get_translation(lang, "no_players_tracked"),
            ephemeral=True
        )
        return

    # Get latest snapshots to determine activity
    from datetime import datetime, timezone, timedelta
    from pubg_api import PubgClient
    from modules.config import pubg

    # Categorize players by activity
    active = []
    declining = []
    inactive = []
    protected_count = 0

    for player in players:
        normalized = normalize_player_name(player)

        if normalized in protected_players:
            protected_count += 1
            continue

        # Check manual inactive date
        if normalized in manual_inactive:
            inactive.append(player)
            continue

        # Check if tracked in snapshots (indicates recent activity)
        snapshots = await history.get_player_snapshots(interaction.guild_id, player, days=7)
        if snapshots:
            # Check if they have recent snapshots
            last_snapshot = snapshots[-1]["date"]
            days_since_snapshot = (datetime.now(timezone.utc) - datetime.strptime(last_snapshot, "%Y-%m-%d")).days

            if days_since_snapshot <= 7:
                active.append(player)
            elif days_since_snapshot <= 14:
                declining.append(player)
            else:
                inactive.append(player)
        else:
            # No snapshots - check inactive_since
            if normalized in inactive_since:
                inactive.append(player)
            else:
                declining.append(player)

    # Build embed
    total = len(players)
    active_count = len(active)
    declining_count = len(declining)
    inactive_count = len(inactive)

    # Calculate health percentage
    health_percentage = (active_count / total) * 100 if total > 0 else 0

    # Determine health color
    if health_percentage >= 70:
        color = discord.Color.green()
        health_emoji = "🟢"
    elif health_percentage >= 50:
        color = discord.Color.yellow()
        health_emoji = "🟡"
    else:
        color = discord.Color.red()
        health_emoji = "🔴"

    embed = discord.Embed(
        title=f"{health_emoji} Clan Health Dashboard",
        color=color
    )

    embed.add_field(
        name="📊 Overview",
        value=f"**Total Tracked:** {total}\n"
              f"**🟢 Active:** {active_count}\n"
              f"**🟡 Declining (7-14 days):** {declining_count}\n"
              f"**🔴 Inactive (14+ days):** {inactive_count}\n"
              f"**🛡️ Protected:** {protected_count}",
        inline=True
    )

    embed.add_field(
        name="📈 Health",
        value=f"**Active Rate:** {health_percentage:.1f}%\n"
              f"**Declining Rate:** {(declining_count / total) * 100:.1f}%\n"
              f"**Inactive Rate:** {(inactive_count / total) * 100:.1f}%",
        inline=True
    )

    # Show inactive players
    if inactive:
        inactive_list = "\n".join(f"• {p}" for p in inactive[:10])
        if len(inactive) > 10:
            inactive_list += f"\n... and {len(inactive) - 10} more"
        embed.add_field(
            name="⚠️ Inactive Players",
            value=inactive_list,
            inline=False
        )

    # Show declining players
    if declining:
        declining_list = "\n".join(f"• {p}" for p in declining[:10])
        if len(declining) > 10:
            declining_list += f"\n... and {len(declining) - 10} more"
        embed.add_field(
            name="⚡ Declining Players",
            value=declining_list,
            inline=False
        )

    embed.set_footer(text="Use /addplayer to add new members, /removeplayer to remove inactive ones")

    await interaction.followup.send(embed=embed)
