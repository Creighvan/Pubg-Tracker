"""
PUBG Server Maintenance Detection Module

This module monitors PUBG server status by combining multiple signals:
1. Steam concurrent player count (app ID 578080)
2. PUBG API /status endpoint
3. PUBG API actual data calls
4. Scheduled maintenance notices (manual or Steam news)

Uses debounce logic to avoid false positives from transient errors.
Posts embed notifications when servers go into/out of maintenance.
Integrates with the existing scheduler to pause other tasks during maintenance.
When servers come back online, immediately triggers all skipped scheduled tasks.
"""

from datetime import datetime, timezone, timedelta
import json
import os
import aiohttp
from discord.ext import tasks
import discord
import logging

import storage
from pubg_api import PubgApiError

logger = logging.getLogger(__name__)

# Steam API constants
STEAM_APP_ID = "578080"
STEAM_PLAYER_COUNT_URL = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={STEAM_APP_ID}"
STEAM_NEWS_URL = f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid={STEAM_APP_ID}&count=3&maxlength=300"

# Maintenance state
MAINTENANCE_STATE = {
    "is_maintenance": False,
    "down_since": None,
    "consecutive_failures": 0,
    "consecutive_successes": 0,
    "last_check": None,
    "scheduled_maintenance": None,  # {start_time, end_time, announced}
}

# Debounce thresholds
FAILURE_THRESHOLD = 3  # consecutive failures before declaring maintenance
SUCCESS_THRESHOLD = 2  # consecutive successes before declaring back online
CHECK_INTERVAL_SECONDS = 120  # check every 2 minutes

# Player count thresholds for maintenance detection
NORMAL_PLAYER_COUNT_MIN = 100000  # below this is suspicious (raised from 50k)
MAINTENANCE_PLAYER_COUNT_MAX = 50000  # at or below this is definitely maintenance (raised from 10k)


# The bot restarts often (deploys, reboots), and the state above only lives in
# memory. Without saving it, a restart in the middle of maintenance would post a
# second "maintenance detected" notice and lose the real downtime, and a restart
# right when maintenance ends would never post "back online". The state is
# therefore saved to this small file and read back at startup.
STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maintenance_state.json")


def _dt_to_str(value):
    return value.isoformat() if isinstance(value, datetime) else None


def _str_to_dt(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _save_state():
    """Write the parts of MAINTENANCE_STATE that must survive a restart."""
    try:
        scheduled = MAINTENANCE_STATE.get("scheduled_maintenance")
        data = {
            "is_maintenance": bool(MAINTENANCE_STATE["is_maintenance"]),
            "down_since": _dt_to_str(MAINTENANCE_STATE["down_since"]),
            "scheduled_maintenance": None if not scheduled else {
                "start_time": _dt_to_str(scheduled["start_time"]),
                "end_time": _dt_to_str(scheduled["end_time"]),
                "source": scheduled.get("source", "Manual"),
                "announced": bool(scheduled.get("announced")),
                "reminded": bool(scheduled.get("reminded")),
            },
        }
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, STATE_FILE)  # atomic: never leaves a half-written file
    except Exception as e:
        logger.error(f"[maintenance] Could not save maintenance state: {e}")


def _load_state():
    """Restore saved maintenance state at startup (no file = first run)."""
    try:
        if not os.path.exists(STATE_FILE):
            return
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        MAINTENANCE_STATE["is_maintenance"] = bool(data.get("is_maintenance"))
        MAINTENANCE_STATE["down_since"] = _str_to_dt(data.get("down_since"))
        if MAINTENANCE_STATE["is_maintenance"] and MAINTENANCE_STATE["down_since"] is None:
            MAINTENANCE_STATE["down_since"] = datetime.now(timezone.utc)
        sched = data.get("scheduled_maintenance")
        if sched:
            start, end = _str_to_dt(sched.get("start_time")), _str_to_dt(sched.get("end_time"))
            if start and end:
                MAINTENANCE_STATE["scheduled_maintenance"] = {
                    "start_time": start, "end_time": end,
                    "source": sched.get("source", "Manual"),
                    "announced": bool(sched.get("announced")),
                    "reminded": bool(sched.get("reminded")),
                }
        logger.info(
            f"[maintenance] Restored state: is_maintenance={MAINTENANCE_STATE['is_maintenance']}, "
            f"down_since={MAINTENANCE_STATE['down_since']}, "
            f"scheduled={'yes' if MAINTENANCE_STATE['scheduled_maintenance'] else 'no'}"
        )
    except Exception as e:
        logger.error(f"[maintenance] Could not load maintenance state (starting fresh): {e}")


def _get_bot():
    """Late-binding helper to avoid stale imports."""
    from modules.config import bot
    return bot


