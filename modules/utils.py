"""
Pure utility helper functions for the PUBG Tracker bot.

These functions only take arguments and return values — no bot, no pubg,
no storage calls. They are moved here to avoid code duplication and
improve testability.
"""

import unicodedata
from datetime import datetime, timezone, timedelta, time

# PUBG daily reset time in UTC (confirmed by PUBG documentation)
PUBG_DAILY_RESET_UTC = time(2, 0)  # 02:00 UTC


def normalize_player_name(name: str) -> str:
    """
    Normalize a PUBG player name for consistent identity matching.

    Uses Unicode NFKC normalization and casefold() to handle:
    - Different Unicode representations of the same characters
    - Case-insensitive matching across languages
    - Leading/trailing whitespace

    Args:
        name: The raw player name

    Returns:
        Normalized name suitable for identity keys
    """
    return unicodedata.normalize("NFKC", name).strip().casefold()


def get_current_pubg_day(now_utc: datetime = None) -> datetime:
    """
    Get the start of the current PUBG day in UTC.
    
    PUBG's daily reset occurs at 02:00 UTC. This function returns the
    datetime of the most recent 02:00 UTC reset point.
    
    Args:
        now_utc: Current UTC datetime (defaults to now if None)
    
    Returns:
        datetime: The start of the current PUBG day in UTC
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    
    # If it's before 02:00 UTC, the PUBG day started yesterday
    if now_utc.time() < PUBG_DAILY_RESET_UTC:
        return now_utc.replace(hour=2, minute=0, second=0, microsecond=0) - timedelta(days=1)
    else:
        return now_utc.replace(hour=2, minute=0, second=0, microsecond=0)


def get_next_pubg_reset(now_utc: datetime = None) -> datetime:
    """
    Get the next PUBG daily reset time in UTC.
    
    Args:
        now_utc: Current UTC datetime (defaults to now if None)
    
    Returns:
        datetime: The next 02:00 UTC reset point
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    
    current_day_start = get_current_pubg_day(now_utc)
    next_reset = current_day_start + timedelta(days=1)
    return next_reset


def _safe_div(a: float, b: float) -> float:
    """Safe division that returns 0.0 if denominator is zero."""
    return a / b if b else 0.0


# How long after its scheduled time a fixed-time daily report may still post
# (catch-up for delays/restarts). Kept under a day so a report never posts
# "yesterday's" slot the next morning.
DAILY_CATCHUP_MINUTES = 360


def _is_due(guild_cfg: dict, hour_key: str, minute_key: str, posted_at_key: str, default_interval_hours: int) -> bool:
    """
    Two scheduling modes, chosen per-report:
    - If hour_key is set (0-23): post once per UTC calendar day, at that
      UTC hour:minute (minute_key, 0/15/30/45). Due ANY time from that
      moment until DAILY_CATCHUP_MINUTES later (default 6 hours), as long as
      it hasn't posted today. A narrow 15-minute window got missed whenever
      the loop was held up (waiting on the shared scheduler lock or a slow
      PUBG API) or the bot restarted, which silently skipped the whole day.
      The posted marker is only written after a successful send, so a failed
      attempt is retried on the next 15-minute tick.
    - If hour_key is None (default): fall back to the old "every N hours
      since last post" behavior, using default_interval_hours (or
      guild_cfg["post_interval_hours"] for the digest specifically).
    """
    target_hour = guild_cfg.get(hour_key)
    posted_at = guild_cfg.get(posted_at_key)

    if target_hour is not None:
        target_minute = guild_cfg.get(minute_key, 0)
        now_utc = datetime.now(timezone.utc)
        target_total = target_hour * 60 + target_minute
        now_total = now_utc.hour * 60 + now_utc.minute
        if not (target_total <= now_total < target_total + DAILY_CATCHUP_MINUTES):
            return False
        if not posted_at:
            return True
        posted_utc = datetime.fromisoformat(posted_at).astimezone(timezone.utc)
        return posted_utc.date() != now_utc.date()

    now = datetime.now(timezone.utc)
    interval_hours = guild_cfg.get("post_interval_hours", default_interval_hours) if hour_key == "digest_hour_utc" else default_interval_hours
    if not posted_at:
        return True
    posted_dt = datetime.fromisoformat(posted_at)
    return now - posted_dt >= timedelta(hours=interval_hours)


def _is_weekly_due(
    guild_cfg: dict,
    weekday_key: str = "clan_weekday_utc",
    hour_key: str = "clan_hour_utc",
    minute_key: str = "clan_minute_utc",
    posted_key: str = "clan_posted_at",
) -> bool:
    """Whether a configured weekly report is due this UTC week."""
    weekday = guild_cfg.get(weekday_key)
    if weekday is None:
        return False
    now_utc = datetime.now(timezone.utc)
    target_minute = guild_cfg.get(hour_key, 0) * 60 + guild_cfg.get(minute_key, 0)
    now_minute = now_utc.hour * 60 + now_utc.minute
    # Due any time AFTER the target time on the scheduled weekday — not just
    # during the first 15 minutes. The posted marker is only written after a
    # successful post, so a failed attempt is retried on the next 15-minute
    # tick instead of silently skipping the whole week.
    if now_utc.weekday() != weekday or now_minute < target_minute:
        return False
    posted_at = guild_cfg.get(posted_key)
    if not posted_at:
        return True
    posted_utc = datetime.fromisoformat(posted_at).astimezone(timezone.utc)
    return posted_utc.isocalendar()[:2] != now_utc.isocalendar()[:2]


