"""
Embed builder functions for PUBG Clan Tracker Discord Bot.

This module contains all functions that construct Discord embeds for various
reports and displays. These functions are pure presentation logic that take
data and return formatted discord.Embed objects.

Functions:
    build_report_status_embed: Summarize scheduled reports for a server
    build_clan_embed: Clan statistics report
    build_clan_level_embed: Weekly clan level progress report
    build_last_active_embed: Player last active times report
    build_ranked_embed: Ranked standings report
    build_highlights_embed: Daily highlights with fun titles
    build_mastery_embed: Weapon and survival mastery report
    build_survival_mastery_embeds: Survival mastery grouped by tier
    build_leaderboard_embed: Official leaderboard placements
    build_feedback_prompt_embed: Feedback collection prompt
    build_chicken_dinner_embed: Flashy Chicken Dinner win display with kill counts

Helper functions:
    _format_time_ago: Format ISO timestamp as relative time
    _pick_leader: Find leader for a stat category
    _compute_award_winners: Calculate all award winners
    _friendly_weapon_name: Convert weapon ID to readable name
    _survival_tier_number: Normalize survival tier to 1-5
    _friendly_map_name: Convert PUBG API map code to readable name
"""

import os
from datetime import datetime, timezone

import discord

from modules.config import RANKED_MODE_LABELS, VALID_GAME_MODES
from modules.utils import _channel_mention, _safe_div, normalize_player_name
import translations

# Import scheduler helpers from bot.utils (these are used in build_report_status_embed)
# Note: These are imported dynamically to avoid circular imports
# They will be available when the module is loaded in the main bot context