def _get_pubg():
    """Late-binding helper to avoid stale imports."""
    from modules.config import pubg
    return pubg


async def get_steam_player_count():
    """
    Fetch current Steam player count for PUBG.
    Returns None on failure, otherwise returns integer count.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(STEAM_PLAYER_COUNT_URL, timeout=10) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                return data.get("response", {}).get("player_count")
    except Exception as e:
        logger.error(f"[maintenance] Steam player count check failed: {e}")
        return None


async def check_pubg_api_status():
    """
    Check PUBG API /status endpoint.
    Returns True if API is healthy, False otherwise.
    """
    try:
        pubg = _get_pubg()
        # Try a lightweight status check
        await pubg.get_api_status()
        return True
    except (PubgApiError, Exception) as e:
        logger.error(f"[maintenance] PUBG API status check failed: {e}")
        return False


async def check_pubg_api_data():
    """
    Check if PUBG API can actually return data (not just status endpoint).
    Returns True if data calls work, False otherwise.
    """
    try:
        pubg = _get_pubg()
        # Try a simple player lookup as a real data test
        # Use a lightweight endpoint that tests actual data retrieval
        await pubg.get_players_by_name(["test"])  # This will fail but tests the endpoint
        return True
    except PubgApiError as e:
        # Expected to fail with no players found, but tests API connectivity
        if "not found" in str(e).lower() or "no players" in str(e).lower():
            return True
        logger.error(f"[maintenance] PUBG API data check failed: {e}")
        return False
    except Exception as e:
        logger.error(f"[maintenance] PUBG API data check failed: {e}")
        return False


async def build_maintenance_embed(maintenance_start: datetime, player_count: int = None):
    """Build an embed for maintenance start notification."""
    embed = discord.Embed(
        title="⚠️ PUBG Servers Under Maintenance",
        description="PUBG game servers are currently under maintenance. Scheduled reports are paused.",
        color=0xFF0000,
        timestamp=maintenance_start
    )
    
    if player_count is not None:
        embed.add_field(name="Steam Players", value=f"{player_count:,}", inline=True)
    
    embed.add_field(name="Status", value="🔴 Maintenance", inline=True)
    embed.add_field(name="Scheduled Reports", value="⏸️ Paused", inline=True)
    embed.set_footer(text="Automatic monitoring - will notify when servers are back online")
    
    return embed


async def build_back_online_embed(maintenance_start: datetime, downtime: str, player_count: int = None):
    """Build an embed for back online notification."""
    embed = discord.Embed(
        title="✅ PUBG Servers Back Online",
        description="PUBG game servers are back online. Running all paused scheduled reports now.",
        color=0x00FF00,
        timestamp=datetime.now(timezone.utc)
    )
    
    if player_count is not None:
        embed.add_field(name="Steam Players", value=f"{player_count:,}", inline=True)
    
    embed.add_field(name="Status", value="🟢 Online", inline=True)
    embed.add_field(name="Downtime", value=downtime, inline=True)
    embed.add_field(name="Scheduled Reports", value="▶️ Running now", inline=True)
    embed.set_footer(text="Automatic monitoring")
    
    return embed


async def build_scheduled_maintenance_embed(start_time: datetime, end_time: datetime, source: str = "Manual", reminder: bool = False):
    """Build an embed for scheduled maintenance announcement (or its "starting soon" reminder)."""
    duration = end_time - start_time
    duration_str = f"{duration.total_seconds() / 3600:.1f} hours"
    
    embed = discord.Embed(
        title="⏰ PUBG Maintenance Starting Soon" if reminder else "📅 Scheduled PUBG Server Maintenance",
        description=("PUBG servers are about to go down for maintenance." if reminder
                     else "PUBG servers will undergo maintenance starting soon."),
        color=0xFFAA00,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="Start Time", value=start_time.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
    embed.add_field(name="Expected End", value=end_time.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
    embed.add_field(name="Duration", value=duration_str, inline=True)
    embed.add_field(name="Source", value=source, inline=True)
    embed.add_field(name="Status", value="⏰ Starting soon" if reminder else "⏳ Scheduled", inline=True)
    embed.set_footer(text="Automatic monitoring will confirm when maintenance actually starts")
    
    return embed


async def check_steam_news():
    """
    Check Steam news for PUBG maintenance announcements.
    Returns (has_maintenance, start_time, end_time, title) if found, else (False, None, None, None).
    Note: This is optional and unverified - PUBG may not always post to Steam news.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(STEAM_NEWS_URL, timeout=10) as response:
                if response.status != 200:
                    return False, None, None, None
                
                data = await response.json()
                news_items = data.get("appnews", {}).get("newsitems", [])
                
                for item in news_items:
                    title = item.get("title", "").lower()
                    feed_label = item.get("feedlabel", "").lower()
                    
                    # Look for maintenance-related keywords
                    keywords = ["maintenance", "downtime", "server", "patch", "update"]
                    if any(keyword in title or keyword in feed_label for keyword in keywords):
                        # Try to extract time from title or description
                        # This is basic - could be enhanced with regex
                        logger.info(f"[maintenance] Found potential maintenance news: {title}")
                        return True, None, None, title
                
                return False, None, None, None
    except Exception as e:
        logger.error(f"[maintenance] Steam news check failed: {e}")
        return False, None, None, None


