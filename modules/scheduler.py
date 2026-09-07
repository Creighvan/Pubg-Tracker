"""
Scheduled task functions for PUBG Clan Tracker Discord Bot.

This module contains all async functions that run on schedules using
discord.ext.tasks to automatically post reports at configured times.

Functions:
    auto_digest: Clan digest every 15 minutes (checks if due)
    auto_last_active: Last active report daily (at 3am KST)
    auto_ranked: Ranked standings daily
    auto_highlights: Daily highlights every 24 hours
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
from pubg_api import PubgApiError
import translations

from modules.config import get_scheduler_lock, _record_status_event, _bot_started_at, SUPPORT_SERVER_ID, DONATION_MESSAGE, RANKED_MODE_LABELS
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
    """Posts the 'last active' report every 24 hours, per guild, same
    interval-based pattern as auto_digest. Updates a single message in place
    at 3am KST daily reset instead of posting new messages."""
    now = datetime.now(timezone.utc)
    
    # Check if it's 3am KST daily reset time
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst)
    reset_time_kst = now_kst.replace(hour=3, minute=0, second=0, microsecond=0)
    if now_kst < reset_time_kst:
        reset_time_kst -= timedelta(days=1)
    
    # Only update during a 15-minute window around 3am KST
    reset_total = 3 * 60  # 3:00 AM in minutes
    now_total = now_kst.hour * 60 + now_kst.minute
    if not (reset_total <= now_total < reset_total + 15):
        return
    
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("activity_enabled", True):
            continue
        channel_id = guild_cfg.get("last_activity_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None:
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
                if message_id:
                    try:
                        message = await channel.fetch_message(message_id)
                        await message.edit(embed=embed)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        # Message deleted/inaccessible - post new one
                        new_message = await channel.send(embed=embed)
                        guild_cfg["last_activity_message_id"] = new_message.id
                        await storage.save_guild(guild_id, guild_cfg)
                else:
                    new_message = await channel.send(embed=embed)
                    guild_cfg["last_activity_message_id"] = new_message.id
                    await storage.save_guild(guild_id, guild_cfg)
                
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
    """
    now = datetime.now(timezone.utc)
    
    # Check if it's 5:30am KST daily reset time
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst)
    reset_time_kst = now_kst.replace(hour=5, minute=30, second=0, microsecond=0)
    if now_kst < reset_time_kst:
        reset_time_kst -= timedelta(days=1)
    
    # Only update during a 15-minute window around 5:30am KST
    reset_total = 5 * 60 + 30  # 5:30 AM in minutes
    now_total = now_kst.hour * 60 + now_kst.minute
    if not (reset_total <= now_total < reset_total + 15):
        return
    
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("ranked_enabled", True):
            continue
        channel_id = guild_cfg.get("ranked_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None:
            continue

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
    human/bot kill split) every 24 hours, per guild. This is the heaviest
    report the bot runs (telemetry downloads), so it's worth giving it
    plenty of headroom rather than tightening the interval.
    """
    now = datetime.now(timezone.utc)
    for guild_id in await storage.all_guild_ids():
        guild_cfg = await storage.get_guild(guild_id)
        if not guild_cfg.get("highlights_enabled", True):
            continue
        channel_id = guild_cfg.get("highlights_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None:
            continue
        if not _is_due(guild_cfg, "highlights_hour_est", "highlights_minute_est", "highlights_posted_at", 24):
            continue

        guild = _get_bot().get_guild(guild_id)
        channel = _get_bot().get_channel(channel_id)
        if guild is None or channel is None:
            continue
        guild_cfg["highlights_posted_at"] = now.isoformat()
        await storage.save_guild(guild_id, guild_cfg)
        try:
            async with get_scheduler_lock():
                result = await fetch_highlights_report(guild_id, guild.name)
            if result:
                embed, players = result
                await channel.send(embed=embed)
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
            
            # Edit existing message or post new one
            if message_id:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(embeds=embeds, files=files)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    # Message deleted/inaccessible - post new one
                    new_message = await channel.send(embeds=embeds, files=files)
                    guild_cfg["survival_message_id"] = new_message.id
                    await storage.save_guild(guild_id, guild_cfg)
            else:
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
    Dinners in players' most recent matches. Dedupes per player against
    chicken_dinner_posted_matches (pubg name -> last alerted match_id), so
    the same win isn't reposted every tick just because nobody has played a
    newer match since the last check.
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

        if not new_wins:
            continue

        try:
            embed = discord.Embed(
                title="🍗 Chicken Dinner!",
                color=discord.Color.gold(),
                timestamp=datetime.now(timezone.utc),
            )
            for name, data in sorted(new_wins, key=lambda item: item[1].get("kills", 0), reverse=True)[:15]:
                map_name = data.get("map_name") or "Unknown map"
                embed.add_field(name=name, value=f"{data.get('kills', 0)} kills · {map_name}", inline=True)
            await channel.send(embed=embed)
            # Only record these matches as alerted once Discord actually
            # accepted the message — a failed send retries next tick
            # instead of silently losing the alert.
            guild_cfg["chicken_dinner_posted_matches"] = updated_matches
            await storage.save_guild(guild_id, guild_cfg)
            await send_audit_log(
                guild_id,
                "Automated Event",
                f"Chicken dinner alert posted",
                is_automated=True,
                details={"Event Type": "Chicken Dinner", "Wins": len(new_wins)},
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


async def send_audit_log(guild_id: int, title: str, description: str, is_automated: bool = False, details: dict = None, report_embed: discord.Embed = None):
    """Send an audit log entry to the configured audit server."""
    from modules.config import AUDIT_SERVER_ID, AUDIT_LOG_CHANNEL_ID
    if not AUDIT_SERVER_ID or not AUDIT_LOG_CHANNEL_ID:
        return

    audit_guild = _get_bot().get_guild(AUDIT_SERVER_ID)
    if not audit_guild:
        try:
            audit_guild = await _get_bot().fetch_guild(AUDIT_SERVER_ID)
        except:
            return

    channel = audit_guild.get_channel(AUDIT_LOG_CHANNEL_ID)
    if not channel:
        try:
            channel = await audit_guild.fetch_channel(AUDIT_LOG_CHANNEL_ID)
        except:
            return

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue() if is_automated else discord.Color.green(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Guild ID", value=str(guild_id), inline=True)
    embed.add_field(name="Automated", value="Yes" if is_automated else "No", inline=True)
    if details:
        for key, value in details.items():
            embed.add_field(name=key, value=str(value), inline=True)
    if report_embed:
        embed.add_field(name="Report Embed", value="See attached embed", inline=False)
    await channel.send(embed=embed)
    if report_embed:
        await channel.send(embed=report_embed)


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
