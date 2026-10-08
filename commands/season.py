"""
Season summary command - shows current season performance for the clan.
"""

import logging
import discord
from discord import app_commands

import storage
import history
import translations
from modules.utils import normalize_player_name

logger = logging.getLogger(__name__)


async def season_impl(interaction: discord.Interaction):
    """Show current season summary for the clan."""
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

    game_mode = guild_cfg.get("game_mode", "squad-fpp")

    # Get historical snapshots for rank progression
    guild_history = await history.get_guild_history(interaction.guild_id)
    daily_snapshots = guild_history.get("daily_snapshots", {})

    # Get latest and previous snapshots (7 days ago)
    from datetime import datetime, timezone, timedelta
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prev_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    # Aggregate season stats from latest snapshots
    total_matches = 0
    total_wins = 0
    total_kills = 0
    total_deaths = 0
    total_damage = 0
    total_ranked_points = 0

    ranked_players = []
    rank_progressions = []

    for player in players:
        normalized = normalize_player_name(player)

        # Get latest snapshot
        latest_data = None
        for date_str in sorted(daily_snapshots.keys(), reverse=True):
            if normalized in daily_snapshots[date_str]:
                latest_data = daily_snapshots[date_str][normalized]
                break

        if latest_data:
            total_matches += latest_data.get("matches", 0)
            total_wins += latest_data.get("wins", 0)
            total_kills += latest_data.get("kills", 0)
            total_deaths += latest_data.get("deaths", 0)
            total_damage += latest_data.get("damage", 0)

            ranked_points = latest_data.get("ranked_points", 0)
            ranked_tier = latest_data.get("ranked_tier", "")

            if ranked_points > 0:
                total_ranked_points += ranked_points
                ranked_players.append({
                    "name": player,
                    "points": ranked_points,
                    "tier": ranked_tier
                })

            # Calculate rank progression using dedicated helper
            prev_data = daily_snapshots.get(prev_date, {}).get(normalized)
            if prev_data:
                progression = history.calculate_rank_progression(prev_data, latest_data)
                if progression["status"] == "delta":
                    rank_progressions.append({
                        "name": player,
                        "points": progression["current_points"],
                        "tier": progression["current_tier"],
                        "change": progression["point_change"],
                        "prev_tier": progression["previous_tier"],
                    })
                elif progression["status"] == "season_reset":
                    # Mark season reset for display
                    rank_progressions.append({
                        "name": player,
                        "points": progression["current_points"],
                        "tier": progression["current_tier"],
                        "change": 0,
                        "prev_tier": progression["previous_tier"],
                        "is_season_reset": True,
                    })

    avg_kd = total_kills / max(total_deaths, 1)
    avg_win_rate = (total_wins / max(total_matches, 1)) * 100

    # Find top performers
    if ranked_players:
        top_ranked = max(ranked_players, key=lambda p: p["points"])
    else:
        top_ranked = None

    # Find most improved
    if rank_progressions:
        most_improved = max(rank_progressions, key=lambda p: p["change"])
    else:
        most_improved = None

    # Build embed
    embed = discord.Embed(
        title="🏆 Season Summary",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="📊 Clan Totals",
        value=f"**Matches:** {total_matches:,}\n"
              f"**Wins:** {total_wins:,}\n"
              f"**Kills:** {total_kills:,}\n"
              f"**Win Rate:** {avg_win_rate:.1f}%\n"
              f"**Avg K/D:** {avg_kd:.2f}",
        inline=True
    )

    ranked_field = f"**Highest Ranked:** {top_ranked['name'] if top_ranked else 'N/A'}\n"
    if top_ranked:
        ranked_field += f"{top_ranked['tier']} ({top_ranked['points']:,} RP)"

    embed.add_field(
        name="🏅 Ranked",
        value=ranked_field,
        inline=True
    )

    progression_field = ""
    if most_improved:
        if most_improved.get("is_season_reset"):
            progression_field = f"**Season Reset:** {most_improved['name']}\n"
            progression_field += f"Previous: {most_improved['prev_tier']}\n"
            progression_field += f"Current: {most_improved['tier']}"
        else:
            change_emoji = "📈" if most_improved["change"] > 0 else "📉"
            progression_field = f"**Most Improved:** {most_improved['name']}\n"
            progression_field += f"{change_emoji} {most_improved['change']:+,} RP\n"
            progression_field += f"Current: {most_improved['tier']}"
    else:
        progression_field = "No rank progression data yet (need 7+ days of snapshots)"

    embed.add_field(
        name="📈 Rank Progression",
        value=progression_field,
        inline=True
    )

    embed.add_field(
        name="🎮 Activity",
        value=f"**Tracked Players:** {len(players)}\n"
              f"**Total Damage:** {total_damage:,.0f}\n"
              f"**Game Mode:** {game_mode}",
        inline=True
    )

    embed.set_footer(text=f"Based on historical snapshots. Rank progression requires 7+ days of data.")

    await interaction.followup.send(embed=embed)