def build_report_status_embed(guild_cfg: dict) -> discord.Embed:
    """Summarize every automatic report configured for one Discord server."""
    # Import scheduler helpers dynamically to avoid circular imports
    from modules.utils import _next_interval_report, _next_daily_report, _next_weekly_report

    embed = discord.Embed(
        title="📅 Scheduled Report Status",
        description="Only configured reports are scheduled. All times are UTC.",
        color=discord.Color.blurple(),
    )

    disabled_reports = []
    digest_channel = guild_cfg.get("post_channel_id")
    if digest_channel and guild_cfg.get("digest_enabled", True):
        hour = guild_cfg.get("digest_hour_utc")
        lang = guild_cfg.get("language", "en")
        if hour is None:
            interval = guild_cfg.get("post_interval_hours", 6)
            count = interval
            unit_key = "hour" if count == 1 else "hours"
            unit = get_translation(lang, unit_key)
            schedule = get_translation(lang, "every_hours").format(count=count, unit=unit)
            next_time = _next_interval_report(interval, guild_cfg.get("last_post_at"))
        else:
            minute = guild_cfg.get("digest_minute_utc", 0)
            schedule = f"Daily at {hour:02d}:{minute:02d} UTC"
            next_time = _next_daily_report(hour, minute, guild_cfg.get("last_post_at"))
        embed.add_field(name="📊 Clan Digest", value=f"{_channel_mention(digest_channel)}\n{schedule}\n**Next:** {next_time}", inline=False)

    elif digest_channel:
        disabled_reports.append("Clan Digest")

    daily_reports = [
        ("🟢 Last Active", "activity_enabled", "last_activity_channel_id", "activity_hour_utc", "activity_minute_utc", "last_activity_posted_at", 24, None),
        ("🏆 Ranked", "ranked_enabled", "ranked_channel_id", "ranked_hour_utc", "ranked_minute_utc", "ranked_posted_at", 24, guild_cfg.get("ranked_queue", "squad")),
        ("✨ Daily Highlights", "highlights_enabled", "highlights_channel_id", "highlights_hour_utc", "highlights_minute_utc", "highlights_posted_at", 24, None),
    ]
    for name, enabled_key, channel_key, hour_key, minute_key, posted_key, interval, queue in daily_reports:
        channel_id = guild_cfg.get(channel_key) or digest_channel
        if not channel_id:
            continue
        if not guild_cfg.get(enabled_key, True):
            disabled_reports.append(name.replace("🟢 ", "").replace("🏆 ", "").replace("✨ ", ""))
        # Special handling for Last Active and Ranked reports - they update in place at fixed UTC times
        if name in ("🟢 Last Active", "🏆 Ranked"):
            hour = guild_cfg.get(hour_key)
            if hour is not None:
                minute = guild_cfg.get(minute_key, 0)
                schedule = f"Daily at {hour:02d}:{minute:02d} UTC (updates in place)"
                next_time = f"{hour:02d}:{minute:02d} UTC"
                embed.add_field(name=name.replace("🟢 ", "").replace("🏆 ", ""), value=f"{_channel_mention(channel_id)}\n{schedule}\n**Next:** {next_time}", inline=False)
                continue
        hour = guild_cfg.get(hour_key)
        if hour is None:
            schedule = f"Every {interval} hours"
            next_time = _next_interval_report(interval, guild_cfg.get(posted_key))
        else:
            minute = guild_cfg.get(minute_key, 0)
            schedule = f"Daily at {hour:02d}:{minute:02d} UTC"
            next_time = _next_daily_report(hour, minute, guild_cfg.get(posted_key))
        if queue:
            schedule += f" · {RANKED_MODE_LABELS.get(queue, queue.title())} {'FPP' if queue.endswith('-fpp') else 'TPP'}"
        embed.add_field(name=name, value=f"{_channel_mention(channel_id)}\n{schedule}\n**Next:** {next_time}", inline=False)

    clan_channel = guild_cfg.get("clan_channel_id")
    clan_weekday = guild_cfg.get("clan_weekday_utc")
    if clan_channel and clan_weekday is not None and guild_cfg.get("clan_level_enabled", True):
        hour = guild_cfg.get("clan_hour_utc", 0)
        minute = guild_cfg.get("clan_minute_utc", 0)
        weekday_name = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[clan_weekday]
        next_time = _next_weekly_report(clan_weekday, hour, minute, guild_cfg.get("clan_posted_at"))
        embed.add_field(name="🛡️ Clan Level", value=f"{_channel_mention(clan_channel)}\nEvery {weekday_name} at {hour:02d}:{minute:02d} UTC (updates in place)\n**Next:** {next_time}", inline=False)
    elif clan_channel and clan_weekday is not None:
        disabled_reports.append("Clan Level")

    survival_channel = guild_cfg.get("survival_channel_id")
    survival_weekday = guild_cfg.get("survival_weekday_utc")
    if survival_channel and survival_weekday is not None and guild_cfg.get("survival_enabled", True):
        hour = guild_cfg.get("survival_hour_utc", 12)
        minute = guild_cfg.get("survival_minute_utc", 0)
        weekday_name = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[survival_weekday]
        next_time = _next_weekly_report(survival_weekday, hour, minute, guild_cfg.get("survival_posted_at"))
        embed.add_field(name="🎖️ Survival Mastery", value=f"{_channel_mention(survival_channel)}\nEvery {weekday_name} at {hour:02d}:{minute:02d} UTC (deletes & reposts with images)\n**Next:** {next_time}", inline=False)
    elif survival_channel and survival_weekday is not None:
        disabled_reports.append("Survival Mastery")

    donation_channel = guild_cfg.get("donation_channel_id")
    if donation_channel and guild_cfg.get("donation_enabled", True):
        hour = guild_cfg.get("donation_hour_utc", 12)
        minute = guild_cfg.get("donation_minute_utc", 0)
        next_time = _next_weekly_report(6, hour, minute, guild_cfg.get("donation_posted_at"))
        embed.add_field(name="☕ Donation Message", value=f"{_channel_mention(donation_channel)}\nEvery Sunday at {hour:02d}:{minute:02d} UTC\n**Next:** {next_time}", inline=False)
    elif donation_channel:
        disabled_reports.append("Donation Message")

    if disabled_reports:
        embed.add_field(name="⛔ Disabled", value=", ".join(disabled_reports), inline=False)

    if not embed.fields:
        embed.description = "No automatic reports are configured yet. Use the `/set...channel` and `/set...time` commands to schedule one."
    embed.set_footer(text="Scheduler checks every 15 minutes; a report can post shortly after its shown time.")
    return embed


def build_clan_embed(guild_name: str, guild_cfg: dict, players: list[dict], not_found: list[str]) -> discord.Embed:
    from translations import get_translation
    lang = guild_cfg.get("language", "en")
    
    game_mode = guild_cfg["game_mode"]
    title = guild_cfg.get("clan_name") or guild_name

    total_kills = sum(p["stats"].get("kills", 0) for p in players)
    total_wins = sum(p["stats"].get("wins", 0) for p in players)
    total_games = sum(p["stats"].get("roundsPlayed", 0) for p in players)
    total_damage = sum(p["stats"].get("damageDealt", 0.0) for p in players)

    embed = discord.Embed(
        title=f"{title} — {get_translation(lang, 'clan_report')} ({game_mode})",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name=f"👥 {get_translation(lang, 'tracked_players')}", value=str(len(players)), inline=True)
    embed.add_field(name=f"💀 {get_translation(lang, 'total_kills')}", value=f"{total_kills:,}", inline=True)
    embed.add_field(name=f"🏆 {get_translation(lang, 'total_wins')}", value=f"{total_wins:,}", inline=True)
    embed.add_field(name=f"📊 {get_translation(lang, 'win_rate')}", value=f"{_safe_div(total_wins, total_games) * 100:.1f}%", inline=True)
    embed.add_field(name=f"🎯 {get_translation(lang, 'total_damage')}", value=f"{total_damage:,.0f}", inline=True)
    embed.add_field(name=f"⚔️ {get_translation(lang, 'total_matches')}", value=f"{total_games:,}", inline=True)

    ranked = sorted(players, key=lambda p: p["stats"].get("kills", 0), reverse=True)[:10]
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = []
    for i, p in enumerate(ranked, start=1):
        s = p["stats"]
        kd = _safe_div(s.get("kills", 0), max(s.get("roundsPlayed", 0) - s.get("wins", 0), 1))
        rank_str = medals.get(i, f"{i}.")
        lines.append(f"{rank_str} **{p['name']}** — {s.get('kills', 0):,} kills, {s.get('wins', 0)} wins, {kd:.2f} K/D")
    if lines:
        embed.add_field(name=f"🔝 {get_translation(lang, 'top_fraggers')}", value="\n".join(lines), inline=False)

    if not_found:
        embed.add_field(
            name=f"⚠️ {get_translation(lang, 'not_found')}",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )

    embed.set_footer(text=get_translation(lang, "lifetime_stats_footer"))
    return embed


