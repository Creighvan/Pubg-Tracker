"""
First-run setup guide.

Sends a short "how to get started" message to servers that have the bot but have not configured it
(no roster, no report channels, no clan). It runs:

  * when the bot is invited to a new server (on_guild_join), and
  * once per process at startup, for servers that installed the bot but never set it up.

Safety rules:
  * Each server is messaged at most once. The claim is written to storage BEFORE sending, atomically, so
    on_guild_join and the startup sweep can never double-post.
  * If delivery fails everywhere (no channel it can post in, owner DMs closed) the claim is rolled back and
    retried no sooner than RETRY_AFTER later, so a server we cannot reach is not retried on every restart.
  * Servers that already configured anything are never messaged.
  * Mentions are never parsed (AllowedMentions.none()).
  * SETUP_GUIDE_ENABLED=false turns everything off; SETUP_GUIDE_SWEEP_EXISTING=false keeps the join message
    but skips the startup sweep of servers that already have the bot.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

import discord

import storage
from modules.config import SUPPORT_SERVER_URL

logger = logging.getLogger(__name__)

SENT_KEY = "setup_guide_sent_at"
FAILED_KEY = "setup_guide_failed_at"

RETRY_AFTER = timedelta(days=7)
SEND_DELAY_SECONDS = 2.0  # pause between servers during the sweep (be polite to Discord's rate limits)
_PREFERRED_NAMES = ("bot", "command", "general", "welcome", "chat", "lobby")
_LOG_WORDS = {"audit", "log", "logs"}
_LOG_NAMES = {"modlog", "modlogs", "adminlog", "adminlogs", "auditlog", "auditlogs"}

SENT_CHANNEL = "sent_channel"
SENT_DM = "sent_dm"
SKIPPED = "skipped"
FAILED = "failed"

_sweep_started = False


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def enabled() -> bool:
    return _env_flag("SETUP_GUIDE_ENABLED", True)


def sweep_enabled() -> bool:
    return enabled() and _env_flag("SETUP_GUIDE_SWEEP_EXISTING", True)


# ----------------------------------------------------------------------------- configuration state
def _setup_fields(cfg: dict) -> list[str]:
    """Every config key that proves somebody already ran a setup command."""
    channel_keys = [k for k in cfg if k.endswith("channel_id")]
    return channel_keys + ["clan_name", "pubg_clan_name", "pubg_clan_id"]


def is_unconfigured(cfg: dict) -> bool:
    """True when nobody has set up this server: no roster, no report channel, no clan."""
    if cfg.get("players"):
        return False
    return not any(cfg.get(k) for k in _setup_fields(cfg))


def setup_progress(cfg: dict) -> list[tuple[bool, str]]:
    """Checklist used by /setupguide."""
    players = cfg.get("players") or []
    return [
        (bool(players), f"Players added ({len(players)})" if players else "No players added yet"),
        (bool(cfg.get("post_channel_id")), "Daily digest channel set" if cfg.get("post_channel_id") else "Digest channel not set"),
        (bool(cfg.get("last_activity_channel_id")), "Activity channel set" if cfg.get("last_activity_channel_id") else "Activity channel not set (optional)"),
        (bool(cfg.get("clan_name") or cfg.get("pubg_clan_id")), "Clan linked" if (cfg.get("clan_name") or cfg.get("pubg_clan_id")) else "Clan not linked (optional)"),
    ]


# ----------------------------------------------------------------------------- the message
def build_setup_embed(guild_name: str | None = None, cfg: dict | None = None, support_url: str | None = SUPPORT_SERVER_URL) -> discord.Embed:
    name = guild_name or "your server"
    embed = discord.Embed(
        title="👋 Thanks for adding PUBG Tracker!",
        description=(
            (f"I track your clan's PUBG stats and post automatic reports. **{name} isn't set up yet**, "
             "and it only takes a couple of minutes.\n\n"
             if (cfg is None or is_unconfigured(cfg)) else
             f"Here is the quick-start guide for **{name}**, with your setup progress below.\n\n")
            + "Setup commands need the **Manage Server** permission."
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="1️⃣  Add your players",
        value=(
            "`/addplayers` — paste your clan's exact PUBG names, separated by commas or new lines.\n"
            "`/addplayer` adds a single name. Names are 3–16 characters (letters, numbers, `-`, `_`)."
        ),
        inline=False,
    )
    embed.add_field(
        name="2️⃣  Choose where reports are posted",
        value=(
            "Open the channel you want, then run `/setchannel` for the daily digest. "
            "Each channel command uses the channel you run it in:\n"
            "`/setactivitychannel` · `/setrankedchannel` · `/sethighlightschannel` · "
            "`/setchickendinnerchannel` · `/setclanchannel` · `/setsurvivalchannel` · `/setstatuschannel`"
        ),
        inline=False,
    )
    embed.add_field(
        name="3️⃣  Optional tweaks",
        value=(
            "`/setclan <member name>` links your official PUBG clan for clan-level reports.\n"
            "`/setgamemode` · `/setlanguage` · `/setdigesttime` · `/reporttoggle`"
        ),
        inline=False,
    )
    embed.add_field(
        name="4️⃣  Try it out",
        value=(
            "`/clanstats` · `/lastactive` · `/leaderboard` · `/profile <player>` · `/compare`\n"
            "`/reportstatus` shows which automatic reports are on and when they run next."
        ),
        inline=False,
    )
    if cfg is not None:
        embed.add_field(
            name="Your progress",
            value="\n".join(f"{'✅' if done else '⬜'} {label}" for done, label in setup_progress(cfg)),
            inline=False,
        )
    help_line = "Type `/` and pick **PUBG Tracker** to see every command, or run `/help`."
    if support_url:
        help_line += f"\nNeed a hand? Join the [support server]({support_url})."
    embed.add_field(name="Need help?", value=help_line, inline=False)
    embed.set_footer(text="Sent once because no setup was detected. Run /setupguide any time to see this again.")
    return embed


# ----------------------------------------------------------------------------- delivery
def _me(client: discord.Client, guild: discord.Guild):
    me = getattr(guild, "me", None)
    if me is None and getattr(client, "user", None) is not None:
        me = guild.get_member(client.user.id)
    return me


def candidate_channels(client: discord.Client, guild: discord.Guild) -> list:
    """Channels the bot can post an embed in, best first: system channel, then public chat-like channels."""
    me = _me(client, guild)

    def can_post(ch) -> bool:
        if me is None:
            return True  # cannot tell; let the send attempt decide
        p = ch.permissions_for(me)
        return bool(p.view_channel and p.send_messages and p.embed_links)

    def is_public(ch) -> bool:
        try:
            return bool(ch.permissions_for(guild.default_role).view_channel)
        except Exception:  # noqa: BLE001
            return False

    ranked = []
    sys_ch = getattr(guild, "system_channel", None)

    for ch in getattr(guild, "text_channels", []):
        if not can_post(ch):
            continue
        name = (ch.name or "").lower()
        # Skip log-style channels. Match whole words only, so "technology" or "catalog" are not excluded.
        if _LOG_WORDS & set(re.split(r"[^a-z0-9]+", name)) or name in _LOG_NAMES:
            continue
        score = (
            0 if (sys_ch is not None and ch.id == sys_ch.id) else 1,
            0 if is_public(ch) else 1,
            0 if any(w in name for w in _PREFERRED_NAMES) else 1,
            getattr(ch, "position", 0),
        )
        ranked.append((score, ch))
    ranked.sort(key=lambda t: t[0])
    return [ch for _, ch in ranked]


async def _claim(guild_id: int) -> bool:
    """Atomically decide that THIS caller owns sending the guide. Returns False if not needed/allowed."""
    now = datetime.now(timezone.utc)

    def modifier(g: dict) -> bool:
        if g.get(SENT_KEY):
            return False
        failed = g.get(FAILED_KEY)
        if failed:
            try:
                if now - datetime.fromisoformat(failed) < RETRY_AFTER:
                    return False
            except ValueError:
                pass
        if not is_unconfigured(g):
            return False
        g[SENT_KEY] = now.isoformat()
        g[FAILED_KEY] = None
        return True

    return bool(await storage.modify_guild(guild_id, modifier))


async def _rollback(guild_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat()

    def modifier(g: dict) -> None:
        g[SENT_KEY] = None
        g[FAILED_KEY] = now

    try:
        await storage.modify_guild(guild_id, modifier)
    except Exception:  # noqa: BLE001
        logger.warning("[onboarding] could not record failed delivery for guild %s", guild_id, exc_info=True)


async def send_setup_guide(client: discord.Client, guild: discord.Guild) -> str:
    """Send the guide to one server if (and only if) it needs it. Returns SENT_CHANNEL/SENT_DM/SKIPPED/FAILED."""
    if not enabled():
        return SKIPPED
    try:
        if not await _claim(guild.id):
            return SKIPPED
    except Exception:  # noqa: BLE001  (e.g. DatabaseCorruptionError: do not message anyone while the DB is unsafe)
        logger.warning("[onboarding] skipping guild %s: could not read/claim config", guild.id, exc_info=True)
        return SKIPPED

    embed = build_setup_embed(guild.name)
    none = discord.AllowedMentions.none()
    
    # Get configured audit channel to exclude it
    cfg = await storage.get_guild(guild.id)
    audit_channel_id = cfg.get("audit_channel_id") if cfg else None

    for ch in candidate_channels(client, guild)[:3]:
        # Skip the configured audit log channel
        if audit_channel_id and ch.id == audit_channel_id:
            logger.info("[onboarding] skipping audit channel #%s in %s", ch.name, guild.name)
            continue
        try:
            await ch.send(embed=embed, allowed_mentions=none)
            logger.info("[onboarding] sent setup guide to #%s in %s (%s)", ch.name, guild.name, guild.id)
            return SENT_CHANNEL
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.info("[onboarding] cannot post in #%s of %s: %s", getattr(ch, "name", "?"), guild.id, e)

    # No channel worked: fall back to a DM to the server owner
    try:
        owner_id = getattr(guild, "owner_id", None)
        if owner_id:
            owner = await client.fetch_user(owner_id)
            await owner.send(
                content=f"I was added to **{guild.name}**, but I can't post in any channel there. Here is how to get started:",
                embed=embed,
                allowed_mentions=none,
            )
            logger.info("[onboarding] DMed setup guide to owner of %s (%s)", guild.name, guild.id)
            return SENT_DM
    except (discord.Forbidden, discord.HTTPException) as e:
        logger.info("[onboarding] cannot DM owner of %s: %s", guild.id, e)

    await _rollback(guild.id)
    logger.warning("[onboarding] could not deliver setup guide to %s (%s); will retry in %s days",
                   guild.name, guild.id, RETRY_AFTER.days)
    return FAILED


# ----------------------------------------------------------------------------- startup sweep
async def sweep_existing_guilds(client: discord.Client) -> Counter:
    stats: Counter = Counter()
    for guild in list(client.guilds):
        try:
            outcome = await send_setup_guide(client, guild)
        except Exception:  # noqa: BLE001
            logger.exception("[onboarding] unexpected error for guild %s", getattr(guild, "id", "?"))
            outcome = "error"
        stats[outcome] += 1
        if outcome in (SENT_CHANNEL, SENT_DM):
            await asyncio.sleep(SEND_DELAY_SECONDS)
    logger.info("[onboarding] startup sweep finished: %s", dict(stats) or "no servers")
    return stats


def start_setup_guide_sweep(client: discord.Client):
    """Kick off the sweep once per process (on_ready can fire again after reconnects)."""
    global _sweep_started
    if _sweep_started or not sweep_enabled():
        return None
    _sweep_started = True
    from modules.scheduler import _spawn  # lazy import: scheduler imports a lot at module load
    return _spawn(sweep_existing_guilds(client), "setup_guide_sweep")


# ----------------------------------------------------------------------------- /setupguide
async def setupguide_impl(interaction: discord.Interaction) -> None:
    cfg = await storage.get_guild(interaction.guild_id)
    embed = build_setup_embed(interaction.guild.name if interaction.guild else None, cfg=cfg)
    await interaction.response.send_message(embed=embed, ephemeral=True)
