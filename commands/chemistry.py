"""
Squad chemistry - analyze team synergy and best squad combinations.
"""

import discord
from discord import app_commands

import storage
import history
import translations
from modules.utils import normalize_player_name
from datetime import datetime, timezone


async def chemistry_impl(interaction: discord.Interaction, player1: str, player2: str):
    """Show chemistry between two players."""
    await interaction.response.defer()

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    normalized1 = normalize_player_name(player1)
    normalized2 = normalize_player_name(player2)
    tracked_players = [normalize_player_name(p) for p in guild_cfg.get("players", [])]

    if normalized1 not in tracked_players or normalized2 not in tracked_players:
        await interaction.followup.send(
            "Both players must be tracked to analyze chemistry.",
            ephemeral=True
        )
        return

    # Get teammate pairs from canonical dataset
    pairs = await history.get_teammate_pairs(interaction.guild_id, days=90, min_matches=1)

    # Create pair key (sorted alphabetically)
    names = sorted([normalized1, normalized2])
    pair_key = f"{names[0]}_{names[1]}"

    if pair_key not in pairs:
        await interaction.followup.send(
            f"No shared match history found between {player1} and {player2}.",
            ephemeral=True
        )
        return

    stats = pairs[pair_key]
    shared_matches = stats["shared_matches"]
    usable_shared_matches = stats["usable_shared_matches"]
    same_team_matches = stats["same_team_matches"]

    # Build embed with transparent measurements
    embed = discord.Embed(
        title=f"🤝 {player1} + {player2} Chemistry",
        color=discord.Color.purple()
    )

    # Show the distinction between shared matches and confirmed teammates
    embed.add_field(
        name="📊 Match Data",
        value=f"**Shared matches:** {shared_matches}\n"
              f"**Usable data:** {usable_shared_matches}\n"
              f"**Confirmed teammates:** {same_team_matches}",
        inline=False
    )

    if same_team_matches == 0:
        embed.add_field(
            name="⚠️ Insufficient Data",
            value=f"No confirmed team data available. {player1} and {player2} have appeared in {shared_matches} matches together, but team information is missing for those matches.\n\n"
                  f"Chemistry requires confirmed team assignments to calculate win rate and performance.",
            inline=False
        )
        await interaction.followup.send(embed=embed)
        return

    # Show confirmed team statistics
    wins = stats["wins"]
    win_rate = stats["win_rate"]
    avg_placement = stats["avg_placement"]
    combined_kills = stats["combined_kills"]
    avg_combined_kills = stats["avg_combined_kills"]
    combined_damage = stats["combined_damage"]
    avg_combined_damage = stats["avg_combined_damage"]
    player_a_kills = stats["player_a_kills"]
    player_b_kills = stats["player_b_kills"]

    embed.add_field(
        name="🏆 Team Performance",
        value=f"**Wins:** {wins}\n"
              f"**Team win rate:** {win_rate:.1f}%\n"
              f"**Avg placement:** {avg_placement:.1f}\n"
              f"**Combined K/D:** {avg_combined_kills:.2f}\n"
              f"**Avg combined damage:** {avg_combined_damage:.0f}",
        inline=False
    )

    embed.add_field(
        name="⚔️ Individual Kills",
        value=f"**{player1}:** {player_a_kills}\n"
              f"**{player2}:** {player_b_kills}",
        inline=False
    )

    # Show sample size warning if small
    if same_team_matches < 5:
        embed.add_field(
            name="⚠️ Small Sample Size",
            value=f"Based on only {same_team_matches} confirmed team matches. "
                  f"Statistics may not be representative.",
            inline=False
        )

    # Show last played time
    last_played = stats.get("last_played")
    if last_played:
        try:
            last_dt = datetime.fromisoformat(last_played.replace("Z", "+00:00"))
            days_ago = (datetime.now(timezone.utc) - last_dt).days
            if days_ago == 0:
                time_str = "Today"
            elif days_ago == 1:
                time_str = "Yesterday"
            else:
                time_str = f"{days_ago} days ago"
            embed.set_footer(text=f"Last played together: {time_str}")
        except:
            embed.set_footer(text="Last played together: Unknown")
    else:
        embed.set_footer(text="Last played together: Unknown")

    await interaction.followup.send(embed=embed)