def build_clan_level_embed(guild_cfg: dict, clan: dict) -> discord.Embed:
    """Build the weekly clan-level report from the official clan endpoint."""
    from translations import get_translation
    lang = guild_cfg.get("language", "en")
    
    embed = discord.Embed(
        title=f"{clan['name']} — {get_translation(lang, 'clan_level_report')}",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Clan", value=f"**{clan['name']}**\nTag: `{clan['tag']}`", inline=True)
    embed.add_field(name=get_translation(lang, "current_level"), value=str(clan["level"]), inline=True)
    embed.add_field(name=get_translation(lang, "members"), value=str(clan["member_count"]), inline=True)

    previous_level = guild_cfg.get("clan_last_level")
    previous_members = guild_cfg.get("clan_last_member_count")
    if previous_level is None:
        progress = get_translation(lang, "first_snapshot")
    else:
        level_change = clan["level"] - previous_level
        member_change = clan["member_count"] - previous_members if previous_members is not None else 0
        progress = get_translation(lang, "level_change").format(change=level_change)
        if previous_members is not None:
            progress += get_translation(lang, "member_change").format(change=member_change)
    embed.add_field(name=get_translation(lang, "weekly_progress"), value=progress, inline=False)
    embed.add_field(
        name=get_translation(lang, "important_note"),
        value=get_translation(lang, "clan_level_note"),
        inline=False,
    )
    embed.set_footer(text=get_translation(lang, "weekly_clan_progress_footer"))
    return embed


def _format_time_ago(iso_str: str | None, days_inactive: int = None, lang: str = "en") -> str:
    from translations import get_translation
    if days_inactive is not None:
        # Use the explicit days_inactive count for auto-counted players
        count = days_inactive
        unit_key = "day" if count == 1 else "days"
        unit = get_translation(lang, unit_key)
        return get_translation(lang, "days_ago").format(count=count, unit=unit)
    if not iso_str:
        return get_translation(lang, "no_recent_matches")
    then = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    delta = datetime.now(timezone.utc) - then
    hours = delta.total_seconds() / 3600
    if hours < 1:
        return get_translation(lang, "less_than_1_hour")
    if hours < 24:
        count = int(hours)
        unit_key = "hour" if count == 1 else "hours"
        unit = get_translation(lang, unit_key)
        return get_translation(lang, "hours_ago").format(count=count, unit=unit)
    count = int(hours // 24)
    unit_key = "day" if count == 1 else "days"
    unit = get_translation(lang, unit_key)
    return get_translation(lang, "days_ago").format(count=count, unit=unit)


def build_last_active_embed(guild_id: int, guild_name: str, guild_cfg: dict, players: list[dict], not_found: list[str], protected_players: list[str] = None) -> discord.Embed:
    from translations import get_translation
    lang = guild_cfg.get("language", "en")
    
    title = guild_cfg.get("clan_name") or guild_name
    protected_lower = [normalize_player_name(p) for p in (protected_players or [])]

    embed = discord.Embed(
        title=f"{title} — {get_translation(lang, 'last_active_report')}",
        description=get_translation(lang, "last_active_description"),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc),
    )

    def _recency_emoji(iso_str: str | None) -> str:
        if not iso_str:
            return "⚪"
        then = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        hours = (datetime.now(timezone.utc) - then).total_seconds() / 3600
        if hours < 24:
            return "🟢"
        if hours < 24 * 7:
            return "🟡"
        return "🔴"

    active_24h = sum(1 for p in players if p.get("last_match_at") and _recency_emoji(p["last_match_at"]) == "🟢")
    # Count only protected players who are actually in the tracked list
    protected_count = sum(1 for p in players if normalize_player_name(p["name"]) in protected_lower)

    embed.add_field(name=f"🟢 {get_translation(lang, 'active_24h')}", value=str(active_24h), inline=True)
    embed.add_field(name=f"👥 {get_translation(lang, 'tracked_players')}", value=str(len(players)), inline=True)
    if protected_count > 0:
        embed.add_field(name=f"🛡️ {get_translation(lang, 'protected_players')}", value=str(protected_count), inline=True)

    def get_match_date(p):
        """Extract the match date for sorting, defaulting to None (oldest)."""
        if manual_data := guild_cfg.get("manual_inactive_dates", {}).get(normalize_player_name(p["name"])):
            return manual_data["date"] if isinstance(manual_data, dict) else manual_data
        elif p.get("data_source") == "auto_count":
            return p.get("last_match_date")
        else:
            return p.get("last_match_at")

    # Sort players by match date (most recent first)
    players_sorted = sorted(players, key=get_match_date, reverse=True)

    lines = []
    for idx, p in enumerate(players_sorted, start=1):
        # Check for manual inactive date override or auto-counted date
        if manual_data := guild_cfg.get("manual_inactive_dates", {}).get(normalize_player_name(p["name"])):
            # manual_data is a dict with 'date' and 'set_at' keys
            match_date = manual_data["date"] if isinstance(manual_data, dict) else manual_data
            source_note = get_translation(lang, "source_manual")
            days_inactive = p.get("days_inactive")
        elif p.get("data_source") == "auto_count":
            match_date = p.get("last_match_date")
            source_note = get_translation(lang, "source_auto_count")
            days_inactive = p.get("days_inactive")
        else:
            match_date = p.get("last_match_at")
            source_note = ""
            days_inactive = None

        # Case-insensitive comparison for protected players
        player_normalized = normalize_player_name(p["name"])
        is_protected = player_normalized in protected_lower
        protected_mark = " 🛡️" if is_protected else ""
        lines.append(f"{idx}. **{p['name']}**{protected_mark} — {_format_time_ago(match_date, days_inactive, lang)}{source_note}")

    # Discord embed fields cap at 1024 chars; chunk if the roster is large.
    chunk_size = 20
    for i in range(0, len(lines), chunk_size):
        field_lines = lines[i : i + chunk_size]
        embed.add_field(
            name=get_translation(lang, "players") if i == 0 else "\u200b",
            value="\n".join(field_lines) or "None",
            inline=False,
        )
    if not_found:
        embed.add_field(
            name=f"⚠️ {get_translation(lang, 'not_found')}",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )
    footer_text = get_translation(lang, "updates_daily")
    if protected_count > 0:
        footer_text += " | " + get_translation(lang, "protected_footer")
    embed.set_footer(text=footer_text)
    return embed


def build_ranked_embed(guild_name: str, guild_cfg: dict, players: list[dict], not_found: list[str], game_mode: str) -> discord.Embed:
    from translations import get_translation
    lang = guild_cfg.get("language", "en")
    
    title = guild_cfg.get("clan_name") or guild_name
    queue_label = f"{RANKED_MODE_LABELS[game_mode]} {'FPP' if game_mode.endswith('-fpp') else 'TPP'}"
    embed = discord.Embed(
        title=f"{title} — {get_translation(lang, 'ranked_report')} ({queue_label})",
        description=get_translation(lang, "ranked_description"),
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc),
    )

    ranked_players = [p for p in players if p.get("ranked", {}).get("currentTier") is not None]
    if ranked_players:
        top = ranked_players[0]
        top_tier = top["ranked"]["currentTier"]
        top_tier_name = f"{top_tier.get('tier', '?')} {top_tier.get('subTier', '')}".strip()
        embed.add_field(name=f"🏅 {get_translation(lang, 'highest_ranked')}", value=f"**{top['name']}** — {top_tier_name}", inline=True)
    embed.add_field(name=f"👥 {get_translation(lang, 'ranked_this_season')}", value=f"{len(ranked_players)}/{len(guild_cfg['players'])}", inline=True)

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = []
    for p in ranked_players:
        i = len(lines) + 1
        r = p.get("ranked", {})
        rank_str = medals.get(i, f"{i}.")
        tier = r.get("currentTier", {})
        tier_name = f"{tier.get('tier', '?')} {tier.get('subTier', '')}".strip()
        rp = r.get("currentRankPoint", 0)
        wins = r.get("wins", 0)
        kills = r.get("kills", 0)
        rounds = r.get("roundsPlayed", 0)
        kd = _safe_div(kills, max(rounds - wins, 1))
        lines.append(f"{rank_str} **{p['name']}** — {tier_name} ({rp} RP), {wins}W, {kd:.2f} K/D")
    if lines:
        for i in range(0, len(lines), 15):
            embed.add_field(name=get_translation(lang, "ranking") if i == 0 else "\u200b", value="\n".join(lines[i:i + 15]), inline=False)
    else:
        embed.add_field(name=get_translation(lang, "no_ranked_matches"), value=get_translation(lang, "no_ranked_description"), inline=False)
    if not_found:
        embed.add_field(
            name=f"⚠️ {get_translation(lang, 'not_found')}",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )
    embed.set_footer(text=get_translation(lang, "ranked_footer"))
    return embed


