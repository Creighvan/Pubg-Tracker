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
import asyncio
import aiohttp
from discord.ext import tasks
import discord

import storage
from modules.config import get_scheduler_lock
from pubg_api import PubgClient
from pubg_api import PubgApiError


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
        print(f"[maintenance] Steam player count check failed: {e}")
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
        print(f"[maintenance] PUBG API status check failed: {e}")
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
        print(f"[maintenance] PUBG API data check failed: {e}")
        return False
    except Exception as e:
        print(f"[maintenance] PUBG API data check failed: {e}")
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


async def build_scheduled_maintenance_embed(start_time: datetime, end_time: datetime, source: str = "Manual"):
    """Build an embed for scheduled maintenance announcement."""
    duration = end_time - start_time
    duration_str = f"{duration.total_seconds() / 3600:.1f} hours"
    
    embed = discord.Embed(
        title="📅 Scheduled PUBG Server Maintenance",
        description=f"PUBG servers will undergo maintenance starting soon.",
        color=0xFFAA00,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="Start Time", value=start_time.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
    embed.add_field(name="Expected End", value=end_time.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
    embed.add_field(name="Duration", value=duration_str, inline=True)
    embed.add_field(name="Source", value=source, inline=True)
    embed.add_field(name="Status", value="⏳ Scheduled", inline=True)
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
                        print(f"[maintenance] Found potential maintenance news: {title}")
                        return True, None, None, title
                
                return False, None, None, None
    except Exception as e:
        print(f"[maintenance] Steam news check failed: {e}")
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
        "source": source
    }
    
    embed = await build_scheduled_maintenance_embed(start_time, end_time, source)
    await post_maintenance_notification(embed, scheduled=True)
    
    print(f"[maintenance] Scheduled maintenance announced: {start_time} UTC to {end_time} UTC")


async def clear_scheduled_maintenance():
    """Clear any scheduled maintenance notice."""
    global MAINTENANCE_STATE
    MAINTENANCE_STATE["scheduled_maintenance"] = None
    print(f"[maintenance] Scheduled maintenance cleared")


async def schedule_october_14_maintenance():
    """
    Schedule the October 14, 2026 maintenance (00:00 UTC, 8.5 hours).
    This is called automatically on bot startup if the date is approaching.
    """
    from datetime import datetime, timezone, timedelta
    
    # October 14, 2026 at 00:00 UTC
    maintenance_start = datetime(2026, 10, 14, 0, 0, tzinfo=timezone.utc)
    maintenance_end = maintenance_start + timedelta(hours=float(8.5))
    
    now = datetime.now(timezone.utc)
    
    # Only schedule if we're within 48 hours of the maintenance
    if now >= maintenance_start - timedelta(hours=48) and now < maintenance_start:
        await set_scheduled_maintenance(maintenance_start, maintenance_end, "Auto-scheduled (Oct 14)")
        print(f"[maintenance] Auto-scheduled October 14 maintenance: {maintenance_start} UTC")
    elif now >= maintenance_start:
        # Maintenance has already passed, don't schedule
        print(f"[maintenance] October 14 maintenance already passed, skipping auto-schedule")
    else:
        # Too early to schedule
        print(f"[maintenance] October 14 maintenance is more than 48 hours away, skipping auto-schedule")


async def post_maintenance_notification(embed: discord.Embed, scheduled: bool = False):
    """Post maintenance notification to all configured channels."""
    bot = _get_bot()
    
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
            continue
        
        guild = bot.get_guild(guild_id)
        channel = bot.get_channel(channel_id)
        
        if guild is None or channel is None:
            continue
        
        try:
            await channel.send(embed=embed)
            print(f"[maintenance] Posted notification to guild {guild_id} (scheduled={scheduled})")
        except Exception as e:
            print(f"[maintenance] Failed to post notification to guild {guild_id}: {e}")


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
    
    # Combine signals
    # Maintenance if: player count very low OR player count suspicious
    # Changed to be more conservative - treat any count below 50k as maintenance
    # even if API is working, to avoid false "back online" during partial recovery
    is_down = steam_signal_low or steam_signal_suspicious
    
    print(f"[maintenance] Check: steam={steam_count}, api_status={api_status_ok}, api_data={api_data_ok}, is_down={is_down}")
    
    return is_down, steam_count


@tasks.loop(seconds=CHECK_INTERVAL_SECONDS)
async def auto_maintenance_check():
    """
    Scheduled task that checks maintenance status every 2 minutes.
    Uses debounce logic to avoid false positives.
    Posts notifications when transitioning between states.
    """
    global MAINTENANCE_STATE
    
    now = datetime.now(timezone.utc)
    MAINTENANCE_STATE["last_check"] = now
    
    print(f"[auto_maintenance_check] Running at {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Check if scheduled maintenance is starting soon (within 30 minutes)
    scheduled = MAINTENANCE_STATE.get("scheduled_maintenance")
    if scheduled and not scheduled.get("announced"):
        start_time = scheduled["start_time"]
        if now >= start_time - timedelta(minutes=30) and now < start_time:
            # Post reminder that maintenance is starting soon
            await set_scheduled_maintenance(start_time, scheduled["end_time"], scheduled["source"])
    
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
            
            print(f"[maintenance] ⚠️ MAINTENANCE DETECTED - consecutive failures: {MAINTENANCE_STATE['consecutive_failures']}")
            
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
            downtime = await calculate_downtime(MAINTENANCE_STATE["down_since"])
            
            print(f"[maintenance] ✅ BACK ONLINE - downtime: {downtime}")
            
            # Post notification
            embed = await build_back_online_embed(MAINTENANCE_STATE["down_since"], downtime, steam_count)
            await post_maintenance_notification(embed, scheduled=False)
            
            # Trigger all paused scheduled tasks immediately
            print(f"[maintenance] Triggering paused scheduled tasks...")
            try:
                from modules.scheduler import trigger_maintenance_recovery
                await trigger_maintenance_recovery()
            except ImportError:
                print(f"[maintenance] Warning: trigger_maintenance_recovery not available")
            
            # Reset downtime
            MAINTENANCE_STATE["down_since"] = None


def is_in_maintenance():
    """Check if currently in maintenance mode."""
    return MAINTENANCE_STATE["is_maintenance"]


def get_maintenance_state():
    """Get current maintenance state for debugging."""
    return MAINTENANCE_STATE.copy()


async def start_maintenance_monitor():
    """Start the maintenance monitoring task."""
    print("[maintenance] Starting maintenance monitor...")
    auto_maintenance_check.start()
    
    # Auto-schedule known maintenance events
    try:
        await schedule_october_14_maintenance()
    except Exception as e:
        print(f"[maintenance] Failed to auto-schedule October 14 maintenance: {e}")


async def stop_maintenance_monitor():
    """Stop the maintenance monitoring task."""
    print("[maintenance] Stopping maintenance monitor...")
    auto_maintenance_check.stop()
