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
  /setclantime <day> <hour> - set the weekly UTC clan-level schedule
  /survivalstats             - show roster Survival Mastery grouped by tier
  /setsurvivalchannel        - set current channel for the weekly Survival Mastery report
  /setsurvivaltime <day> <hour> - set the weekly UTC Survival Mastery schedule
  /reporttoggle <report> <enabled> - turn a scheduled report on or off
  /reportstatus              - show this server's report schedules and next run times
  /setstatuschannel           - set current channel for live bot status updates
  /help                     - show help and the official support server
  /donate                   - show the optional donation link
  /setchannel               - set current channel as the auto-post channel
  /setinterval <hours>      - how often (in hours) the digest auto-posts (default 6)
  /setdigesttime <0-23>      - post digest daily at a fixed UTC hour instead
  /postnow                  - manually trigger a digest post immediately
  /lastactive                - show when each roster player last played, right now
  /setactivitychannel        - set current channel for the 24h "last active" report
  /rankedsquad                 - show current-season ranked Squad TPP standings
  /rankedduo                   - show current-season ranked Duo TPP standings
  /rankedsolo                  - show current-season ranked Solo TPP standings
  /rankedsquadfpp              - show current-season ranked Squad FPP standings
  /rankedduofpp                - show current-season ranked Duo FPP standings
  /rankedsolofpp               - show current-season ranked Solo FPP standings
  /refreshranked            - rescan ranked roster and update the ranked report
  /updateranked              - update the ranked report with fresh data without clearing cache
  /setrankedchannel           - set current channel for the daily ranked report (updates at 04:30 UTC)
  /setrankedqueue <queue>      - choose the single TPP or FPP queue for daily reports
  /dailyhighlights              - last-24h fun-title awards + top 10 + human/bot kills, right now
  /sethighlightschannel          - set current channel for the 24h highlights report
  /sethighlightstime <0-23>       - fixed UTC hour for the highlights report
  /masterystats                     - top weapon mastery + survival level per player (on-demand only, slow)
  /leaderboardstats [pages]          - check official leaderboard for roster placements (on-demand only)
  /setleaderboardregion               - platform-region shard for leaderboard lookups (default pc-na)
  /setleaderboardqueue                - squad, duo, or solo (TPP) for leaderboard lookups
  /linkme <pubg_name>                   - link your Discord account to a PUBG name (shows as a mention on /leaderboardstats and lets you /unlinkme it later)
  /linkplayer <member> <pubg_name>       - link someone else's Discord account to a PUBG name (requires Manage Server)
  /unlinkme <pubg_name>                - remove a Discord-to-PUBG-name link
  /links                                - show every PUBG-name-to-Discord link for this server
  /chickendinner                        - check the roster's most recent matches for wins right now
  /setchickendinnerchannel               - set current channel for win alerts (defaults to the digest channel)
  /setapistatuschannel                   - set current channel for live PUBG API status (updates only when status changes)
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
import copy
import logging
import os
import random
import string
import hmac
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

import storage
from pubg_api import PubgApiError, PubgClient
import translations
from modules.utils import normalize_player_name
from storage import DatabaseCorruptionError

logger = logging.getLogger(__name__)