async def set_scheduled_maintenance(start_time: datetime, end_time: datetime, source: str = "Manual"):
    """
    Set a scheduled maintenance notice.
    Posts notification to all configured maintenance channels.
    """
    global MAINTENANCE_STATE
    
    MAINTENANCE_STATE["scheduled_maintenance"] = {
        "start_time": start_time,
        "end_time": end_time,
        "announced": True,
        "reminded": False,
        "source": source
    }
    _save_state()
    
    embed = await build_scheduled_maintenance_embed(start_time, end_time, source)
    await post_maintenance_notification(embed, scheduled=True)

    logger.info(f"[maintenance] Scheduled maintenance announced: {start_time} UTC to {end_time} UTC")


async def clear_scheduled_maintenance():
    """Clear any scheduled maintenance notice."""
    global MAINTENANCE_STATE
    MAINTENANCE_STATE["scheduled_maintenance"] = None
    _save_state()
    logger.info("[maintenance] Scheduled maintenance cleared")


async def post_maintenance_notification(embed: discord.Embed, scheduled: bool = False):
    """Post maintenance notification to all configured channels."""
    # Same channel lookup the scheduled reports use (cache first, then Discord's
    # REST API), so a channel that is missing from the cache is still found.
    from modules.scheduler import _get_channel_cached

    posted = skipped = failed = 0

    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        
        # Use scheduled maintenance channel for scheduled notices, regular channel for status updates
        if scheduled:
            channel_id = guild_cfg.get("scheduled_maintenance_channel_id")
            # Fall back to regular maintenance channel if scheduled channel not set
            if channel_id is None:
                channel_id = guild_cfg.get("maintenance_channel_id")
        else:
            channel_id = guild_cfg.get("maintenance_channel_id")
        
        if channel_id is None:
            continue  # this server has no maintenance channel set

        channel = await _get_channel_cached(channel_id, guild_id)
        if channel is None:
            skipped += 1
            logger.warning(
                f"[maintenance] Guild {guild_id}: channel {channel_id} not found or inaccessible, "
                f"skipping notification (scheduled={scheduled})"
            )
            continue
        
        try:
            await channel.send(embed=embed)
            posted += 1
            logger.info(f"[maintenance] Posted notification to guild {guild_id} (scheduled={scheduled})")
        except Exception as e:
            failed += 1
            logger.error(f"[maintenance] Failed to post notification to guild {guild_id}: {e}")

    logger.info(f"[maintenance] Notification finished: {posted} posted, {skipped} skipped, {failed} failed (scheduled={scheduled})")


async def calculate_downtime(maintenance_start: datetime) -> str:
    """Calculate human-readable downtime duration."""
    delta = datetime.now(timezone.utc) - maintenance_start
    total_seconds = int(delta.total_seconds())
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


async def check_maintenance_status():
    """
    Main maintenance check logic using multiple signals with debounce.
    Returns True if in maintenance, False otherwise.
    """
    global MAINTENANCE_STATE
    
    # Signal 1: Steam player count
    steam_count = await get_steam_player_count()
    steam_signal_low = steam_count is not None and steam_count < MAINTENANCE_PLAYER_COUNT_MAX
    steam_signal_suspicious = steam_count is not None and steam_count < NORMAL_PLAYER_COUNT_MIN
    
    # Signal 2: PUBG API status
    api_status_ok = await check_pubg_api_status()
    
    # Signal 3: PUBG API data calls
    api_data_ok = await check_pubg_api_data()
    
    # Combine signals.
    # PUBG's normal Steam count is far above 100k (about 240-260k even in the
    # small hours, 700k+ at peak), while a real maintenance reads around 18k.
    # So anything under 100k means servers are down or only partly back, and is
    # treated as maintenance even when the API answers. That avoids a false
    # "back online" notice during a partial recovery. If the Steam number could
    # not be fetched at all, both PUBG API checks failing counts as down.
    api_down = (not api_status_ok) and (not api_data_ok)
    steam_unavailable = steam_count is None
    is_down = steam_signal_low or steam_signal_suspicious or (steam_unavailable and api_down)

    logger.info(f"[maintenance] Check: steam={steam_count}, api_status={api_status_ok}, api_data={api_data_ok}, is_down={is_down}")

    return is_down, steam_count


