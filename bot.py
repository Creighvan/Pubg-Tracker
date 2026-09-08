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
  /refreshranked            - rescan ranked roster and update the ranked report
  /updateranked              - update the ranked report with fresh data without clearing cache
  /setrankedchannel           - set current channel for the daily ranked report (updates at 5:30am KST)
  /setrankedqueue <queue>      - choose the single TPP or FPP queue for daily reports
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
  /setapistatuschannel                   - set current channel for PUBG API status alerts
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
import hmac
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

import storage
from pubg_api import PubgApiError, PubgClient
import translations

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
    DONATION_MESSAGE,
    VALID_GAME_MODES,
    RANKED_MODE_LABELS,
    EASTERN,
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
    _is_sunday_donation_due,
    _as_eastern,
    _format_eastern_time,
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
    auto_donations,
    auto_chicken_dinner,
    auto_feedback_prompt,
    auto_api_status,
    start_all_scheduled_tasks,
    _set_audit_log_func,
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
            except:
                return
        
        # Get the target channel
        channel = audit_guild.get_channel(target_channel_id)
        if not channel:
            try:
                channel = await audit_guild.fetch_channel(target_channel_id)
            except:
                return
        
        # Get source guild info
        source_guild = bot.get_guild(guild_id)
        if not source_guild:
            try:
                source_guild = await bot.fetch_guild(guild_id)
            except:
                source_guild = None
        
        guild_name = source_guild.name if source_guild else f"Unknown ({guild_id})"
        
        # If we have a report embed, send it directly with a footer
        if report_embed:
            # Add footer with server info
            user_info = f"{user.display_name} ({user.id})" if user else "Automated (N/A)"
            report_embed.set_footer(
                text=f"Server: {guild_name} ({guild_id}) | "
                      f"User: {user_info} | "
                      f"Event: {event_type}"
            )
            await channel.send(embed=report_embed)
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
        print(f"[audit_log] Failed to send audit log: {e}")




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
        start_all_scheduled_tasks(bot)
        # Wire up the audit log function so scheduler uses our implementation
        _set_audit_log_func(send_audit_log)
    bot.add_view(FeedbackPromptView())
    print(f"Logged in as {bot.user} (id={bot.user.id})")
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
        print(f"Instantly synced {count} commands to newly joined guild {guild.name} ({guild.id})")
    except Exception as e:
        print(f"[on_guild_join] Command sync failed for guild {guild.id}: {e}")


@bot.event
async def on_guild_remove(guild: discord.Guild):
    await _record_status_event(f"Removed from server: {guild.name}")
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
# - auto_clan_level, auto_survival_mastery, auto_donations
# - auto_chicken_dinner, auto_feedback_prompt
# - start_all_scheduled_tasks


# ---------- slash commands ----------

@bot.tree.command(description="Add a PUBG player name to this server's tracked clan roster")
@app_commands.describe(name="Exact in-game PUBG name (case-insensitive)")
async def addplayer(interaction: discord.Interaction, name: str):
    added = await storage.add_player(interaction.guild_id, name)
    if added:
        await interaction.response.send_message(f"✅ Added **{name}** to the roster.")
        await send_audit_log(
            interaction.guild_id,
            "Player Added",
            f"Added {name} to roster",
            user=interaction.user,
            details={"Player": name}
        )
        # Refresh last active report if configured
        await _refresh_last_active_report(interaction.guild_id, interaction.guild.name)
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
    
    # Refresh last active report if configured
    if added:
        await _refresh_last_active_report(interaction.guild_id, interaction.guild.name)


@bot.tree.command(description="Remove a player from this server's tracked clan roster")
@app_commands.describe(name="PUBG name to remove")
async def removeplayer(interaction: discord.Interaction, name: str):
    removed = await storage.remove_player(interaction.guild_id, name)
    if removed:
        await interaction.response.send_message(f"🗑️ Removed **{name}** from the roster.")
        await send_audit_log(
            interaction.guild_id,
            "Player Removed",
            f"Removed {name} from roster",
            user=interaction.user,
            details={"Player": name}
        )
        # Refresh last active report if configured
        await _refresh_last_active_report(interaction.guild_id, interaction.guild.name)
    else:
        await interaction.response.send_message(f"**{name}** wasn't on the roster.", ephemeral=True)


