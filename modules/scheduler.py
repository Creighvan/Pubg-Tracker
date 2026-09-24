"""
Scheduled task functions for PUBG Clan Tracker Discord Bot.

This module contains all async functions that run on schedules using
discord.ext.tasks to automatically post reports at configured times.

Functions:
    auto_digest: Clan digest every 15 minutes (checks if due)
    auto_last_active: Last active report daily (after 10pm EST, recovers from downtime)
    auto_ranked: Ranked standings daily (after 12:30am EST, recovers from downtime)
    auto_highlights: Highlights report daily (after 10:00pm EST, recovers from downtime)
    auto_clan_level: Clan level progress weekly
    auto_survival_mastery: Survival mastery weekly
    auto_donations: Donation message weekly (Sunday)
    auto_chicken_dinner: Chicken dinner congratulatory messages
    auto_feedback_prompt: Feedback collection weekly

All loops use a 15-minute check interval and only post when their specific
time conditions are met.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import discord
from discord.ext import tasks
import asyncio

import storage
from pubg_api import PubgApiError, PubgClient
import translations

from modules.config import get_scheduler_lock, _record_status_event, _bot_started_at, SUPPORT_SERVER_ID, DONATION_MESSAGE, RANKED_MODE_LABELS
from storage import modify_guild
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
from modules.embeds import build_report_status_embed, build_feedback_prompt_embed
from modules.utils import _is_due, _is_weekly_due, _is_sunday_donation_due

# Late-binding helpers to avoid stale imports at module load time
# These re-read the values from config on each call to get the real instances
def _get_bot():
    from modules.config import bot
    return bot

def _get_pubg():
    from modules.config import pubg
    return pubg


@tasks.loop(minutes=15)
async def auto_digest():
    """
    Every 15 minutes, checks whether each guild's digest is due — either
    a fixed Eastern-time hour (digest_hour_est) or the older interval-based
    behavior (post_interval_hours), depending on what's configured.
    """
    now = datetime.now(timezone.utc)
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("digest_enabled", True):
            continue
        channel_id = guild_cfg.get("post_channel_id")
        if channel_id is None:
            continue
        if not _is_due(guild_cfg, "digest_hour_est", "digest_minute_est", "last_post_at", 6):
            continue

        guild = _get_bot().get_guild(guild_id)
        channel = _get_bot().get_channel(channel_id)
        if guild is None or channel is None:
            continue
        # Mark the attempt now, before making any API calls — so a failure
        # (e.g. a transient rate limit) waits for the next full interval
        # instead of retrying on every 15-min check, which is what was
        # causing bursts and repeated rate-limit errors.
        guild_cfg["last_post_at"] = now.isoformat()
        await storage.save_guild(guild_id, guild_cfg)
        try:
            async with get_scheduler_lock():
                result = await fetch_clan_report(guild_id, guild.name)
            if result:
                embed, players = result
                await channel.send(embed=embed)
                await send_audit_log(
                    guild_id,
                    "Scheduled Report Posted",
                    f"Clan digest posted automatically",
                    is_automated=True,
                    details={"Report Type": "Clan Digest", "Players": len(players)},
                    report_embed=embed
                )
        except PubgApiError as e:
            print(f"[auto_digest] PUBG API error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_digest report failed for guild {guild_id}: {e}"[:200])
        except Exception as e:
            print(f"[auto_digest] Unexpected error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_digest report failed for guild {guild_id}: {e}"[:200])


@auto_digest.before_loop
async def before_auto_digest():
    await _get_bot().wait_until_ready()


@tasks.loop(minutes=15)
async def auto_last_active():
    """Posts the 'last active' report every 24 hours, per guild.
    Runs once per day after 10pm EST daily reset. Recovers if bot was offline."""
    kst = ZoneInfo("America/New_York")
    now_kst = datetime.now(kst)
    print(f"[auto_last_active] Running at {now_kst}")
    
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("activity_enabled", True):
            print(f"[auto_last_active] Guild {guild_id}: activity_enabled=False, skipping")
            continue
        channel_id = guild_cfg.get("last_activity_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None:
            print(f"[auto_last_active] Guild {guild_id}: No channel configured, skipping")
            continue

        # Check if we've already posted today (using last_activity_posted_at)
        last_posted = guild_cfg.get("last_activity_posted_at")
        if last_posted:
            last_posted_date = datetime.fromisoformat(last_posted).astimezone(kst)
            days_since_last_post = (now_kst.date() - last_posted_date.date()).days
            print(f"[auto_last_active] Guild {guild_id}: last_posted={last_posted}, last_posted_date={last_posted_date.date()}, now={now_kst.date()}, days_since={days_since_last_post}")
            if days_since_last_post == 0:
                print(f"[auto_last_active] Guild {guild_id}: Already posted today, skipping")
                continue  # Already posted today
            elif days_since_last_post < 0:
                print(f"[auto_last_active] Guild {guild_id}: Last post is in the future (clock skew?), treating as today and skipping")
                continue
            else:
                # Bot was offline for multiple days - proceed to update immediately
                print(f"[auto_last_active] Guild {guild_id}: Last post was {days_since_last_post} days ago, updating (recovering from offline period)")
        else:
            print(f"[auto_last_active] Guild {guild_id}: No last_posted timestamp, first run")
            # Only run after 10pm EST daily reset for first run
            if now_kst.hour < 22:
                print(f"[auto_last_active] Guild {guild_id}: Before 10pm EST ({now_kst.hour}), skipping")
                continue

        guild = _get_bot().get_guild(guild_id)
        channel = _get_bot().get_channel(channel_id)
        if guild is None:
            print(f"[auto_last_active] Guild {guild_id}: Guild not found (bot may have been removed), skipping")
            continue
        if channel is None:
            print(f"[auto_last_active] Guild {guild_id}: Channel {channel_id} not found (may have been deleted or bot lacks permission), skipping")
            continue
        
        print(f"[auto_last_active] Guild {guild_id}: All checks passed, posting report")
        try:
            async with get_scheduler_lock():
                result = await fetch_last_active_report(guild_id, guild.name)
            if result:
                embed, players = result
                message_id = guild_cfg.get("last_activity_message_id")
                
                # Edit existing message or post new one
                if message_id:
                    try:
                        message = await channel.fetch_message(message_id)
                        await message.edit(embed=embed)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        # Message deleted/inaccessible - post new one
                        new_message = await channel.send(embed=embed)
                        guild_cfg["last_activity_message_id"] = new_message.id
                else:
                    new_message = await channel.send(embed=embed)
                    guild_cfg["last_activity_message_id"] = new_message.id

                # Mark as posted today and save using modify_guild for atomic write
                def save_config(guild):
                    guild["last_activity_posted_at"] = datetime.now(timezone.utc).isoformat()
                await storage.modify_guild(guild_id, save_config)
                
                print(f"[auto_last_active] Guild {guild_id}: Report posted successfully")
                
                await send_audit_log(
                    guild_id,
                    "Scheduled Report Updated",
                    f"Last active report updated at 10pm EST daily reset",
                    is_automated=True,
                    details={"Report Type": "Last Active", "Players": len(players)},
                    report_embed=embed
                )
        except PubgApiError as e:
            print(f"[auto_last_active] PUBG API error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_last_active report failed for guild {guild_id}: {e}"[:200])
        except Exception as e:
            print(f"[auto_last_active] Unexpected error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_last_active report failed for guild {guild_id}: {e}"[:200])


@auto_last_active.before_loop
async def before_auto_last_active():
    await _get_bot().wait_until_ready()


@tasks.loop(minutes=15)
async def auto_ranked():
    """
    Updates the ranked standings report daily at 12:30am EST.
    Edits a single message in place instead of posting new messages.
    Uses a posted_at timestamp to ensure it runs once per day even if
    the bot is offline during the 12:30am EST window.
    """
    now = datetime.now(timezone.utc)
    
    # Check if it's 12:30am EST daily reset time
    kst = ZoneInfo("America/New_York")
    now_kst = datetime.now(kst)
    reset_time_kst = now_kst.replace(hour=0, minute=30, second=0, microsecond=0)
    if now_kst < reset_time_kst:
        reset_time_kst -= timedelta(days=1)
    
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("ranked_enabled", True):
            continue
        channel_id = guild_cfg.get("ranked_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None:
            continue
        
        # Check if already posted today (using EST date)
        posted_at = guild_cfg.get("ranked_posted_at")
        if posted_at:
            posted_date = datetime.fromisoformat(posted_at).astimezone(kst).date()
            today_kst = reset_time_kst.date()
            if posted_date >= today_kst:
                continue  # Already posted today (or future date)
        
        # Only run during or after the 12:30am EST window
        reset_total = 0 * 60 + 30  # 12:30 AM in minutes
        now_total = now_kst.hour * 60 + now_kst.minute
        if now_total < reset_total:
            continue  # Not yet 12:30 AM EST

        guild = _get_bot().get_guild(guild_id)
        channel = _get_bot().get_channel(channel_id)
        if guild is None or channel is None:
            continue
        
        try:
            async with get_scheduler_lock():
                result = await fetch_ranked_report(guild_id, guild.name)
            if result:
                embed, players = result
                message_id = guild_cfg.get("ranked_message_id")
                
                # Edit existing message or post new one
                if message_id:
                    try:
                        message = await channel.fetch_message(message_id)
                        await message.edit(embed=embed)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        # Message deleted/inaccessible - post new one
                        new_message = await channel.send(embed=embed)
                        guild_cfg["ranked_message_id"] = new_message.id
                        await storage.save_guild(guild_id, guild_cfg)
                else:
                    new_message = await channel.send(embed=embed)
                    guild_cfg["ranked_message_id"] = new_message.id
                    await storage.save_guild(guild_id, guild_cfg)
                
                # Mark as posted today
                guild_cfg["ranked_posted_at"] = now.isoformat()
                await storage.save_guild(guild_id, guild_cfg)
                
                await send_audit_log(
                    guild_id,
                    "Scheduled Report Updated",
                    f"Ranked standings report updated at 12:30am EST daily",
                    is_automated=True,
                    details={"Report Type": "Ranked Standings", "Players": len(players)},
                    report_embed=embed
                )
        except PubgApiError as e:
            print(f"[auto_ranked] PUBG API error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_ranked report failed for guild {guild_id}: {e}"[:200])
        except Exception as e:
            print(f"[auto_ranked] Unexpected error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_ranked report failed for guild {guild_id}: {e}"[:200])


@auto_ranked.before_loop
async def before_auto_ranked():
    await _get_bot().wait_until_ready()


@tasks.loop(minutes=15)
async def _wait_until_time(target_hour: int, target_minute: int, timezone_str: str = "America/New_York"):
    """Sleep until the specified time in the given timezone."""
    tz = ZoneInfo(timezone_str)
    while True:
        now = datetime.now(tz)
        target = datetime.now(tz).replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        
        # If target time has passed today, schedule for tomorrow
        if now >= target:
            target += timedelta(days=1)
        
        sleep_seconds = (target - now).total_seconds()
        print(f"[scheduler] Sleeping {sleep_seconds/3600:.1f} hours until {target_hour}:{target_minute:02d} {timezone_str}")
        await asyncio.sleep(sleep_seconds)
        break


async def auto_highlights():
    """
    Posts the 'last 24 hours' highlights report (fun titles + top 10 +
    human/bot kill split) every 24 hours at exactly 10:00pm EST.
    Edits existing message instead of posting new ones.
    """
    while True:
        # Wait until 10:00pm EST
        await _wait_until_time(22, 0, "America/New_York")
        
        # Run the highlights report for all guilds
        kst = ZoneInfo("America/New_York")
        now_kst = datetime.now(kst)
        
        for guild_id in await storage.all_guild_ids():
            guild_cfg = await storage.get_guild(guild_id)
            if not guild_cfg.get("highlights_enabled", True):
                continue
            channel_id = guild_cfg.get("highlights_channel_id") or guild_cfg.get("post_channel_id")
            if channel_id is None:
                continue

            # Check if we've already posted today (using highlights_posted_at)
            last_posted = guild_cfg.get("highlights_posted_at")
            if last_posted:
                last_posted_date = datetime.fromisoformat(last_posted).astimezone(kst)
                if last_posted_date.date() == now_kst.date():
                    continue  # Already posted today

            guild = _get_bot().get_guild(guild_id)
            channel = _get_bot().get_channel(channel_id)
            if guild is None or channel is None:
                continue
            
            try:
                async with get_scheduler_lock():
                    result = await fetch_highlights_report(guild_id, guild.name)
                if result:
                    embed, players = result
                    message_id = guild_cfg.get("highlights_message_id")
                    
                    # Edit existing message or post new one
                    if message_id:
                        try:
                            message = await channel.fetch_message(message_id)
                            await message.edit(embed=embed)
                        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                            # Message deleted/inaccessible - post new one
                            new_message = await channel.send(embed=embed)
                            guild_cfg["highlights_message_id"] = new_message.id
                    else:
                        new_message = await channel.send(embed=embed)
                        guild_cfg["highlights_message_id"] = new_message.id

                    # Mark as posted today immediately after posting (before audit log)
                    def save_config(guild):
                        guild["highlights_posted_at"] = datetime.now(timezone.utc).isoformat()
                    await storage.modify_guild(guild_id, save_config)
                    
                    # Send audit log (non-critical if this fails)
                    try:
                        await send_audit_log(
                            guild_id,
                            "Scheduled Report Updated",
                            f"Highlights report updated at 10:00pm EST daily",
                            is_automated=True,
                            details={"Report Type": "Highlights", "Players": len(players)},
                            report_embed=embed
                        )
                    except Exception as audit_error:
                        pass  # Audit log failure is non-critical
            except PubgApiError as e:
                print(f"[auto_highlights] PUBG API error for guild {guild_id}: {e}")
                await _record_status_event(f"⚠️ auto_highlights report failed for guild {guild_id}: {e}"[:200])
            except Exception as e:
                print(f"[auto_highlights] Unexpected error for guild {guild_id}: {e}")
                await _record_status_event(f"⚠️ auto_highlights report failed for guild {guild_id}: {e}"[:200])


async def run_auto_highlights():
    """Wrapper to start auto_highlights as a background task."""
    await _get_bot().wait_until_ready()
    await auto_highlights()


@tasks.loop(minutes=15)
async def auto_clan_level():
    """Post the configured clan-level snapshot once per Eastern calendar week."""
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("clan_level_enabled", True):
            continue
        channel_id = guild_cfg.get("clan_channel_id")
        if channel_id is None or not _is_weekly_due(guild_cfg):
            continue

        channel = _get_bot().get_channel(channel_id)
        guild = _get_bot().get_guild(guild_id)
        if channel is None or guild is None:
            continue
        try:
            async with get_scheduler_lock():
                result = await fetch_clan_level_report(guild_id)
            if result is None:
                continue
            embed, clan = result
            message_id = guild_cfg.get("clan_message_id")
            
            # Edit existing message or post new one
            if message_id:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    # Message deleted/inaccessible - post new one
                    new_message = await channel.send(embed=embed)
                    guild_cfg["clan_message_id"] = new_message.id
                    await storage.save_guild(guild_id, guild_cfg)
            else:
                new_message = await channel.send(embed=embed)
                guild_cfg["clan_message_id"] = new_message.id
                await storage.save_guild(guild_id, guild_cfg)
            
            # A snapshot only counts after Discord accepted the report.
            guild_cfg["clan_posted_at"] = datetime.now(timezone.utc).isoformat()
            guild_cfg["clan_last_level"] = clan["level"]
            guild_cfg["clan_last_member_count"] = clan["member_count"]
            await storage.save_guild(guild_id, guild_cfg)
        except PubgApiError as e:
            print(f"[auto_clan_level] PUBG API error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_clan_level report failed for guild {guild_id}: {e}"[:200])
        except Exception as e:
            print(f"[auto_clan_level] Unexpected error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_clan_level report failed for guild {guild_id}: {e}"[:200])


@auto_clan_level.before_loop
async def before_auto_clan_level():
    await _get_bot().wait_until_ready()


@tasks.loop(minutes=15)
async def auto_survival_mastery():
    """Post the configured weekly Survival Mastery snapshot."""
    now = datetime.now(timezone.utc)
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("survival_enabled", True):
            continue
        channel_id = guild_cfg.get("survival_channel_id")
        if channel_id is None or not _is_weekly_due(
            guild_cfg,
            weekday_key="survival_weekday_est",
            hour_key="survival_hour_est",
            minute_key="survival_minute_est",
            posted_key="survival_posted_at",
        ):
            continue

        channel = _get_bot().get_channel(channel_id)
        guild = _get_bot().get_guild(guild_id)
        if channel is None or guild is None:
            continue
        try:
            async with get_scheduler_lock():
                result = await fetch_survival_mastery_report(guild_id, guild.name)
            if result is None:
                continue
            embeds, files = result
            message_id = guild_cfg.get("survival_message_id")
            
            # Survival Mastery uses files (images), so we must delete and repost
            # Discord doesn't allow editing files on existing messages
            if message_id:
                try:
                    old_message = await channel.fetch_message(message_id)
                    await old_message.delete()
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    # Message already deleted or inaccessible - just post new one
                    pass
            new_message = await channel.send(embeds=embeds, files=files)
            guild_cfg["survival_message_id"] = new_message.id
            await storage.save_guild(guild_id, guild_cfg)
            
            guild_cfg["survival_posted_at"] = now.isoformat()
            await storage.save_guild(guild_id, guild_cfg)
        except PubgApiError as e:
            print(f"[auto_survival_mastery] PUBG API error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_survival_mastery report failed for guild {guild_id}: {e}"[:200])
        except Exception as e:
            print(f"[auto_survival_mastery] Unexpected error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_survival_mastery report failed for guild {guild_id}: {e}"[:200])


@auto_survival_mastery.before_loop
async def before_auto_survival_mastery():
    await _get_bot().wait_until_ready()


@tasks.loop(minutes=15)
async def auto_donations():
    """Post the optional donation link on Sunday for servers that opt in."""
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("donation_enabled", True):
            continue
        channel_id = guild_cfg.get("donation_channel_id")
        if channel_id is None or not _is_sunday_donation_due(guild_cfg):
            continue
        channel = _get_bot().get_channel(channel_id)
        if channel is None:
            continue
        try:
            await channel.send(DONATION_MESSAGE)
            guild_cfg["donation_posted_at"] = datetime.now(timezone.utc).isoformat()
            await storage.save_guild(guild_id, guild_cfg)
            # Create embed for donation message
            donation_embed = discord.Embed(
                title="☕ Donation Message",
                description=DONATION_MESSAGE,
                color=discord.Color.gold(),
                timestamp=datetime.now(timezone.utc)
            )
            await send_audit_log(
                guild_id,
                "Scheduled Report Posted",
                f"Donation message posted automatically",
                is_automated=True,
                details={"Report Type": "Donation Message"},
                report_embed=donation_embed
            )
        except Exception as e:
            print(f"[auto_donations] Could not post for guild {guild_id}: {e}")


@auto_donations.before_loop
async def before_auto_donations():
    await _get_bot().wait_until_ready()


@tasks.loop(minutes=15)
async def auto_chicken_dinner():
    """
    Every 15 minutes, checks each opted-in guild's roster for recent squad wins
    in the last 5 matches per player. Groups players who won together in the same match.
    Updates a persistent message with the list of squad wins and a running tally
    of total wins for the current 24-hour period starting at 12:00am EST.
    The tally and posted matches reset daily at 12:00am EST.
    """
    kst = ZoneInfo("America/New_York")
    now_kst = datetime.now(kst)
    
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("chicken_dinner_enabled", True):
            continue
        channel_id = guild_cfg.get("chicken_dinner_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None or not guild_cfg["players"]:
            continue
        guild = _get_bot().get_guild(guild_id)
        channel = _get_bot().get_channel(channel_id)
        if guild is None or channel is None:
            continue

        # Check if we need to reset for new day (12:00am EST daily reset)
        last_reset = guild_cfg.get("chicken_dinner_reset_at")
        needs_reset = False
        if last_reset:
            last_reset_date = datetime.fromisoformat(last_reset).astimezone(kst)
            # Reset if we're on a different date AND it's after 12:00am EST
            if last_reset_date.date() != now_kst.date() and now_kst.hour >= 0:
                needs_reset = True
        else:
            # First time setup - set reset time
            guild_cfg["chicken_dinner_reset_at"] = datetime.now(timezone.utc).isoformat()
            await storage.save_guild(guild_id, guild_cfg)
            guild_cfg = await storage.get_guild(guild_id)
        
        if needs_reset:
            # New day - reset tally and posted matches
            guild_cfg["chicken_dinner_posted_matches"] = {}
            guild_cfg["chicken_dinner_total_wins"] = 0
            guild_cfg["chicken_dinner_reset_at"] = datetime.now(timezone.utc).isoformat()
            await storage.save_guild(guild_id, guild_cfg)
            # Update guild_cfg after reset
            guild_cfg = await storage.get_guild(guild_id)

        try:
            async with get_scheduler_lock():
                wins, _ = await _get_pubg().get_squad_wins(guild_cfg["players"], matches_to_check=5)
        except PubgApiError as e:
            print(f"[auto_chicken_dinner] PUBG API error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_chicken_dinner report failed for guild {guild_id}: {e}"[:200])
            continue
        except Exception as e:
            print(f"[auto_chicken_dinner] Unexpected error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_chicken_dinner report failed for guild {guild_id}: {e}"[:200])
            continue

        posted_matches = guild_cfg.get("chicken_dinner_posted_matches", {})
        updated_matches = dict(posted_matches)
        new_wins = []
        
        # Process squad wins from the new format
        for win in wins:
            match_id = win.get("match_id")
            if not match_id:
                continue
            
            # Check if this match was already posted
            if match_id in posted_matches:
                continue
            
            # Extract player data for this win
            players_data = []
            for player in win.get("players", []):
                players_data.append((player["name"], {
                    "winPlace": player["winPlace"],
                    "kills": player["kills"],
                    "match_id": match_id,
                    "created_at": win.get("created_at")
                }))
            
            new_wins.extend(players_data)
            # Track this match as posted using match_id as key
            updated_matches[match_id] = match_id

        # Update running tally for current 24-hour period (count matches, not players)
        current_total = guild_cfg.get("chicken_dinner_total_wins", 0)
        new_match_count = len([win for win in wins if win.get("match_id") not in posted_matches])
        total_wins = current_total + new_match_count

        try:
            from modules.embeds import build_chicken_dinner_embed
            
            # Get all squad wins for the display
            all_winners = []
            for win in wins:
                for player in win.get("players", []):
                    all_winners.append((player["name"], {
                        "winPlace": player["winPlace"],
                        "kills": player["kills"],
                        "match_id": win.get("match_id")
                    }))
            
            if not all_winners:
                # No recent wins, skip update
                continue
            
            embed = build_chicken_dinner_embed(all_winners, is_automated=True, total_wins=total_wins)
            
            # Try to edit existing message
            message_id = guild_cfg.get("chicken_dinner_message_id")
            message = None
            if message_id:
                try:
                    message = await channel.fetch_message(message_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    message = None
            
            if message is not None:
                await message.edit(embed=embed)
            else:
                new_message = await channel.send(embed=embed)
                guild_cfg["chicken_dinner_message_id"] = new_message.id
            
            # Only record these matches as alerted once Discord actually
            # accepted the message
            guild_cfg["chicken_dinner_posted_matches"] = updated_matches
            guild_cfg["chicken_dinner_total_wins"] = total_wins
            await storage.save_guild(guild_id, guild_cfg)
            
            if new_wins:
                await send_audit_log(
                    guild_id,
                    "Automated Event",
                    f"Chicken dinner report updated",
                    is_automated=True,
                    details={"Event Type": "Chicken Dinner", "New Wins": len(new_wins), "Total Wins": total_wins},
                    report_embed=embed
                )
        except Exception as e:
            print(f"[auto_chicken_dinner] Could not post for guild {guild_id}: {e}")


@auto_chicken_dinner.before_loop
async def before_auto_chicken_dinner():
    await _get_bot().wait_until_ready()


@tasks.loop(minutes=30)
async def auto_feedback_prompt():
    """Posts a feedback prompt with an interactive modal button once every 14 days per guild."""
    now = datetime.now(timezone.utc)
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if guild_id == SUPPORT_SERVER_ID:
            continue

        last_prompt = guild_cfg.get("last_feedback_prompt_at")
        if last_prompt:
            try:
                last_dt = datetime.fromisoformat(last_prompt)
                if now - last_dt < timedelta(days=14):
                    continue
            except (ValueError, TypeError):
                pass

        guild = _get_bot().get_guild(guild_id)
        if guild is None:
            continue

        channel_id = (
            guild_cfg.get("post_channel_id")
            or guild_cfg.get("clan_channel_id")
            or guild_cfg.get("highlights_channel_id")
            or guild_cfg.get("last_activity_channel_id")
        )
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel is None:
            channel = guild.system_channel or next(
                (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages),
                None,
            )
        if channel is None:
            continue

        guild_cfg["last_feedback_prompt_at"] = now.isoformat()
        await storage.save_guild(guild_id, guild_cfg)

        embed = build_feedback_prompt_embed()
        try:
            # Import FeedbackPromptView from bot.py to avoid circular import
            # We import it here dynamically since it's defined in the main bot file
            import bot as bot_module
            FeedbackPromptView = bot_module.FeedbackPromptView
            await channel.send(embed=embed, view=FeedbackPromptView())
            print(f"[auto_feedback] Posted 14-day feedback prompt to {guild.name} (#{channel.name})")
        except Exception as e:
            print(f"[auto_feedback] Failed to send prompt in {guild.name}: {e}")


@auto_feedback_prompt.before_loop
async def before_auto_feedback_prompt():
    await _get_bot().wait_until_ready()


# Audit log function injection - set by bot.py during startup
_audit_log_func = None


def _set_audit_log_func(func):
    """Set the audit log function from bot.py."""
    global _audit_log_func
    _audit_log_func = func


async def send_audit_log(guild_id: int, title: str, description: str, is_automated: bool = False, details: dict = None, report_embed: discord.Embed = None):
    """Send an audit log entry to the configured audit server."""
    # This is a wrapper that will be replaced by the real implementation from bot.py
    # The real implementation is set in main.py via _set_audit_log_func
    # Note: bot.py signature is (guild_id, event_type, description, user, details, is_automated, report_embed)
    # We map title->event_type and pass None for user since scheduled events have no user
    if _audit_log_func:
        return await _audit_log_func(guild_id, title, description, None, details, is_automated, report_embed)
    print(f"[audit_log] Audit log function not set: {title} for guild {guild_id}")




def start_all_scheduled_tasks(bot_instance):
    """Start all scheduled task loops."""
    auto_digest.start()
    auto_last_active.start()
    auto_ranked.start()
    # Start auto_highlights as a background task (custom 24-hour schedule)
    bot_instance.loop.create_task(run_auto_highlights())
    auto_clan_level.start()
    auto_survival_mastery.start()
    auto_donations.start()
    auto_chicken_dinner.start()
    auto_feedback_prompt.start()
    # auto_api_status.start()  # DISABLED: API status feature removed
