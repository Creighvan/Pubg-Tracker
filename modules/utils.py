"""
Pure utility helper functions for the PUBG Tracker bot.

These functions only take arguments and return values — no bot, no pubg,
no storage calls. They are moved here to avoid code duplication and
improve testability.
"""

from datetime import datetime, timezone, timedelta, time

# PUBG daily reset time in UTC (confirmed by PUBG documentation)
PUBG_DAILY_RESET_UTC = time(2, 0)  # 02:00 UTC


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


def _is_due(guild_cfg: dict, hour_key: str, minute_key: str, posted_at_key: str, default_interval_hours: int) -> bool:
    """
    Two scheduling modes, chosen per-report:
    - If hour_key is set (0-23): post once per UTC calendar day, at that
      UTC hour:minute (minute_key, 0/15/30/45). Uses a 15-minute
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
        now_utc = datetime.now(timezone.utc)
        target_total = target_hour * 60 + target_minute
        now_total = now_utc.hour * 60 + now_utc.minute
        if not (target_total <= now_total < target_total + 15):
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


def _is_sunday_donation_due(guild_cfg: dict) -> bool:
    """Whether this server's opt-in donation message is due this Sunday."""
    now_utc = datetime.now(timezone.utc)
    target_minute = guild_cfg.get("donation_hour_utc", 12) * 60 + guild_cfg.get("donation_minute_utc", 0)
    now_minute = now_utc.hour * 60 + now_utc.minute
    # Same retry rule as the other weekly reports: due any time after the
    # target time on Sunday, so a failed attempt retries instead of the
    # whole week being skipped.
    if now_utc.weekday() != 6 or now_minute < target_minute:
        return False
    posted_at = guild_cfg.get("donation_posted_at")
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


def _format_utc_time(when: datetime) -> str:
    """Format a datetime as a readable UTC time string."""
    return when.strftime("%A, %b %d at %H:%M UTC")


def _next_daily_report(hour: int, minute: int, posted_at: str | None) -> str:
    """Calculate when the next daily report is due."""
    now = datetime.now(timezone.utc)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    posted = _as_utc(posted_at)
    has_posted_today = posted is not None and posted.date() == now.date()
    if target <= now < target + timedelta(minutes=15) and not has_posted_today:
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