@bot.tree.command(description="Add a player to the protected list (immune to inactivity removal)")
@app_commands.describe(name="PUBG name to protect")
async def addprotected(interaction: discord.Interaction, name: str):
    added = await storage.add_protected_player(interaction.guild_id, name)
    if added:
        await interaction.response.send_message(f"🛡️ Added **{name}** to the protected list. They won't be flagged for removal due to inactivity.")
        await send_audit_log(
            interaction.guild_id,
            "Protected Player Added",
            f"Added {name} to protected list",
            user=interaction.user,
            details={"Player": name}
        )
    else:
        await interaction.response.send_message(f"**{name}** is already on the protected list.", ephemeral=True)


@bot.tree.command(description="Remove a player from the protected list")
@app_commands.describe(name="PUBG name to unprotect")
async def removeprotected(interaction: discord.Interaction, name: str):
    removed = await storage.remove_protected_player(interaction.guild_id, name)
    if removed:
        await interaction.response.send_message(f"🔓 Removed **{name}** from the protected list. They can now be flagged for inactivity removal.")
        await send_audit_log(
            interaction.guild_id,
            "Protected Player Removed",
            f"Removed {name} from protected list",
            user=interaction.user,
            details={"Player": name}
        )
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
    guild_cfg["manual_inactive_dates"][name.lower()] = {
        "date": inactive_date,
        "set_at": datetime.now(timezone.utc).isoformat()
    }
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Set **{name}** last played {days_ago} days ago. This will increment daily until they return to PUBG.")
    await send_audit_log(
        interaction.guild_id,
        "Manual Inactive Date Set",
        f"Set {name} to {days_ago} days inactive",
        user=interaction.user,
        details={"Player": name, "Days Ago": days_ago}
    )


@bot.tree.command(description="Remove manual inactive date for a player")
@app_commands.describe(name="PUBG name")
async def removeinactivedate(interaction: discord.Interaction, name: str):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    if name.lower() in guild_cfg.get("manual_inactive_dates", {}):
        del guild_cfg["manual_inactive_dates"][name.lower()]
        await storage.save_guild(interaction.guild_id, guild_cfg)
        await interaction.response.send_message(f"✅ Removed manual inactive date for **{name}**. Will use PUBG API data.")
        await send_audit_log(
            interaction.guild_id,
            "Manual Inactive Date Removed",
            f"Removed manual date for {name}",
            user=interaction.user,
            details={"Player": name}
        )
    else:
        await interaction.response.send_message(f"**{name}** doesn't have a manual inactive date set.", ephemeral=True)


@bot.tree.command(description="Reset auto-counting for a specific player (start counting from today)")
@app_commands.describe(name="PUBG name")
async def resetinactivedate(interaction: discord.Interaction, name: str):
    reset = await storage.reset_inactive_count(interaction.guild_id, name)
    if reset:
        await interaction.response.send_message(f"✅ Reset auto-counting for **{name}**. Will start counting from 14 days from now.")
    else:
        await interaction.response.send_message(f"**{name}** doesn't have auto-counting active.", ephemeral=True)


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
    await send_audit_log(
        interaction.guild_id,
        "Command Executed",
        f"Clan stats report generated manually",
        user=interaction.user,
        details={"Command": "/clanstats", "Players": len(players)},
        report_embed=embed
    )


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
    guild_cfg["clan_message_id"] = None  # force a fresh message in the new channel
    await storage.save_guild(interaction.guild_id, guild_cfg)
    
    await interaction.response.defer()
    
    # Immediately post the report
    try:
        result = await fetch_clan_level_report(interaction.guild_id)
        if result:
            embed, clan = result
            new_message = await interaction.channel.send(embed=embed)
            guild_cfg["clan_message_id"] = new_message.id
            await storage.save_guild(interaction.guild_id, guild_cfg)
            
            await interaction.followup.send(
                f"✅ Clan level report posted in {interaction.channel.mention}. "
                f"Choose the weekly time with `/setclantime`."
            )
            
            await send_audit_log(
                interaction.guild_id,
                "Channel Configured & Report Posted",
                f"Clan level report channel set and initial report posted",
                user=interaction.user,
                details={"Channel": interaction.channel_id, "Clan": clan["name"]},
                report_embed=embed
            )
        else:
            await interaction.followup.send(
                f"✅ Weekly clan-level reports will post in {interaction.channel.mention}. "
                f"Choose the weekly time with `/setclantime`."
            )
    except PubgApiError as e:
        await interaction.followup.send(f"PUBG API error: {e}")
    except Exception as e:
        await interaction.followup.send(f"Something went wrong: {e}")