TITLE_DEFINITIONS = [
    # (emoji, title, stat key inside p["daily"], label for the value)
    ("💀", "Top Fragger", "kills", "kills"),
    ("🏆", "The Champion", "wins", "wins"),
    ("🎯", "Damage Machine", "damageDealt", "damage"),
    ("🔫", "Top Sniper", "headshotKills", "headshot kills"),
    ("💉", "Top Medic", "revives", "revives"),
    ("🤝", "Top Supporter", "assists", "assists"),
    ("👽", "Predator", "human_kills", "human kills"),
    ("🤖", "Jon Connor", "bot_kills", "bot kills"),
    ("🤡", "Stooge Award", "stooge_kills", "own-goal kills (self + team)"),
    ("🔋", "Copper Top Award", "boosts", "energy used"),
    ("➕", "Sir Heals-A-Lot", "heals", "heals used"),
    ("🚗", "Grand Theft Auto", "road_kills", "roadkills"),
    ("🏊", "Michael Phelps", "swim_distance", "m swam"),
    ("🎒", "Window Shopper", "loot_ratio", "weapons picked up per kill"),
]


def _pick_leader(players: list[dict], stat_key: str) -> dict | None:
    contenders = [p for p in players if p["daily"].get(stat_key, 0) > 0]
    if not contenders:
        return None
    return max(contenders, key=lambda p: p["daily"].get(stat_key, 0))


