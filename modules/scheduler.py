"""
Scheduled task functions for PUBG Clan Tracker Discord Bot.

This module contains all async functions that run on schedules using
discord.ext.tasks to automatically post reports at configured times.

Functions:
    auto_digest: Clan digest every 15 minutes (checks if due)
    auto_last_active: Last active report daily (after 3am KST, recovers from downtime)
    auto_ranked: Ranked standings daily (after 5:30am KST, recovers from downtime)
    auto_highlights: Highlights report daily (after 3am KST, recovers from downtime)
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
    Runs once per day after 3am KST daily reset. Recovers if bot was offline."""
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst)
    
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("activity_enabled", True):
            continue
        channel_id = guild_cfg.get("last_activity_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None:
            continue

        # Check if we've already posted today (using last_activity_posted_at)
        last_posted = guild_cfg.get("last_activity_posted_at")
        if last_posted:
            last_posted_date = datetime.fromisoformat(last_posted).astimezone(kst)
            if last_posted_date.date() == now_kst.date():
                continue  # Already posted today
        
        # Only run after 3am KST daily reset
        if now_kst.hour < 3:
            continue

        guild = _get_bot().get_guild(guild_id)
        channel = _get_bot().get_channel(channel_id)
        if guild is None or channel is None:
            continue
        
        try:
            async with get_scheduler_lock():
                result = await fetch_last_active_report(guild_id, guild.name)
            if result:
                embed, players = result
                message_id = guild_cfg.get("last_activity_message_id")
                
                # Edit existing message or post new one
                message_id = guild_cfg.get("last_activity_message_id")
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
                
                await send_audit_log(
                    guild_id,
                    "Scheduled Report Updated",
                    f"Last active report updated at 3am KST daily reset",
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
    Updates the ranked standings report daily at 5:30am KST.
    Edits a single message in place instead of posting new messages.
    Uses a posted_at timestamp to ensure it runs once per day even if
    the bot is offline during the 5:30am KST window.
    """
    now = datetime.now(timezone.utc)
    
    # Check if it's 5:30am KST daily reset time
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst)
    reset_time_kst = now_kst.replace(hour=5, minute=30, second=0, microsecond=0)
    if now_kst < reset_time_kst:
        reset_time_kst -= timedelta(days=1)
    
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("ranked_enabled", True):
            continue
        channel_id = guild_cfg.get("ranked_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None:
            continue
        
        # Check if already posted today (using KST date)
        posted_at = guild_cfg.get("ranked_posted_at")
        if posted_at:
            posted_date = datetime.fromisoformat(posted_at).astimezone(kst).date()
            today_kst = now_kst.date()
            if posted_date >= today_kst:
                continue  # Already posted today (or future date)
        
        # Only run during or after the 5:30am KST window
        reset_total = 5 * 60 + 30  # 5:30 AM in minutes
        now_total = now_kst.hour * 60 + now_kst.minute
        if now_total < reset_total:
            continue  # Not yet 5:30 AM KST

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
                    f"Ranked standings report updated at 5:30am KST daily",
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
async def auto_highlights():
    """
    Posts the 'last 24 hours' highlights report (fun titles + top 10 +
    human/bot kill split) every 24 hours, per guild. Runs once per day after 3am KST daily reset.
    Edits existing message instead of posting new ones.
    """
    kst = ZoneInfo("Asia/Seoul")
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
        
        # Only run after 3am KST daily reset
        if now_kst.hour < 3:
            continue

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

                # Mark as posted today and save using modify_guild for atomic write
                def save_config(guild):
                    guild["highlights_posted_at"] = datetime.now(timezone.utc).isoformat()
                await storage.modify_guild(guild_id, save_config)
                
                await send_audit_log(
                    guild_id,
                    "Scheduled Report Updated",
                    f"Highlights report updated at 3am KST daily reset",
                    is_automated=True,
                    details={"Report Type": "Highlights", "Players": len(players)},
                    report_embed=embed
                )
        except PubgApiError as e:
            print(f"[auto_highlights] PUBG API error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_highlights report failed for guild {guild_id}: {e}"[:200])
        except Exception as e:
            print(f"[auto_highlights] Unexpected error for guild {guild_id}: {e}")
            await _record_status_event(f"⚠️ auto_highlights report failed for guild {guild_id}: {e}"[:200])


@auto_highlights.before_loop
async def before_auto_highlights():
    await _get_bot().wait_until_ready()


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
    Every 15 minutes, checks each opted-in guild's roster for new Chicken
    Dinners in players' most recent matches. Updates a persistent message
    with grouped wins (players who won together on the same line) and a
    running tally of total wins.
    """
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

        try:
            async with get_scheduler_lock():
                results, _ = await _get_pubg().get_recent_wins(guild_cfg["players"])
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
        for name, data in results.items():
            if data.get("winPlace") != 1:
                continue
            match_id = data.get("match_id")
            key = name.lower()
            if match_id and posted_matches.get(key) == match_id:
                continue  # already alerted for this exact match
            new_wins.append((name, data))
            if match_id:
                updated_matches[key] = match_id

        # Update running tally
        current_total = guild_cfg.get("chicken_dinner_total_wins", 0)
        
        # If total is 0 and we have recent wins, initialize it (first-time setup)
        if current_total == 0:
            all_winners = [(name, data) for name, data in results.items() if data.get("winPlace") == 1]
            if all_winners:
                current_total = len(all_winners)
        
        total_wins = current_total + len(new_wins)

        try:
            from modules.embeds import build_chicken_dinner_embed
            
            # Get all recent wins (not just new ones) for the display
            all_winners = [(name, data) for name, data in results.items() if data.get("winPlace") == 1]
            
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


# Track previous API status to only update when it changes
_previous_api_status = {"status": None, "error": None, "version": None, "days_old": None}


# DISABLED: API status feature removed due to unreliable PUBG.PLUS integration
# @tasks.loop(minutes=30)
# async def auto_api_status():
#     """
#     Check PUBG API status every 30 minutes and update the live embed ONLY if status changed.
#     Uses the official /status endpoint to check service health.
#     Similar to bot status - single message that gets edited in place.
#     """
#     global _previous_api_status
#     
#     try:
#         async with get_scheduler_lock():
#             pubg = _get_pubg()
#             status = await pubg.get_api_status()
#             
#             # Determine current status
#             current_status = {}
#
#             # Check PUBG.PLUS game server status first (most accurate for game servers)
#             pubg_plus_status = status.get("pubg_plus_status", "unknown")
#             if pubg_plus_status == "up":
#                 server_status = status.get("pubg_plus_server_status", 1)
#                 maintenance = status.get("pubg_plus_maintenance", 1)
#
#                 # server_status: 1 = normal, 2 = maintenance
#                 # maintenance: 1 = normal, 2 = maintenance
#                 if server_status == 2 or maintenance == 2:
#                     current_status["status"] = "down"
#                     current_status["error"] = "PUBG game servers are under maintenance"
#                     current_status["server_version"] = status.get("pubg_plus_server_version", "unknown")
#                     current_status["online_players"] = status.get("pubg_plus_online", 0)
#                 else:
#                     current_status["status"] = "operational"
#                     current_status["server_version"] = status.get("pubg_plus_server_version", "unknown")
#                     current_status["online_players"] = status.get("pubg_plus_online", 0)
#             elif pubg_plus_status == "down":
#                 current_status["status"] = "down"
#                 current_status["error"] = f"Unable to check PUBG.PLUS server status: {status.get('pubg_plus_error', 'Unknown error')}"
#             elif pubg_plus_status == "unavailable":
#                 # PUBG.PLUS is unavailable - fall back to Steam and official API status
#                 steam_status = status.get("steam_status", "unknown")
#                 if steam_status == "down":
#                     current_status["status"] = "degraded"
#                     current_status["error"] = f"Steam servers are down: {status.get('steam_error', 'Unknown error')}"
#                 elif "error" in status:
#                     current_status["status"] = "degraded"
#                     current_status["error"] = status.get("error", "Unknown API error")
#                 else:
#                     # No errors - assume operational based on official API
#                     current_status["status"] = "operational"
#                     current_status["note"] = "PUBG.PLUS unavailable - using official API status"
#             else:
#                 # Fallback to Steam status check
#                 steam_status = status.get("steam_status", "unknown")
#                 if steam_status == "down":
#                     current_status["status"] = "down"
#                     current_status["error"] = f"Steam servers are down: {status.get('steam_error', 'Unknown error')}"
#                 elif "error" in status:
#                     current_status["status"] = "down"
#                     current_status["error"] = status["error"]
#                 else:
#                     released_at = status.get("releasedAt")
#                     api_version = status.get("id")
#
#                     if released_at and api_version:
#                         release_date = datetime.fromisoformat(released_at.replace("Z", "+00:00"))
#                         days_old = (datetime.now(timezone.utc) - release_date).days
#
#                         if days_old > 365:
#                             current_status["status"] = "warning"
#                             current_status["version"] = api_version
#                             current_status["days_old"] = days_old
#                         else:
#                             current_status["status"] = "operational"
#                             current_status["version"] = api_version
#                     else:
#                         # No release date/version info - API is still operational
#                         current_status["status"] = "operational"
#                         current_status["version"] = status.get("id", "unknown")
#             
#             # Build and send status message
#             bot = _get_bot()
#             from storage import all_guild_ids, get_guild
#             
#             # Save previous status before processing to detect actual changes
#             status_actually_changed = (current_status != _previous_api_status)
#             
#             for guild_id in await all_guild_ids():
#                 guild_cfg = await get_guild(guild_id)
#                 channel_id = guild_cfg.get("api_status_channel_id")
#                 if not channel_id:
#                     continue
#                 
#                 # Check if this guild needs an initial post (no message_id yet)
#                 needs_initial_post = not guild_cfg.get("api_status_message_id")
#                 
#                 # Skip if status unchanged AND this guild already has a message
#                 if not needs_initial_post and current_status == _previous_api_status:
#                     continue
#                 
#                 guild = bot.get_guild(int(guild_id))
#                 if not guild:
#                     continue
#                 
#                 channel = guild.get_channel(channel_id)
#                 if not channel:
#                     continue
#                 
#                 # Build embed based on status
#                 if current_status["status"] == "down":
#                     status_text = "🔴 DOWN"
#                     status_color = discord.Color.red()
#                     description = f"**Unable to reach PUBG API:** {current_status['error']}\n\n"
#                     description += "The bot cannot determine the reason or estimated downtime from the API. "
#                     description += "Check the following for official updates:\n"
#                     description += "• https://developer.pubg.com/status\n"
#                     description += "• @PUBG_Support on Twitter/X\n"
#                     description += "• Downdetector PUBG page\n"
#                     description += "• Steam Server Status: https://steamstat.us"
#                 elif current_status["status"] == "warning":
#                     status_text = "🟡 WARNING"
#                     status_color = discord.Color.orange()
#                     description = f"API version is {current_status['days_old']} days old. This may indicate reduced service or maintenance mode.\n\n"
#                     description += "Check official channels for maintenance details:\n"
#                     description += "• https://developer.pubg.com/status\n"
#                     description += "• @PUBG_Support on Twitter/X"
#                 else:  # operational
#                     status_text = "🟢 OPERATIONAL"
#                     status_color = discord.Color.green()
#                     description = f"PUBG game servers are operational."
#                     if current_status.get("server_version"):
#                         description += f"\nServer Version: {current_status['server_version']}"
#                     if current_status.get("online_players"):
#                         description += f"\nOnline Players: {current_status['online_players']:,}"
#                     if current_status.get("version"):
#                         description += f"\nAPI Version: {current_status['version']}"
#                 
#                 embed = discord.Embed(
#                     title=f"PUBG Server Status - {status_text}",
#                     description=description,
#                     color=status_color,
#                     timestamp=datetime.now(timezone.utc),
#                 )
#                 embed.set_footer(text="Updates only when status changes • Game server data from PUBG.PLUS")
#                 
#                 # Try to edit existing message, or post new one
#                 message_id = guild_cfg.get("api_status_message_id")
#                 message_edited = False
#                 
#                 if message_id:
#                     try:
#                         message = await channel.fetch_message(message_id)
#                         await message.edit(embed=embed)
#                         message_edited = True
#                     except (discord.NotFound, discord.Forbidden, discord.HTTPException):
#                         # Message doesn't exist or can't be edited, will post new
#                         pass
#                 
#                 if not message_edited:
#                     new_message = await channel.send(embed=embed)
#                     guild_cfg["api_status_message_id"] = new_message.id
#                     await storage.save_guild(int(guild_id), guild_cfg)
#             
#             # Update global status after processing all guilds
#             _previous_api_status = current_status
#             
#             # Only log if status actually changed (not every tick)
#             if status_actually_changed:
#                 await _record_status_event(f"📊 API status changed to {current_status['status']}")
#             
#     except Exception as e:
#         print(f"[auto_api_status] Error checking API status: {e}")
#         await _record_status_event(f"⚠️ auto_api_status error: {e}"[:200])
#
#
# @auto_api_status.before_loop
# async def before_auto_api_status():
#     await _get_bot().wait_until_ready()


def start_all_scheduled_tasks(bot_instance):
    """Start all scheduled task loops."""
    auto_digest.start()
    auto_last_active.start()
    auto_ranked.start()
    auto_highlights.start()
    auto_clan_level.start()
    auto_survival_mastery.start()
    auto_donations.start()
    auto_chicken_dinner.start()
    auto_feedback_prompt.start()
    # auto_api_status.start()  # DISABLED: API status feature removed
