"""
PUBG Clan Tracker Discord Bot

Slash commands:
  /addplayer <name>        - add a PUBG player name to this server's roster
  /addplayers <names>       - add many players at once (comma or newline separated)
  /removeplayer <name>     - remove a player from the roster
  /roster                  - list tracked players
  /clanstats                - aggregated lifetime stats for the whole roster
  /leaderboard              - roster sorted by kills (or wins/kd, see options)
  /setgamemode <mode>       - squad-fpp, squad, duo-fpp, duo, solo-fpp, solo
  /setclan <member_name>    - set the clan using a PUBG member's in-game name
  /clanlevel                - show the current clan level and weekly progress
  /setclanchannel           - set current channel for the weekly clan-level report
  /setclantime <day> <hour> - set the weekly Eastern-time clan-level schedule
  /survivalstats             - show roster Survival Mastery grouped by tier
  /setsurvivalchannel        - set current channel for the weekly Survival Mastery report
  /setsurvivaltime <day> <hour> - set the weekly Eastern-time Survival Mastery schedule
  /reporttoggle <report> <enabled> - turn a scheduled report on or off
  /reportstatus              - show this server's report schedules and next run times
  /setstatuschannel           - set current channel for live bot status updates
  /help                     - show help and the official support server
  /donate                   - show the optional donation link
  /setdonationchannel       - enable the weekly Sunday donation post here
  /setdonationtime <0-23>   - choose its Sunday Eastern-time posting time
  /setchannel               - set current channel as the auto-post channel
  /setinterval <hours>      - how often (in hours) the digest auto-posts (default 6)
  /setdigesttime <0-23>      - post digest daily at a fixed Eastern-time hour instead
  /postnow                  - manually trigger a digest post immediately
  /lastactive                - show when each roster player last played, right now
  /setactivitychannel        - set current channel for the 24h "last active" report
  /setactivitytime <0-23>     - fixed Eastern-time hour for the last-active report
  /rankedsquad                 - show current-season ranked Squad TPP standings
  /rankedduo                   - show current-season ranked Duo TPP standings
  /rankedsolo                  - show current-season ranked Solo TPP standings
  /rankedsquadfpp              - show current-season ranked Squad FPP standings
  /rankedduofpp                - show current-season ranked Duo FPP standings
  /rankedsolofpp               - show current-season ranked Solo FPP standings
  /refreshrankedcache           - make the next ranked command rescan the roster
  /setrankedchannel           - set current channel for the 24h ranked TPP report
  /setrankedqueue <queue>      - choose the single TPP or FPP queue for daily reports
  /setrankedtime <0-23>         - fixed Eastern-time hour for the ranked report
  /dailyhighlights              - last-24h fun-title awards + top 10 + human/bot kills, right now
  /sethighlightschannel          - set current channel for the 24h highlights report
  /sethighlightstime <0-23>       - fixed Eastern-time hour for the highlights report
  /masterystats                     - top weapon mastery + survival level per player (on-demand only, slow)
  /leaderboardstats [pages]          - check official leaderboard for roster placements (on-demand only)
  /setleaderboardregion               - platform-region shard for leaderboard lookups (default pc-na)
  /setleaderboardqueue                - squad, duo, or solo (TPP) for leaderboard lookups
  /linkme <pubg_name>                   - link your Discord account to a PUBG name (shows as a mention on /leaderboardstats and lets you /unlinkme it later)
  /linkplayer <member> <pubg_name>       - link someone else's Discord account to a PUBG name (open to anyone)
  /unlinkme <pubg_name>                - remove a Discord-to-PUBG-name link
  /links                                - show every PUBG-name-to-Discord link for this server
  /chickendinner                        - check the roster's most recent matches for wins right now
  /setchickendinnerchannel               - set current channel for win alerts (defaults to the digest channel)
  /pingtoggle                           - toggle mention notifications for achievement awards
  /botservers                          - [Admin] list all Discord servers the bot is in
  /askfeedback [channel] [secret_key]  - [Admin] post feedback & support prompt to a server channel

Report identity behavior:
  Reports never post a separate per-player message and never @mention/ping
  anyone. The only place a link (/linkme) still shows up is a non-pinging
  <@id> mention in place of the plain name on /leaderboardstats results.

Setup:
  1. pip install -r requirements.txt
  2. Copy .env.example to .env and fill in DISCORD_TOKEN and PUBG_API_KEY
  3. Enable Server Members Intent in Discord Developer Portal for avatar functionality
  4. python bot.py
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

import storage
from pubg_api import PubgApiError, PubgClient

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
PUBG_API_KEY = os.environ["PUBG_API_KEY"]
PUBG_SHARD = os.environ.get("PUBG_SHARD", "steam")
BOT_ADMIN_KEY = os.environ.get("BOT_ADMIN_KEY", "")
ADMIN_USER_IDS = {int(x.strip()) for x in os.environ.get("ADMIN_USER_IDS", "").split(",") if x.strip().isdigit()}
SUPPORT_SERVER_URL = "https://discord.gg/KEUWmwBYV4"
SUPPORT_SERVER_ID = int(os.environ.get("SUPPORT_SERVER_ID", "1539320166318481459"))
SUPPORT_FEEDBACK_CHANNEL_ID = int(os.environ.get("SUPPORT_FEEDBACK_CHANNEL_ID", "0"))
DONATION_URL = "https://ko-fi.com/creighvan"
BUY_ME_A_COFFEE_URL = "https://buymeacoffee.com/creighvan"
DONATION_MESSAGE = (
    "☕ **Support PUBG Tracker Development**\n\n"
    "PUBG Tracker is completely free to use and will remain so. Your donations help keep the bot running and enable continued development:\n"
    "• 🖥️ Server hosting and maintenance\n"
    "• 🚀 New features and improvements\n"
    "• 🐛 Bug fixes and stability updates\n"
    "• 📈 PUBG API access and rate limits\n"
    "• 🎮 Future free bot projects\n\n"
    "❤️ **Why donate?**\n"
    "Even small amounts make a big difference in keeping this project alive and improving it for everyone. Your support directly powers the servers and development time.\n\n"
    "🎁 **What you get:**\n"
    "Donations are voluntary and don't provide special bot features, but you'll have our eternal gratitude and help ensure PUBG Tracker stays free for everyone!\n\n"
    "☕ **Support the project:**\n"
    f"• Ko-Fi: {DONATION_URL}\n"
    f"• Buy Me a Coffee: {BUY_ME_A_COFFEE_URL}\n\n"
    "Thank you for considering supporting PUBG Tracker! 🙏"
)

VALID_GAME_MODES = {"squad-fpp", "squad", "duo-fpp", "duo", "solo-fpp", "solo"}
RANKED_MODE_LABELS = {
    "squad": "Squad",
    "duo": "Duo",
    "solo": "Solo",
    "squad-fpp": "Squad",
    "duo-fpp": "Duo",
    "solo-fpp": "Solo",
}

# America/New_York rather than a fixed UTC-5 offset, so this automatically
# tracks EST/EDT across daylight saving changes instead of drifting an hour
# twice a year.
EASTERN = ZoneInfo("America/New_York")

intents = discord.Intents.default()
intents.members = True  # Required for guild.get_member() and guild.fetch_member() for avatars


class GuildOnlyTree(app_commands.CommandTree):
    """Every command is server-only. Using one in a DM previously crashed
    with a confusing error (reports need a server's channels); this gives a
    clear message instead."""

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        if interaction.guild_id is None:
            raise app_commands.NoPrivateMessage(
                "This command only works inside a Discord server — try it there instead."
            )
        return True


bot = commands.Bot(command_prefix="!", intents=intents, tree_cls=GuildOnlyTree)
pubg = PubgClient(PUBG_API_KEY, shard=PUBG_SHARD)

# Serializes the four scheduled reports so they never run concurrently
# against the PUBG API — running all four at once was overwhelming the
# real PUBG rate limit even though each report respects it individually.
_scheduler_lock = asyncio.Lock()
_commands_synced_once = False
_command_templates = None
_bot_ready_once = False
_bot_started_at = datetime.now(timezone.utc)

# ---------- live status feed ----------
# A rolling in-memory log of notable events (connect/disconnect, guild
# join/leave, a scheduled report failing, PUBG rate-limit hits). Resets on
# restart by design — this is a live feed, not a persisted audit log.
# /setstatuschannel points a channel at a single persistent embed message
# that gets EDITED in place whenever something happens, rather than a new
# message being posted every time.
_status_events: list[dict] = []
_STATUS_LOG_LIMIT = 12
_status_broadcast_lock = asyncio.Lock()
_last_status_broadcast_at: datetime | None = None
_STATUS_MIN_INTERVAL_SECONDS = 15  # collapses bursts (e.g. several reports failing at once) into one edit


async def _record_status_event(text: str) -> None:
    """Log an event and push it to every configured status channel (debounced)."""
    _status_events.append({"at": datetime.now(timezone.utc), "text": text})
    del _status_events[: -_STATUS_LOG_LIMIT]
    await _refresh_all_status_messages()


def _build_status_embed() -> discord.Embed:
    now = datetime.now(timezone.utc)
    uptime = now - _bot_started_at
    days, rem = divmod(int(uptime.total_seconds()), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    uptime_str = (f"{days}d " if days else "") + f"{hours}h {minutes}m"

    embed = discord.Embed(
        title="🟢 PUBG Tracker — Bot Status",
        description=(
            "Updates automatically whenever something notable happens — "
            "connects/disconnects, server joins/leaves, a report failing, "
            "or a PUBG API rate-limit hit. Not on a timer."
        ),
        color=discord.Color.green(),
        timestamp=now,
    )
    embed.add_field(name="Uptime", value=uptime_str, inline=True)
    embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)

    if _status_events:
        # Discord's <t:unix:R> renders as a live "5 minutes ago"-style
        # relative timestamp in the client, no manual formatting needed.
        lines = [f"<t:{int(e['at'].timestamp())}:R> {e['text']}" for e in reversed(_status_events)]
        embed.add_field(name="Recent Events", value="\n".join(lines)[:1024], inline=False)
    else:
        embed.add_field(name="Recent Events", value="No events recorded yet since this message was created.", inline=False)

    embed.set_footer(text="This message is edited in place, not reposted.")
    return embed


async def _push_status_message(guild_id: int, guild_cfg: dict, channel_id: int) -> None:
    channel = bot.get_channel(channel_id)
    if channel is None:
        return
    embed = _build_status_embed()
    message = None
    message_id = guild_cfg.get("status_message_id")
    if message_id:
        try:
            message = await channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            message = None  # deleted/inaccessible — fall through and post a fresh one
    try:
        if message is not None:
            await message.edit(embed=embed)
        else:
            new_message = await channel.send(embed=embed)
            guild_cfg["status_message_id"] = new_message.id
            await storage.save_guild(guild_id, guild_cfg)
    except discord.HTTPException as e:
        print(f"[status] Could not update status message for guild {guild_id}: {e}")


async def _refresh_all_status_messages(force: bool = False) -> None:
    """
    Pushes the current status embed to every guild that has configured a
    status channel. Debounced to at most once every _STATUS_MIN_INTERVAL_SECONDS
    so a burst of events (e.g. several reports failing back to back) collapses
    into a single edit instead of hammering Discord's edit-rate limit.
    """
    global _last_status_broadcast_at
    now = datetime.now(timezone.utc)
    async with _status_broadcast_lock:
        if not force and _last_status_broadcast_at is not None:
            if (now - _last_status_broadcast_at).total_seconds() < _STATUS_MIN_INTERVAL_SECONDS:
                return
        _last_status_broadcast_at = now

    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        channel_id = guild_cfg.get("status_channel_id")
        if channel_id is None:
            continue
        await _push_status_message(guild_id, guild_cfg, channel_id)


async def _on_pubg_rate_limited(delay_seconds: float) -> None:
    """Called by pubg_api.py only when PUBG itself returns a 429 — not on
    the routine self-imposed pacing wait, which happens on nearly every
    call and isn't an 'issue'."""
    await _record_status_event(f"⏳ PUBG API rate-limited us — pausing {delay_seconds:.0f}s then retrying")


pubg.on_rate_limit_hit = _on_pubg_rate_limited


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """
    Global safety net for slash-command errors. The per-command try/except
    blocks only catch errors that happen INSIDE our own code, starting at
    interaction.response.defer(). Anything that goes wrong before that —
    e.g. Discord's own parameter validation (like the 'pages' range on
    /leaderboardstats), a permission check, or any other error in the
    dispatch path — happens outside those blocks entirely. Without this
    handler, discord.py just logs those quietly and Discord shows
    "The application did not respond" with no way to know why. This
    ensures every command always gets SOME reply.
    """
    cmd_name = interaction.command.name if interaction.command else "unknown"
    print(f"[app_command_error] /{cmd_name}: {error}")
    message = f"Something went wrong running this command: {error}"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except Exception as e:
        # The interaction token may already be expired/invalid at this
        # point — nothing more we can do but log it.
        print(f"[app_command_error] Also failed to notify the user: {e}")


# ---------- helpers ----------

def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _is_due(guild_cfg: dict, hour_key: str, minute_key: str, posted_at_key: str, default_interval_hours: int) -> bool:
    """
    Two scheduling modes, chosen per-report:
    - If hour_key is set (0-23): post once per Eastern calendar day, at that
      Eastern-time hour:minute (minute_key, 0/15/30/45). Uses a 15-minute
      match window rather than exact equality, since the scheduler loop
      itself only ticks every 15 minutes and its phase isn't necessarily
      aligned to :00/:15/:30/:45 on the wall clock — the window guarantees
      exactly one tick lands in range regardless of that offset.
    - If hour_key is None (default): fall back to the old "every N hours
      since last post" behavior, using default_interval_hours (or
      guild_cfg["post_interval_hours"] for the digest specifically).
    """
    target_hour = guild_cfg.get(hour_key)
    posted_at = guild_cfg.get(posted_at_key)

    if target_hour is not None:
        target_minute = guild_cfg.get(minute_key, 0)
        now_est = datetime.now(EASTERN)
        target_total = target_hour * 60 + target_minute
        now_total = now_est.hour * 60 + now_est.minute
        if not (target_total <= now_total < target_total + 15):
            return False
        if not posted_at:
            return True
        posted_est = datetime.fromisoformat(posted_at).astimezone(EASTERN)
        return posted_est.date() != now_est.date()

    now = datetime.now(timezone.utc)
    interval_hours = guild_cfg.get("post_interval_hours", default_interval_hours) if hour_key == "digest_hour_est" else default_interval_hours
    if not posted_at:
        return True
    posted_dt = datetime.fromisoformat(posted_at)
    return now - posted_dt >= timedelta(hours=interval_hours)


def _is_weekly_due(
    guild_cfg: dict,
    weekday_key: str = "clan_weekday_est",
    hour_key: str = "clan_hour_est",
    minute_key: str = "clan_minute_est",
    posted_key: str = "clan_posted_at",
) -> bool:
    """Whether a configured weekly report is due this Eastern week."""
    weekday = guild_cfg.get(weekday_key)
    if weekday is None:
        return False
    now_est = datetime.now(EASTERN)
    target_minute = guild_cfg.get(hour_key, 0) * 60 + guild_cfg.get(minute_key, 0)
    now_minute = now_est.hour * 60 + now_est.minute
    # Due any time AFTER the target time on the scheduled weekday — not just
    # during the first 15 minutes. The posted marker is only written after a
    # successful post, so a failed attempt is retried on the next 15-minute
    # tick instead of silently skipping the whole week.
    if now_est.weekday() != weekday or now_minute < target_minute:
        return False
    posted_at = guild_cfg.get(posted_key)
    if not posted_at:
        return True
    posted_est = datetime.fromisoformat(posted_at).astimezone(EASTERN)
    return posted_est.isocalendar()[:2] != now_est.isocalendar()[:2]


def _is_sunday_donation_due(guild_cfg: dict) -> bool:
    """Whether this server's opt-in donation message is due this Sunday."""
    now_est = datetime.now(EASTERN)
    target_minute = guild_cfg.get("donation_hour_est", 12) * 60 + guild_cfg.get("donation_minute_est", 0)
    now_minute = now_est.hour * 60 + now_est.minute
    # Same retry rule as the other weekly reports: due any time after the
    # target time on Sunday, so a failed attempt retries instead of the
    # whole week being skipped.
    if now_est.weekday() != 6 or now_minute < target_minute:
        return False
    posted_at = guild_cfg.get("donation_posted_at")
    if not posted_at:
        return True
    posted_est = datetime.fromisoformat(posted_at).astimezone(EASTERN)
    return posted_est.isocalendar()[:2] != now_est.isocalendar()[:2]


def _as_eastern(iso_timestamp: str | None) -> datetime | None:
    if not iso_timestamp:
        return None
    try:
        return datetime.fromisoformat(iso_timestamp).astimezone(EASTERN)
    except (TypeError, ValueError):
        return None


def _format_eastern_time(when: datetime) -> str:
    return when.strftime("%A, %b %d at %I:%M %p %Z")


def _next_daily_report(hour: int, minute: int, posted_at: str | None) -> str:
    now = datetime.now(EASTERN)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    posted = _as_eastern(posted_at)
    has_posted_today = posted is not None and posted.date() == now.date()
    if target <= now < target + timedelta(minutes=15) and not has_posted_today:
        return "Due now (the scheduler checks about every 15 minutes)"
    if target <= now:
        target += timedelta(days=1)
    return _format_eastern_time(target)


def _next_interval_report(interval_hours: int, posted_at: str | None) -> str:
    posted = _as_eastern(posted_at)
    if posted is None:
        return "On the next scheduler check (within about 15 minutes)"
    next_time = posted + timedelta(hours=interval_hours)
    if next_time <= datetime.now(EASTERN):
        return "Due now (the scheduler checks about every 15 minutes)"
    return _format_eastern_time(next_time)


def _next_weekly_report(weekday: int, hour: int, minute: int, posted_at: str | None) -> str:
    now = datetime.now(EASTERN)
    days_until = (weekday - now.weekday()) % 7
    target = (now + timedelta(days=days_until)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    posted = _as_eastern(posted_at)
    posted_this_week = posted is not None and posted.isocalendar()[:2] == now.isocalendar()[:2]
    if days_until == 0 and target <= now and not posted_this_week:
        return "Due now (the scheduler checks about every 15 minutes)"
    if target <= now:
        target += timedelta(days=7)
    return _format_eastern_time(target)


def _channel_mention(channel_id: int | None) -> str:
    return f"<#{channel_id}>" if channel_id else "Not configured"


def build_report_status_embed(guild_cfg: dict) -> discord.Embed:
    """Summarize every automatic report configured for one Discord server."""
    embed = discord.Embed(
        title="📅 Scheduled Report Status",
        description="Only configured reports are scheduled. All times are Eastern and automatically follow EST/EDT.",
        color=discord.Color.blurple(),
    )

    disabled_reports = []
    digest_channel = guild_cfg.get("post_channel_id")
    if digest_channel and guild_cfg.get("digest_enabled", True):
        hour = guild_cfg.get("digest_hour_est")
        if hour is None:
            interval = guild_cfg.get("post_interval_hours", 6)
            schedule = f"Every {interval} hour(s)"
            next_time = _next_interval_report(interval, guild_cfg.get("last_post_at"))
        else:
            minute = guild_cfg.get("digest_minute_est", 0)
            schedule = f"Daily at {hour:02d}:{minute:02d} Eastern"
            next_time = _next_daily_report(hour, minute, guild_cfg.get("last_post_at"))
        embed.add_field(name="📊 Clan Digest", value=f"{_channel_mention(digest_channel)}\n{schedule}\n**Next:** {next_time}", inline=False)

    elif digest_channel:
        disabled_reports.append("Clan Digest")

    daily_reports = [
        ("🟢 Last Active", "activity_enabled", "last_activity_channel_id", "activity_hour_est", "activity_minute_est", "last_activity_posted_at", 24, None),
        ("🏆 Ranked", "ranked_enabled", "ranked_channel_id", "ranked_hour_est", "ranked_minute_est", "ranked_posted_at", 24, guild_cfg.get("ranked_queue", "squad")),
        ("✨ Daily Highlights", "highlights_enabled", "highlights_channel_id", "highlights_hour_est", "highlights_minute_est", "highlights_posted_at", 24, None),
    ]
    for name, enabled_key, channel_key, hour_key, minute_key, posted_key, interval, queue in daily_reports:
        channel_id = guild_cfg.get(channel_key) or digest_channel
        if not channel_id:
            continue
        if not guild_cfg.get(enabled_key, True):
            disabled_reports.append(name.replace("🟢 ", "").replace("🏆 ", "").replace("✨ ", ""))
            continue
        hour = guild_cfg.get(hour_key)
        if hour is None:
            schedule = f"Every {interval} hours"
            next_time = _next_interval_report(interval, guild_cfg.get(posted_key))
        else:
            minute = guild_cfg.get(minute_key, 0)
            schedule = f"Daily at {hour:02d}:{minute:02d} Eastern"
            next_time = _next_daily_report(hour, minute, guild_cfg.get(posted_key))
        if queue:
            schedule += f" · {RANKED_MODE_LABELS.get(queue, queue.title())} {'FPP' if queue.endswith('-fpp') else 'TPP'}"
        embed.add_field(name=name, value=f"{_channel_mention(channel_id)}\n{schedule}\n**Next:** {next_time}", inline=False)

    clan_channel = guild_cfg.get("clan_channel_id")
    clan_weekday = guild_cfg.get("clan_weekday_est")
    if clan_channel and clan_weekday is not None and guild_cfg.get("clan_level_enabled", True):
        hour = guild_cfg.get("clan_hour_est", 0)
        minute = guild_cfg.get("clan_minute_est", 0)
        weekday_name = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[clan_weekday]
        next_time = _next_weekly_report(clan_weekday, hour, minute, guild_cfg.get("clan_posted_at"))
        embed.add_field(name="🛡️ Clan Level", value=f"{_channel_mention(clan_channel)}\nEvery {weekday_name} at {hour:02d}:{minute:02d} Eastern\n**Next:** {next_time}", inline=False)
    elif clan_channel and clan_weekday is not None:
        disabled_reports.append("Clan Level")

    survival_channel = guild_cfg.get("survival_channel_id")
    survival_weekday = guild_cfg.get("survival_weekday_est")
    if survival_channel and survival_weekday is not None and guild_cfg.get("survival_enabled", True):
        hour = guild_cfg.get("survival_hour_est", 12)
        minute = guild_cfg.get("survival_minute_est", 0)
        weekday_name = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[survival_weekday]
        next_time = _next_weekly_report(survival_weekday, hour, minute, guild_cfg.get("survival_posted_at"))
        embed.add_field(name="🎖️ Survival Mastery", value=f"{_channel_mention(survival_channel)}\nEvery {weekday_name} at {hour:02d}:{minute:02d} Eastern\n**Next:** {next_time}", inline=False)
    elif survival_channel and survival_weekday is not None:
        disabled_reports.append("Survival Mastery")

    donation_channel = guild_cfg.get("donation_channel_id")
    if donation_channel and guild_cfg.get("donation_enabled", True):
        hour = guild_cfg.get("donation_hour_est", 12)
        minute = guild_cfg.get("donation_minute_est", 0)
        next_time = _next_weekly_report(6, hour, minute, guild_cfg.get("donation_posted_at"))
        embed.add_field(name="☕ Donation Message", value=f"{_channel_mention(donation_channel)}\nEvery Sunday at {hour:02d}:{minute:02d} Eastern\n**Next:** {next_time}", inline=False)
    elif donation_channel:
        disabled_reports.append("Donation Message")

    if disabled_reports:
        embed.add_field(name="⛔ Disabled", value=", ".join(disabled_reports), inline=False)

    if not embed.fields:
        embed.description = "No automatic reports are configured yet. Use the `/set...channel` and `/set...time` commands to schedule one."
    embed.set_footer(text="Scheduler checks every 15 minutes; a report can post shortly after its shown time.")
    return embed


def build_clan_embed(guild_name: str, guild_cfg: dict, players: list[dict], not_found: list[str]) -> discord.Embed:
    game_mode = guild_cfg["game_mode"]
    title = guild_cfg.get("clan_name") or guild_name

    total_kills = sum(p["stats"].get("kills", 0) for p in players)
    total_wins = sum(p["stats"].get("wins", 0) for p in players)
    total_games = sum(p["stats"].get("roundsPlayed", 0) for p in players)
    total_damage = sum(p["stats"].get("damageDealt", 0.0) for p in players)

    embed = discord.Embed(
        title=f"{title} — Clan Report ({game_mode})",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="👥 Tracked players", value=str(len(players)), inline=True)
    embed.add_field(name="💀 Total kills", value=f"{total_kills:,}", inline=True)
    embed.add_field(name="🏆 Total wins", value=f"{total_wins:,}", inline=True)
    embed.add_field(name="📊 Win rate", value=f"{_safe_div(total_wins, total_games) * 100:.1f}%", inline=True)
    embed.add_field(name="🎯 Total damage", value=f"{total_damage:,.0f}", inline=True)
    embed.add_field(name="⚔️ Total matches", value=f"{total_games:,}", inline=True)

    ranked = sorted(players, key=lambda p: p["stats"].get("kills", 0), reverse=True)[:10]
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = []
    for i, p in enumerate(ranked, start=1):
        s = p["stats"]
        kd = _safe_div(s.get("kills", 0), max(s.get("roundsPlayed", 0) - s.get("wins", 0), 1))
        rank_str = medals.get(i, f"{i}.")
        lines.append(f"{rank_str} **{p['name']}** — {s.get('kills', 0):,} kills, {s.get('wins', 0)} wins, {kd:.2f} K/D")
    if lines:
        embed.add_field(name="🔝 Top Fraggers", value="\n".join(lines), inline=False)

    if not_found:
        embed.add_field(
            name="⚠️ Not found",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )

    embed.set_footer(text="Stats from the official PUBG API · lifetime, per game mode")
    return embed


async def fetch_clan_report(guild_id: int, guild_name: str) -> tuple[discord.Embed, list[dict]] | None:
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await pubg.get_players_and_stats(guild_cfg["players"], game_mode=guild_cfg["game_mode"])
    embed = build_clan_embed(guild_name, guild_cfg, players, not_found)
    return embed, players


def build_clan_level_embed(guild_cfg: dict, clan: dict) -> discord.Embed:
    """Build the weekly clan-level report from the official clan endpoint."""
    embed = discord.Embed(
        title=f"{clan['name']} — Clan Level & Weekly Progress",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Clan", value=f"**{clan['name']}**\nTag: `{clan['tag']}`", inline=True)
    embed.add_field(name="Current Level", value=str(clan["level"]), inline=True)
    embed.add_field(name="Members", value=str(clan["member_count"]), inline=True)

    previous_level = guild_cfg.get("clan_last_level")
    previous_members = guild_cfg.get("clan_last_member_count")
    if previous_level is None:
        progress = "This is the first clan snapshot. The next weekly report will show the level change."
    else:
        level_change = clan["level"] - previous_level
        member_change = clan["member_count"] - previous_members if previous_members is not None else 0
        progress = f"Level change since last weekly report: **{level_change:+d}**"
        if previous_members is not None:
            progress += f" · Member change: **{member_change:+d}**"
    embed.add_field(name="Weekly Progress", value=progress, inline=False)
    embed.add_field(
        name="Important",
        value=(
            "PUBG exposes the clan level and member count, but not the XP needed for the next level. "
            "Progress is therefore measured by the change in clan level between weekly reports."
        ),
        inline=False,
    )
    embed.set_footer(text="Weekly Clan Progress · Official PUBG API")
    return embed


async def fetch_clan_level_report(guild_id: int) -> tuple[discord.Embed, dict] | None:
    guild_cfg = await storage.get_guild(guild_id)
    clan_id = guild_cfg.get("pubg_clan_id")
    if not clan_id:
        return None
    clan = await pubg.get_clan_by_id(clan_id)
    return build_clan_level_embed(guild_cfg, clan), clan


def _format_time_ago(iso_str: str | None) -> str:
    if not iso_str:
        return "No recent matches found"
    then = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    delta = datetime.now(timezone.utc) - then
    hours = delta.total_seconds() / 3600
    if hours < 1:
        return "< 1 hour ago"
    if hours < 24:
        return f"{int(hours)} hour(s) ago"
    return f"{int(hours // 24)} day(s) ago"


def build_last_active_embed(guild_id: int, guild_name: str, guild_cfg: dict, players: list[dict], not_found: list[str], protected_players: list[str] = None) -> discord.Embed:
    title = guild_cfg.get("clan_name") or guild_name
    protected_lower = [p.lower().strip() for p in (protected_players or [])]
    
    embed = discord.Embed(
        title=f"{title} — Last Active Report",
        description=(
            "PUBG's API doesn't expose login history, so this shows the time "
            "of each player's most recent **match**, which is the closest "
            "available signal for \"last played.\""
        ),
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
    protected_count = len(protected_players or [])
    
    embed.add_field(name="🟢 Active last 24h", value=str(active_24h), inline=True)
    embed.add_field(name="👥 Tracked players", value=str(len(players)), inline=True)
    if protected_count > 0:
        embed.add_field(name="🛡️ Protected players", value=str(protected_count), inline=True)

    lines = []
    for p in players:
        # Check for manual inactive date override
        manual_date = guild_cfg.get("manual_inactive_dates", {}).get(p["name"].lower())
        if manual_date:
            match_date = manual_date
            source_note = " *(manual)*"
        else:
            match_date = p.get("last_match_at")
            source_note = ""
        
        recency = _recency_emoji(match_date)
        # Case-insensitive comparison for protected players
        player_lower = p["name"].lower().strip()
        is_protected = player_lower in protected_lower
        protected_mark = " 🛡️" if is_protected else ""
        lines.append(f"{recency} **{p['name']}**{protected_mark} — {_format_time_ago(match_date)}{source_note}")
    
    # Discord embed fields cap at 1024 chars; chunk if the roster is large.
    chunk_size = 20
    for i in range(0, len(lines), chunk_size):
        field_lines = lines[i : i + chunk_size]
        embed.add_field(
            name="Players" if i == 0 else "\u200b",
            value="\n".join(field_lines) or "None",
            inline=False,
        )
    if not_found:
        embed.add_field(
            name="⚠️ Not found",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )
    if protected_count > 0:
        embed.set_footer(text="🛡️ = Protected from inactivity removal (PUBG API: 14-day limit, use /setinactivedate for historical data)")
    return embed


async def fetch_last_active_report(guild_id: int, guild_name: str) -> tuple[discord.Embed, list[dict]] | None:
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await pubg.get_last_active_times(guild_cfg["players"])
    
    # Note: OP.GG scraping disabled due to website structure changes and blocking
    # Historical data beyond 14 days is now handled via manual inactive dates
    # The PUBG API has a hard 14-day limit for match data retention
    
    protected_players = await storage.get_protected_players(guild_id)
    return build_last_active_embed(guild_id, guild_name, guild_cfg, players, not_found, protected_players), players


def build_ranked_embed(guild_name: str, guild_cfg: dict, players: list[dict], not_found: list[str], game_mode: str) -> discord.Embed:
    title = guild_cfg.get("clan_name") or guild_name
    queue_label = f"{RANKED_MODE_LABELS[game_mode]} {'FPP' if game_mode.endswith('-fpp') else 'TPP'}"
    embed = discord.Embed(
        title=f"{title} — Ranked ({queue_label})",
        description="Current-season competitive ranked standings.",
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc),
    )

    ranked_players = [p for p in players if p.get("ranked", {}).get("currentTier") is not None]
    if ranked_players:
        top = ranked_players[0]
        top_tier = top["ranked"]["currentTier"]
        top_tier_name = f"{top_tier.get('tier', '?')} {top_tier.get('subTier', '')}".strip()
        embed.add_field(name="🏅 Highest Ranked", value=f"**{top['name']}** — {top_tier_name}", inline=True)
    embed.add_field(name="👥 Ranked this season", value=f"{len(ranked_players)}/{len(guild_cfg['players'])}", inline=True)

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
            embed.add_field(name="Ranking" if i == 0 else "\u200b", value="\n".join(lines[i:i + 15]), inline=False)
    else:
        embed.add_field(name="No ranked matches", value="No tracked players have ranked matches in this queue this season.", inline=False)
    if not_found:
        embed.add_field(
            name="⚠️ Not found",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )
    embed.set_footer(text="Stats from the official PUBG API · ranked, current season")
    return embed


async def fetch_ranked_report(guild_id: int, guild_name: str, game_mode: str | None = None) -> tuple[discord.Embed, list[dict]] | None:
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    game_mode = game_mode or guild_cfg.get("ranked_queue", "squad")
    known_by_mode = guild_cfg.get("ranked_known_players", {})
    # The first report for a queue must scan the roster because PUBG has no
    # ranked-player filter. Later reports only recheck players previously
    # found in that queue, keeping a large clan roster fast and API-friendly.
    names_to_check = known_by_mode.get(game_mode)
    if names_to_check is None:
        names_to_check = guild_cfg["players"]
    players, not_found = await pubg.get_ranked_report(names_to_check, game_mode)
    if game_mode not in known_by_mode:
        guild_cfg["ranked_known_players"] = dict(known_by_mode)
        guild_cfg["ranked_known_players"][game_mode] = [
            p["name"] for p in players if p.get("ranked", {}).get("currentTier") is not None
        ]
        await storage.save_guild(guild_id, guild_cfg)
    embed = build_ranked_embed(guild_name, guild_cfg, players, not_found, game_mode)
    return embed, players


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
    title = guild_cfg.get("clan_name") or guild_name
    active_players = [p for p in players if p["daily"]["matches"] > 0]

    embed = discord.Embed(
        title=f"{title} — Last {hours}h Highlights",
        description=f"Based on {len(active_players)} player(s) who played in the last {hours} hours.",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc),
    )

    if not active_players:
        # Check if players have expired matches (telemetry unavailable after 14 days)
        expired_count = sum(1 for p in players if p.get("_expired_matches", 0) > 0)
        if expired_count > 0:
            embed.add_field(
                name="No recent matches available",
                value=f"PUBG match telemetry is only available for the last 14 days. {expired_count} player(s) have older matches that can't be analyzed.",
                inline=False
            )
        else:
            embed.add_field(name="No matches played", value="Nobody on the roster played in this window.", inline=False)
        return embed

    for emoji, label, winner_name, val_str in _compute_award_winners(active_players):
        embed.add_field(name=f"{emoji} {label}", value=f"**{winner_name}** — {val_str}", inline=True)

    # Top 10 overall, ranked by kills, with human/bot kill split
    lines = []
    for i, p in enumerate(active_players[:10], start=1):
        d = p["daily"]
        lines.append(
            f"{i}. **{p['name']}** — {d['kills']} kills ({d['human_kills']} human / {d['bot_kills']} bot), "
            f"{d['damageDealt']:,.0f} dmg, {d['wins']}W, {d['matches']} match(es)"
        )
    embed.add_field(name="Top 10", value="\n".join(lines), inline=False)

    if not_found:
        embed.add_field(
            name="⚠️ Not found",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )
    embed.set_footer(text="Human vs bot kills come from match telemetry (PUBG tags bot accounts internally)")
    return embed


async def fetch_highlights_report(guild_id: int, guild_name: str, hours: int = 24) -> tuple[discord.Embed, list[dict]] | None:
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    try:
        players, not_found = await pubg.get_daily_activity_report(guild_cfg["players"], hours=hours)
    except PubgApiError as e:
        # Provide better error message for telemetry availability issues
        if "telemetry" in str(e).lower() or "404" in str(e):
            embed = discord.Embed(
                title=f"{guild_name} — Highlights Unavailable",
                description="No matches found in the last 14 days. PUBG match telemetry is only available for the last 14 days, so highlights reports cannot be generated for older matches.",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc),
            )
            return embed, []
        raise
    embed = build_highlights_embed(guild_name, guild_cfg, players, not_found, hours)
    return embed, players


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
    title = guild_cfg.get("clan_name") or guild_name
    embed = discord.Embed(
        title=f"{title} — Weapon & Survival Mastery",
        description="Each player's highest-level weapon and overall survival mastery.",
        color=discord.Color.dark_teal(),
        timestamp=datetime.now(timezone.utc),
    )

    weapon_leader = max(players, key=lambda p: p["mastery"].get("best_weapon_level", 0), default=None)
    survival_leader = max(players, key=lambda p: p["mastery"].get("survival_level", 0), default=None)
    if weapon_leader:
        w = weapon_leader["mastery"]
        embed.add_field(
            name="🔫 Top Weapon Mastery",
            value=f"**{weapon_leader['name']}** — {_friendly_weapon_name(w['best_weapon'])} Lv.{w['best_weapon_level']}",
            inline=True,
        )
    if survival_leader:
        embed.add_field(
            name="🎖️ Top Survival Level",
            value=f"**{survival_leader['name']}** — Lv.{survival_leader['mastery']['survival_level']}",
            inline=True,
        )

    lines = []
    for i, p in enumerate(players, start=1):
        m = p["mastery"]
        weapon_name = _friendly_weapon_name(m["best_weapon"])
        lines.append(
            f"{i}. **{p['name']}** — {weapon_name} Lv.{m['best_weapon_level']} "
            f"({m['best_weapon_kills']} kills) · Survival Lv.{m['survival_level']}"
        )
    chunk_size = 15
    for i in range(0, len(lines), chunk_size):
        embed.add_field(
            name="Mastery" if i == 0 else "\u200b",
            value="\n".join(lines[i:i + chunk_size]) or "None",
            inline=False,
        )
    if not_found:
        embed.add_field(
            name="⚠️ Not found",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )
    embed.set_footer(text="Field names for this endpoint aren't fully documented by PUBG — flag me if numbers look off")
    return embed


async def fetch_mastery_report(guild_id: int, guild_name: str) -> tuple[discord.Embed, list[dict]] | None:
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await pubg.get_mastery_report(guild_cfg["players"])
    return build_mastery_embed(guild_name, guild_cfg, players, not_found), players


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
SURVIVAL_TIER_ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")


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
                p.get("name", "").lower(),
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


async def fetch_survival_mastery_report(
    guild_id: int, guild_name: str
) -> tuple[list[discord.Embed], list[discord.File]] | None:
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await pubg.get_mastery_report(guild_cfg["players"])
    return build_survival_mastery_embeds(guild_cfg, guild_name, players, not_found)


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
        discord_id = guild_cfg.get("discord_links", {}).get(e["name"].lower())
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


async def fetch_leaderboard_report(
    guild_id: int, guild_name: str, max_pages: int = 4
) -> tuple[discord.Embed, dict[str, dict]] | None:
    guild_cfg = await storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    queue = guild_cfg.get("leaderboard_queue", "squad")
    season_id = await pubg.get_current_season_id()
    found, checked = await pubg.get_leaderboard_placements(
        guild_cfg["players"], season_id, game_mode=queue,
        max_pages=max_pages, leaderboard_shard=guild_cfg.get("leaderboard_shard", "pc-na"),
    )
    mentions_enabled = guild_cfg.get("mentions_enabled", True)
    embed = build_leaderboard_embed(guild_id, guild_name, guild_cfg, found, checked, max_pages, queue, mentions_enabled)
    return embed, found


# ---------- lifecycle ----------

async def _sync_guild_commands(guild: discord.Guild) -> int:
    """Replace one guild's command set with the current command templates."""
    bot.tree.clear_commands(guild=guild)
    for command in _command_templates or []:
        bot.tree.add_command(command, guild=guild, override=True)
    synced = await bot.tree.sync(guild=guild)
    return len(synced)

@bot.event
async def on_ready():
    global _commands_synced_once, _command_templates, _bot_ready_once
    try:
        if not _commands_synced_once:
            # Guild commands are available immediately. Each sync bulk-replaces
            # that guild's command list, so stale commands cannot accumulate.
            _command_templates = bot.tree.get_commands()
            for guild in bot.guilds:
                count = await _sync_guild_commands(guild)
                print(f"Instantly synced {count} commands to guild {guild.name} ({guild.id})")

            # Remove the old global command set. Keeping it alongside the
            # immediate guild commands can make old/global command versions
            # appear in Discord while propagation catches up.
            bot.tree.clear_commands(guild=None)
            await bot.tree.sync()
            _commands_synced_once = True
    except Exception as e:
        # A sync hiccup here should NEVER prevent the scheduled reports
        # below from starting — this used to be able to silently kill
        # every auto-post if this step threw, since the task-start code
        # was unreachable after an unhandled exception here.
        print(f"[on_ready] Command sync failed (scheduled reports will still start): {e}")
    if not auto_digest.is_running():
        auto_digest.start()
    if not auto_last_active.is_running():
        auto_last_active.start()
    if not auto_ranked.is_running():
        auto_ranked.start()
    if not auto_highlights.is_running():
        auto_highlights.start()
    if not auto_clan_level.is_running():
        auto_clan_level.start()
    if not auto_survival_mastery.is_running():
        auto_survival_mastery.start()
    if not auto_donations.is_running():
        auto_donations.start()
    if not auto_chicken_dinner.is_running():
        auto_chicken_dinner.start()
    if not auto_feedback_prompt.is_running():
        auto_feedback_prompt.start()
    bot.add_view(FeedbackPromptView())
    print(f"Logged in as {bot.user} (id={bot.user.id})")
    if not _bot_ready_once:
        _bot_ready_once = True
        await _record_status_event("🟢 Bot started and connected to Discord")


@bot.event
async def on_disconnect():
    await _record_status_event("🔴 Lost connection to Discord — reconnecting...")


@bot.event
async def on_resumed():
    await _record_status_event("🟢 Reconnected to Discord")


@bot.event
async def on_guild_join(guild: discord.Guild):
    """Make commands available immediately when the bot is invited somewhere new."""
    await _record_status_event(f"➕ Joined server: {guild.name}")
    if not _commands_synced_once:
        return
    try:
        count = await _sync_guild_commands(guild)
        print(f"Instantly synced {count} commands to newly joined guild {guild.name} ({guild.id})")
    except Exception as e:
        print(f"[on_guild_join] Command sync failed for guild {guild.id}: {e}")


@bot.event
async def on_guild_remove(guild: discord.Guild):
    await _record_status_event(f"➖ Removed from server: {guild.name}")


# ---------- scheduled task ----------

@tasks.loop(minutes=15)
async def auto_digest():
    """
    Every 15 minutes, checks whether each guild's digest is due — either
    a fixed Eastern-time hour (digest_hour_est) or the older interval-based
    behavior (post_interval_hours), depending on what's configured.
    """
    now = datetime.now(timezone.utc)
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("digest_enabled", True):
            continue
        channel_id = guild_cfg.get("post_channel_id")
        if channel_id is None:
            continue
        if not _is_due(guild_cfg, "digest_hour_est", "digest_minute_est", "last_post_at", 6):
            continue

        guild = bot.get_guild(guild_id)
        channel = bot.get_channel(channel_id)
        if guild is None or channel is None:
            continue
        # Mark the attempt now, before making any API calls — so a failure
        # (e.g. a transient rate limit) waits for the next full interval
        # instead of retrying on every 15-min check, which is what was
        # causing bursts and repeated rate-limit errors.
        guild_cfg["last_post_at"] = now.isoformat()
        await storage.save_guild(guild_id, guild_cfg)
        try:
            async with _scheduler_lock:
                result = await fetch_clan_report(guild_id, guild.name)
            if result:
                embed, players = result
                await channel.send(embed=embed)
        except PubgApiError as e:
            print(f"[auto_digest] PUBG API error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_digest report failed for guild {guild_id}: {e}"[:200])
        except Exception as e:
            print(f"[auto_digest] Unexpected error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_digest report failed for guild {guild_id}: {e}"[:200])


@auto_digest.before_loop
async def before_auto_digest():
    await bot.wait_until_ready()


@tasks.loop(minutes=15)
async def auto_last_active():
    """Posts the 'last active' report every 24 hours, per guild, same
    interval-based pattern as auto_digest."""
    now = datetime.now(timezone.utc)
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("activity_enabled", True):
            continue
        channel_id = guild_cfg.get("last_activity_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None:
            continue
        if not _is_due(guild_cfg, "activity_hour_est", "activity_minute_est", "last_activity_posted_at", 24):
            continue

        guild = bot.get_guild(guild_id)
        channel = bot.get_channel(channel_id)
        if guild is None or channel is None:
            continue
        guild_cfg["last_activity_posted_at"] = now.isoformat()
        await storage.save_guild(guild_id, guild_cfg)
        try:
            async with _scheduler_lock:
                result = await fetch_last_active_report(guild_id, guild.name)
            if result:
                embed, players = result
                await channel.send(embed=embed)
        except PubgApiError as e:
            print(f"[auto_last_active] PUBG API error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_last_active report failed for guild {guild_id}: {e}"[:200])
        except Exception as e:
            print(f"[auto_last_active] Unexpected error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_last_active report failed for guild {guild_id}: {e}"[:200])


@auto_last_active.before_loop
async def before_auto_last_active():
    await bot.wait_until_ready()


@tasks.loop(minutes=15)
async def auto_ranked():
    """Posts the ranked TPP report every 24 hours, per guild."""
    now = datetime.now(timezone.utc)
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("ranked_enabled", True):
            continue
        channel_id = guild_cfg.get("ranked_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None:
            continue
        if not _is_due(guild_cfg, "ranked_hour_est", "ranked_minute_est", "ranked_posted_at", 24):
            continue

        guild = bot.get_guild(guild_id)
        channel = bot.get_channel(channel_id)
        if guild is None or channel is None:
            continue
        guild_cfg["ranked_posted_at"] = now.isoformat()
        await storage.save_guild(guild_id, guild_cfg)
        try:
            async with _scheduler_lock:
                result = await fetch_ranked_report(guild_id, guild.name)
            if result:
                embed, players = result
                await channel.send(embed=embed)
                queue = guild_cfg.get("ranked_queue", "squad")
                queue_label = f"{RANKED_MODE_LABELS[queue]} {'FPP' if queue.endswith('-fpp') else 'TPP'}"
        except PubgApiError as e:
            print(f"[auto_ranked] PUBG API error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_ranked report failed for guild {guild_id}: {e}"[:200])
        except Exception as e:
            print(f"[auto_ranked] Unexpected error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_ranked report failed for guild {guild_id}: {e}"[:200])


@auto_ranked.before_loop
async def before_auto_ranked():
    await bot.wait_until_ready()


@tasks.loop(minutes=15)
async def auto_highlights():
    """
    Posts the 'last 24 hours' highlights report (fun titles + top 10 +
    human/bot kill split) every 24 hours, per guild. This is the heaviest
    report the bot runs (telemetry downloads), so it's worth giving it
    plenty of headroom rather than tightening the interval.
    """
    now = datetime.now(timezone.utc)
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("highlights_enabled", True):
            continue
        channel_id = guild_cfg.get("highlights_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None:
            continue
        if not _is_due(guild_cfg, "highlights_hour_est", "highlights_minute_est", "highlights_posted_at", 24):
            continue

        guild = bot.get_guild(guild_id)
        channel = bot.get_channel(channel_id)
        if guild is None or channel is None:
            continue
        guild_cfg["highlights_posted_at"] = now.isoformat()
        await storage.save_guild(guild_id, guild_cfg)
        try:
            async with _scheduler_lock:
                result = await fetch_highlights_report(guild_id, guild.name)
            if result:
                embed, players = result
                await channel.send(embed=embed)
        except PubgApiError as e:
            print(f"[auto_highlights] PUBG API error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_highlights report failed for guild {guild_id}: {e}"[:200])
        except Exception as e:
            print(f"[auto_highlights] Unexpected error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_highlights report failed for guild {guild_id}: {e}"[:200])


@auto_highlights.before_loop
async def before_auto_highlights():
    await bot.wait_until_ready()


@tasks.loop(minutes=15)
async def auto_clan_level():
    """Post the configured clan-level snapshot once per Eastern calendar week."""
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("clan_level_enabled", True):
            continue
        channel_id = guild_cfg.get("clan_channel_id")
        if channel_id is None or not _is_weekly_due(guild_cfg):
            continue

        channel = bot.get_channel(channel_id)
        if channel is None:
            continue
        try:
            async with _scheduler_lock:
                result = await fetch_clan_level_report(guild_id)
            if result is None:
                continue
            embed, clan = result
            await channel.send(embed=embed)
            # A snapshot only counts after Discord accepted the report.
            guild_cfg["clan_posted_at"] = datetime.now(timezone.utc).isoformat()
            guild_cfg["clan_last_level"] = clan["level"]
            guild_cfg["clan_last_member_count"] = clan["member_count"]
            await storage.save_guild(guild_id, guild_cfg)
        except PubgApiError as e:
            print(f"[auto_clan_level] PUBG API error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_clan_level report failed for guild {guild_id}: {e}"[:200])
        except Exception as e:
            print(f"[auto_clan_level] Unexpected error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_clan_level report failed for guild {guild_id}: {e}"[:200])


@auto_clan_level.before_loop
async def before_auto_clan_level():
    await bot.wait_until_ready()


@tasks.loop(minutes=15)
async def auto_survival_mastery():
    """Post the configured weekly Survival Mastery snapshot."""
    now = datetime.now(timezone.utc)
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("survival_enabled", True):
            continue
        channel_id = guild_cfg.get("survival_channel_id")
        if channel_id is None or not _is_weekly_due(
            guild_cfg,
            weekday_key="survival_weekday_est",
            hour_key="survival_hour_est",
            minute_key="survival_minute_est",
            posted_key="survival_posted_at",
        ):
            continue

        channel = bot.get_channel(channel_id)
        guild = bot.get_guild(guild_id)
        if channel is None or guild is None:
            continue
        try:
            async with _scheduler_lock:
                result = await fetch_survival_mastery_report(guild_id, guild.name)
            if result is None:
                continue
            embeds, files = result
            await channel.send(embeds=embeds, files=files)
            guild_cfg["survival_posted_at"] = now.isoformat()
            await storage.save_guild(guild_id, guild_cfg)
        except PubgApiError as e:
            print(f"[auto_survival_mastery] PUBG API error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_survival_mastery report failed for guild {guild_id}: {e}"[:200])
        except Exception as e:
            print(f"[auto_survival_mastery] Unexpected error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_survival_mastery report failed for guild {guild_id}: {e}"[:200])


@auto_survival_mastery.before_loop
async def before_auto_survival_mastery():
    await bot.wait_until_ready()


@tasks.loop(minutes=15)
async def auto_donations():
    """Post the optional donation link on Sunday for servers that opt in."""
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("donation_enabled", True):
            continue
        channel_id = guild_cfg.get("donation_channel_id")
        if channel_id is None or not _is_sunday_donation_due(guild_cfg):
            continue
        channel = bot.get_channel(channel_id)
        if channel is None:
            continue
        try:
            await channel.send(DONATION_MESSAGE)
            guild_cfg["donation_posted_at"] = datetime.now(timezone.utc).isoformat()
            await storage.save_guild(guild_id, guild_cfg)
        except Exception as e:
            print(f"[auto_donations] Could not post for guild {guild_id}: {e}")


@auto_donations.before_loop
async def before_auto_donations():
    await bot.wait_until_ready()


@tasks.loop(minutes=15)
async def auto_chicken_dinner():
    """
    Every 15 minutes, checks each opted-in guild's roster for new Chicken
    Dinners in players' most recent matches. Dedupes per player against
    chicken_dinner_posted_matches (pubg name -> last alerted match_id), so
    the same win isn't reposted every tick just because nobody has played a
    newer match since the last check.
    """
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("chicken_dinner_enabled", True):
            continue
        channel_id = guild_cfg.get("chicken_dinner_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None or not guild_cfg["players"]:
            continue
        guild = bot.get_guild(guild_id)
        channel = bot.get_channel(channel_id)
        if guild is None or channel is None:
            continue

        try:
            async with _scheduler_lock:
                results, _ = await pubg.get_recent_wins(guild_cfg["players"])
        except PubgApiError as e:
            print(f"[auto_chicken_dinner] PUBG API error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_chicken_dinner report failed for guild {guild_id}: {e}"[:200])
            continue
        except Exception as e:
            print(f"[auto_chicken_dinner] Unexpected error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_chicken_dinner report failed for guild {guild_id}: {e}"[:200])
            continue

        posted_matches = guild_cfg.get("chicken_dinner_posted_matches", {})
        updated_matches = dict(posted_matches)
        new_wins = []
        for name, data in results.items():
            if data.get("winPlace") != 1:
                continue
            match_id = data.get("match_id")
            key = name.lower()
            if match_id and posted_matches.get(key) == match_id:
                continue  # already alerted for this exact match
            new_wins.append((name, data))
            if match_id:
                updated_matches[key] = match_id

        if not new_wins:
            continue

        try:
            embed = discord.Embed(
                title="🍗 Chicken Dinner!",
                color=discord.Color.gold(),
                timestamp=datetime.now(timezone.utc),
            )
            for name, data in sorted(new_wins, key=lambda item: item[1].get("kills", 0), reverse=True)[:15]:
                map_name = data.get("map_name") or "Unknown map"
                embed.add_field(name=name, value=f"{data.get('kills', 0)} kills · {map_name}", inline=True)
            await channel.send(embed=embed)
            # Only record these matches as alerted once Discord actually
            # accepted the message — a failed send retries next tick
            # instead of silently losing the alert.
            guild_cfg["chicken_dinner_posted_matches"] = updated_matches
            await storage.save_guild(guild_id, guild_cfg)
        except Exception as e:
            print(f"[auto_chicken_dinner] Could not post for guild {guild_id}: {e}")


@auto_chicken_dinner.before_loop
async def before_auto_chicken_dinner():
    await bot.wait_until_ready()


@tasks.loop(minutes=30)
async def auto_feedback_prompt():
    """Posts a feedback prompt with an interactive modal button once every 14 days per guild."""
    now = datetime.now(timezone.utc)
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if guild_id == SUPPORT_SERVER_ID:
            continue

        last_prompt = guild_cfg.get("last_feedback_prompt_at")
        if last_prompt:
            try:
                last_dt = datetime.fromisoformat(last_prompt)
                if now - last_dt < timedelta(days=14):
                    continue
            except (ValueError, TypeError):
                pass

        guild = bot.get_guild(guild_id)
        if guild is None:
            continue

        channel_id = (
            guild_cfg.get("post_channel_id")
            or guild_cfg.get("clan_channel_id")
            or guild_cfg.get("highlights_channel_id")
            or guild_cfg.get("last_activity_channel_id")
        )
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel is None:
            channel = guild.system_channel or next(
                (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages),
                None,
            )
        if channel is None:
            continue

        guild_cfg["last_feedback_prompt_at"] = now.isoformat()
        await storage.save_guild(guild_id, guild_cfg)

        embed = build_feedback_prompt_embed()
        try:
            await channel.send(embed=embed, view=FeedbackPromptView())
            print(f"[auto_feedback] Posted 14-day feedback prompt to {guild.name} (#{channel.name})")
        except Exception as e:
            print(f"[auto_feedback] Failed to send prompt in {guild.name}: {e}")


@auto_feedback_prompt.before_loop
async def before_auto_feedback_prompt():
    await bot.wait_until_ready()


# ---------- slash commands ----------

@bot.tree.command(description="Add a PUBG player name to this server's tracked clan roster")
@app_commands.describe(name="Exact in-game PUBG name (case-insensitive)")
async def addplayer(interaction: discord.Interaction, name: str):
    added = await storage.add_player(interaction.guild_id, name)
    if added:
        await interaction.response.send_message(f"✅ Added **{name}** to the roster.")
    else:
        await interaction.response.send_message(f"**{name}** is already on the roster.", ephemeral=True)


@bot.tree.command(description="Add many PUBG players at once — paste names separated by commas or new lines")
@app_commands.describe(names="e.g. PlayerOne, PlayerTwo, PlayerThree (commas or newlines both work)")
async def addplayers(interaction: discord.Interaction, names: str):
    raw = names.replace("\n", ",").split(",")
    candidates = [n.strip() for n in raw if n.strip()]
    if not candidates:
        await interaction.response.send_message("Didn't find any names in that — separate them with commas or new lines.", ephemeral=True)
        return

    added, duplicates = await storage.add_players(interaction.guild_id, candidates)

    lines = [f"✅ Added **{len(added)}** player(s) to the roster."]
    if added:
        lines.append(", ".join(added))
    if duplicates:
        lines.append(f"⚠️ Skipped {len(duplicates)} already on the roster: " + ", ".join(duplicates))
    await interaction.response.send_message("\n".join(lines))


@bot.tree.command(description="Remove a player from this server's tracked clan roster")
@app_commands.describe(name="PUBG name to remove")
async def removeplayer(interaction: discord.Interaction, name: str):
    removed = await storage.remove_player(interaction.guild_id, name)
    if removed:
        await interaction.response.send_message(f"🗑️ Removed **{name}** from the roster.")
    else:
        await interaction.response.send_message(f"**{name}** wasn't on the roster.", ephemeral=True)


@bot.tree.command(description="Add a player to the protected list (immune to inactivity removal)")
@app_commands.describe(name="PUBG name to protect")
async def addprotected(interaction: discord.Interaction, name: str):
    added = await storage.add_protected_player(interaction.guild_id, name)
    if added:
        await interaction.response.send_message(f"🛡️ Added **{name}** to the protected list. They won't be flagged for removal due to inactivity.")
    else:
        await interaction.response.send_message(f"**{name}** is already on the protected list.", ephemeral=True)


@bot.tree.command(description="Remove a player from the protected list")
@app_commands.describe(name="PUBG name to unprotect")
async def removeprotected(interaction: discord.Interaction, name: str):
    removed = await storage.remove_protected_player(interaction.guild_id, name)
    if removed:
        await interaction.response.send_message(f"🔓 Removed **{name}** from the protected list. They can now be flagged for inactivity removal.")
    else:
        await interaction.response.send_message(f"**{name}** wasn't on the protected list.", ephemeral=True)


@bot.tree.command(description="List all protected players (immune to inactivity removal)")
async def listprotected(interaction: discord.Interaction):
    protected = await storage.get_protected_players(interaction.guild_id)
    # Clean the list first
    removed = await storage.clean_protected_players(interaction.guild_id)
    protected = await storage.get_protected_players(interaction.guild_id)
    
    if not protected:
        await interaction.response.send_message("No protected players. Use `/addprotected` to add players who should be immune to inactivity removal.")
        return
    
    message = f"**Protected players ({len(protected)}):**\n" + ", ".join(protected)
    if removed > 0:
        message += f"\n\n🧹 Cleaned up {removed} duplicate/empty entries."
    message += "\n\n🛡️ These players won't be flagged for removal due to inactivity."
    await interaction.response.send_message(message)


@bot.tree.command(description="Clean up protected player list (remove duplicates and empty entries)")
async def cleanprotected(interaction: discord.Interaction):
    removed = await storage.clean_protected_players(interaction.guild_id)
    protected = await storage.get_protected_players(interaction.guild_id)
    await interaction.response.send_message(f"🧹 Cleaned up {removed} duplicate/empty entries. Protected players: {len(protected)}")


@bot.tree.command(description="Clear and reset the entire protected player list")
async def resetprotected(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["protected_players"] = []
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message("🗑️ Protected player list has been cleared. Use `/addprotected` to rebuild it.")


@bot.tree.command(description="Bulk add protected players (one per line or comma-separated)")
@app_commands.describe(players="Player names (one per line or comma-separated)")
async def addprotectedbulk(interaction: discord.Interaction, players: str):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    
    # Parse the input - handle both comma and newline separators
    player_list = [p.strip() for p in players.replace(',', '\n').split('\n')]
    player_list = [p for p in player_list if p]  # Remove empty entries
    
    # Get current protected list
    current_protected = set(p.lower() for p in guild_cfg["protected_players"])
    
    added = []
    duplicates = []
    
    for player in player_list:
        if player.lower() in current_protected:
            duplicates.append(player)
        else:
            guild_cfg["protected_players"].append(player)
            current_protected.add(player.lower())
            added.append(player)
    
    await storage.save_guild(interaction.guild_id, guild_cfg)
    
    message = f"✅ Added **{len(added)}** protected player(s):\n" + ", ".join(added)
    if duplicates:
        message += f"\n⚠️ Skipped {len(duplicates)} already protected: " + ", ".join(duplicates)
    await interaction.response.send_message(message)


@bot.tree.command(description="Set manual inactive date for a player (beyond 14-day API limit)")
@app_commands.describe(name="PUBG name", days_ago="How many days ago they last played")
async def setinactivedate(interaction: discord.Interaction, name: str, days_ago: app_commands.Range[int, 1, 365]):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    from datetime import datetime, timedelta, timezone
    inactive_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    guild_cfg["manual_inactive_dates"][name.lower()] = inactive_date
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Set **{name}** last played {days_ago} days ago. This will override the PUBG API data.")


@bot.tree.command(description="Remove manual inactive date for a player")
@app_commands.describe(name="PUBG name")
async def removeinactivedate(interaction: discord.Interaction, name: str):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    if name.lower() in guild_cfg.get("manual_inactive_dates", {}):
        del guild_cfg["manual_inactive_dates"][name.lower()]
        await storage.save_guild(interaction.guild_id, guild_cfg)
        await interaction.response.send_message(f"✅ Removed manual inactive date for **{name}**. Will use PUBG API data.")
    else:
        await interaction.response.send_message(f"**{name}** doesn't have a manual inactive date set.", ephemeral=True)


@bot.tree.command(description="List everyone currently tracked for this server's clan")
async def roster(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    players = guild_cfg["players"]
    if not players:
        await interaction.response.send_message("No players tracked yet. Add some with `/addplayer`.")
        return
    await interaction.response.send_message(
        f"**Tracked roster ({len(players)}):**\n" + ", ".join(players)
    )


class CheatReportModal(discord.ui.Modal, title="Report Cheater"):
    accused_name = discord.ui.TextInput(
        label="Accused Player Name",
        placeholder="Enter the suspected cheater's PUBG name",
        required=True,
    )
    
    cheat_type = discord.ui.TextInput(
        label="Cheat Type",
        placeholder="e.g., Aimbot, ESP, Wallhack, Speedhack, No Recoil",
        required=True,
    )
    
    description = discord.ui.TextInput(
        label="Description",
        style=discord.TextStyle.long,
        placeholder="Describe what happened, when, and any specific suspicious behavior",
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
    
    async def on_submit(self, interaction: discord.Interaction):
        reporter_name = interaction.user.display_name
        accused_name = self.accused_name.value
        cheat_type = self.cheat_type.value
        description = self.description.value
        match_id = self.match_id.value or None
        evidence_urls = [url.strip() for url in self.evidence_urls.value.split('\n') if url.strip()] if self.evidence_urls.value else None
        
        await interaction.response.defer()
        
        try:
            report_id = await storage.add_cheat_report(
                interaction.guild_id,
                reporter_name,
                accused_name,
                cheat_type,
                description,
                match_id,
                evidence_urls,
            )
            
            # Auto-detect if player is suspicious
            guild_cfg = await storage.get_guild(interaction.guild_id)
            players, _ = await pubg.get_players_and_stats([accused_name], game_mode=guild_cfg.get("game_mode", "squad-fpp"))
            if players:
                player = players[0]
                stats = player.get("stats", {})
                flags = _detect_suspicious_stats(stats)
                if flags:
                    await storage.update_suspicious_player(interaction.guild_id, accused_name, stats, flags)
            
            embed = discord.Embed(
                title="🚨 Cheat Report Submitted",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="Report ID", value=report_id, inline=False)
            embed.add_field(name="Accused", value=accused_name, inline=True)
            embed.add_field(name="Cheat Type", value=cheat_type, inline=True)
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
                channel = bot.get_channel(channel_id)
                if channel:
                    await channel.send(f"🚨 New cheat report submitted by {reporter_name} against **{accused_name}**")
                    
        except Exception as e:
            await interaction.followup.send(f"Error submitting report: {e}")


@bot.tree.command(description="Report a suspected cheater with evidence")
async def reportcheater(interaction: discord.Interaction):
    await interaction.response.send_modal(CheatReportModal())


def _detect_suspicious_stats(stats: dict) -> list[str]:
    """Detect suspicious statistics that might indicate cheating."""
    flags = []
    
    kills = stats.get("kills", 0)
    deaths = stats.get("deaths", 0)
    headshot_kills = stats.get("headshotKills", 0)
    rounds = stats.get("roundsPlayed", 0)
    wins = stats.get("wins", 0)
    damage = stats.get("damageDealt", 0)
    
    if rounds == 0:
        return flags
    
    kd = kills / max(deaths, 1)
    kdr = kills / max(rounds - wins, 1)
    headshot_rate = (headshot_kills / max(kills, 1)) * 100 if kills > 0 else 0
    avg_damage = damage / max(rounds, 1)
    
    # Suspicious thresholds
    if kd > 10:
        flags.append(f"Extremely high K/D: {kd:.2f}")
    if kdr > 8:
        flags.append(f"Impossible kill rate: {kdr:.2f} kills/round")
    if headshot_rate > 80:
        flags.append(f"Suspicious headshot rate: {headshot_rate:.1f}%")
    if avg_damage > 2000:
        flags.append(f"Unrealistic average damage: {avg_damage:.0f}")
    if wins / rounds > 0.5 and rounds > 10:
        flags.append(f"Impossible win rate: {(wins/rounds)*100:.1f}%")
    
    return flags


@bot.tree.command(description="Post aggregated clan stats right now")
async def clanstats(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        result = await fetch_clan_report(interaction.guild_id, interaction.guild.name)
    except PubgApiError as e:
        await interaction.followup.send(f"PUBG API error: {e}")
        return
    except Exception as e:
        await interaction.followup.send(f"Something went wrong generating this report: {e}")
        return
    if result is None:
        await interaction.followup.send("No players tracked yet. Add some with `/addplayer`.")
        return
    embed, players = result
    await interaction.followup.send(embed=embed)


@bot.tree.command(description="Manually post today's clan digest to this channel")
async def postnow(interaction: discord.Interaction):
    await clanstats.callback(interaction)


@bot.tree.command(description="Show roster sorted by a stat")
@app_commands.describe(sort_by="Which stat to sort by")
@app_commands.choices(
    sort_by=[
        app_commands.Choice(name="Kills", value="kills"),
        app_commands.Choice(name="Wins", value="wins"),
        app_commands.Choice(name="Damage dealt", value="damageDealt"),
    ]
)
async def leaderboard(interaction: discord.Interaction, sort_by: app_commands.Choice[str] = None):
    stat_key = sort_by.value if sort_by else "kills"
    guild_cfg = await storage.get_guild(interaction.guild_id)
    if not guild_cfg["players"]:
        await interaction.response.send_message("No players tracked yet. Add some with `/addplayer`.")
        return
    await interaction.response.defer()
    try:
        players, not_found = await pubg.get_players_and_stats(guild_cfg["players"], game_mode=guild_cfg["game_mode"])
    except PubgApiError as e:
        await interaction.followup.send(f"PUBG API error: {e}")
        return
    except Exception as e:
        await interaction.followup.send(f"Something went wrong generating this report: {e}")
        return

    ranked = sorted(players, key=lambda p: p["stats"].get(stat_key, 0), reverse=True)
    lines = [f"{i}. **{p['name']}** — {p['stats'].get(stat_key, 0):,}" for i, p in enumerate(ranked, start=1)]
    embed = discord.Embed(
        title=f"Leaderboard — {stat_key} ({guild_cfg['game_mode']})",
        description="\n".join(lines) or "No data.",
        color=discord.Color.blue(),
    )
    if not_found:
        embed.set_footer(text=f"Not found: {', '.join(not_found)}")
    await interaction.followup.send(embed=embed)


@bot.tree.command(description="Set the PUBG game mode used for stats (default squad-fpp)")
@app_commands.choices(
    mode=[app_commands.Choice(name=m, value=m) for m in sorted(VALID_GAME_MODES)]
)
async def setgamemode(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["game_mode"] = mode.value
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"Game mode set to **{mode.value}**.")


@bot.tree.command(description="Set the clan-level report from a current PUBG clan member")
@app_commands.describe(name="Exact in-game PUBG name of a member of the clan")
async def setclan(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    try:
        clan = await pubg.get_clan_for_player_name(name.strip())
    except PubgApiError as e:
        await interaction.followup.send(f"PUBG API error: {e}", ephemeral=True)
        return
    if clan is None:
        await interaction.followup.send(
            f"I couldn't find a clan for **{name.strip()}** on the **{PUBG_SHARD}** shard. "
            "Use the exact PUBG name of a current clan member.",
            ephemeral=True,
        )
        return
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["pubg_clan_id"] = clan["id"]
    guild_cfg["pubg_clan_name"] = clan["name"]
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.followup.send(
        f"✅ Clan-level reports will track **{clan['name']}** (`{clan['tag']}`), currently level **{clan['level']}**.",
        ephemeral=True,
    )


@bot.tree.command(description="Show the current PUBG clan level and weekly progress")
async def clanlevel(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        result = await fetch_clan_level_report(interaction.guild_id)
    except PubgApiError as e:
        await interaction.followup.send(f"PUBG API error: {e}")
        return
    if result is None:
        await interaction.followup.send("Set a clan first with `/setclan <current clan member>`.")
        return
    embed, _ = result
    await interaction.followup.send(embed=embed)


@bot.tree.command(description="Set this channel for the weekly clan-level report")
async def setclanchannel(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["clan_channel_id"] = interaction.channel_id
    guild_cfg["clan_level_enabled"] = True
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ Weekly clan-level reports will post in {interaction.channel.mention}. "
        f"Choose the weekly time with `/setclantime`."
    )


@bot.tree.command(description="Get help with PUBG Tracker and join the official support server")
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**Need help with PUBG Tracker?**\n"
        "Use `/` to browse the Bot's commands, or join the official support server for "
        "setup help, bug reports, feature requests, and Bot updates:\n"
        f"{SUPPORT_SERVER_URL}"
    )


@bot.tree.command(description="Show this server's automatic report schedules and next run times")
async def reportstatus(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    await interaction.response.send_message(embed=build_report_status_embed(guild_cfg))


@bot.tree.command(description="Set this channel to show live bot status (connects, joins/leaves, failures, rate limits)")
async def setstatuschannel(interaction: discord.Interaction):
    """
    Points a channel at a single persistent status embed that gets EDITED
    in place whenever something notable happens (see _record_status_event
    call sites) — never a new message per event. The event log itself is
    in-memory and resets on restart; it's a live feed, not an audit trail.
    """
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["status_channel_id"] = interaction.channel_id
    guild_cfg["status_message_id"] = None  # force a fresh message in the new channel
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ Bot status will be posted and kept up to date in {interaction.channel.mention}. "
        "It only updates when something actually happens — connect/disconnect, a server join/leave, "
        "a report failing, or a PUBG rate-limit hit — never on a fixed timer."
    )
    await _refresh_all_status_messages(force=True)


@bot.tree.command(description="Administrator: turn a scheduled report on or off without losing its settings")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.choices(
    report=[
        app_commands.Choice(name="Clan Digest", value="digest_enabled"),
        app_commands.Choice(name="Last Active", value="activity_enabled"),
        app_commands.Choice(name="Ranked", value="ranked_enabled"),
        app_commands.Choice(name="Daily Highlights", value="highlights_enabled"),
        app_commands.Choice(name="Clan Level", value="clan_level_enabled"),
        app_commands.Choice(name="Survival Mastery", value="survival_enabled"),
        app_commands.Choice(name="Donation Message", value="donation_enabled"),
        app_commands.Choice(name="Chicken Dinner Alerts", value="chicken_dinner_enabled"),
    ],
    enabled=[
        app_commands.Choice(name="On", value="on"),
        app_commands.Choice(name="Off", value="off"),
    ],
)
async def reporttoggle(
    interaction: discord.Interaction,
    report: app_commands.Choice[str],
    enabled: app_commands.Choice[str],
):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    is_enabled = enabled.value == "on"
    guild_cfg[report.value] = is_enabled
    await storage.save_guild(interaction.guild_id, guild_cfg)
    state = "enabled" if is_enabled else "disabled"
    await interaction.response.send_message(
        f"✅ **{report.name}** scheduled reports are now **{state}**. "
        "Its saved channel and schedule have not been changed. Use `/reportstatus` to review all schedules."
    )


@bot.tree.command(description="Show the optional donation link for PUBG Tracker")
async def donate(interaction: discord.Interaction):
    await interaction.response.send_message(DONATION_MESSAGE)


@bot.tree.command(description="Enable the weekly Sunday donation post in this channel")
async def setdonationchannel(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["donation_channel_id"] = interaction.channel_id
    guild_cfg["donation_enabled"] = True
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ The optional donation message will post in {interaction.channel.mention} every "
        f"**Sunday at {guild_cfg['donation_hour_est']:02d}:{guild_cfg['donation_minute_est']:02d} Eastern**. "
        "Use `/setdonationtime` to change the time."
    )


@bot.tree.command(description="Set this channel as where the clan digest gets auto-posted")
async def setchannel(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["post_channel_id"] = interaction.channel_id
    guild_cfg["digest_enabled"] = True
    # Seed last_post_at to now so the first auto-post fires a full interval
    # from now, rather than immediately on the next 15-min check.
    guild_cfg["last_post_at"] = datetime.now(timezone.utc).isoformat()
    await storage.save_guild(interaction.guild_id, guild_cfg)
    interval = guild_cfg.get("post_interval_hours", 6)
    await interaction.response.send_message(
        f"✅ Digest will auto-post in {interaction.channel.mention} every **{interval} hour(s)**. "
        f"Use `/postnow` any time for an immediate one."
    )


@bot.tree.command(description="Set how often (in hours) the digest auto-posts (ignored if a fixed time is set via /setdigesttime)")
@app_commands.describe(hours="e.g. 6 for every 6 hours")
async def setinterval(interaction: discord.Interaction, hours: app_commands.Range[int, 1, 24]):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["post_interval_hours"] = hours
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Digest will now auto-post every **{hours} hour(s)**.")


QUARTER_HOUR_CHOICES = [
    app_commands.Choice(name=":00", value=0),
    app_commands.Choice(name=":15", value=15),
    app_commands.Choice(name=":30", value=30),
    app_commands.Choice(name=":45", value=45),
]

WEEKDAY_CHOICES = [
    app_commands.Choice(name="Monday", value=0),
    app_commands.Choice(name="Tuesday", value=1),
    app_commands.Choice(name="Wednesday", value=2),
    app_commands.Choice(name="Thursday", value=3),
    app_commands.Choice(name="Friday", value=4),
    app_commands.Choice(name="Saturday", value=5),
    app_commands.Choice(name="Sunday", value=6),
]


@bot.tree.command(description="Post the digest once a day at a fixed Eastern-time, instead of by interval")
@app_commands.describe(hour="0-23, Eastern time (e.g. 9 for 9am ET)", minute="Quarter-hour, defaults to :00")
@app_commands.choices(minute=QUARTER_HOUR_CHOICES)
async def setdigesttime(interaction: discord.Interaction, hour: app_commands.Range[int, 0, 23], minute: app_commands.Choice[int] = None):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["digest_hour_est"] = hour
    guild_cfg["digest_minute_est"] = minute.value if minute else 0
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ Digest will now post once a day at **{hour:02d}:{guild_cfg['digest_minute_est']:02d} Eastern** (auto-adjusts for EST/EDT). "
        f"This overrides `/setinterval`."
    )


@bot.tree.command(description="Set the weekly clan-level report time in Eastern time")
@app_commands.describe(day="Day of the week", hour="0-23 Eastern time", minute="Quarter-hour, defaults to :00")
@app_commands.choices(day=WEEKDAY_CHOICES, minute=QUARTER_HOUR_CHOICES)
async def setclantime(
    interaction: discord.Interaction,
    day: app_commands.Choice[int],
    hour: app_commands.Range[int, 0, 23],
    minute: app_commands.Choice[int] = None,
):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["clan_weekday_est"] = day.value
    guild_cfg["clan_hour_est"] = hour
    guild_cfg["clan_minute_est"] = minute.value if minute else 0
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ Clan-level report will post every **{day.name} at {hour:02d}:{guild_cfg['clan_minute_est']:02d} Eastern**."
    )


@bot.tree.command(description="Set the Sunday Eastern-time donation post time")
@app_commands.describe(hour="0-23, Eastern time (e.g. 12 for noon)", minute="Quarter-hour, defaults to :00")
@app_commands.choices(minute=QUARTER_HOUR_CHOICES)
async def setdonationtime(
    interaction: discord.Interaction,
    hour: app_commands.Range[int, 0, 23],
    minute: app_commands.Choice[int] = None,
):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["donation_hour_est"] = hour
    guild_cfg["donation_minute_est"] = minute.value if minute else 0
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ The optional donation message will post every **Sunday at "
        f"{hour:02d}:{guild_cfg['donation_minute_est']:02d} Eastern**."
    )


@bot.tree.command(description="Show when each roster player last played PUBG, right now")
async def lastactive(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    if not guild_cfg["players"]:
        await interaction.response.send_message("No players tracked yet. Add some with `/addplayer`.")
        return
    await interaction.response.defer()
    try:
        result = await fetch_last_active_report(interaction.guild_id, interaction.guild.name)
    except PubgApiError as e:
        await interaction.followup.send(f"PUBG API error: {e}")
        return
    except Exception as e:
        await interaction.followup.send(f"Something went wrong generating this report: {e}")
        return
    if result is None:
        await interaction.followup.send("No players tracked yet. Add some with `/addplayer`.")
        return
    embed, players = result
    await interaction.followup.send(embed=embed)


@bot.tree.command(description="Set this channel for the 24-hour 'last active' report (defaults to the digest channel)")
async def setactivitychannel(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["last_activity_channel_id"] = interaction.channel_id
    guild_cfg["activity_enabled"] = True
    guild_cfg["last_activity_posted_at"] = datetime.now(timezone.utc).isoformat()
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ Last-active report will post in {interaction.channel.mention} every 24 hours. "
        f"Use `/lastactive` any time for an immediate one."
    )


@bot.tree.command(description="Post the last-active report at a fixed Eastern-time each day")
@app_commands.describe(hour="0-23, Eastern time (e.g. 9 for 9am ET)", minute="Quarter-hour, defaults to :00")
@app_commands.choices(minute=QUARTER_HOUR_CHOICES)
async def setactivitytime(interaction: discord.Interaction, hour: app_commands.Range[int, 0, 23], minute: app_commands.Choice[int] = None):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["activity_hour_est"] = hour
    guild_cfg["activity_minute_est"] = minute.value if minute else 0
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Last-active report will now post daily at **{hour:02d}:{guild_cfg['activity_minute_est']:02d} Eastern**.")


async def _run_ranked_command(interaction: discord.Interaction, game_mode: str, queue_label: str):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    if not guild_cfg["players"]:
        await interaction.response.send_message("No players tracked yet. Add some with `/addplayer`.")
        return
    # Discord only allows a slash command to reply for 15 minutes. The first
    # full roster scan is one ranked API call per player (paced at 8/min by
    # the PUBG rate limiter), which can exceed that window on large rosters —
    # so acknowledge instantly and post the finished report to the channel
    # instead of through the command reply.
    await interaction.response.send_message(
        f"⏳ Fetching {queue_label} ranked standings. Only players with ranked matches will be posted. "
        f"With a large roster, PUBG's request limit can make this take 15+ minutes — "
        f"the report will appear in this channel when it's ready."
    )
    channel = interaction.channel
    try:
        result = await fetch_ranked_report(interaction.guild_id, interaction.guild.name, game_mode)
    except PubgApiError as e:
        await channel.send(f"PUBG API error while fetching {queue_label} ranked standings: {e}")
        return
    except Exception as e:
        await channel.send(f"Something went wrong generating this report: {e}")
        return
    embed, players = result
    await channel.send(embed=embed)


@bot.tree.command(description="Show current-season ranked Squad TPP standings")
async def rankedsquad(interaction: discord.Interaction):
    await _run_ranked_command(interaction, "squad", "Squad TPP")


@bot.tree.command(description="Show current-season ranked Duo TPP standings")
async def rankedduo(interaction: discord.Interaction):
    await _run_ranked_command(interaction, "duo", "Duo TPP")


@bot.tree.command(description="Show current-season ranked Solo TPP standings")
async def rankedsolo(interaction: discord.Interaction):
    await _run_ranked_command(interaction, "solo", "Solo TPP")


@bot.tree.command(description="Show current-season ranked Squad FPP standings")
async def rankedsquadfpp(interaction: discord.Interaction):
    await _run_ranked_command(interaction, "squad-fpp", "Squad FPP")


@bot.tree.command(description="Show current-season ranked Duo FPP standings")
async def rankedduofpp(interaction: discord.Interaction):
    await _run_ranked_command(interaction, "duo-fpp", "Duo FPP")


@bot.tree.command(description="Show current-season ranked Solo FPP standings")
async def rankedsolofpp(interaction: discord.Interaction):
    await _run_ranked_command(interaction, "solo-fpp", "Solo FPP")


@bot.tree.command(description="Rescan the full roster the next time a ranked queue is checked")
async def refreshrankedcache(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["ranked_known_players"] = {}
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        "✅ Ranked-player cache cleared. The next check for each ranked queue will scan the full roster; "
        "later checks will only query players known to play that queue."
    )


@bot.tree.command(description="Set this channel for the daily ranked report (defaults to the digest channel)")
async def setrankedchannel(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["ranked_channel_id"] = interaction.channel_id
    guild_cfg["ranked_enabled"] = True
    guild_cfg["ranked_posted_at"] = datetime.now(timezone.utc).isoformat()
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ Ranked report will post in {interaction.channel.mention} every 24 hours. "
        f"Use one of the `/ranked...` commands any time for an immediate one."
    )


@bot.tree.command(description="Set which ranked queue the daily report tracks")
@app_commands.choices(
    queue=[
        app_commands.Choice(name="Squad TPP", value="squad"),
        app_commands.Choice(name="Duo TPP", value="duo"),
        app_commands.Choice(name="Solo TPP", value="solo"),
        app_commands.Choice(name="Squad FPP", value="squad-fpp"),
        app_commands.Choice(name="Duo FPP", value="duo-fpp"),
        app_commands.Choice(name="Solo FPP", value="solo-fpp"),
    ]
)
async def setrankedqueue(interaction: discord.Interaction, queue: app_commands.Choice[str]):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["ranked_queue"] = queue.value
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Daily ranked reports will now track **{queue.name}**.")


@bot.tree.command(description="Post the selected ranked report at a fixed Eastern-time each day")
@app_commands.describe(hour="0-23, Eastern time (e.g. 9 for 9am ET)", minute="Quarter-hour, defaults to :00")
@app_commands.choices(minute=QUARTER_HOUR_CHOICES)
async def setrankedtime(interaction: discord.Interaction, hour: app_commands.Range[int, 0, 23], minute: app_commands.Choice[int] = None):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["ranked_hour_est"] = hour
    guild_cfg["ranked_minute_est"] = minute.value if minute else 0
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Ranked report will now post daily at **{hour:02d}:{guild_cfg['ranked_minute_est']:02d} Eastern**.")


@bot.tree.command(description="Show the last-24h highlights (fun titles, top 10, human vs bot kills), right now")
async def dailyhighlights(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    if not guild_cfg["players"]:
        await interaction.response.send_message("No players tracked yet. Add some with `/addplayer`.")
        return
    await interaction.response.defer()  # this one can take a while — it downloads match telemetry
    try:
        result = await fetch_highlights_report(interaction.guild_id, interaction.guild.name)
    except PubgApiError as e:
        await interaction.followup.send(f"PUBG API error: {e}")
        return
    except Exception as e:
        await interaction.followup.send(f"Something went wrong generating this report: {e}")
        return
    embed, players = result
    await interaction.followup.send(embed=embed)


@bot.tree.command(description="Set this channel for the daily highlights report (defaults to the digest channel)")
async def sethighlightschannel(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["highlights_channel_id"] = interaction.channel_id
    guild_cfg["highlights_enabled"] = True
    guild_cfg["highlights_posted_at"] = datetime.now(timezone.utc).isoformat()
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ Daily highlights will post in {interaction.channel.mention} every 24 hours. "
        f"Use `/dailyhighlights` any time for an immediate one (it can take a minute — it reads match telemetry)."
    )


@bot.tree.command(description="Post the daily highlights report at a fixed Eastern-time each day")
@app_commands.describe(hour="0-23, Eastern time (e.g. 9 for 9am ET)", minute="Quarter-hour, defaults to :00")
@app_commands.choices(minute=QUARTER_HOUR_CHOICES)
async def sethighlightstime(interaction: discord.Interaction, hour: app_commands.Range[int, 0, 23], minute: app_commands.Choice[int] = None):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["highlights_hour_est"] = hour
    guild_cfg["highlights_minute_est"] = minute.value if minute else 0
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Daily highlights will now post daily at **{hour:02d}:{guild_cfg['highlights_minute_est']:02d} Eastern**.")


@bot.tree.command(description="Show roster Survival Mastery grouped by tier and sorted by level")
async def survivalstats(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    if not guild_cfg["players"]:
        await interaction.response.send_message("No players tracked yet. Add some with `/addplayer`.")
        return
    # Survival mastery is 2 PUBG API calls per player, paced at 8/min —
    # roughly 15 seconds per player. That blows past Discord's 15-minute
    # slash-command reply window on rosters of ~60+, so acknowledge
    # instantly and post the finished report straight to the channel.
    est_minutes = (len(guild_cfg["players"]) * 15 + 59) // 60
    await interaction.response.send_message(
        f"⏳ Working on it — with {len(guild_cfg['players'])} player(s) this takes about {est_minutes} minute(s) "
        f"(PUBG's request limit paces the lookups). The report will appear in this channel when it's ready; "
        f"you don't need to keep waiting here."
    )
    channel = interaction.channel
    try:
        result = await fetch_survival_mastery_report(interaction.guild_id, interaction.guild.name)
    except PubgApiError as e:
        await channel.send(f"PUBG API error while building the Survival Mastery report: {e}")
        return
    except Exception as e:
        await channel.send(f"Something went wrong generating this report: {e}")
        return
    if result is None:
        await channel.send("No players tracked yet. Add some with `/addplayer`.")
        return
    embeds, files = result
    await channel.send(embeds=embeds, files=files)


@bot.tree.command(description="Set this channel for the weekly Survival Mastery report")
async def setsurvivalchannel(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["survival_channel_id"] = interaction.channel_id
    guild_cfg["survival_enabled"] = True
    await storage.save_guild(interaction.guild_id, guild_cfg)
    weekday = guild_cfg.get("survival_weekday_est")
    if weekday is None:
        await interaction.response.send_message(
            f"✅ Weekly Survival Mastery reports will post in {interaction.channel.mention}. "
            "Use `/setsurvivaltime` to choose the weekly day and time."
        )
    else:
        weekday_name = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[weekday]
        await interaction.response.send_message(
            f"✅ Weekly Survival Mastery reports will post in {interaction.channel.mention} every "
            f"**{weekday_name} at {guild_cfg.get('survival_hour_est', 12):02d}:{guild_cfg.get('survival_minute_est', 0):02d} Eastern**. "
            "Use `/setsurvivaltime` to change the schedule."
        )


@bot.tree.command(description="Set the weekly Survival Mastery report time in Eastern time")
@app_commands.describe(day="Day of the week", hour="0-23 Eastern time", minute="Quarter-hour, defaults to :00")
@app_commands.choices(day=WEEKDAY_CHOICES, minute=QUARTER_HOUR_CHOICES)
async def setsurvivaltime(
    interaction: discord.Interaction,
    day: app_commands.Choice[int],
    hour: app_commands.Range[int, 0, 23],
    minute: app_commands.Choice[int] = None,
):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["survival_weekday_est"] = day.value
    guild_cfg["survival_hour_est"] = hour
    guild_cfg["survival_minute_est"] = minute.value if minute else 0
    guild_cfg["survival_enabled"] = True
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ Survival Mastery report will post every **{day.name} at {hour:02d}:{guild_cfg['survival_minute_est']:02d} Eastern**."
    )


@bot.tree.command(description="Show each player's top weapon mastery and survival level (slow — 2 calls/player)")
async def masterystats(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    if not guild_cfg["players"]:
        await interaction.response.send_message("No players tracked yet. Add some with `/addplayer`.")
        return
    # Same 15-seconds-per-player pacing as /survivalstats (2 PUBG calls per
    # player) — reply instantly and post to the channel so large rosters
    # aren't cut off by Discord's 15-minute command reply window.
    est_minutes = (len(guild_cfg["players"]) * 15 + 59) // 60
    await interaction.response.send_message(
        f"⏳ Working on it — with {len(guild_cfg['players'])} player(s) this takes about {est_minutes} minute(s). "
        f"The report will appear in this channel when it's ready."
    )
    channel = interaction.channel
    try:
        result = await fetch_mastery_report(interaction.guild_id, interaction.guild.name)
    except PubgApiError as e:
        await channel.send(f"PUBG API error while building the mastery report: {e}")
        return
    except Exception as e:
        await channel.send(f"Something went wrong generating this report: {e}")
        return
    if result is None:
        await channel.send("No players tracked yet. Add some with `/addplayer`.")
        return
    embed, players = result
    await channel.send(embed=embed)


@bot.tree.command(description="Check the official leaderboard for roster placements (most won't appear — top ladder only)")
@app_commands.describe(pages="How many 500-player pages to check (default 4 = top 2000)")
async def leaderboardstats(interaction: discord.Interaction, pages: app_commands.Range[int, 1, 10] = 4):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    if not guild_cfg["players"]:
        await interaction.response.send_message("No players tracked yet. Add some with `/addplayer`.")
        return
    await interaction.response.defer()
    try:
        result = await fetch_leaderboard_report(interaction.guild_id, interaction.guild.name, max_pages=pages)
    except PubgApiError as e:
        await interaction.followup.send(f"PUBG API error: {e}")
        return
    except Exception as e:
        await interaction.followup.send(f"Something went wrong generating this report: {e}")
        return
    if result is None:
        await interaction.followup.send("No players tracked yet. Add some with `/addplayer`.")
        return
    embed, found = result
    await interaction.followup.send(embed=embed)


@bot.tree.command(description="Set the platform-region shard used for leaderboard lookups (default pc-na)")
@app_commands.choices(
    region=[
        app_commands.Choice(name="NA", value="pc-na"),
        app_commands.Choice(name="EU", value="pc-eu"),
        app_commands.Choice(name="AS (Asia)", value="pc-as"),
        app_commands.Choice(name="OC (Oceania)", value="pc-oc"),
        app_commands.Choice(name="SA (South America)", value="pc-sa"),
        app_commands.Choice(name="SEA", value="pc-sea"),
        app_commands.Choice(name="KRJP (Korea/Japan)", value="pc-krjp"),
        app_commands.Choice(name="Kakao", value="pc-kakao"),
    ]
)
async def setleaderboardregion(interaction: discord.Interaction, region: app_commands.Choice[str]):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["leaderboard_shard"] = region.value
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Leaderboard lookups will now use **{region.name}**.")


@bot.tree.command(description="Set which queue the leaderboard check looks at (squad, duo, or solo TPP)")
@app_commands.choices(
    queue=[
        app_commands.Choice(name="Squad TPP", value="squad"),
        app_commands.Choice(name="Duo TPP", value="duo"),
        app_commands.Choice(name="Solo TPP", value="solo"),
    ]
)
async def setleaderboardqueue(interaction: discord.Interaction, queue: app_commands.Choice[str]):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["leaderboard_queue"] = queue.value
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Leaderboard checks will now use **{queue.name}**.")


async def _resolve_and_link(interaction: discord.Interaction, pubg_name: str, target: discord.Member) -> None:
    """
    Shared PUBG-name verification + await storage.link_discord_account() call
    used by both /linkme (self) and /linkplayer (linking someone
    else). Always replies ephemerally; caller must have already deferred.
    """
    pubg_name = pubg_name.strip()
    if not pubg_name:
        await interaction.followup.send("Please provide a PUBG name.", ephemeral=True)
        return

    try:
        players = await pubg.get_players_by_name([pubg_name])
    except PubgApiError as e:
        await interaction.followup.send(f"❌ Could not verify that name right now: {e}", ephemeral=True)
        return

    if not players:
        await interaction.followup.send(
            f"❌ Could not find a PUBG player named **{pubg_name}**. Check the spelling — it's case-sensitive-looking but PUBG names aren't, so this only fails on an actual typo.",
            ephemeral=True,
        )
        return

    # Use the API's returned casing so the link key matches what every
    # other report already resolves against (storage lowercases the key
    # internally, but the display name elsewhere in reports comes from
    # this exact casing via pubg.get_players_by_name).
    correct_name = players[0]["name"]
    existing_id = await storage.get_discord_id(interaction.guild_id, correct_name)
    await storage.link_discord_account(interaction.guild_id, correct_name, target.id)

    note = ""
    if existing_id is not None and existing_id != target.id:
        note = " (this replaces a link to a different Discord account)"
    await interaction.followup.send(
        f"✅ Linked **{target.display_name}** to PUBG player **{correct_name}**{note}.\n"
        f"{'You' if target.id == interaction.user.id else target.display_name} will show as a mention next to "
        "that name on `/leaderboardstats` if placing on the official ladder. Use `/unlinkme` to remove it.",
        ephemeral=True,
    )


@bot.tree.command(description="Link your Discord account to a PUBG name (shows as a mention on the official leaderboard report)")
@app_commands.describe(pubg_name="Your exact PUBG in-game name")
async def linkme(interaction: discord.Interaction, pubg_name: str):
    """
    Creates the report-identity link that await storage.link_discord_account()
    already supported but nothing called before this command existed.
    Reports no longer post a separate per-player message or ping anyone;
    the sole remaining effect of a link is that /leaderboardstats shows a
    non-pinging @mention next to your name instead of the plain PUBG name
    when you place on the official ladder.
    """
    await interaction.response.defer(ephemeral=True)
    await _resolve_and_link(interaction, pubg_name, interaction.user)


@bot.tree.command(description="Link another member's Discord account to a PUBG name on their behalf")
@app_commands.describe(member="The Discord member to link", pubg_name="Their exact PUBG in-game name")
async def linkplayer(interaction: discord.Interaction, member: discord.Member, pubg_name: str):
    """
    Counterpart to /linkme, for linking someone other than yourself — e.g.
    a member who won't run the self-link command themselves. Open to
    anyone, same as /linkme; not gated behind manage_guild. Same
    verification and storage call as /linkme, just targeting an arbitrary
    member instead of the caller.
    """
    await interaction.response.defer(ephemeral=True)
    await _resolve_and_link(interaction, pubg_name, member)


@bot.tree.command(description="Remove your Discord-to-PUBG-name link")
@app_commands.describe(pubg_name="The PUBG name to unlink")
async def unlinkme(interaction: discord.Interaction, pubg_name: str):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    linked_id = guild_cfg["discord_links"].get(pubg_name.lower())
    # Only the Discord account a link points to — or a server manager — may
    # remove it. Previously anyone in the server could delete anyone's link.
    is_their_own_link = linked_id is not None and linked_id == interaction.user.id
    is_server_manager = interaction.user.guild_permissions.manage_guild
    if not (is_their_own_link or is_server_manager):
        await interaction.response.send_message(
            "You can only remove a link that points to your own account — ask a server manager for other names.",
            ephemeral=True,
        )
        return
    removed = await storage.unlink_discord_account(interaction.guild_id, pubg_name)
    if removed:
        await interaction.response.send_message(f"🗑️ Unlinked **{pubg_name}**.")
    else:
        await interaction.response.send_message(f"**{pubg_name}** wasn't linked to anyone.", ephemeral=True)


@bot.tree.command(description="Show every PUBG-name-to-Discord link for this server")
async def links(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    discord_links = guild_cfg["discord_links"]
    if not discord_links:
        await interaction.response.send_message(
            "No accounts are linked yet. Use `/linkme <pubg_name>` to link your own, "
            "or `/linkplayer <member> <pubg_name>` to link someone else's."
        )
        return

    # discord_links keys are lowercased; show the roster's actual casing
    # when the linked name is still tracked, otherwise fall back to the
    # lowercased key as stored (e.g. the player was later removed from
    # the roster but the link was never cleaned up).
    proper_case = {p.lower(): p for p in guild_cfg["players"]}
    lines = [
        f"**{proper_case.get(name_lower, name_lower)}** — <@{discord_id}>"
        for name_lower, discord_id in sorted(discord_links.items())
    ]

    embed = discord.Embed(title="🔗 Linked Accounts", color=discord.Color.blurple())
    chunk_size = 20
    for i in range(0, len(lines), chunk_size):
        embed.add_field(
            name="Links" if i == 0 else "\u200b",
            value="\n".join(lines[i : i + chunk_size]),
            inline=False,
        )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(description="Check the roster's most recent matches for wins right now")
async def chickendinner(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    if not guild_cfg["players"]:
        await interaction.response.send_message("No players tracked yet — use `/addplayer` first.")
        return

    await interaction.response.defer()
    try:
        results, _ = await pubg.get_recent_wins(guild_cfg["players"])
    except PubgApiError as e:
        await interaction.followup.send(f"❌ Could not check the PUBG API right now: {e}")
        return

    winners = [(name, data) for name, data in results.items() if data.get("winPlace") == 1]
    if not winners:
        await interaction.followup.send("🥈 No Chicken Dinners in anyone's most recent match right now.")
        return

    embed = discord.Embed(
        title="🍗 Recent Chicken Dinners",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc),
    )
    for name, data in sorted(winners, key=lambda item: item[1].get("kills", 0), reverse=True)[:15]:
        map_name = data.get("map_name") or "Unknown map"
        embed.add_field(name=name, value=f"{data.get('kills', 0)} kills · {map_name}", inline=True)
    await interaction.followup.send(embed=embed)


@bot.tree.command(description="Set this channel for automatic Chicken Dinner win alerts (defaults to the digest channel)")
async def setchickendinnerchannel(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["chicken_dinner_channel_id"] = interaction.channel_id
    guild_cfg["chicken_dinner_enabled"] = True
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ Chicken Dinner win alerts will post in {interaction.channel.mention}. "
        "The bot checks every 15 minutes and only posts wins it hasn't posted before."
    )


@bot.tree.command(description="Toggle mention notifications for achievement awards in reports")
@app_commands.choices(
    enabled=[
        app_commands.Choice(name="On", value="on"),
        app_commands.Choice(name="Off", value="off"),
    ],
)
async def pingtoggle(interaction: discord.Interaction, enabled: app_commands.Choice[str]):
    """Enable or disable @mentions for linked Discord accounts in reports."""
    guild_cfg = await storage.get_guild(interaction.guild_id)
    is_enabled = enabled.value == "on"
    await storage.set_mentions_enabled(interaction.guild_id, is_enabled)
    state = "enabled" if is_enabled else "disabled"
    await interaction.response.send_message(
        f"✅ Mention notifications are now **{state}**. "
        f"When {'enabled' if is_enabled else 'disabled'}, linked Discord accounts will {'be @mentioned' if is_enabled else 'not be @mentioned'} "
        f"in achievement reports. Their avatar links will still work regardless of this setting."
    )


async def _is_admin_authorized(interaction: discord.Interaction, secret_key: str = None) -> bool:
    """Check if the user is the bot application owner, on the ADMIN_USER_IDS whitelist, or supplied the correct BOT_ADMIN_KEY."""
    app_info = await bot.application_info()
    is_owner = interaction.user.id == app_info.owner.id if app_info.owner else False
    if not is_owner and hasattr(app_info, "team") and app_info.team:
        is_owner = any(m.id == interaction.user.id for m in app_info.team.members)

    has_admin_id = interaction.user.id in ADMIN_USER_IDS
    has_valid_key = bool(BOT_ADMIN_KEY) and (secret_key == BOT_ADMIN_KEY)
    return is_owner or has_admin_id or has_valid_key


@bot.tree.command(description="[Admin] List all Discord servers the bot is in")
@app_commands.describe(secret_key="Optional admin secret key to unlock this command")
@app_commands.default_permissions(administrator=True)
async def botservers(interaction: discord.Interaction, secret_key: str = None):
    if not await _is_admin_authorized(interaction, secret_key):
        await interaction.response.send_message("⛔ You are not authorized to use this command.", ephemeral=True)
        return

    guilds = sorted(bot.guilds, key=lambda g: g.member_count or 0, reverse=True)
    total_members = sum(g.member_count or 0 for g in guilds)

    embed = discord.Embed(
        title=f"🌐 Installed Servers ({len(guilds)})",
        description=f"Total Members Reach: **{total_members:,}**",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc),
    )

    lines = []
    for i, g in enumerate(guilds, start=1):
        guild_cfg = await storage.get_guild(g.id)
        player_count = len(guild_cfg.get("players", []))
        lines.append(f"**{i}. {g.name}**\n`ID:` {g.id} · `Members:` {g.member_count or 0:,} · `Tracked Players:` {player_count}")

    for start in range(0, len(lines), 10):
        embed.add_field(
            name="Server List" if start == 0 else "\u200b",
            value="\n".join(lines[start : start + 10]) or "None",
            inline=False,
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)


def build_feedback_prompt_embed() -> discord.Embed:
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


async def _send_feedback_to_support_server(interaction: discord.Interaction, feedback_text: str, optional_info: str):
    """Sends submitted user feedback to the official support server or bot owner."""
    embed = discord.Embed(
        title="📬 New User Feedback Received",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name="👤 Submitted By",
        value=f"{interaction.user.mention} (`{interaction.user}` - ID: `{interaction.user.id}`)",
        inline=False,
    )
    guild_name = interaction.guild.name if interaction.guild else "Direct Message"
    guild_id = interaction.guild.id if interaction.guild else "N/A"
    embed.add_field(name="🏠 Origin Server", value=f"**{guild_name}** (`{guild_id}`)", inline=False)
    embed.add_field(name="📝 Feedback & Suggestions", value=feedback_text[:1024], inline=False)
    if len(feedback_text) > 1024:
        embed.add_field(name="📝 Feedback (Continued)", value=feedback_text[1024:2048], inline=False)
    if optional_info:
        embed.add_field(name="ℹ️ Additional Info / Clan", value=optional_info[:1024], inline=False)

    delivered = False
    if SUPPORT_FEEDBACK_CHANNEL_ID:
        channel = bot.get_channel(SUPPORT_FEEDBACK_CHANNEL_ID)
        if channel is None:
            try:
                channel = await bot.fetch_channel(SUPPORT_FEEDBACK_CHANNEL_ID)
            except Exception:
                channel = None
        if channel:
            try:
                await channel.send(embed=embed)
                delivered = True
            except Exception as e:
                print(f"[feedback] Error sending to SUPPORT_FEEDBACK_CHANNEL_ID: {e}")

    if not delivered and SUPPORT_SERVER_ID:
        support_guild = bot.get_guild(SUPPORT_SERVER_ID)
        if support_guild:
            target_channel = None
            for c in support_guild.text_channels:
                if any(k in c.name.lower() for k in ("feedback", "suggestion", "bot-log", "support", "general")):
                    if c.permissions_for(support_guild.me).send_messages:
                        target_channel = c
                        break
            if not target_channel:
                target_channel = support_guild.system_channel or next(
                    (c for c in support_guild.text_channels if c.permissions_for(support_guild.me).send_messages),
                    None,
                )
            if target_channel:
                try:
                    await target_channel.send(embed=embed)
                    delivered = True
                except Exception as e:
                    print(f"[feedback] Error sending to support guild channel: {e}")

    if not delivered:
        try:
            app_info = await bot.application_info()
            if app_info.owner:
                await app_info.owner.send(embed=embed)
                delivered = True
        except Exception as e:
            print(f"[feedback] Error sending fallback DM to owner: {e}")


class FeedbackModal(discord.ui.Modal, title="PUBG Tracker Feedback"):
    feedback_text = discord.ui.TextInput(
        label="Feedback, Suggestions, or Issues",
        style=discord.TextStyle.paragraph,
        placeholder="What features would you like to see? How are current reports working?",
        required=True,
        max_length=2000,
    )
    optional_info = discord.ui.TextInput(
        label="PUBG Clan / Player Name (Optional)",
        style=discord.TextStyle.short,
        placeholder="e.g. All_Father / Creighvan",
        required=False,
        max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await _send_feedback_to_support_server(
            interaction,
            self.feedback_text.value.strip(),
            self.optional_info.value.strip(),
        )
        await interaction.response.send_message(
            "✅ **Thank you for your feedback!**\n"
            "Your suggestions have been sent directly to the development team on our Support Server.\n"
            f"Feel free to join us anytime: {SUPPORT_SERVER_URL}",
            ephemeral=True,
        )


class FeedbackPromptView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Submit Feedback / Suggestions",
        style=discord.ButtonStyle.primary,
        emoji="💬",
        custom_id="pubg_tracker:feedback_modal_btn",
    )
    async def feedback_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FeedbackModal())


@bot.tree.command(description="[Admin] Post a feedback & suggestions prompt to a channel in this server")
@app_commands.describe(
    channel="Channel to post the feedback prompt in (defaults to current channel)",
    secret_key="Optional admin secret key to unlock this command",
)
@app_commands.default_permissions(administrator=True)
async def askfeedback(
    interaction: discord.Interaction,
    channel: discord.TextChannel = None,
    secret_key: str = None,
):
    if not await _is_admin_authorized(interaction, secret_key):
        await interaction.response.send_message("⛔ You are not authorized to use this command.", ephemeral=True)
        return

    target_channel = channel or interaction.channel
    if not isinstance(target_channel, discord.TextChannel):
        await interaction.response.send_message("Please specify a valid text channel.", ephemeral=True)
        return

    embed = build_feedback_prompt_embed()
    try:
        await target_channel.send(embed=embed, view=FeedbackPromptView())
        await interaction.response.send_message(
            f"✅ Feedback prompt has been posted in {target_channel.mention}!",
            ephemeral=True,
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ The bot does not have permission to send messages in {target_channel.mention}.",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to send message: {e}", ephemeral=True)


async def main():
    try:
        async with bot:
            await bot.start(DISCORD_TOKEN)
    finally:
        await pubg.close()


if __name__ == "__main__":
    asyncio.run(main())