def _compute_award_winners(active_players: list[dict]) -> list[tuple[str, str, str, str]]:
    """Returns [(emoji, label, winner_name, formatted_value), ...] for every
    award category that has a qualifying winner."""
    winners = []
    for emoji, label, stat_key, unit in TITLE_DEFINITIONS:
        leader = _pick_leader(active_players, stat_key)
        if leader:
            val = leader["daily"][stat_key]
            if stat_key == "loot_ratio":
                val_str = f"{val:,.2f}"
            elif isinstance(val, float):
                val_str = f"{val:,.0f}"
            else:
                val_str = f"{val:,}"
            winners.append((emoji, label, leader["name"], f"{val_str} {unit}"))

    wookiee_candidates = [
        p for p in active_players if p["daily"].get("best_zero_kill_placement") is not None
    ]
    if wookiee_candidates:
        wookiee = min(wookiee_candidates, key=lambda p: p["daily"]["best_zero_kill_placement"])
        placement = wookiee["daily"]["best_zero_kill_placement"]
        winners.append(("🌳", "Tactical Shrub", wookiee["name"], f"placed #{placement} with 0 kills that match"))

    return winners


def build_highlights_embed(guild_name: str, guild_cfg: dict, players: list[dict], not_found: list[str], hours: int) -> discord.Embed:
    from translations import get_translation
    lang = guild_cfg.get("language", "en")
    
    title = guild_cfg.get("clan_name") or guild_name
    active_players = [p for p in players if p["daily"]["matches"] > 0]

    embed = discord.Embed(
        title=f"{title} — {get_translation(lang, 'daily_highlights')} ({get_translation(lang, 'fun_titles')})",
        description=get_translation(lang, "highlights_description").format(
            count=len(active_players),
            unit=get_translation(lang, "players" if len(active_players) != 1 else "player")
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc),
    )

    if not active_players:
        # Check if players have expired matches (telemetry unavailable after 14 days)
        expired_count = sum(1 for p in players if p.get("_expired_matches", 0) > 0)
        if expired_count > 0:
            embed.add_field(
                name=get_translation(lang, "no_recent_matches_available"),
                value=get_translation(lang, "no_recent_matches_description").format(
                    count=expired_count,
                    unit=get_translation(lang, "players" if expired_count != 1 else "player")
                ),
                inline=False
            )
        else:
            embed.add_field(name=get_translation(lang, "no_matches_played"), value=get_translation(lang, "no_matches_description"), inline=False)
        return embed

    for emoji, label, winner_name, val_str in _compute_award_winners(active_players):
        embed.add_field(name=f"{emoji} {label}", value=f"**{winner_name}** — {val_str}", inline=True)

    # Top 10 overall, ranked by best single-match kills, with human/bot kill split
    # Sort players by best match kills (highest first)
    top_players = sorted(active_players, key=lambda p: p["daily"].get("best_match_kills", p["daily"]["kills"]), reverse=True)[:10]
    
    lines = []
    for i, p in enumerate(top_players, start=1):
        d = p["daily"]
        # Use best single-match stats instead of aggregated totals
        best_kills = d.get("best_match_kills", d["kills"])
        best_damage = d.get("best_match_damage", d["damageDealt"])
        lines.append(
            f"{i}. **{p['name']}** — {best_kills} {get_translation(lang, 'kills_best_match')}, {best_damage:,.0f} {get_translation(lang, 'dmg_best_match')}, "
            f"{d['human_kills']} {get_translation(lang, 'human_bot_split').format(count=d['bot_kills'])}, {d['wins']}W, {d['matches']} {get_translation(lang, 'matches_count')}"
        )
    embed.add_field(name=get_translation(lang, "top_10"), value="\n".join(lines), inline=False)

    if not_found:
        embed.add_field(
            name=f"⚠️ {get_translation(lang, 'not_found')}",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )
    embed.set_footer(text=get_translation(lang, "highlights_footer"))
    return embed