@bot.tree.command(description="Get help with PUBG Tracker and join the official support server")
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**Need help with PUBG Tracker?**\n"
        "Use `/` to browse the Bot's commands, or join the official support server for "
        "setup help, bug reports, feature requests, and Bot updates:\n"
        f"{SUPPORT_SERVER_URL}"
    )


@bot.tree.command(description="Set the preferred language for this server")
@app_commands.describe(language="Language code (en, zh, hi, es, ar, fr, bn, pt, id, ur)")
async def setlanguage(interaction: discord.Interaction, language: str):
    # Valid language codes
    VALID_LANGUAGES = {"en", "zh", "hi", "es", "ar", "fr", "bn", "pt", "id", "ur"}
    LANGUAGE_NAMES = {
        "en": "English",
        "zh": "Mandarin Chinese",
        "hi": "Hindi",
        "es": "Spanish",
        "ar": "Arabic",
        "fr": "French",
        "bn": "Bengali",
        "pt": "Portuguese",
        "id": "Indonesian",
        "ur": "Urdu"
    }
    
    language = language.lower()
    if language not in VALID_LANGUAGES:
        await interaction.response.send_message(
            f"❌ Invalid language code. Valid options: {', '.join(VALID_LANGUAGES)}\n"
            f"Example: English (en), Spanish (es), Chinese (zh)"
        )
        return
    
    success = await storage.set_language(interaction.guild_id, language)
    if success:
        language_name = LANGUAGE_NAMES[language]
        await interaction.response.send_message(
            f"✅ Language set to **{language_name}** ({language}).\n"
            f"Reports and messages will now appear in this language."
        )
    else:
        await interaction.response.send_message("❌ Failed to set language. Please try again.")