def _as_utc(iso_timestamp: str | None) -> datetime | None:
    """Convert an ISO timestamp string to UTC time."""
    if not iso_timestamp:
        return None
    try:
        return datetime.fromisoformat(iso_timestamp).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def discord_time(when: datetime, style: str = "F") -> str:
    """Return a Discord timestamp that every reader sees in THEIR OWN time zone.

    The bot keeps all schedules and settings in UTC. Putting this in a message or
    an embed field/description (not a title or footer, which cannot render it)
    lets Discord convert it to each player's local time automatically.
    Styles: t = 9:00 PM, F = Thursday, November 5, 2026 9:00 PM, R = in 3 hours.
    """
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return f"<t:{int(when.timestamp())}:{style}>"


def next_daily_utc(hour: int, minute: int = 0, now: datetime | None = None) -> datetime:
    """The next moment it is HH:MM UTC (today if still ahead, else tomorrow)."""
    now = now or datetime.now(timezone.utc)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


def next_weekly_utc(weekday: int, hour: int, minute: int = 0, now: datetime | None = None) -> datetime:
    """The next moment it is the given UTC weekday (Monday=0) at HH:MM UTC."""
    now = now or datetime.now(timezone.utc)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    target += timedelta(days=(weekday - now.weekday()) % 7)
    return target if target > now else target + timedelta(days=7)


def utc_with_local(hhmm_utc: str, when: datetime, style: str = "F") -> str:
    """'02:00 UTC · <your local time>' for confirmation messages."""
    return f"{hhmm_utc} UTC · {discord_time(when, style)}"


# Last Active refreshes ONCE a day, shortly after this UTC time (the scheduler checks
# every 15 minutes, so it posts within about 15 minutes of it). Change it here only.
LAST_ACTIVE_RUN_UTC = (3, 0)


def most_recent_slot(hour: int, minute: int = 0, now: datetime | None = None) -> datetime:
    """The latest HH:MM UTC moment that is not in the future (today's, or yesterday's if it has not happened yet)."""
    now = now or datetime.now(timezone.utc)
    slot = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return slot if slot <= now else slot - timedelta(days=1)


def next_last_active_report(posted_at: str | None, now: datetime | None = None) -> str:
    """When Last Active updates next: tomorrow's slot once today's is done, otherwise on the next check."""
    now = now or datetime.now(timezone.utc)
    slot = most_recent_slot(*LAST_ACTIVE_RUN_UTC, now=now)
    try:
        posted = datetime.fromisoformat(posted_at) if posted_at else None
    except ValueError:
        posted = None
    if posted is not None and posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)
    if posted is None or posted < slot:
        return "On the next scheduler check (within about 15 minutes)"
    return _format_utc_time(slot + timedelta(days=1))


def _format_utc_time(when: datetime) -> str:
    """Show a time in each reader's local zone, with the UTC time kept for reference."""
    return f"{discord_time(when, 'F')} ({discord_time(when, 'R')}) · {when.strftime('%H:%M')} UTC"


def _next_daily_report(hour: int, minute: int, posted_at: str | None) -> str:
    """Calculate when the next daily report is due."""
    now = datetime.now(timezone.utc)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    posted = _as_utc(posted_at)
    has_posted_today = posted is not None and posted.date() == now.date()
    if target <= now < target + timedelta(minutes=DAILY_CATCHUP_MINUTES) and not has_posted_today:
        return "Due now (the scheduler checks about every 15 minutes)"
    if target <= now:
        target += timedelta(days=1)
    return _format_utc_time(target)


def _next_interval_report(interval_hours: int, posted_at: str | None) -> str:
    """Calculate when the next interval-based report is due."""
    posted = _as_utc(posted_at)
    if posted is None:
        return "On the next scheduler check (within about 15 minutes)"
    next_time = posted + timedelta(hours=interval_hours)
    if next_time <= datetime.now(timezone.utc):
        return "Due now (the scheduler checks about every 15 minutes)"
    return _format_utc_time(next_time)


def _next_weekly_report(weekday: int, hour: int, minute: int, posted_at: str | None) -> str:
    """Calculate when the next weekly report is due."""
    now = datetime.now(timezone.utc)
    days_until = (weekday - now.weekday()) % 7
    target = (now + timedelta(days=days_until)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    posted = _as_utc(posted_at)
    posted_this_week = posted is not None and posted.isocalendar()[:2] == now.isocalendar()[:2]
    if days_until == 0 and target <= now and not posted_this_week:
        return "Due now (the scheduler checks about every 15 minutes)"
    if target <= now:
        target += timedelta(days=7)
    return _format_utc_time(target)


def _channel_mention(channel_id: int | None) -> str:
    """Format a channel ID as a Discord mention or 'Not configured'."""
    return f"<#{channel_id}>" if channel_id else "Not configured"