def generate_error_id() -> str:
    """Generate a unique error reference ID for user-facing messages."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

async def send_error_response(interaction, error, error_id=None, context=""):
    """Send a sanitized error response to the user and log the full exception."""
    if error_id is None:
        error_id = generate_error_id()
    logger.error(f"[{error_id}] {context}: {error}", exc_info=error)
    await interaction.followup.send(f"❌ Something went wrong. Error reference: {error_id}")

# Import all shared configuration and state
from modules.config import (
    DISCORD_TOKEN,
    PUBG_API_KEY,
    PUBG_SHARD,
    BOT_ADMIN_KEY,
    ADMIN_USER_IDS,
    SUPPORT_SERVER_URL,
    SUPPORT_SERVER_ID,
    SUPPORT_FEEDBACK_CHANNEL_ID,
    AUDIT_SERVER_ID,
    AUDIT_LOG_CHANNEL_ID,
    DONATION_URL,
    BUY_ME_A_COFFEE_URL,
    VALID_GAME_MODES,
    RANKED_MODE_LABELS,
    intents,
    GuildOnlyTree,
    get_scheduler_lock,
    mark_bot_ready,
    has_bot_been_ready,
    mark_commands_synced,
    have_commands_been_synced,
    _status_broadcast_lock,
    _last_status_broadcast_at,
    _STATUS_MIN_INTERVAL_SECONDS,
    _record_status_event,
    _build_status_embed,
    _push_status_message,
    _refresh_all_status_messages,
    _bot_started_at,
)

# Global state for command sync
_commands_synced_once = False
_command_templates = None
_bot_ready_once = False

# Import utility helpers
from modules.utils import (
    _safe_div,
    _is_due,
    _is_weekly_due,
    _as_utc,
    _format_utc_time,
    _next_daily_report,
    _next_interval_report,
    _next_weekly_report,
    _channel_mention,
)

# Import embed builder functions
from modules.embeds import (
    build_report_status_embed,
    build_clan_embed,
    build_clan_level_embed,
    _format_time_ago,
    build_last_active_embed,
    build_ranked_embed,
    _pick_leader,
    _compute_award_winners,
    build_highlights_embed,
    _friendly_weapon_name,
    build_mastery_embed,
    _survival_tier_number,
    build_survival_mastery_embeds,
    build_leaderboard_embed,
    build_feedback_prompt_embed,
    build_chicken_dinner_embed,
)

# Import report fetcher functions
from modules.reports import (
    fetch_clan_report,
    fetch_clan_level_report,
    fetch_last_active_report,
    fetch_ranked_report,
    fetch_highlights_report,
    fetch_mastery_report,
    fetch_survival_mastery_report,
    fetch_leaderboard_report,
)

# Import scheduled task functions
from modules.scheduler import (
    auto_digest,
    auto_last_active,
    auto_ranked,
    auto_highlights,
    auto_clan_level,
    auto_survival_mastery,
    auto_chicken_dinner,
    auto_feedback_prompt,
    start_all_scheduled_tasks,
    run_auto_highlights,
    _set_audit_log_func,
)

# Import command implementations
from commands.roster import (
    addplayer_impl,
    addplayers_impl,
    removeplayer_impl,
    roster_impl,
)
from commands.protected import (
    addprotected_impl,
    removeprotected_impl,
    listprotected_impl,
    cleanprotected_impl,
    resetprotected_impl,
    addprotectedbulk_impl,
)
from commands.inactive import (
    setinactivedate_impl,
    removeinactivedate_impl,
    resetinactivecount_impl,
)
from commands.clan import (
    setclan_impl,
    clanlevel_impl,
    setclanchannel_impl,
    setclantime_impl,
)
from commands.ranked import (
    rankedsquad_impl,
    rankedduo_impl,
    rankedsolo_impl,
    rankedsquadfpp_impl,
    rankedduofpp_impl,
    rankedsolofpp_impl,
    refreshranked_impl,
    updateranked_impl,
)
from commands.mastery import (
    masterystats_impl,
    survivalstats_impl,
)
from commands.reports import (
    clanstats_impl,
    postnow_impl,
    leaderboard_impl,
    lastactive_impl,
)
from commands.settings import (
    setgamemode_impl,
    setchannel_impl,
    setinterval_impl,
    setdigesttime_impl,
    setactivitychannel_impl,
    setrankedchannel_impl,
    setrankedqueue_impl,
    sethighlightschannel_impl,
    sethighlightstime_impl,
    setsurvivalchannel_impl,
    setsurvivaltime_impl,
    setstatuschannel_impl,
    setauditchannel_impl,
    clearauditchannel_impl,
    showauditconfig_impl,
    setlanguage_impl,
    language_impl,
    reportstatus_impl,
    reporttoggle_impl,
    donate_impl,
)
from commands.links import (
    linkme_impl,
    linkplayer_impl,
    unlinkme_impl,
    links_impl,
)
from commands.chicken_dinner import (
    chickendinner_impl,
    setchickendinnerchannel_impl,
    pingtoggle_impl,
)
from commands.highlights import (
    dailyhighlights_impl,
)
from commands.leaderboard import (
    leaderboardstats_impl,
    setleaderboardregion_impl,
    setleaderboardqueue_impl,
)
from commands.admin import (
    reportcheater_impl,
    askfeedback_impl,
    botservers_impl,
)

from commands.inactive import (
    setinactivedate_impl,
    removeinactivedate_impl,
    resetinactivecount_impl,
)
from commands.clan import (
    setclan_impl,
    clanlevel_impl,
    setclanchannel_impl,
    setclantime_impl,
)
from commands.ranked import (
    rankedsquad_impl,
    rankedduo_impl,
    rankedsolo_impl,
    rankedsquadfpp_impl,
    rankedduofpp_impl,
    rankedsolofpp_impl,
    refreshranked_impl,
    updateranked_impl,
)
from commands.mastery import (
    masterystats_impl,
    survivalstats_impl,
)
from commands.reports import (
    clanstats_impl,
    postnow_impl,
    leaderboard_impl,
    lastactive_impl,
)
from commands.settings import (
    setgamemode_impl,
    setchannel_impl,
    setinterval_impl,
    setdigesttime_impl,
    setactivitychannel_impl,
    setrankedchannel_impl,
    setrankedqueue_impl,
    sethighlightschannel_impl,
    sethighlightstime_impl,
    setsurvivalchannel_impl,
    setsurvivaltime_impl,
    setstatuschannel_impl,
    setauditchannel_impl,
    clearauditchannel_impl,
    showauditconfig_impl,
    setlanguage_impl,
    language_impl,
    reportstatus_impl,
    reporttoggle_impl,
    donate_impl,
)
from commands.links import (
    linkme_impl,
    linkplayer_impl,
    unlinkme_impl,
    links_impl,
)
from commands.chicken_dinner import (
    chickendinner_impl,
    setchickendinnerchannel_impl,
    pingtoggle_impl,
)
from commands.highlights import (
    dailyhighlights_impl,
)
from commands.leaderboard import (
    leaderboardstats_impl,
    setleaderboardregion_impl,
    setleaderboardqueue_impl,
)
from commands.admin import (
    reportcheater_impl,
    askfeedback_impl,
    botservers_impl,
)

# Initialize bot and pubg instances
bot = commands.Bot(command_prefix="!", intents=intents, tree_cls=GuildOnlyTree)
pubg = PubgClient(PUBG_API_KEY, shard=PUBG_SHARD)

# Set bot and pubg instances in config for use by other modules
import modules.config as config_module
config_module.bot = bot
config_module.pubg = pubg

# ---------- live status feed ----------
# A rolling in-memory log of notable events (connect/disconnect, guild
# join/leave, a scheduled report failing, PUBG rate-limit hits). Resets on
# restart by design — this is a live feed, not a persisted audit log.
# /setstatuschannel points a channel at a single persistent embed message
# that gets EDITED in place whenever something happens, rather than a new
# message being posted every time.
# Note: The actual status event system lives in modules/config.py
_STATUS_LOG_LIMIT = 12


# ---------- audit logging ----------
async def send_audit_log(
    guild_id: int,
    event_type: str,
    description: str,
    user: discord.User | discord.Member | None = None,
    details: dict | None = None,
    is_automated: bool = False,
    report_embed: discord.Embed | None = None
):
    """Send an audit log entry to the central audit server or custom channel."""
    if not AUDIT_SERVER_ID or not AUDIT_LOG_CHANNEL_ID:
        return
    
    try:
        # Check if guild has custom audit log channel
        custom_channel_id = await storage.get_audit_log_channel(guild_id)
        target_channel_id = custom_channel_id if custom_channel_id else AUDIT_LOG_CHANNEL_ID
        
        # Get the target guild (audit server)
        audit_guild = bot.get_guild(AUDIT_SERVER_ID)
        if not audit_guild:
            try:
                audit_guild = await bot.fetch_guild(AUDIT_SERVER_ID)
            except Exception:
                return
        
        # Get the target channel
        channel = audit_guild.get_channel(target_channel_id)
        if not channel:
            try:
                channel = await audit_guild.fetch_channel(target_channel_id)
            except Exception:
                return
        
        # Get source guild info
        source_guild = bot.get_guild(guild_id)
        if not source_guild:
            try:
                source_guild = await bot.fetch_guild(guild_id)
            except Exception:
                source_guild = None
        
        guild_name = source_guild.name if source_guild else f"Unknown ({guild_id})"
        
        # If we have a report embed, send it directly with a footer
        if report_embed:
            # Copy the embed to avoid mutating the original
            audit_embed = copy.deepcopy(report_embed)
            # Add footer with server info
            user_info = f"{user.display_name} ({user.id})" if user else "Automated (N/A)"
            audit_embed.set_footer(
                text=f"Server: {guild_name} ({guild_id}) | "
                      f"User: {user_info} | "
                      f"Event: {event_type}"
            )
            await channel.send(embed=audit_embed)
        else:
            # Build metadata embed
            color = discord.Color.blue() if is_automated else discord.Color.green()
            title = f"🤖 {event_type}" if is_automated else f"👤 {event_type}"
            
            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(name="Server", value=f"{guild_name} (`{guild_id}`)", inline=True)
            
            if user:
                embed.add_field(name="User", value=f"{user.display_name} (`{user.id}`)", inline=True)
            else:
                embed.add_field(name="User", value="Automated Event", inline=True)
            
            if details:
                details_text = "\n".join(f"**{k}**: {v}" for k, v in details.items())
                if details_text:
                    embed.add_field(name="Details", value=details_text[:1024], inline=False)
            
            await channel.send(embed=embed)
    except Exception as e:
        # Log to console so admin knows if audit logging fails
        logger.error(f"[audit_log] Failed to send audit log: {e}", exc_info=e)




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
    error_id = generate_error_id()
    logger.exception(f"[{error_id}] /{cmd_name} command error: {error}")
    message = f"❌ Something went wrong running this command. Error reference: {error_id}"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except Exception as e:
        # The interaction token may already be expired/invalid at this
        # point — nothing more we can do but log it.
        logger.error(f"[app_command_error] Also failed to notify the user: {e}", exc_info=e)


# ---------- helpers ----------
# (Moved to bot/utils.py)


# build_report_status_embed - moved to bot/embeds.py


# build_clan_embed - moved to bot/embeds.py
# fetch_clan_report - moved to bot/reports.py

# build_clan_level_embed - moved to bot/embeds.py
# fetch_clan_level_report - moved to bot/reports.py

# _format_time_ago - moved to bot/embeds.py

# build_last_active_embed - moved to bot/embeds.py
# fetch_last_active_report - moved to bot/reports.py

# build_ranked_embed - moved to bot/embeds.py
# fetch_ranked_report - moved to bot/reports.py

# TITLE_DEFINITIONS, _pick_leader, _compute_award_winners - moved to bot/embeds.py

# build_highlights_embed - moved to bot/embeds.py
# fetch_highlights_report - moved to bot/reports.py

# A handful of common weapon IDs mapped to friendly names. Anything not in
# here falls back to a cleaned-up version of the raw ID (e.g.
# "Item_Weapon_M416_C" -> "M416") so the report is still readable even for
# weapons this dict doesn't know about.
# WEAPON_DISPLAY_NAMES, _friendly_weapon_name, build_mastery_embed - moved to bot/embeds.py
# fetch_mastery_report - moved to bot/reports.py

# SURVIVAL_TIER_NAMES, SURVIVAL_TIER_ICON_FILES, SURVIVAL_TIER_ASSET_DIR, _survival_tier_number, build_survival_mastery_embeds - moved to bot/embeds.py
# fetch_survival_mastery_report - moved to bot/reports.py

# build_leaderboard_embed - moved to bot/embeds.py
# fetch_leaderboard_report - moved to bot/reports.py


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
                logger.info(f"Instantly synced {count} commands to guild {guild.name} ({guild.id})")

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
        logger.warning(f"[on_ready] Command sync failed (scheduled reports will still start): {e}", exc_info=e)
    if not auto_digest.is_running():
        start_all_scheduled_tasks(bot)
        # Wire up the audit log function so scheduler uses our implementation
        _set_audit_log_func(send_audit_log)
    bot.add_view(FeedbackPromptView())
    logger.info(f"Logged in as {bot.user} (id={bot.user.id})")
    if not _bot_ready_once:
        _bot_ready_once = True
        await _record_status_event("Bot started and connected to Discord")
    
    # Wire up the PUBG rate limit callback
    pubg.on_rate_limit_hit = lambda delay: _record_status_event(f"⏳ PUBG API rate-limited us — pausing {delay:.0f}s then retrying")


@bot.event
async def on_disconnect():
    await _record_status_event("Lost connection to Discord — reconnecting...")


@bot.event
async def on_resumed():
    await _record_status_event("Reconnected to Discord")


@bot.event
async def on_guild_join(guild: discord.Guild):
    """Make commands available immediately when the bot is invited somewhere new."""
    await _record_status_event(f"Joined server: {guild.name}")
    await send_audit_log(
        guild.id,
        "Bot Joined Server",
        f"Bot was added to server {guild.name}",
        is_automated=True,
        details={"Server Name": guild.name, "Member Count": guild.member_count}
    )
    if not _commands_synced_once:
        return
    try:
        count = await _sync_guild_commands(guild)
        logger.info(f"Instantly synced {count} commands to newly joined guild {guild.name} ({guild.id})")
    except Exception as e:
        logger.error(f"[on_guild_join] Command sync failed for guild {guild.id}: {e}", exc_info=e)


@bot.event
async def on_guild_remove(guild: discord.Guild):
    await send_audit_log(
        guild.id,
        "Bot Left Server",
        f"Bot was removed from server {guild.name}",
        is_automated=True,
        details={"Server Name": guild.name}
    )


# ---------- scheduled task ----------
# (Scheduled tasks moved to bot/scheduler.py - see that file for implementation)
# The following functions are now imported from bot.scheduler:
# - auto_digest, auto_last_active, auto_ranked, auto_highlights
# - auto_clan_level, auto_survival_mastery
# - auto_chicken_dinner, auto_feedback_prompt
# - start_all_scheduled_tasks


# ---------- slash commands ----------
# Roster and protected commands are now in commands/roster.py and commands/protected.py
# For now, keeping old commands in bot.py as backup during migration
# After testing, these will be removed

@bot.tree.command(description="Add a PUBG player name to this server's tracked clan roster")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(name="Exact in-game PUBG name (case-insensitive)")
async def addplayer(interaction: discord.Interaction, name: str):
    await addplayer_impl(interaction, name, send_audit_log, _refresh_last_active_report)

@bot.tree.command(description="Add many PUBG players at once — paste names separated by commas or new lines")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(names="e.g. PlayerOne, PlayerTwo, PlayerThree (commas or newlines both work)")
async def addplayers(interaction: discord.Interaction, names: str):
    await addplayers_impl(interaction, names, send_audit_log, _refresh_last_active_report)

@bot.tree.command(description="Remove a player from this server's tracked clan roster")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(name="PUBG name to remove")
async def removeplayer(interaction: discord.Interaction, name: str):
    await removeplayer_impl(interaction, name, send_audit_log, _refresh_last_active_report)

@bot.tree.command(description="Add a player to the protected list (immune to inactivity removal)")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(name="PUBG name to protect")
async def addprotected(interaction: discord.Interaction, name: str):
    await addprotected_impl(interaction, name, send_audit_log)

@bot.tree.command(description="Remove a player from the protected list")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(name="PUBG name to unprotect")
async def removeprotected(interaction: discord.Interaction, name: str):
    await removeprotected_impl(interaction, name, send_audit_log)

@bot.tree.command(description="List all protected players (immune to inactivity removal)")
async def listprotected(interaction: discord.Interaction):
    await listprotected_impl(interaction)

@bot.tree.command(description="Clean up protected player list (remove duplicates and empty entries)")
@app_commands.checks.has_permissions(manage_guild=True)
async def cleanprotected(interaction: discord.Interaction):
    await cleanprotected_impl(interaction)

@bot.tree.command(description="Clear and reset the entire protected player list")
@app_commands.checks.has_permissions(manage_guild=True)
async def resetprotected(interaction: discord.Interaction):
    await resetprotected_impl(interaction)

@bot.tree.command(description="Bulk add protected players (one per line or comma-separated)")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(players="Player names (one per line or comma-separated)")
async def addprotectedbulk(interaction: discord.Interaction, players: str):
    await addprotectedbulk_impl(interaction, players)

@bot.tree.command(description="Set manual inactive date for a player (beyond 14-day API limit)")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(name="PUBG name", days_ago="How many days ago they last played")
async def setinactivedate(interaction: discord.Interaction, name: str, days_ago: app_commands.Range[int, 1, 365]):
    from datetime import datetime, timedelta, timezone
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    inactive_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    
    def modifier(guild_cfg):
        guild_cfg["manual_inactive_dates"][normalize_player_name(name)] = {
            "date": inactive_date,
            "set_at": datetime.now(timezone.utc).isoformat()
        }
    
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(translations.get_translation(lang, "inactive_date_set").format(name=name, date=days_ago))
    await send_audit_log(
        interaction.guild_id,
        "Manual Inactive Date Set",
        f"Set {name} to {days_ago} days inactive",
        user=interaction.user,
        details={"Player": name, "Days Ago": days_ago}
    )


@bot.tree.command(description="Remove manual inactive date for a player")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(name="PUBG name")
async def removeinactivedate(interaction: discord.Interaction, name: str):
    await removeinactivedate_impl(interaction, name)

@bot.tree.command(description="Reset auto-counting for a specific player (start counting from today)")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(name="PUBG name")
async def resetinactivedate(interaction: discord.Interaction, name: str):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    reset = await storage.reset_inactive_count(interaction.guild_id, name)
    if reset:
        await interaction.response.send_message(translations.get_translation(lang, "inactive_count_reset").format(name=name))
    else:
        await interaction.response.send_message(translations.get_translation(lang, "inactive_count_not_active").format(name=name), ephemeral=True)


@bot.tree.command(description="List everyone currently tracked for this server's clan")
async def roster(interaction: discord.Interaction):
    await roster_impl(interaction)

@bot.tree.command(description="Report suspicious statistics for manual review")
@app_commands.checks.has_permissions(manage_guild=True)
async def reportcheater(interaction: discord.Interaction):
    await reportcheater_impl(interaction, pubg, _detect_statistical_anomalies)

@bot.tree.command(description="Post aggregated clan stats right now")
async def clanstats(interaction: discord.Interaction):
    await clanstats_impl(interaction, pubg)

@bot.tree.command(description="Manually post today's clan digest to this channel")
async def postnow(interaction: discord.Interaction):
    await postnow_impl(interaction, pubg)

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
    await leaderboard_impl(interaction, pubg, sort_by)

@bot.tree.command(description="Set the PUBG game mode used for stats (default squad-fpp)")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.choices(
    mode=[app_commands.Choice(name=m, value=m) for m in sorted(VALID_GAME_MODES)]
)
async def setgamemode(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    await setgamemode_impl(interaction, mode)

@bot.tree.command(description="Set the clan-level report from a current PUBG clan member")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(name="Exact in-game PUBG name of a member of the clan")
async def setclan(interaction: discord.Interaction, name: str):
    await setclan_impl(interaction, name, pubg)

@bot.tree.command(description="Show the current PUBG clan level and weekly progress")
async def clanlevel(interaction: discord.Interaction):
    await clanlevel_impl(interaction, pubg)

@bot.tree.command(description="Set this channel for the weekly clan-level report (scheduled in UTC)")
@app_commands.checks.has_permissions(manage_guild=True)
async def setclanchannel(interaction: discord.Interaction):
    await setclanchannel_impl(interaction, send_audit_log)

@bot.tree.command(description="Get help with PUBG Tracker and join the official support server")
async def help(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    await interaction.response.send_message(
        translations.get_translation(lang, "help_title") + "\n" +
        translations.get_translation(lang, "help_description") + "\n" +
        f"{SUPPORT_SERVER_URL}"
    )

@bot.tree.command(description="Set the preferred language for this server")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(language="Language code (en, zh, hi, es, ar, fr, bn, pt, id, ur)")
async def setlanguage(interaction: discord.Interaction, language: str):
    await setlanguage_impl(interaction, language)

@bot.tree.command(description="Show the current language setting for this server")
async def language(interaction: discord.Interaction):
    await language_impl(interaction)

@bot.tree.command(description="Show this server's automatic report schedules and next run times")
async def reportstatus(interaction: discord.Interaction):
    await reportstatus_impl(interaction)

@bot.tree.command(description="Set this channel to show live bot status (connects, joins/leaves, failures, rate limits)")
@app_commands.checks.has_permissions(manage_guild=True)
async def setstatuschannel(interaction: discord.Interaction):
    await setstatuschannel_impl(interaction)

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
    lang = guild_cfg.get("language", "en")
    
    is_enabled = enabled.value == "on"
    def modifier(guild_cfg):
        guild_cfg[report.value] = is_enabled
    await storage.modify_guild(interaction.guild_id, modifier)
    if is_enabled:
        await interaction.response.send_message(
            translations.get_translation(lang, "toggle_report_on").format(report=report.name)
        )
    else:
        await interaction.response.send_message(
            translations.get_translation(lang, "toggle_report_off").format(report=report.name)
        )


@bot.tree.command(description="Show the optional donation link for PUBG Tracker")
async def donate(interaction: discord.Interaction):
    await donate_impl(interaction)

@bot.tree.command(description="Set this channel as where the clan digest gets auto-posted")
@app_commands.checks.has_permissions(manage_guild=True)
async def setchannel(interaction: discord.Interaction):
    await setchannel_impl(interaction)

@bot.tree.command(description="Set how often (in hours) the digest auto-posts (ignored if a fixed time is set via /setdigesttime)")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(hours="e.g. 6 for every 6 hours")
async def setinterval(interaction: discord.Interaction, hours: app_commands.Range[int, 1, 24]):
    def modifier(guild_cfg):
        guild_cfg["post_interval_hours"] = hours
    await storage.modify_guild(interaction.guild_id, modifier)
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    count = hours
    unit_key = "hour" if count == 1 else "hours"
    unit = translations.get_translation(lang, unit_key)
    schedule = translations.get_translation(lang, 'every_hours').format(count=count, unit=unit)
    await interaction.response.send_message(translations.get_translation(lang, "interval_set").format(schedule=schedule))


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


@bot.tree.command(description="Post the digest once a day at a fixed UTC time, instead of by interval")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(hour="0-23, UTC (e.g. 9 for 9am UTC)", minute="Quarter-hour, defaults to :00")
@app_commands.choices(minute=QUARTER_HOUR_CHOICES)
async def setdigesttime(interaction: discord.Interaction, hour: app_commands.Range[int, 0, 23], minute: app_commands.Choice[int] = None):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    minute_val = minute.value if minute else 0
    def modifier(guild_cfg):
        guild_cfg["digest_hour_utc"] = hour
        guild_cfg["digest_minute_utc"] = minute_val
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(
        translations.get_translation(lang, "digest_time_set").format(time=f"{hour:02d}:{minute_val:02d} UTC")
    )


@bot.tree.command(description="Set the weekly clan-level report time in UTC")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(day="Day of the week", hour="0-23 UTC", minute="Quarter-hour, defaults to :00")
@app_commands.choices(day=WEEKDAY_CHOICES, minute=QUARTER_HOUR_CHOICES)
async def setclantime(
    interaction: discord.Interaction,
    day: app_commands.Choice[int],
    hour: app_commands.Range[int, 0, 23],
    minute: app_commands.Choice[int] = None,
):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    minute_val = minute.value if minute else 0
    def modifier(guild_cfg):
        guild_cfg["clan_weekday_utc"] = day.value
        guild_cfg["clan_hour_utc"] = hour
        guild_cfg["clan_minute_utc"] = minute_val
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(
        translations.get_translation(lang, "clan_time_set").format(weekday=day.name, time=f"{hour:02d}:{minute_val:02d} UTC")
    )

@bot.tree.command(description="Show when each roster player last played PUBG, right now")
async def lastactive(interaction: discord.Interaction):
    await lastactive_impl(interaction, pubg)

@bot.tree.command(description="Set this channel for the live-updating 'last active' report (updates at 02:00 UTC daily reset)")
@app_commands.checks.has_permissions(manage_guild=True)
async def setactivitychannel(interaction: discord.Interaction):
    await setactivitychannel_impl(interaction)

@bot.tree.command(description="[Admin] Set a custom audit log channel for this server (overrides central server)")
async def setauditchannel(interaction: discord.Interaction):
    await setauditchannel_impl(interaction, ADMIN_USER_IDS)

@bot.tree.command(description="[Admin] Remove custom audit channel and use central audit server for this server")
async def clearauditchannel(interaction: discord.Interaction):
    await clearauditchannel_impl(interaction, ADMIN_USER_IDS)

@bot.tree.command(description="[Admin] Show current audit logging configuration for this server")
async def showauditconfig(interaction: discord.Interaction):
    await showauditconfig_impl(interaction, ADMIN_USER_IDS)

@bot.tree.command(description="Show current-season ranked Squad TPP standings")
async def rankedsquad(interaction: discord.Interaction):
    await rankedsquad_impl(interaction, pubg)

@bot.tree.command(description="Show current-season ranked Duo TPP standings")
async def rankedduo(interaction: discord.Interaction):
    await rankedduo_impl(interaction, pubg)

@bot.tree.command(description="Show current-season ranked Solo TPP standings")
async def rankedsolo(interaction: discord.Interaction):
    await rankedsolo_impl(interaction, pubg)

@bot.tree.command(description="Show current-season ranked Squad FPP standings")
async def rankedsquadfpp(interaction: discord.Interaction):
    await rankedsquadfpp_impl(interaction, pubg)

@bot.tree.command(description="Show current-season ranked Duo FPP standings")
async def rankedduofpp(interaction: discord.Interaction):
    await rankedduofpp_impl(interaction, pubg)

@bot.tree.command(description="Show current-season ranked Solo FPP standings")
async def rankedsolofpp(interaction: discord.Interaction):
    await rankedsolofpp_impl(interaction, pubg)

@bot.tree.command(description="Rescan the full roster the next time a ranked queue is checked and update the ranked report")
async def refreshranked(interaction: discord.Interaction):
    await refreshranked_impl(interaction, pubg)

@bot.tree.command(description="Update the ranked report with fresh data without clearing the cache")
async def updateranked(interaction: discord.Interaction):
    await updateranked_impl(interaction, pubg)

@bot.tree.command(description="Set this channel for the daily ranked report (defaults to the digest channel)")
@app_commands.checks.has_permissions(manage_guild=True)
async def setrankedchannel(interaction: discord.Interaction):
    await setrankedchannel_impl(interaction)

@bot.tree.command(description="Set which ranked queue the daily report tracks")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.guild_only()
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
    await setrankedqueue_impl(interaction, queue)

@bot.tree.command(description="Show daily-reset fun-title awards + top 10 + human/bot kills, right now")
async def dailyhighlights(interaction: discord.Interaction):
    await dailyhighlights_impl(interaction, pubg)

@bot.tree.command(description="Set this channel for the daily highlights report (defaults to the digest channel)")
@app_commands.checks.has_permissions(manage_guild=True)
async def sethighlightschannel(interaction: discord.Interaction):
    await sethighlightschannel_impl(interaction)

@bot.tree.command(description="Post the daily highlights report at a fixed UTC time each day")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(hour="0-23, UTC (e.g. 9 for 9am UTC)", minute="Quarter-hour, defaults to :00")
@app_commands.choices(minute=QUARTER_HOUR_CHOICES)
async def sethighlightstime(interaction: discord.Interaction, hour: app_commands.Range[int, 0, 23], minute: app_commands.Choice[int] = None):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    minute_val = minute.value if minute else 0
    def modifier(guild_cfg):
        guild_cfg["highlights_hour_utc"] = hour
        guild_cfg["highlights_minute_utc"] = minute_val
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(
        translations.get_translation(lang, "highlights_time_set").format(time=f"{hour:02d}:{minute_val:02d} UTC")
    )


@bot.tree.command(description="Show roster Survival Mastery grouped by tier and sorted by level")
async def survivalstats(interaction: discord.Interaction):
    await survivalstats_impl(interaction, pubg)

@bot.tree.command(description="Set this channel for the weekly Survival Mastery report (scheduled in UTC)")
@app_commands.checks.has_permissions(manage_guild=True)
async def setsurvivalchannel(interaction: discord.Interaction):
    await setsurvivalchannel_impl(interaction)

@bot.tree.command(description="Set the weekly Survival Mastery report time in UTC")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(day="Day of the week", hour="0-23 UTC", minute="Quarter-hour, defaults to :00")
@app_commands.choices(day=WEEKDAY_CHOICES, minute=QUARTER_HOUR_CHOICES)
async def setsurvivaltime(
    interaction: discord.Interaction,
    day: app_commands.Choice[int],
    hour: app_commands.Range[int, 0, 23],
    minute: app_commands.Choice[int] = None,
):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")
    
    minute_val = minute.value if minute else 0
    def modifier(guild_cfg):
        guild_cfg["survival_weekday_utc"] = day.value
        guild_cfg["survival_hour_utc"] = hour
        guild_cfg["survival_minute_utc"] = minute_val
        guild_cfg["survival_enabled"] = True
    await storage.modify_guild(interaction.guild_id, modifier)
    await interaction.response.send_message(
        translations.get_translation(lang, "survival_time_set").format(weekday=day.name, time=f"{hour:02d}:{minute_val:02d} UTC")
    )


@bot.tree.command(description="Show each player's top weapon mastery and survival level (slow — 2 calls/player)")
async def masterystats(interaction: discord.Interaction):
    await masterystats_impl(interaction, pubg)

@bot.tree.command(description="Check the official leaderboard for roster placements (most won't appear — top ladder only)")
@app_commands.describe(pages="How many 500-player pages to check (default 4 = top 2000)")
async def leaderboardstats(interaction: discord.Interaction, pages: app_commands.Range[int, 1, 10] = 4):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    if not guild_cfg["players"]:
        await interaction.response.send_message(translations.get_translation(lang, "no_players_tracked"))
        return
    await interaction.response.defer()
    try:
        result = await fetch_leaderboard_report(interaction.guild_id, interaction.guild.name, max_pages=pages)
    except PubgApiError as e:
        await send_error_response(interaction, e, context="PUBG API error")
        return
    except Exception as e:
        await send_error_response(interaction, e, context="Error generating report")
        return
    if result is None:
        await interaction.followup.send(translations.get_translation(lang, "no_players_tracked"))
        return
    embed, found = result
    await interaction.followup.send(embed=embed)


@bot.tree.command(description="Set the platform-region shard used for leaderboard lookups (default pc-na)")
@app_commands.checks.has_permissions(manage_guild=True)
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
    await setleaderboardregion_impl(interaction, region)

@bot.tree.command(description="Set which queue the leaderboard check looks at (squad, duo, or solo TPP)")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.choices(
    queue=[
        app_commands.Choice(name="Squad TPP", value="squad"),
        app_commands.Choice(name="Duo TPP", value="duo"),
        app_commands.Choice(name="Solo TPP", value="solo"),
    ]
)
async def setleaderboardqueue(interaction: discord.Interaction, queue: app_commands.Choice[str]):
    await setleaderboardqueue_impl(interaction, queue)

@bot.tree.command(description="Link your Discord account to a PUBG name (shows as a mention on the official leaderboard report)")
@app_commands.describe(pubg_name="Your exact PUBG in-game name")
async def linkme(interaction: discord.Interaction, pubg_name: str):
    await linkme_impl(interaction, pubg_name)

@bot.tree.command(description="Link another member's Discord account to a PUBG name on their behalf")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(member="The Discord member to link", pubg_name="Their exact PUBG in-game name")
async def linkplayer(interaction: discord.Interaction, member: discord.Member, pubg_name: str):
    await linkplayer_impl(interaction, member, pubg_name)

@bot.tree.command(description="Remove your Discord-to-PUBG-name link")
@app_commands.describe(pubg_name="The PUBG name to unlink")
async def unlinkme(interaction: discord.Interaction, pubg_name: str):
    await unlinkme_impl(interaction, pubg_name)

@bot.tree.command(description="Show every PUBG-name-to-Discord link for this server")
@app_commands.checks.has_permissions(manage_guild=True)
async def links(interaction: discord.Interaction):
    await links_impl(interaction)

@bot.tree.command(description="Check the roster's recent match history for wins in all game modes")
async def chickendinner(interaction: discord.Interaction):
    await chickendinner_impl(interaction, pubg)

@bot.tree.command(description="Set this channel for automatic Chicken Dinner win alerts (defaults to the digest channel)")
@app_commands.checks.has_permissions(manage_guild=True)
async def setchickendinnerchannel(interaction: discord.Interaction):
    await setchickendinnerchannel_impl(interaction)

@bot.tree.command(description="Toggle mention notifications for achievement awards in reports")
@app_commands.checks.has_permissions(manage_guild=True)
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
    has_valid_key = bool(BOT_ADMIN_KEY) and secret_key is not None and hmac.compare_digest(secret_key.encode(), BOT_ADMIN_KEY.encode())
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


# build_feedback_prompt_embed - moved to bot/embeds.py


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
                logger.error(f"[feedback] Error sending to SUPPORT_FEEDBACK_CHANNEL_ID: {e}", exc_info=e)

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
                    logger.error(f"[feedback] Error sending to support guild channel: {e}", exc_info=e)

    if not delivered:
        try:
            app_info = await bot.application_info()
            if app_info.owner:
                await app_info.owner.send(embed=embed)
                delivered = True
        except Exception as e:
            logger.error(f"[feedback] Error sending fallback DM to owner: {e}", exc_info=e)


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


@bot.tree.command(description="[Admin] Post feedback & suggestions prompt to a channel")
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

    guild_cfg = await storage.get_guild(interaction.guild_id)
    lang = guild_cfg.get("language", "en")

    target_channel = channel or interaction.channel
    if not isinstance(target_channel, discord.TextChannel):
        await interaction.response.send_message(f"❌ {translations.get_translation(lang, 'valid_text_channel')}", ephemeral=True)
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