async def _maintenance_tick():
    """
    One maintenance check (runs every 2 minutes from auto_maintenance_check).
    Uses debounce logic to avoid false positives.
    Posts notifications when transitioning between states.
    """
    global MAINTENANCE_STATE
    
    now = datetime.now(timezone.utc)
    MAINTENANCE_STATE["last_check"] = now

    logger.info(f"[auto_maintenance_check] Running at {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Scheduled maintenance: one "starting soon" reminder within 30 minutes of the
    # start, then forget the schedule once it is over.
    scheduled = MAINTENANCE_STATE.get("scheduled_maintenance")
    if scheduled:
        start_time, end_time = scheduled["start_time"], scheduled["end_time"]
        if not scheduled.get("reminded") and start_time - timedelta(minutes=30) <= now < start_time:
            scheduled["reminded"] = True
            _save_state()
            logger.info(f"[maintenance] Posting 'starting soon' reminder for {start_time} UTC")
            reminder = await build_scheduled_maintenance_embed(start_time, end_time, scheduled.get("source", "Manual"), reminder=True)
            await post_maintenance_notification(reminder, scheduled=True)
        elif now > end_time + timedelta(hours=1):
            logger.info("[maintenance] Scheduled maintenance window is over, clearing it")
            MAINTENANCE_STATE["scheduled_maintenance"] = None
            _save_state()
    
    # Check current status
    is_down, steam_count = await check_maintenance_status()
    
    if is_down:
        # Potential maintenance - increment failure counter
        MAINTENANCE_STATE["consecutive_failures"] += 1
        MAINTENANCE_STATE["consecutive_successes"] = 0
        
        # Check if we've hit the threshold
        if MAINTENANCE_STATE["consecutive_failures"] >= FAILURE_THRESHOLD and not MAINTENANCE_STATE["is_maintenance"]:
            # Transition to maintenance
            MAINTENANCE_STATE["is_maintenance"] = True
            MAINTENANCE_STATE["down_since"] = now
            _save_state()

            logger.info(f"[maintenance] ⚠️ MAINTENANCE DETECTED - consecutive failures: {MAINTENANCE_STATE['consecutive_failures']}")

            # Post notification
            embed = await build_maintenance_embed(now, steam_count)
            await post_maintenance_notification(embed, scheduled=False)
    else:
        # Potentially back online - increment success counter
        MAINTENANCE_STATE["consecutive_successes"] += 1
        MAINTENANCE_STATE["consecutive_failures"] = 0
        
        # Check if we've hit the threshold
        if MAINTENANCE_STATE["consecutive_successes"] >= SUCCESS_THRESHOLD and MAINTENANCE_STATE["is_maintenance"]:
            # Transition back online
            MAINTENANCE_STATE["is_maintenance"] = False
            if MAINTENANCE_STATE["down_since"] is None:
                MAINTENANCE_STATE["down_since"] = now
            downtime = await calculate_downtime(MAINTENANCE_STATE["down_since"])

            logger.info(f"[maintenance] ✅ BACK ONLINE - downtime: {downtime}")

            # Post notification
            embed = await build_back_online_embed(MAINTENANCE_STATE["down_since"], downtime, steam_count)
            await post_maintenance_notification(embed, scheduled=False)

            # Trigger all paused scheduled tasks immediately
            logger.info("[maintenance] Triggering paused scheduled tasks...")
            try:
                from modules.scheduler import trigger_maintenance_recovery
                await trigger_maintenance_recovery()
            except ImportError:
                logger.error("[maintenance] Warning: trigger_maintenance_recovery not available")
            
            # Reset downtime
            MAINTENANCE_STATE["down_since"] = None
            _save_state()


@tasks.loop(seconds=CHECK_INTERVAL_SECONDS)
async def auto_maintenance_check():
    """Run one maintenance check; an unexpected error must never stop the monitor."""
    try:
        await _maintenance_tick()
    except Exception as e:
        logger.error(f"[maintenance] Check failed unexpectedly (monitor keeps running): {e}", exc_info=True)


def is_in_maintenance():
    """Check if currently in maintenance mode."""
    return MAINTENANCE_STATE["is_maintenance"]


def get_maintenance_state():
    """Get current maintenance state for debugging."""
    return MAINTENANCE_STATE.copy()


async def start_maintenance_monitor():
    """Start the maintenance monitoring task."""
    logger.info("[maintenance] Starting maintenance monitor...")
    _load_state()
    if not auto_maintenance_check.is_running():
        auto_maintenance_check.start()


async def stop_maintenance_monitor():
    """Stop the maintenance monitoring task."""
    logger.info("[maintenance] Stopping maintenance monitor...")
    auto_maintenance_check.stop()
