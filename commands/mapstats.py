"""
Map analytics - map-specific performance tracking.
"""

import discord
from discord import app_commands

import storage
import history
import translations
from modules.utils import normalize_player_name


async def mapstats_impl(interaction: discord.Interaction):
    """Show clan map performance statistics."""
    await interaction.response.defer()

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    players = guild_cfg.get("players", [])

    if not players:
        await interaction.followup.send(
            translations.get_translation(lang, "no_players_tracked"),
            ephemeral=True
        )
        return

    # Get match history from historical data
    guild_history = await history.get_guild_history(interaction.guild_id)
    match_history = guild_history.get("match_history", [])

    if not match_history:
        await interaction.followup.send(
            "No match history data available yet. Map analytics require accumulated match data.",
            ephemeral=True
        )
        return

    # Aggregate by map
    map_stats = {}
    total_matches = len(match_history)

    for match in match_history:
        map_name = match.get("map", "Unknown")
        if map_name not in map_stats:
            map_stats[map_name] = {
                "matches": 0,
                "wins": 0,
                "kills": 0,
                "deaths": 0,
                "damage": 0,
                "placements": [],
            }

        map_stats[map_name]["matches"] += 1
        if match.get("is_win", False):
            map_stats[map_name]["wins"] += 1
        map_stats[map_name]["kills"] += match.get("total_kills", 0)
        map_stats[map_name]["damage"] += match.get("total_damage", 0)
        placement = match.get("placement", 0)
        if placement > 0:
            map_stats[map_name]["placements"].append(placement)
            # Estimate deaths (assuming 100 players, placement - 1 = deaths before you)
            map_stats[map_name]["deaths"] += max(0, placement - 1)

    # Calculate derived stats
    map_results = []
    for map_name, stats in map_stats.items():
        matches = stats["matches"]
        wins = stats["wins"]
        kills = stats["kills"]
        deaths = stats["deaths"]
        damage = stats["damage"]
        placements = stats["placements"]

        win_rate = (wins / matches * 100) if matches > 0 else 0
        kd = (kills / deaths) if deaths > 0 else 0
        avg_placement = (sum(placements) / len(placements)) if placements else 0
        avg_damage = (damage / matches) if matches > 0 else 0
        activity_pct = (matches / total_matches * 100) if total_matches > 0 else 0

        map_results.append({
            "map": map_name,
            "matches": matches,
            "wins": wins,
            "win_rate": win_rate,
            "kd": kd,
            "avg_placement": avg_placement,
            "avg_damage": avg_damage,
            "activity_pct": activity_pct,
        })

    # Sort by matches (most played first)
    map_results.sort(key=lambda x: x["matches"], reverse=True)

    if not map_results:
        await interaction.followup.send(
            "No map data available in match history.",
            ephemeral=True
        )
        return

    # Find best and worst maps
    best_map = max(map_results, key=lambda x: x["win_rate"])
    worst_map = min(map_results, key=lambda x: x["win_rate"])

    # Build embed
    embed = discord.Embed(
        title="🗺️ Map Performance",
        color=discord.Color.green()
    )

    # Add each map's stats
    for result in map_results[:5]:  # Show top 5 maps
        map_name = result["map"]
        matches = result["matches"]
        wins = result["wins"]
        win_rate = result["win_rate"]
        kd = result["kd"]
        avg_placement = result["avg_placement"]
        avg_damage = result["avg_damage"]

        field_value = (
            f"{matches} matches · {wins} wins\n"
            f"{win_rate:.1f}% win rate\n"
            f"{kd:.2f} K/D\n"
            f"Avg placement: {avg_placement:.1f}\n"
            f"Avg damage: {avg_damage:.0f}"
        )

        embed.add_field(
            name=map_name,
            value=field_value,
            inline=False
        )

    # Add best/worst summary
    embed.add_field(
        name="🏆 Best Map",
        value=f"{best_map['map']}\n{best_map['win_rate']:.1f}% win rate",
        inline=True
    )

    embed.add_field(
        name="📉 Needs Improvement",
        value=f"{worst_map['map']}\n{worst_map['win_rate']:.1f}% win rate",
        inline=True
    )

    embed.set_footer(text=f"Based on {total_matches} historical matches")

    await interaction.followup.send(embed=embed)
