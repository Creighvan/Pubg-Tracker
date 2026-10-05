"""
Season summary command - shows current season performance for the clan.
"""

import discord
from discord import app_commands

import storage
import translations
from modules.utils import normalize_player_name


async def season_impl(interaction: discord.Interaction):
    """Show current season summary for the clan."""
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

    game_mode = guild_cfg.get("game_mode", "squad-fpp")

    # For now, use lifetime stats as "season" data
    # In the future, this could pull from actual ranked season data
    from pubg_api import PubgClient, PubgApiError
    from modules.config import pubg

    try:
        found, not_found = await pubg.get_players_and_stats(players, game_mode=game_mode)

        if not found:
            await interaction.followup.send(
                translations.get_translation(lang, "no_data_available"),
                ephemeral=True
            )
            return

        # Aggregate season stats
        total_matches = sum(p.get("stats", {}).get("matches", 0) for p in found)
        total_wins = sum(p.get("stats", {}).get("wins", 0) for p in found)
        total_kills = sum(p.get("stats", {}).get("kills", 0) for p in found)
        total_deaths = sum(p.get("stats", {}).get("deaths", 0) for p in found)
        total_damage = sum(p.get("stats", {}).get("damageDealt", 0) for p in found)

        avg_kd = total_kills / max(total_deaths, 1)
        avg_win_rate = (total_wins / max(total_matches, 1)) * 100

        # Find top performers
        top_killer = max(found, key=lambda p: p.get("stats", {}).get("kills", 0))
        top_winner = max(found, key=lambda p: p.get("stats", {}).get("wins", 0))
        top_kd = max(found, key=lambda p: p.get("stats", {}).get("kd", 0))

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

        embed.add_field(
            name="🥇 Top Performers",
            value=f"**Most Kills:** {top_killer['name']} ({top_killer.get('stats', {}).get('kills', 0):,})\n"
                  f"**Most Wins:** {top_winner['name']} ({top_winner.get('stats', {}).get('wins', 0):,})\n"
                  f"**Best K/D:** {top_kd['name']} ({top_kd.get('stats', {}).get('kd', 0):.2f})",
            inline=True
        )

        embed.add_field(
            name="🎮 Activity",
            value=f"**Tracked Players:** {len(found)}\n"
                  f"**Total Damage:** {total_damage:,.0f}\n"
                  f"**Game Mode:** {game_mode}",
            inline=True
        )

        embed.set_footer(text=f"Based on lifetime stats. Ranked season data coming soon.")

        await interaction.followup.send(embed=embed)

    except PubgApiError as e:
        await interaction.followup.send(
            translations.get_translation(lang, "api_error").format(error=str(e)),
            ephemeral=True
        )
