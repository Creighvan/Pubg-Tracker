"""
PUBG Server Maintenance Detection Module

This module monitors PUBG server status by combining multiple signals:
1. Steam concurrent player count (app ID 578080)
2. PUBG API /status endpoint
3. PUBG API actual data calls

Uses debounce logic to avoid false positives from transient errors.
Posts embed notifications when servers go into/out of maintenance.
Integrates with the existing scheduler to pause other tasks during maintenance.
"""

from datetime import datetime, timezone
import asyncio
import aiohttp
from discord.ext import tasks
import discord

import storage
from modules.config import get_scheduler_lock
from pubg_api import PubgClient, PubgApiError


# Steam API constants
STEAM_APP_ID = "578080"
STEAM_PLAYER_COUNT_URL = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={STEAM_APP_ID}"

# Maintenance state
MAINTENANCE_STATE = {
    "is_maintenance": False,
    "down_since": None,
    "consecutive_failures": 0,
    "consecutive_successes": 0,
    "last_check": None,
}

# Debounce thresholds
FAILURE_THRESHOLD = 3  # consecutive failures before declaring maintenance
SUCCESS_THRESHOLD = 2  # consecutive successes before declaring back online
CHECK_INTERVAL_SECONDS = 120  # check every 2 minutes

# Player count thresholds for maintenance detection
NORMAL_PLAYER_COUNT_MIN = 50000  # below this is suspicious
MAINTENANCE_PLAYER_COUNT_MAX = 10000  # at or below this is definitely maintenance


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
        await pubg.get_status()
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
        # Try a simple shards list as a real data test
        # This is lightweight and tests actual API data retrieval
        await pubg.get_shards()
        return True
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
        description="PUBG game servers are back online. Scheduled reports will resume.",
        color=0x00FF00,
        timestamp=datetime.now(timezone.utc)
    )
    
    if player_count is not None:
        embed.add_field(name="Steam Players", value=f"{player_count:,}", inline=True)
    
    embed.add_field(name="Status", value="🟢 Online", inline=True)
    embed.add_field(name="Downtime", value=downtime, inline=True)
    embed.add_field(name="Scheduled Reports", value="▶️ Resuming", inline=True)
    embed.set_footer(text="Automatic monitoring")
    
    return embed


async def post_maintenance_notification(embed: discord.Embed):
    """Post maintenance notification to all configured channels."""
    bot = _get_bot()
    
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        channel_id = guild_cfg.get("maintenance_channel_id")
        
        if channel_id is None:
            continue
        
        guild = bot.get_guild(guild_id)
        channel = bot.get_channel(channel_id)
        
        if guild is None or channel is None:
            continue
        
        try:
            await channel.send(embed=embed)
            print(f"[maintenance] Posted notification to guild {guild_id}")
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
    # Maintenance if: player count very low OR (player count suspicious AND API not working)
    is_down = steam_signal_low or (steam_signal_suspicious and not (api_status_ok and api_data_ok))
    
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
            await post_maintenance_notification(embed)
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
            await post_maintenance_notification(embed)
            
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


async def stop_maintenance_monitor():
    """Stop the maintenance monitoring task."""
    print("[maintenance] Stopping maintenance monitor...")
    auto_maintenance_check.stop()