@bot.tree.command(description="Show the current language setting for this server")
async def language(interaction: discord.Interaction):
    LANGUAGE_NAMES = {
        "en": "English",
        "zh": "Mandarin Chinese",
        "hi": "Hindi",
        "es": "Spanish",
        "ar": "Arabic",
        "fr": "French",
        "bn": "Bengali",
        "pt": "Portuguese",
        "id": "Indonesian",
        "ur": "Urdu"
    }
    
    current_lang = await storage.get_language(interaction.guild_id)
    language_name = LANGUAGE_NAMES.get(current_lang, current_lang)
    
    await interaction.response.send_message(
        f"🌐 Current language: **{language_name}** ({current_lang})\n"
        f"Use `/setlanguage <code>` to change it.\n"
        f"Available: {', '.join(LANGUAGE_NAMES.keys())}"
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
    await send_audit_log(
        interaction.guild_id,
        "Command Executed",
        f"Last active report generated manually",
        user=interaction.user,
        details={"Command": "/lastactive", "Players": len(players)},
        report_embed=embed
    )


async def _refresh_last_active_report(guild_id: int, guild_name: str) -> None:
    """Refresh the live-updating last active report for a guild."""
    guild_cfg = await storage.get_guild(guild_id)
    channel_id = guild_cfg.get("last_activity_channel_id")
    message_id = guild_cfg.get("last_activity_message_id")
    
    if not channel_id or not message_id:
        return  # No live-updating report configured
    
    guild = bot.get_guild(guild_id)
    if not guild:
        return
    
    channel = bot.get_channel(channel_id)
    if not channel:
        return
    
    try:
        result = await fetch_last_active_report(guild_id, guild_name)
        if result:
            embed, players = result
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                # Message deleted/inaccessible - post new one
                new_message = await channel.send(embed=embed)
                guild_cfg["last_activity_message_id"] = new_message.id
                await storage.save_guild(guild_id, guild_cfg)
    except Exception as e:
        print(f"[_refresh_last_active_report] Failed to refresh for guild {guild_id}: {e}")


@bot.tree.command(description="Set this channel for the live-updating 'last active' report (updates at 3am KST daily reset)")
async def setactivitychannel(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["last_activity_channel_id"] = interaction.channel_id
    guild_cfg["activity_enabled"] = True
    guild_cfg["last_activity_message_id"] = None  # force a fresh message in the new channel
    await storage.save_guild(interaction.guild_id, guild_cfg)
    
    await interaction.response.defer()
    
    # Immediately post the report
    try:
        result = await fetch_last_active_report(interaction.guild_id, interaction.guild.name)
        if result:
            embed, players = result
            new_message = await interaction.channel.send(embed=embed)
            guild_cfg["last_activity_message_id"] = new_message.id
            await storage.save_guild(interaction.guild_id, guild_cfg)
            
            await interaction.followup.send(
                f"✅ Last-active report posted in {interaction.channel.mention}. "
                f"It will live-update at 3am KST daily reset."
            )
            
            await send_audit_log(
                interaction.guild_id,
                "Channel Configured & Report Posted",
                f"Last active report channel set and initial report posted",
                user=interaction.user,
                details={"Channel": interaction.channel_id, "Players": len(players)},
                report_embed=embed
            )
    except PubgApiError as e:
        await interaction.followup.send(f"❌ Failed to generate report: {e}")
    except Exception as e:
        await interaction.followup.send(f"❌ Something went wrong: {e}")


@bot.tree.command(description="Last-active report now updates at 3am KST daily reset (no custom time needed)")
async def setactivitytime(interaction: discord.Interaction):
    await interaction.response.send_message(
        "ℹ️ The last-active report now automatically updates at **3am KST daily reset**. "
        "Custom time scheduling is no longer available for this report. "
        "Use `/setactivitychannel` to choose where it updates."
    )


@bot.tree.command(description="[Admin] Set a custom audit log channel for this server (overrides central server)")
async def setauditchannel(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("This command is only available to bot administrators.", ephemeral=True)
        return
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["audit_log_channel_id"] = interaction.channel_id
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ Audit logs for this server will now post in {interaction.channel.mention} instead of the central audit server."
    )


@bot.tree.command(description="[Admin] Remove custom audit channel and use central audit server for this server")
async def clearauditchannel(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("This command is only available to bot administrators.", ephemeral=True)
        return
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["audit_log_channel_id"] = None
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        "✅ Custom audit channel removed. This server will now use the central audit server for logs."
    )


@bot.tree.command(description="[Admin] Show current audit logging configuration for this server")
async def showauditconfig(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("This command is only available to bot administrators.", ephemeral=True)
        return
    guild_cfg = await storage.get_guild(interaction.guild_id)
    custom_channel_id = guild_cfg.get("audit_log_channel_id")
    
    embed = discord.Embed(
        title="📋 Audit Logging Configuration",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    if AUDIT_SERVER_ID and AUDIT_LOG_CHANNEL_ID:
        embed.add_field(
            name="Central Audit Server",
            value=f"Server ID: `{AUDIT_SERVER_ID}`\nChannel ID: `{AUDIT_LOG_CHANNEL_ID}`",
            inline=False
        )
    else:
        embed.add_field(
            name="Central Audit Server",
            value="❌ Not configured (AUDIT_SERVER_ID or AUDIT_LOG_CHANNEL_ID not set in .env)",
            inline=False
        )
    
    if custom_channel_id:
        embed.add_field(
            name="Custom Channel for This Server",
            value=f"Channel ID: `{custom_channel_id}` (overrides central server)\nUse `/clearauditchannel` to remove and use central server",
            inline=False
        )
    else:
        embed.add_field(
            name="Custom Channel for This Server",
            value="Not set (using central audit server)\nUse `/setauditchannel` to set a custom channel",
            inline=False
        )
    
    embed.add_field(
        name="What Gets Logged",
        value="• Manual commands (add/remove player, protected players, inactive dates)\n• Automated events (scheduled reports, chicken dinner alerts)\n• Bot server joins/leaves",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


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


@bot.tree.command(description="Rescan the full roster the next time a ranked queue is checked and update the ranked report")
async def refreshranked(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["ranked_known_players"] = {}
    await storage.save_guild(interaction.guild_id, guild_cfg)
    
    await interaction.response.defer()
    
    # Update the ranked report if a message exists
    channel_id = guild_cfg.get("ranked_channel_id")
    message_id = guild_cfg.get("ranked_message_id")
    
    if channel_id and message_id:
        try:
            guild = bot.get_guild(interaction.guild_id)
            channel = bot.get_channel(channel_id)
            if guild and channel:
                result = await fetch_ranked_report(interaction.guild_id, guild.name)
                if result:
                    embed, players = result
                    try:
                        message = await channel.fetch_message(message_id)
                        await message.edit(embed=embed)
                        await interaction.followup.send(
                            "✅ Ranked-player cache cleared and report updated."
                        )
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        await interaction.followup.send(
                            "✅ Ranked-player cache cleared. (Message not found - use /setrankedchannel to repost)"
                        )
                else:
                    await interaction.followup.send("✅ Ranked-player cache cleared.")
                return
        except PubgApiError as e:
            await interaction.followup.send(f"✅ Ranked-player cache cleared. (API error updating report: {e})")
            return
        except Exception as e:
            await interaction.followup.send(f"✅ Ranked-player cache cleared. (Error updating report: {e})")
            return
    
    await interaction.followup.send(
        "✅ Ranked-player cache cleared. The next check for each ranked queue will scan the full roster; "
        "later checks will only query players known to play that queue."
    )


@bot.tree.command(description="Update the ranked report with fresh data without clearing the cache")
async def updateranked(interaction: discord.Interaction):
    await interaction.response.defer()
    
    # Update the ranked report if a message exists
    guild_cfg = await storage.get_guild(interaction.guild_id)
    channel_id = guild_cfg.get("ranked_channel_id")
    message_id = guild_cfg.get("ranked_message_id")
    
    if channel_id and message_id:
        try:
            guild = bot.get_guild(interaction.guild_id)
            channel = bot.get_channel(channel_id)
            if guild and channel:
                result = await fetch_ranked_report(interaction.guild_id, guild.name)
                if result:
                    embed, players = result
                    try:
                        message = await channel.fetch_message(message_id)
                        await message.edit(embed=embed)
                        await interaction.followup.send(
                            "✅ Ranked report updated with fresh data."
                        )
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        await interaction.followup.send(
                            "✅ Message not found - use /setrankedchannel to repost"
                        )
                else:
                    await interaction.followup.send("No players tracked yet.")
                return
        except PubgApiError as e:
            await interaction.followup.send(f"API error updating report: {e}")
            return
        except Exception as e:
            await interaction.followup.send(f"Error updating report: {e}")
            return
    
    await interaction.followup.send(
        "No ranked report message found. Use /setrankedchannel to set up the report first."
    )


@bot.tree.command(description="Set this channel for the daily ranked report (defaults to the digest channel)")
async def setrankedchannel(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["ranked_channel_id"] = interaction.channel_id
    guild_cfg["ranked_enabled"] = True
    guild_cfg["ranked_message_id"] = None  # force a fresh message in the new channel
    await storage.save_guild(interaction.guild_id, guild_cfg)
    
    await interaction.response.defer()
    
    # Immediately post the report
    try:
        result = await fetch_ranked_report(interaction.guild_id, interaction.guild.name)
        if result:
            embed, players = result
            new_message = await interaction.channel.send(embed=embed)
            guild_cfg["ranked_message_id"] = new_message.id
            await storage.save_guild(interaction.guild_id, guild_cfg)
            
            await interaction.followup.send(
                f"✅ Ranked report posted in {interaction.channel.mention}. "
                f"It will update at 5:30am KST daily."
            )
            
            await send_audit_log(
                interaction.guild_id,
                "Channel Configured & Report Posted",
                f"Ranked report channel set and initial report posted",
                user=interaction.user,
                details={"Channel": interaction.channel_id, "Players": len(players)},
                report_embed=embed
            )
        else:
            await interaction.followup.send("No players tracked yet. Add some with `/addplayer`.")
    except PubgApiError as e:
        await interaction.followup.send(f"PUBG API error: {e}")
    except Exception as e:
        await interaction.followup.send(f"Something went wrong: {e}")


@bot.tree.command(description="Set which ranked queue the daily report tracks")
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
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["ranked_queue"] = queue.value
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Daily ranked reports will now track **{queue.name}**.")
    await send_audit_log(
        interaction.guild_id,
        "Queue Configured",
        f"Ranked report queue set to {queue.name}",
        user=interaction.user,
        details={"Queue": queue.value}
    )


# Deprecated: Time is now fixed at 5:30am KST
# @bot.tree.command(description="Post the selected ranked report at a fixed Eastern-time each day")
# @app_commands.describe(hour="0-23, Eastern time (e.g. 9 for 9am ET)", minute="Quarter-hour, defaults to :00")
# @app_commands.choices(minute=QUARTER_HOUR_CHOICES)
# async def setrankedtime(interaction: discord.Interaction, hour: app_commands.Range[int, 0, 23], minute: app_commands.Choice[int] = None):
#     await interaction.response.send_message("⚠️ This command is deprecated. The ranked report now updates daily at a fixed time of 5:30am KST.")


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
    await send_audit_log(
        interaction.guild_id,
        "Channel Configured",
        f"Daily highlights channel set",
        user=interaction.user,
        details={"Channel": interaction.channel_id}
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
    guild_cfg["survival_message_id"] = None  # force a fresh message in the new channel
    await storage.save_guild(interaction.guild_id, guild_cfg)
    
    await interaction.response.defer()
    
    # Immediately post the report
    try:
        result = await fetch_survival_mastery_report(interaction.guild_id, interaction.guild.name)
        if result:
            embeds, files = result
            new_message = await interaction.channel.send(embeds=embeds, files=files)
            guild_cfg["survival_message_id"] = new_message.id
            await storage.save_guild(interaction.guild_id, guild_cfg)
            
            weekday = guild_cfg.get("survival_weekday_est")
            if weekday is None:
                await interaction.followup.send(
                    f"✅ Survival Mastery report posted in {interaction.channel.mention}. "
                    "Use `/setsurvivaltime` to choose the weekly day and time."
                )
            else:
                weekday_name = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[weekday]
                await interaction.followup.send(
                    f"✅ Survival Mastery report posted in {interaction.channel.mention}. "
                    f"Next update: every **{weekday_name} at {guild_cfg.get('survival_hour_est', 12):02d}:{guild_cfg.get('survival_minute_est', 0):02d} Eastern**."
                )
            
            await send_audit_log(
                interaction.guild_id,
                "Channel Configured & Report Posted",
                f"Survival Mastery report channel set and initial report posted",
                user=interaction.user,
                details={"Channel": interaction.channel_id}
            )
        else:
            await interaction.followup.send("No players tracked yet. Add some with `/addplayer`.")
    except PubgApiError as e:
        await interaction.followup.send(f"PUBG API error: {e}")
    except Exception as e:
        await interaction.followup.send(f"Something went wrong: {e}")


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
    total_wins = guild_cfg.get("chicken_dinner_total_wins", 0)
    
    # If total_wins is 0 but we have recent wins, initialize the tally
    if total_wins == 0 and winners:
        total_wins = len(winners)
        guild_cfg["chicken_dinner_total_wins"] = total_wins
        await storage.save_guild(interaction.guild_id, guild_cfg)
    
    embed = build_chicken_dinner_embed(winners, is_automated=False, total_wins=total_wins)
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


@bot.tree.command(description="Set current channel for PUBG API status alerts")
async def setapistatuschannel(interaction: discord.Interaction):
    guild_cfg = await storage.get_guild(interaction.guild_id)
    guild_cfg["api_status_channel_id"] = interaction.channel_id
    await storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ PUBG API status alerts will post in {interaction.channel.mention}. "
        "The bot checks every 30 minutes and alerts if the API is down or in maintenance mode."
    )
    await send_audit_log(
        interaction.guild_id,
        "API Status Channel Set",
        f"API status alerts will post in {interaction.channel.mention}",
        user=interaction.user,
        is_automated=False,
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
    has_valid_key = bool(BOT_ADMIN_KEY) and hmac.compare_digest(secret_key.encode(), BOT_ADMIN_KEY.encode())
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

