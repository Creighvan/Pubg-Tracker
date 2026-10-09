"""
Analytics commands for trend tracking and player comparison.
"""

import logging
import discord
from discord import app_commands
from discord.ext import commands

import storage
import history
import translations
from modules.utils import normalize_player_name

logger = logging.getLogger(__name__)


async def playertrend_impl(interaction: discord.Interaction, player_name: str, days: int = 7):
    """Show 7-day trend for a player."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    try:
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

        # Calculate trend
        trend = await history.calculate_trend(interaction.guild_id, player_name, days)

        if "error" in trend:
            await interaction.followup.send(
                translations.get_translation(lang, "insufficient_history").format(days=days),
                ephemeral=True
            )
            return

        # Build embed
        stats_start = trend["stats_start"]
        stats_end = trend["stats_end"]
        delta = trend["delta"]
        percent_change = trend["percent_change"]

        # Format trend arrows
        def format_change(value, is_good_higher=True, is_percentage_points=False):
            if value is None:
                return "N/A"
            if value > 0:
                arrow = "▲" if is_good_higher else "▼"
                if is_percentage_points:
                    return f"{arrow} {abs(value):.1f}pp"  # percentage points
                return f"{arrow} {abs(value):.1f}%"
            elif value < 0:
                arrow = "▼" if is_good_higher else "▲"
                if is_percentage_points:
                    return f"{arrow} {abs(value):.1f}pp"  # percentage points
                return f"{arrow} {abs(value):.1f}%"
            else:
                return "–"

        embed = discord.Embed(
            title=f"📈 {player_name} — {days}-Day Trend",
            color=discord.Color.blue()
        )

        # Key metrics with trend
        kd_change = format_change(percent_change.get("kd"), is_good_higher=True)
        win_rate_change = format_change(percent_change.get("win_rate"), is_good_higher=True, is_percentage_points=True)
        avg_placement_change = format_change(percent_change.get("avg_placement"), is_good_higher=False)
        kills_change = format_change(percent_change.get("kills"), is_good_higher=True)

        embed.add_field(
            name="K/D Ratio",
            value=f"{stats_start.get('kd', 0):.2f} → {stats_end.get('kd', 0):.2f} {kd_change}",
            inline=True
        )
        embed.add_field(
            name="Win Rate",
            value=f"{stats_start.get('win_rate', 0):.1f}% → {stats_end.get('win_rate', 0):.1f}% {win_rate_change}",
            inline=True
        )
        embed.add_field(
            name="Avg Placement",
            value=f"{stats_start.get('avg_placement', 0):.1f} → {stats_end.get('avg_placement', 0):.1f} {avg_placement_change}",
            inline=True
        )

        embed.add_field(
            name="Kills",
            value=f"{delta.get('kills', 0):+d} ({kills_change})",
            inline=True
        )
        embed.add_field(
            name="Wins",
            value=f"{delta.get('wins', 0):+d}",
            inline=True
        )
        embed.add_field(
            name="Matches",
            value=f"{delta.get('matches', 0):+d}",
            inline=True
        )

        # Additional stats
        embed.add_field(
            name="Total Damage",
            value=f"{delta.get('damage', 0):+,.0f}",
            inline=True
        )
        embed.add_field(
            name="Top 10s",
            value=f"{delta.get('top10', 0):+d}",
            inline=True
        )
        embed.add_field(
            name="Data Points",
            value=f"{trend['snapshots_count']} snapshots",
            inline=True
        )

        embed.set_footer(text=f"Based on {trend['period_days']} days of historical data")

        await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.error(f"[playertrend_impl] Error for player {player_name}: {e}", exc_info=True)
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")
        await interaction.followup.send(
            f"❌ Error calculating trend: {str(e)}",
            ephemeral=True
        )


async def compare_impl(interaction: discord.Interaction, player1: str, player2: str):
    """Compare two tracked players."""
    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.NotFound:
        # Interaction already expired, nothing we can do
        return

    try:
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")

        normalized1 = normalize_player_name(player1)
        normalized2 = normalize_player_name(player2)

        # Check if both players are tracked
        tracked_players = [normalize_player_name(p) for p in guild_cfg.get("players", [])]
        if normalized1 not in tracked_players:
            await interaction.followup.send(
                translations.get_translation(lang, "player_not_tracked").format(name=player1),
                ephemeral=True
            )
            return
        if normalized2 not in tracked_players:
            await interaction.followup.send(
                translations.get_translation(lang, "player_not_tracked").format(name=player2),
                ephemeral=True
            )
            return

        # Get current stats from latest snapshot
        snapshots1 = await history.get_player_snapshots(interaction.guild_id, player1, days=7)
        snapshots2 = await history.get_player_snapshots(interaction.guild_id, player2, days=7)

        if not snapshots1 or not snapshots2:
            await interaction.followup.send(
                translations.get_translation(lang, "insufficient_history_compare"),
                ephemeral=True
            )
            return

        stats1 = snapshots1[-1]["stats"]
        stats2 = snapshots2[-1]["stats"]

        # Build comparison embed
        embed = discord.Embed(
            title=f"⚔️ {player1} vs {player2}",
            color=discord.Color.gold()
        )

        # Side-by-side comparison
        def format_stat(label, key1, key2=None, lower_better=False):
            if key2 is None:
                key2 = key1
            val1 = stats1.get(key1, 0)
            val2 = stats2.get(key2, 0)

            if lower_better:
                winner = player1 if val1 < val2 else player2 if val2 < val1 else "Tie"
            else:
                winner = player1 if val1 > val2 else player2 if val2 > val1 else "Tie"

            return f"{label}: {val1} vs {val2} ({winner})"

        embed.add_field(
            name="Matches",
            value=f"{stats1.get('matches', 0)} vs {stats2.get('matches', 0)}",
            inline=True
        )
        embed.add_field(
            name="Wins",
            value=f"{stats1.get('wins', 0)} vs {stats2.get('wins', 0)}",
            inline=True
        )
        embed.add_field(
            name="Win Rate",
            value=f"{stats1.get('win_rate', 0):.1f}% vs {stats2.get('win_rate', 0):.1f}%",
            inline=True
        )

        embed.add_field(
            name="Kills",
            value=f"{stats1.get('kills', 0)} vs {stats2.get('kills', 0)}",
            inline=True
        )
        embed.add_field(
            name="K/D",
            value=f"{stats1.get('kd', 0):.2f} vs {stats2.get('kd', 0):.2f}",
            inline=True
        )
        embed.add_field(
            name="Avg Placement",
            value=f"{stats1.get('avg_placement', 0):.1f} vs {stats2.get('avg_placement', 0):.1f}",
            inline=True
        )

        embed.add_field(
            name="Damage",
            value=f"{stats1.get('damage', 0):,.0f} vs {stats2.get('damage', 0):,.0f}",
            inline=True
        )
        embed.add_field(
            name="Top 10s",
            value=f"{stats1.get('top10', 0)} vs {stats2.get('top10', 0)}",
            inline=True
        )

        # Identify strengths
        strengths = []
        if stats1.get('kd', 0) > stats2.get('kd', 0):
            strengths.append(f"**{player1}** has better K/D")
        elif stats2.get('kd', 0) > stats1.get('kd', 0):
            strengths.append(f"**{player2}** has better K/D")

        if stats1.get('avg_placement', 100) < stats2.get('avg_placement', 100):
            strengths.append(f"**{player1}** has better placement")
        elif stats2.get('avg_placement', 100) < stats1.get('avg_placement', 100):
            strengths.append(f"**{player2}** has better placement")

        if stats1.get('damage', 0) > stats2.get('damage', 0):
            strengths.append(f"**{player1}** has higher damage output")
        elif stats2.get('damage', 0) > stats1.get('damage', 0):
            strengths.append(f"**{player2}** has higher damage output")

        if strengths:
            embed.add_field(
                name="Strengths",
                value="\n".join(strengths),
                inline=False
            )

        await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.error(f"[compare_impl] Error comparing {player1} and {player2}: {e}", exc_info=True)
        guild_cfg = await storage.get_guild(interaction.guild_id)
        lang = guild_cfg.get("language", "en")
        await interaction.followup.send(
            f"❌ Error comparing players: {str(e)}",
            ephemeral=True
        )
