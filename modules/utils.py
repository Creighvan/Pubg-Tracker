"""
Pure utility helper functions for the PUBG Tracker bot.

These functions only take arguments and return values — no bot, no pubg,
no storage calls. They are moved here to avoid code duplication and
improve testability.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from modules.config import EASTERN


def _safe_div(a: float, b: float) -> float:
    """Safe division that returns 0.0 if denominator is zero."""
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
    """Convert an ISO timestamp string to Eastern time."""
    if not iso_timestamp:
        return None
    try:
        return datetime.fromisoformat(iso_timestamp).astimezone(EASTERN)
    except (TypeError, ValueError):
        return None


def _format_eastern_time(when: datetime) -> str:
    """Format a datetime as a readable Eastern time string."""
    return when.strftime("%A, %b %d at %I:%M %p %Z")


def _next_daily_report(hour: int, minute: int, posted_at: str | None) -> str:
    """Calculate when the next daily report is due."""
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
    """Calculate when the next interval-based report is due."""
    posted = _as_eastern(posted_at)
    if posted is None:
        return "On the next scheduler check (within about 15 minutes)"
    next_time = posted + timedelta(hours=interval_hours)
    if next_time <= datetime.now(EASTERN):
        return "Due now (the scheduler checks about every 15 minutes)"
    return _format_eastern_time(next_time)


def _next_weekly_report(weekday: int, hour: int, minute: int, posted_at: str | None) -> str:
    """Calculate when the next weekly report is due."""
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
    """Format a channel ID as a Discord mention or 'Not configured'."""
    return f"<#{channel_id}>" if channel_id else "Not configured"