# A handful of common weapon IDs mapped to friendly names. Anything not in
# here falls back to a cleaned-up version of the raw ID (e.g.
# "Item_Weapon_M416_C" -> "M416") so the report is still readable even for
# weapons this dict doesn't know about.
WEAPON_DISPLAY_NAMES = {
    "Item_Weapon_M416_C": "M416",
    "Item_Weapon_AK47_C": "AKM",
    "Item_Weapon_K98_C": "Kar98k",
    "Item_Weapon_M24_C": "M24",
    "Item_Weapon_AWM_C": "AWM",
    "Item_Weapon_UMP_C": "UMP45",
    "Item_Weapon_Vector_C": "Vector",
    "Item_Weapon_SCAR-L_C": "SCAR-L",
    "Item_Weapon_M16A4_C": "M16A4",
    "Item_Weapon_Groza_C": "Groza",
    "Item_Weapon_Mini14_C": "Mini14",
    "Item_Weapon_SKS_C": "SKS",
    "Item_Weapon_DesertEagle_C": "Desert Eagle",
    "Item_Weapon_M9_C": "P92",
    "Item_Weapon_Shotgun_C": "S12K",
    "Item_Weapon_Winchester_C": "Win94",
}


def _friendly_weapon_name(weapon_id: str | None) -> str:
    if not weapon_id:
        return "—"
    if weapon_id in WEAPON_DISPLAY_NAMES:
        return WEAPON_DISPLAY_NAMES[weapon_id]
    return weapon_id.replace("Item_Weapon_", "").replace("_C", "")


def build_mastery_embed(guild_name: str, guild_cfg: dict, players: list[dict], not_found: list[str]) -> discord.Embed:
    from translations import get_translation
    lang = guild_cfg.get("language", "en")
    
    title = guild_cfg.get("clan_name") or guild_name
    embed = discord.Embed(
        title=f"{title} — {get_translation(lang, 'mastery_report')}",
        description=get_translation(lang, "mastery_description"),
        color=discord.Color.dark_teal(),
        timestamp=datetime.now(timezone.utc),
    )

    weapon_leader = max(players, key=lambda p: p["mastery"].get("best_weapon_level", 0), default=None)
    survival_leader = max(players, key=lambda p: p["mastery"].get("survival_level", 0), default=None)
    if weapon_leader:
        w = weapon_leader["mastery"]
        embed.add_field(
            name=f"🔫 {get_translation(lang, 'top_weapon_mastery')}",
            value=f"**{weapon_leader['name']}** — {_friendly_weapon_name(w['best_weapon'])} Lv.{w['best_weapon_level']}",
            inline=True,
        )
    if survival_leader:
        embed.add_field(
            name=f"🎖️ {get_translation(lang, 'top_survival_level')}",
            value=f"**{survival_leader['name']}** — Lv.{survival_leader['mastery']['survival_level']}",
            inline=True,
        )

    lines = []
    for i, p in enumerate(players, start=1):
        m = p["mastery"]
        weapon_name = _friendly_weapon_name(m["best_weapon"])
        lines.append(
            f"{i}. **{p['name']}** — {weapon_name} Lv.{m['best_weapon_level']} "
            f"({m['best_weapon_kills']} {get_translation(lang, 'kills')}) · {get_translation(lang, 'survival')} Lv.{m['survival_level']}"
        )
    chunk_size = 15
    for i in range(0, len(lines), chunk_size):
        embed.add_field(
            name=get_translation(lang, "mastery") if i == 0 else "\u200b",
            value="\n".join(lines[i:i + chunk_size]) or "None",
            inline=False,
        )
    if not_found:
        embed.add_field(
            name=f"⚠️ {get_translation(lang, 'not_found')}",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )
    embed.set_footer(text="Field names for this endpoint aren't fully documented by PUBG — flag me if numbers look off")
    return embed


