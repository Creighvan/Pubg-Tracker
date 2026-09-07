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


async def _record_status_event(event_type: str, details: dict = None):
    """Record a status event for the live status feed."""
    global _status_events
    _status_events.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "details": details or {},
    })
    # Keep only the most recent events
    if len(_status_events) > _STATUS_LOG_LIMIT:
        _status_events = _status_events[-_STATUS_LOG_LIMIT:]


def get_status_events() -> list[dict]:
    """Get the current status events list."""
    return _status_events.copy()


# Bot and pubg instances will be set in main.py after initialization
bot: commands.Bot = None
pubg = None
