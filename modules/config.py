"""
Shared configuration and state for the PUBG Tracker bot.

This module contains all module-level globals, the bot and pubg client instances,
and shared constants. All other modules import from here rather than redefining
these values.

IMPORTANT: This module must have ZERO imports from other bot modules to avoid
circular imports. Only standard library and external dependencies are allowed.
"""

import asyncio
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# ---------- Environment variables ----------
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
PUBG_API_KEY = os.environ["PUBG_API_KEY"]
PUBG_SHARD = os.environ.get("PUBG_SHARD", "steam")
BOT_ADMIN_KEY = os.environ.get("BOT_ADMIN_KEY", "")
ADMIN_USER_IDS = {int(x.strip()) for x in os.environ.get("ADMIN_USER_IDS", "").split(",") if x.strip().isdigit()}
SUPPORT_SERVER_URL = "https://discord.gg/KEUWmwBYV4"
SUPPORT_SERVER_ID = int(os.environ.get("SUPPORT_SERVER_ID", "1539320166318481459"))
SUPPORT_FEEDBACK_CHANNEL_ID = int(os.environ.get("SUPPORT_FEEDBACK_CHANNEL_ID", "0"))
AUDIT_SERVER_ID = int(os.environ.get("AUDIT_SERVER_ID", "0")) if os.environ.get("AUDIT_SERVER_ID") else None
AUDIT_LOG_CHANNEL_ID = int(os.environ.get("AUDIT_LOG_CHANNEL_ID", "0")) if os.environ.get("AUDIT_LOG_CHANNEL_ID") else None

# ---------- Donation configuration ----------
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

# ---------- Game mode constants ----------
VALID_GAME_MODES = {"squad-fpp", "squad", "duo-fpp", "duo", "solo-fpp", "solo"}
RANKED_MODE_LABELS = {
    "squad": "Squad",
    "duo": "Duo",
    "solo": "Solo",
    "squad-fpp": "Squad",
    "duo-fpp": "Duo",
    "solo-fpp": "Solo",
}

# ---------- Timezone ----------
# America/New_York rather than a fixed UTC-5 offset, so this automatically
# tracks EST/EDT across daylight saving changes instead of drifting an hour
# twice a year.
EASTERN = ZoneInfo("America/New_York")

# ---------- Discord bot setup ----------
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


# ---------- Global state ----------
# Serializes the four scheduled reports so they never run concurrently
# against the PUBG API — running all four at once was overwhelming the
# real PUBG rate limit even though each report respects it individually.
_scheduler_lock = asyncio.Lock()
_commands_synced_once = False
_command_templates = None
_bot_ready_once = False
_bot_started_at = datetime.now(timezone.utc)

# ---------- Live status feed ----------
# A rolling in-memory log of notable events (connect/disconnect, guild
# join/leave, a scheduled report failing, PUBG rate-limit hits). Resets on
# restart by design — this is a live feed, not a persisted audit log.
# /setstatuschannel points a channel at a single persistent embed message
# that gets EDITED in place whenever something happens, rather than a new
# message being posted every time.
_status_events: list[dict] = []
_STATUS_LOG_LIMIT = 12
_STATUS_MIN_INTERVAL_SECONDS = 15  # collapses bursts (e.g. several reports failing at once) into one edit


def get_scheduler_lock() -> asyncio.Lock:
    """Get the scheduler lock for serializing scheduled reports."""
    return _scheduler_lock


def mark_bot_ready():
    """Mark that the bot has been ready at least once."""
    global _bot_ready_once
    _bot_ready_once = True


def has_bot_been_ready() -> bool:
    """Check if the bot has been ready at least once."""
    return _bot_ready_once


def mark_commands_synced():
    """Mark that commands have been synced at least once."""
    global _commands_synced_once
    _commands_synced_once = True


def have_commands_been_synced() -> bool:
    """Check if commands have been synced at least once."""
    return _commands_synced_once


# ---------- Live status feed ----------
# A rolling in-memory log of notable events (connect/disconnect, guild
# join/leave, a scheduled report failing, PUBG rate-limit hits). Resets on
# restart by design — this is a live feed, not a persisted audit log.
# /setstatuschannel points a channel at a single persistent embed message
# that gets EDITED in place whenever something happens, rather than a new
# message being posted every time.
_status_events: list[dict] = []
_STATUS_LOG_LIMIT = 12
_STATUS_MIN_INTERVAL_SECONDS = 15  # collapses bursts (e.g. several reports failing at once) into one edit
_status_broadcast_lock = asyncio.Lock()
_last_status_broadcast_at: datetime | None = None
_bot_started_at = datetime.now(timezone.utc)


async def _record_status_event(event_type: str, details: dict = None):
    """Record a status event for the live status feed. Can be called with just a string or with event_type and details."""
    global _status_events
    # For backward compatibility with bot.py which calls with just a string
    if details is None and isinstance(event_type, str):
        # Treat the string as both the event type and the text
        _status_events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "details": {},
        })
    else:
        _status_events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "details": details or {},
        })
    # Keep only the most recent events
    if len(_status_events) > _STATUS_LOG_LIMIT:
        _status_events = _status_events[-_STATUS_LOG_LIMIT:]
    await _refresh_all_status_messages()


def get_status_events() -> list[dict]:
    """Get the current status events list."""
    return _status_events.copy()


def _build_status_embed() -> discord.Embed:
    """Build the status embed for the live status feed."""
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
    if bot:
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)

    if _status_events:
        # Discord's <t:unix:R> renders as a live "5 minutes ago"-style
        # relative timestamp in the client, no manual formatting needed.
        lines = [f"<t:{int(datetime.fromisoformat(e['timestamp']).timestamp())}:R> {e['event_type']}" for e in reversed(_status_events)]
        embed.add_field(name="Recent Events", value="\n".join(lines)[:1024], inline=False)
    else:
        embed.add_field(name="Recent Events", value="No events recorded yet since this message was created.", inline=False)

    embed.set_footer(text="This message is edited in place, not reposted.")
    return embed


async def _push_status_message(guild_id: int, guild_cfg: dict, channel_id: int) -> None:
    """Push the current status embed to a specific guild's status channel."""
    if not bot:
        return
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
            # Import storage here to avoid circular import
            from storage import save_guild
            await save_guild(guild_id, guild_cfg)
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

    if not bot:
        return
    
    from storage import all_guild_ids, get_guild
    
    for guild_id in await all_guild_ids():
        guild_cfg = await get_guild(guild_id)
        channel_id = guild_cfg.get("status_channel_id")
        if channel_id is None:
            continue
        await _push_status_message(guild_id, guild_cfg, channel_id)


# Bot and pubg instances will be set in main.py after initialization
bot: commands.Bot = None
pubg = None