SURVIVAL_TIER_NAMES = {
    5: "Tier 5",
    4: "Tier 4",
    3: "Tier 3",
    2: "Tier 2",
    1: "Tier 1",
}
SURVIVAL_TIER_ICON_FILES = {
    5: "survival_tier_5.png",
    4: "survival_tier_4.png",
    3: "survival_tier_3.png",
    2: "survival_tier_2.png",
    1: "survival_tier_1.png",
}
SURVIVAL_TIER_ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")


def _survival_tier_number(value) -> int:
    """Normalize the API's survival tier value to 1-5."""
    if isinstance(value, dict):
        value = value.get("tier", value.get("Tier", 0))
    try:
        tier = int(value)
    except (TypeError, ValueError):
        tier = 0
    return tier if tier in SURVIVAL_TIER_NAMES else 0


def build_survival_mastery_embeds(
    guild_cfg: dict, guild_name: str, players: list[dict], not_found: list[str]
) -> tuple[list[discord.Embed], list[discord.File]]:
    title = guild_cfg.get("clan_name") or guild_name
    grouped = {tier: [] for tier in range(5, 0, -1)}
    unknown = []
    for player in players:
        mastery = player.get("mastery", {})
        tier = _survival_tier_number(mastery.get("survival_tier"))
        if tier in grouped:
            grouped[tier].append(player)
        else:
            unknown.append(player)

    for tier in grouped:
        grouped[tier].sort(
            key=lambda p: (
                p.get("mastery", {}).get("survival_level", 0),
                p.get("mastery", {}).get("survival_xp", 0),
                normalize_player_name(p.get("name", "")),
            ),
            reverse=True,
        )

    embeds: list[discord.Embed] = []
    files: list[discord.File] = []
    for tier in range(5, 0, -1):
        tier_players = grouped[tier]
        if not tier_players:
            continue
        filename = SURVIVAL_TIER_ICON_FILES[tier]
        path = os.path.join(SURVIVAL_TIER_ASSET_DIR, filename)
        file = None
        if os.path.exists(path):
            file = discord.File(path, filename=filename)
            files.append(file)
        # A missing icon file must not abort the whole report — post without
        # the thumbnail instead.
        embed = discord.Embed(
            title=f"{title} — Survival Mastery {SURVIVAL_TIER_NAMES[tier]}",
            description=f"**{len(tier_players)} player(s)** · Highest Survival Level first",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        if file is not None:
            embed.set_thumbnail(url=f"attachment://{filename}")
        lines = []
        for i, player in enumerate(tier_players, start=1):
            m = player.get("mastery", {})
            level = m.get("survival_level", 0)
            xp = m.get("survival_xp", 0)
            lines.append(f"{i}. **{player['name']}** — Lv.{level} ({xp:,} XP)")
        for start in range(0, len(lines), 15):
            embed.add_field(
                name="Players" if start == 0 else "\u200b",
                value="\n".join(lines[start:start + 15]),
                inline=False,
            )
        embed.set_footer(text="Stats from the official PUBG API · Survival Mastery")
        embeds.append(embed)

    if unknown:
        embed = discord.Embed(
            title=f"{title} — Survival Mastery (Tier unavailable)",
            color=discord.Color.dark_grey(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.description = "\n".join(
            f"**{p['name']}** — Lv.{p.get('mastery', {}).get('survival_level', 0)}" for p in unknown
        )
        embeds.append(embed)

    if not_found:
        embed = discord.Embed(
            title=f"{title} — Survival Mastery (Not Found)",
            color=discord.Color.dark_grey(),
        )
        embed.description = ", ".join(not_found[:25]) + (" ..." if len(not_found) > 25 else "")
        embeds.append(embed)

    return embeds, files


def build_leaderboard_embed(
    guild_id: int, guild_name: str, guild_cfg: dict, found: dict[str, dict], checked: int, pages: int, queue: str,
    mentions_enabled: bool = True
) -> discord.Embed:
    title = guild_cfg.get("clan_name") or guild_name
    embed = discord.Embed(
        title=f"{title} — Official Leaderboard ({queue.upper()} TPP)",
        description=(
            f"Checked the top {checked:,} ranked players ({pages} page(s)). "
            f"This is the official ladder — most players won't appear unless they're highly ranked."
        ),
        color=discord.Color.dark_gold(),
        timestamp=datetime.now(timezone.utc),
    )
    if not found:
        embed.add_field(name="No matches", value="Nobody on the roster is in the checked range.", inline=False)
        return embed

    ranked = sorted(found.values(), key=lambda e: e["rank"])
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = []
    for i, e in enumerate(ranked, start=1):
        discord_id = guild_cfg.get("discord_links", {}).get(normalize_player_name(e["name"]))
        who = f"<@{discord_id}>" if discord_id and mentions_enabled else f"**{e['name']}**"
        rank_str = medals.get(i, f"#{i}")
        lines.append(f"{rank_str} — Ladder #{e['rank']:,} — {who}")
    # Discord embed field values cap at 1024 chars; chunk if many roster
    # members land on the leaderboard at once.
    chunk_size = 20
    for i in range(0, len(lines), chunk_size):
        field_lines = lines[i : i + chunk_size]
        embed.add_field(
            name="🏆 Roster Members Found" if i == 0 else "\u200b",
            value="\n".join(field_lines) or "None",
            inline=False,
        )
    return embed


def build_feedback_prompt_embed() -> discord.Embed:
    from modules.config import SUPPORT_SERVER_URL
    embed = discord.Embed(
        title="👋 How is PUBG Tracker working for your clan?",
        description=(
            "We want to make sure the bot is giving your clan the best experience possible!\n\n"
            "• **How are the stats, digests, and reports working for you?**\n"
            "• **Have any feature requests, new report ideas, or suggestions?**\n"
            "• **Need custom schedule adjustments or clan modifications?**\n\n"
            "Click the **💬 Submit Feedback / Suggestions** button below to open a quick submission window, "
            f"or join our **[Discord Support Server]({SUPPORT_SERVER_URL})** to chat directly with the developer!"
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text="PUBG Clan Tracker · Community Feedback & Support")
    return embed


def build_chicken_dinner_embed(winners: list[tuple[str, dict]], is_automated: bool = False, total_wins: int = 0) -> discord.Embed:
    """
    Build a simple Chicken Dinner embed with grouped matches in a feed-style format.
    
    Args:
        winners: List of (player_name, match_data) tuples where match_data contains
                 kills, winPlace, match_id, etc.
        is_automated: Whether this is an automated alert (True) or manual check (False)
        total_wins: Running tally of total wins (for live-updating display)
    
    Returns:
        A Discord embed with simple feed-style formatting, grouped by match.
        Solo wins show "won a Chicken Dinner!" while squad wins show "won a Chicken Dinner together!"
        Dates are not displayed - matches are sorted by match_id.
    """
    from translations import get_translation
    # Use guild language if available, otherwise default to English
    # Note: This function doesn't receive guild_cfg, so we'll use a default
    lang = "en"  # Could be enhanced to fetch from guild config if needed
    
    if not winners:
        return discord.Embed(
            title="🥈 No Chicken Dinners",
            description=get_translation(lang, "no_wins_yet"),
            color=discord.Color.light_gray(),
            timestamp=datetime.now(timezone.utc),
        )
    
    # Group winners by match_id (players who won together)
    matches_dict = {}
    for name, data in winners:
        match_id = data.get("match_id", "unknown")
        if match_id not in matches_dict:
            matches_dict[match_id] = []
        matches_dict[match_id].append((name, data))
    
    # Sort matches by actual created_at timestamp (most recent first)
    matches_list = []
    for match_id, players in matches_dict.items():
        # Get created_at from first player in this match
        created_at = players[0][1].get("created_at")
        matches_list.append((match_id, players, created_at))
    matches_list.sort(key=lambda x: x[2] or "", reverse=True)
    
    # Build the embed with simple styling
    embed = discord.Embed(
        title=f"🍗 {get_translation(lang, 'chicken_dinner')}",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc),
    )
    
    # Create feed-style display - players who won together on the same line
    match_lines = []
    for match_id, players, created_at in matches_list:
        # Sort players alphabetically for consistent display
        players_sorted = sorted(players, key=lambda x: normalize_player_name(x[0]))
        
        # Build player list (names only, no kills)
        player_names = [name for name, _ in players_sorted]
        players_str = ", ".join(player_names)
        
        # Format: ◆ **Player1** won a Chicken Dinner! (solo)
        #         ◆ **Player1, Player2** won a Chicken Dinner together! (squad)
        if len(player_names) == 1:
            match_lines.append(f"◆ **{players_str}** won a Chicken Dinner!")
        else:
            match_lines.append(f"◆ **{players_str}** won a Chicken Dinner together!")
    
    # Limit to most recent 10 wins to avoid embed overflow
    match_lines = match_lines[:10]
    
    # Add the matches as a single field
    embed.add_field(
        name=get_translation(lang, "recent_squad_wins"),
        value="\n".join(match_lines),
        inline=False,
    )
    
    # Add total wins summary
    embed.add_field(
        name=get_translation(lang, "total_wins_today"),
        value=f"**{total_wins}**",
        inline=True,
    )
    
    # Footer based on whether it's automated or manual
    if is_automated:
        embed.set_footer(text=get_translation(lang, "chicken_dinner_footer"))
    else:
        embed.set_footer(text="Manual check · Last 5 matches per player")
    
    return embed
