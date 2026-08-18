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
  /setchannel               - set current channel as the auto-post channel
  /setinterval <hours>      - how often (in hours) the digest auto-posts (default 6)
  /setdigesttime <0-23>      - post digest daily at a fixed Eastern-time hour instead
  /postnow                  - manually trigger a digest post immediately
  /lastactive                - show when each roster player last played, right now
  /setactivitychannel        - set current channel for the 24h "last active" report
  /setactivitytime <0-23>     - fixed Eastern-time hour for the last-active report
  /rankedstats                - show current-season ranked TPP standings, right now
  /setrankedchannel           - set current channel for the 24h ranked TPP report
  /setrankedqueue <queue>      - squad, duo, or solo (TPP only)
  /setrankedtime <0-23>         - fixed Eastern-time hour for the ranked report
  /dailyhighlights              - last-24h fun-title awards + top 10 + human/bot kills, right now
  /sethighlightschannel          - set current channel for the 24h highlights report
  /sethighlightstime <0-23>       - fixed Eastern-time hour for the highlights report
  /masterystats                     - top weapon mastery + survival level per player (on-demand only, slow)
  /leaderboardstats [pages]          - check official leaderboard for roster placements (on-demand only)
  /setleaderboardregion               - platform-region shard for leaderboard lookups (default pc-na)
  /setleaderboardqueue                - squad, duo, or solo (TPP) for leaderboard lookups
  /linkme <pubg_name>                    - link your own Discord account to a PUBG name
  /linkplayer <pubg_name> <member>          - link someone else's Discord account to a PUBG name
  /unlinkme <pubg_name>                       - remove a Discord-to-PUBG-name link

Report identity behavior:
  Linked players are displayed through a channel webhook using their PUBG
  name and linked Discord avatar. The bot never changes Discord nicknames.
  The bot needs Manage Webhooks in report channels (Administrator includes it).

Setup:
  1. pip install -r requirements.txt
  2. Copy .env.example to .env and fill in DISCORD_TOKEN and PUBG_API_KEY
  3. python bot.py
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

import storage
from pubg_api import PubgApiError, PubgClient

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
PUBG_API_KEY = os.environ["PUBG_API_KEY"]
PUBG_SHARD = os.environ.get("PUBG_SHARD", "steam")
DEV_GUILD_ID = os.environ.get("DEV_GUILD_ID")  # optional: instant command sync for this one server

VALID_GAME_MODES = {"squad-fpp", "squad", "duo-fpp", "duo", "solo-fpp", "solo"}

# America/New_York rather than a fixed UTC-5 offset, so this automatically
# tracks EST/EDT across daylight saving changes instead of drifting an hour
# twice a year.
EASTERN = ZoneInfo("America/New_York")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
pubg = PubgClient(PUBG_API_KEY, shard=PUBG_SHARD)

# Serializes the four scheduled reports so they never run concurrently
# against the PUBG API — running all four at once was overwhelming the
# real PUBG rate limit even though each report respects it individually.
_scheduler_lock = asyncio.Lock()

# Webhooks are used for Tupperbox-style player identities in reports.
# The webhook display name is the PUBG name and its avatar is the linked
# Discord member avatar. This never changes a member's actual nickname.
_REPORT_WEBHOOK_NAME = "PUBG Clan Tracker"
_report_webhooks: dict[int, discord.Webhook] = {}
_report_webhook_locks: dict[int, asyncio.Lock] = {}


def _webhook_lock(channel_id: int) -> asyncio.Lock:
    lock = _report_webhook_locks.get(channel_id)
    if lock is None:
        lock = asyncio.Lock()
        _report_webhook_locks[channel_id] = lock
    return lock


async def _get_report_webhook(channel: discord.TextChannel) -> discord.Webhook:
    """Get or create the channel webhook used for PUBG player identities."""
    cached = _report_webhooks.get(channel.id)
    if cached is not None:
        return cached

    async with _webhook_lock(channel.id):
        cached = _report_webhooks.get(channel.id)
        if cached is not None:
            return cached

        hooks = await channel.webhooks()
        for hook in hooks:
            if hook.name == _REPORT_WEBHOOK_NAME and hook.user and bot.user and hook.user.id == bot.user.id:
                _report_webhooks[channel.id] = hook
                return hook

        hook = await channel.create_webhook(name=_REPORT_WEBHOOK_NAME, reason="PUBG report player identities")
        _report_webhooks[channel.id] = hook
        return hook


async def _linked_member(guild: discord.Guild, guild_id: int, pubg_name: str) -> discord.Member | None:
    """Resolve a linked PUBG player to a Discord member for avatar/mention data."""
    discord_id = storage.get_discord_id(guild_id, pubg_name)
    if discord_id is None:
        return None
    member = guild.get_member(discord_id)
    if member is not None:
        return member
    try:
        return await guild.fetch_member(discord_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None


def _clean_webhook_name(name: str) -> str:
    # Discord webhook usernames have a 80-character limit; PUBG names are
    # normally much shorter, but truncating here makes this helper safe.
    return name[:80] or "PUBG Player"


async def send_tupper_player_messages(
    channel: discord.TextChannel,
    guild: discord.Guild,
    guild_id: int,
    player_messages: list[tuple[str, str]],
) -> None:
    """Send linked-player report lines through a webhook using PUBG identity.

    Each tuple is (PUBG name, message text). Linked players appear as a
    Tupperbox-style webhook identity with the Discord member's avatar. The
    real Discord member can still be mentioned in the message body.
    Unlinked players are skipped because the normal summary embed already
    contains them.
    """
    if not player_messages:
        return

    webhook = await _get_report_webhook(channel)
    for pubg_name, text in player_messages:
        member = await _linked_member(guild, guild_id, pubg_name)
        if member is None:
            continue
        avatar_url = str(member.display_avatar.url)
        mention = member.mention
        content = f"{text}\n{mention}"
        try:
            await webhook.send(
                content=content,
                username=_clean_webhook_name(pubg_name),
                avatar_url=avatar_url,
                allowed_mentions=discord.AllowedMentions(users=True),
                wait=False,
            )
        except discord.NotFound:
            # The webhook may have been deleted between lookup and send.
            _report_webhooks.pop(channel.id, None)
            webhook = await _get_report_webhook(channel)
            await webhook.send(
                content=content,
                username=_clean_webhook_name(pubg_name),
                avatar_url=avatar_url,
                allowed_mentions=discord.AllowedMentions(users=True),
                wait=False,
            )


def _clan_player_messages(players: list[dict]) -> list[tuple[str, str]]:
    ranked = sorted(players, key=lambda p: p["stats"].get("kills", 0), reverse=True)
    messages = []
    for i, p in enumerate(ranked[:10], start=1):
        s = p["stats"]
        kd = _safe_div(s.get("kills", 0), max(s.get("roundsPlayed", 0) - s.get("wins", 0), 1))
        messages.append((p["name"], f"**#{i} Top Fragger**\n{s.get('kills', 0):,} kills · {s.get('wins', 0):,} wins · {kd:.2f} K/D"))
    return messages


def _last_active_player_messages(players: list[dict]) -> list[tuple[str, str]]:
    return [(p["name"], f"**Last active:** {_format_time_ago(p.get('last_match_at'))}") for p in players]


def _ranked_player_messages(players: list[dict]) -> list[tuple[str, str]]:
    messages = []
    for i, p in enumerate(players, start=1):
        r = p.get("ranked", {})
        if not r or r.get("currentTier") is None:
            text = f"**#{i} Ranked**\nNo ranked matches this season"
        else:
            tier = r.get("currentTier", {})
            tier_name = f"{tier.get('tier', '?')} {tier.get('subTier', '')}".strip()
            rp = r.get("currentRankPoint", 0)
            wins = r.get("wins", 0)
            kills = r.get("kills", 0)
            rounds = r.get("roundsPlayed", 0)
            kd = _safe_div(kills, max(rounds - wins, 1))
            text = f"**#{i} Ranked**\n{tier_name} · {rp} RP · {wins}W · {kd:.2f} K/D"
        messages.append((p["name"], text))
    return messages


def _highlight_player_messages(players: list[dict]) -> list[tuple[str, str]]:
    active = [p for p in players if p["daily"]["matches"] > 0]
    messages = []
    for i, p in enumerate(active[:10], start=1):
        d = p["daily"]
        text = (
            f"**#{i} Daily Highlights**\n"
            f"{d['kills']} kills · {d['human_kills']} human · {d['bot_kills']} bot · "
            f"{d['damageDealt']:,.0f} damage · {d['wins']}W · {d['matches']} match(es)"
        )
        messages.append((p["name"], text))
    return messages


def _mastery_player_messages(players: list[dict]) -> list[tuple[str, str]]:
    messages = []
    for i, p in enumerate(players, start=1):
        m = p["mastery"]
        weapon_name = _friendly_weapon_name(m["best_weapon"])
        messages.append((p["name"], f"**#{i} Mastery**\n{weapon_name} Lv.{m['best_weapon_level']} · {m['best_weapon_kills']} kills · Survival Lv.{m['survival_level']}"))
    return messages


def _leaderboard_player_messages(guild_id: int, found: dict[str, dict]) -> list[tuple[str, str]]:
    ranked = sorted(found.values(), key=lambda e: e["rank"])
    return [(e["name"], f"**Official Leaderboard**\n#{e['rank']:,}") for e in ranked]


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

def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _is_due(guild_cfg: dict, hour_key: str, minute_key: str, posted_at_key: str, default_interval_hours: int) -> bool:
    """
    Two scheduling modes, chosen per-report:
    - If hour_key is set (0-23): post once per Eastern calendar day, at that
      Eastern-time hour:minute (minute_key, 0/15/30/45). Uses a 15-minute
      match window rather than exact equality, since the scheduler loop
      itself only ticks every 15 minutes and its phase isn't necessarily
      aligned to :00/:15/:30/:45 on the wall clock — the window guarantees
      exactly one tick lands in range regardless of that offset.
    - If hour_key is None (default): fall back to the old "every N hours
      since last post" behavior, using default_interval_hours (or
      guild_cfg["post_interval_hours"] for the digest specifically).
    """
    target_hour = guild_cfg.get(hour_key)
    posted_at = guild_cfg.get(posted_at_key)

    if target_hour is not None:
        target_minute = guild_cfg.get(minute_key, 0)
        now_est = datetime.now(EASTERN)
        target_total = target_hour * 60 + target_minute
        now_total = now_est.hour * 60 + now_est.minute
        if not (target_total <= now_total < target_total + 15):
            return False
        if not posted_at:
            return True
        posted_est = datetime.fromisoformat(posted_at).astimezone(EASTERN)
        return posted_est.date() != now_est.date()

    now = datetime.now(timezone.utc)
    interval_hours = guild_cfg.get("post_interval_hours", default_interval_hours) if hour_key == "digest_hour_est" else default_interval_hours
    if not posted_at:
        return True
    posted_dt = datetime.fromisoformat(posted_at)
    return now - posted_dt >= timedelta(hours=interval_hours)


def _build_congrats(guild_id: int, achievements: list[tuple[str, str]]) -> str | None:
    """
    achievements: list of (label, pubg_name) pairs, e.g. [("Top Fragger", "Alice")].
    Only names with a linked Discord account produce an actual @mention —
    unlinked names are silently skipped here (they still show in the embed
    itself, just without a ping). Returns None if nobody linked qualifies.
    """
    lines = []
    for label, name in achievements:
        discord_id = storage.get_discord_id(guild_id, name)
        if discord_id is not None:
            lines.append(f"🎉 **{label}**: <@{discord_id}>")
    if not lines:
        return None
    return "👏 Congrats!\n" + "\n".join(lines)


def build_clan_embed(guild_name: str, guild_cfg: dict, players: list[dict], not_found: list[str]) -> discord.Embed:
    game_mode = guild_cfg["game_mode"]
    title = guild_cfg.get("clan_name") or guild_name

    total_kills = sum(p["stats"].get("kills", 0) for p in players)
    total_wins = sum(p["stats"].get("wins", 0) for p in players)
    total_games = sum(p["stats"].get("roundsPlayed", 0) for p in players)
    total_damage = sum(p["stats"].get("damageDealt", 0.0) for p in players)

    embed = discord.Embed(
        title=f"{title} — Clan Report ({game_mode})",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Tracked players", value=str(len(players)), inline=True)
    embed.add_field(name="Total kills", value=f"{total_kills:,}", inline=True)
    embed.add_field(name="Total wins", value=f"{total_wins:,}", inline=True)
    embed.add_field(name="Win rate", value=f"{_safe_div(total_wins, total_games) * 100:.1f}%", inline=True)
    embed.add_field(name="Total damage", value=f"{total_damage:,.0f}", inline=True)
    embed.add_field(name="Total matches", value=f"{total_games:,}", inline=True)

    ranked = sorted(players, key=lambda p: p["stats"].get("kills", 0), reverse=True)[:10]
    lines = []
    for i, p in enumerate(ranked, start=1):
        s = p["stats"]
        kd = _safe_div(s.get("kills", 0), max(s.get("roundsPlayed", 0) - s.get("wins", 0), 1))
        lines.append(f"**{i}. {p['name']}** — {s.get('kills', 0):,} kills, {s.get('wins', 0)} wins, {kd:.2f} K/D")
    if lines:
        embed.add_field(name="Top fraggers", value="\n".join(lines), inline=False)

    if not_found:
        embed.add_field(
            name="⚠️ Not found",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )

    embed.set_footer(text="Stats from the official PUBG API · lifetime, per game mode")
    return embed


async def fetch_clan_report(guild_id: int, guild_name: str) -> tuple[discord.Embed, str | None, list[dict]] | None:
    guild_cfg = storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await pubg.get_players_and_stats(guild_cfg["players"], game_mode=guild_cfg["game_mode"])
    embed = build_clan_embed(guild_name, guild_cfg, players, not_found)

    achievements = []
    qualifying = [p for p in players if p["stats"].get("kills", 0) > 0]
    if qualifying:
        top = max(qualifying, key=lambda p: p["stats"].get("kills", 0))
        achievements.append(("Top Fragger", top["name"]))
    congrats = _build_congrats(guild_id, achievements)

    return embed, congrats, players


def _format_time_ago(iso_str: str | None) -> str:
    if not iso_str:
        return "No recent matches found"
    then = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    delta = datetime.now(timezone.utc) - then
    hours = delta.total_seconds() / 3600
    if hours < 1:
        return "< 1 hour ago"
    if hours < 24:
        return f"{int(hours)} hour(s) ago"
    return f"{int(hours // 24)} day(s) ago"


def build_last_active_embed(guild_name: str, guild_cfg: dict, players: list[dict], not_found: list[str]) -> discord.Embed:
    title = guild_cfg.get("clan_name") or guild_name
    embed = discord.Embed(
        title=f"{title} — Last Active Report",
        description=(
            "PUBG's API doesn't expose login history, so this shows the time "
            "of each player's most recent **match**, which is the closest "
            "available signal for \"last played.\""
        ),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc),
    )
    lines = [f"**{p['name']}** — {_format_time_ago(p.get('last_match_at'))}" for p in players]
    # Discord embed fields cap at 1024 chars; chunk if the roster is large.
    chunk_size = 20
    for i in range(0, len(lines), chunk_size):
        field_lines = lines[i : i + chunk_size]
        embed.add_field(
            name="Players" if i == 0 else "\u200b",
            value="\n".join(field_lines) or "None",
            inline=False,
        )
    if not_found:
        embed.add_field(
            name="⚠️ Not found",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )
    return embed


async def fetch_last_active_report(guild_id: int, guild_name: str) -> tuple[discord.Embed, list[dict]] | None:
    guild_cfg = storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await pubg.get_last_active_times(guild_cfg["players"])
    return build_last_active_embed(guild_name, guild_cfg, players, not_found), players


def build_ranked_embed(guild_name: str, guild_cfg: dict, players: list[dict], not_found: list[str]) -> discord.Embed:
    title = guild_cfg.get("clan_name") or guild_name
    queue = guild_cfg.get("ranked_queue", "squad")
    embed = discord.Embed(
        title=f"{title} — Ranked ({queue.upper()} TPP)",
        description="Current-season competitive ranked stats.",
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc),
    )

    lines = []
    for i, p in enumerate(players, start=1):
        r = p.get("ranked", {})
        if not r or r.get("currentTier") is None:
            lines.append(f"{i}. **{p['name']}** — no ranked matches this season")
            continue
        tier = r.get("currentTier", {})
        tier_name = f"{tier.get('tier', '?')} {tier.get('subTier', '')}".strip()
        rp = r.get("currentRankPoint", 0)
        wins = r.get("wins", 0)
        kills = r.get("kills", 0)
        rounds = r.get("roundsPlayed", 0)
        kd = _safe_div(kills, max(rounds - wins, 1))
        lines.append(f"{i}. **{p['name']}** — {tier_name} ({rp} RP), {wins}W, {kd:.2f} K/D")

    # Discord embed field values cap at 1024 chars; chunk if the roster is large.
    chunk_size = 15
    for i in range(0, len(lines), chunk_size):
        field_lines = lines[i : i + chunk_size]
        embed.add_field(
            name="Ranking" if i == 0 else "\u200b",
            value="\n".join(field_lines) or "None",
            inline=False,
        )
    if not_found:
        embed.add_field(
            name="⚠️ Not found",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )
    embed.set_footer(text="Stats from the official PUBG API · ranked, current season")
    return embed


async def fetch_ranked_report(guild_id: int, guild_name: str) -> tuple[discord.Embed, str | None, list[dict]] | None:
    guild_cfg = storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await pubg.get_ranked_report(guild_cfg["players"], game_mode=guild_cfg.get("ranked_queue", "squad"))
    embed = build_ranked_embed(guild_name, guild_cfg, players, not_found)

    achievements = []
    qualifying = [p for p in players if p.get("ranked", {}).get("currentTier") is not None]
    if qualifying:
        # players is already sorted by currentRankPoint descending
        achievements.append(("Top Rank", qualifying[0]["name"]))
    congrats = _build_congrats(guild_id, achievements)

    return embed, congrats, players


TITLE_DEFINITIONS = [
    # (emoji, title, stat key inside p["daily"], label for the value)
    ("💀", "Top Fragger", "kills", "kills"),
    ("🏆", "The Champion", "wins", "wins"),
    ("🎯", "Damage Machine", "damageDealt", "damage"),
    ("🔫", "Top Sniper", "headshotKills", "headshot kills"),
    ("💉", "Top Medic", "revives", "revives"),
    ("🤝", "Top Supporter", "assists", "assists"),
    ("👽", "Predator", "human_kills", "human kills"),
    ("🤖", "Jon Connor", "bot_kills", "bot kills"),
    ("🤡", "Stooge Award", "stooge_kills", "own-goal kills (self + team)"),
    ("🔋", "Copper Top Award", "boosts", "energy used"),
    ("➕", "Sir Heals-A-Lot", "heals", "heals used"),
    ("🚗", "Grand Theft Auto", "road_kills", "roadkills"),
    ("🏊", "Michael Phelps", "swim_distance", "m swam"),
    ("🎒", "Window Shopper", "loot_ratio", "weapons picked up per kill"),
]


def _pick_leader(players: list[dict], stat_key: str) -> dict | None:
    contenders = [p for p in players if p["daily"].get(stat_key, 0) > 0]
    if not contenders:
        return None
    return max(contenders, key=lambda p: p["daily"].get(stat_key, 0))


def _compute_award_winners(active_players: list[dict]) -> list[tuple[str, str, str, str]]:
    """Returns [(emoji, label, winner_name, formatted_value), ...] for every
    award category that has a qualifying winner. Shared by the embed
    builder and the congrats-message builder so the two never disagree."""
    winners = []
    for emoji, label, stat_key, unit in TITLE_DEFINITIONS:
        leader = _pick_leader(active_players, stat_key)
        if leader:
            val = leader["daily"][stat_key]
            if stat_key == "loot_ratio":
                val_str = f"{val:,.2f}"
            elif isinstance(val, float):
                val_str = f"{val:,.0f}"
            else:
                val_str = f"{val:,}"
            winners.append((emoji, label, leader["name"], f"{val_str} {unit}"))

    wookiee_candidates = [
        p for p in active_players if p["daily"].get("best_zero_kill_placement") is not None
    ]
    if wookiee_candidates:
        wookiee = min(wookiee_candidates, key=lambda p: p["daily"]["best_zero_kill_placement"])
        placement = wookiee["daily"]["best_zero_kill_placement"]
        winners.append(("🌳", "Bush Wookiee", wookiee["name"], f"placed #{placement} with 0 kills that match"))

    return winners


def build_highlights_embed(guild_name: str, guild_cfg: dict, players: list[dict], not_found: list[str], hours: int) -> discord.Embed:
    title = guild_cfg.get("clan_name") or guild_name
    active_players = [p for p in players if p["daily"]["matches"] > 0]

    embed = discord.Embed(
        title=f"{title} — Last {hours}h Highlights",
        description=f"Based on {len(active_players)} player(s) who played in the last {hours} hours.",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc),
    )

    if not active_players:
        embed.add_field(name="No matches played", value="Nobody on the roster played in this window.", inline=False)
        return embed

    for emoji, label, winner_name, val_str in _compute_award_winners(active_players):
        embed.add_field(name=f"{emoji} {label}", value=f"**{winner_name}** — {val_str}", inline=True)

    # Top 10 overall, ranked by kills, with human/bot kill split
    lines = []
    for i, p in enumerate(active_players[:10], start=1):
        d = p["daily"]
        lines.append(
            f"{i}. **{p['name']}** — {d['kills']} kills ({d['human_kills']} human / {d['bot_kills']} bot), "
            f"{d['damageDealt']:,.0f} dmg, {d['wins']}W, {d['matches']} match(es)"
        )
    embed.add_field(name="Top 10", value="\n".join(lines), inline=False)

    if not_found:
        embed.add_field(
            name="⚠️ Not found",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )
    embed.set_footer(text="Human vs bot kills come from match telemetry (PUBG tags bot accounts internally)")
    return embed


async def fetch_highlights_report(guild_id: int, guild_name: str, hours: int = 24) -> tuple[discord.Embed, str | None, list[dict]] | None:
    guild_cfg = storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await pubg.get_daily_activity_report(guild_cfg["players"], hours=hours)
    embed = build_highlights_embed(guild_name, guild_cfg, players, not_found, hours)

    active_players = [p for p in players if p["daily"]["matches"] > 0]
    achievements = [(label, name) for _, label, name, _ in _compute_award_winners(active_players)]
    congrats = _build_congrats(guild_id, achievements)

    return embed, congrats, players


# A handful of common weapon IDs mapped to friendly names. Anything not in
# here falls back to a cleaned-up version of the raw ID (e.g.
# "Item_Weapon_M416_C" -> "M416") so the report is still readable even for
# weapons this dict doesn't know about.
WEAPON_DISPLAY_NAMES = {
    "Item_Weapon_M416_C": "M416",
    "Item_Weapon_AK47_C": "AKM",
    "Item_Weapon_K98_C": "Kar98k",
    "Item_Weapon_M24_C": "M24",
    "Item_Weapon_AWM_C": "AWM",
    "Item_Weapon_UMP_C": "UMP45",
    "Item_Weapon_Vector_C": "Vector",
    "Item_Weapon_SCAR-L_C": "SCAR-L",
    "Item_Weapon_M16A4_C": "M16A4",
    "Item_Weapon_Groza_C": "Groza",
    "Item_Weapon_Mini14_C": "Mini14",
    "Item_Weapon_SKS_C": "SKS",
    "Item_Weapon_DesertEagle_C": "Desert Eagle",
    "Item_Weapon_M9_C": "P92",
    "Item_Weapon_Shotgun_C": "S12K",
    "Item_Weapon_Winchester_C": "Win94",
}


def _friendly_weapon_name(weapon_id: str | None) -> str:
    if not weapon_id:
        return "—"
    if weapon_id in WEAPON_DISPLAY_NAMES:
        return WEAPON_DISPLAY_NAMES[weapon_id]
    return weapon_id.replace("Item_Weapon_", "").replace("_C", "")


def build_mastery_embed(guild_name: str, guild_cfg: dict, players: list[dict], not_found: list[str]) -> discord.Embed:
    title = guild_cfg.get("clan_name") or guild_name
    embed = discord.Embed(
        title=f"{title} — Weapon & Survival Mastery",
        description="Each player's highest-level weapon and overall survival mastery.",
        color=discord.Color.dark_teal(),
        timestamp=datetime.now(timezone.utc),
    )
    lines = []
    for i, p in enumerate(players, start=1):
        m = p["mastery"]
        weapon_name = _friendly_weapon_name(m["best_weapon"])
        lines.append(
            f"{i}. **{p['name']}** — {weapon_name} Lv.{m['best_weapon_level']} "
            f"({m['best_weapon_kills']} kills) · Survival Lv.{m['survival_level']}"
        )
    chunk_size = 15
    for i in range(0, len(lines), chunk_size):
        embed.add_field(
            name="Mastery" if i == 0 else "\u200b",
            value="\n".join(lines[i:i + chunk_size]) or "None",
            inline=False,
        )
    if not_found:
        embed.add_field(
            name="⚠️ Not found",
            value=", ".join(not_found[:15]) + (" ..." if len(not_found) > 15 else ""),
            inline=False,
        )
    embed.set_footer(text="Field names for this endpoint aren't fully documented by PUBG — flag me if numbers look off")
    return embed


async def fetch_mastery_report(guild_id: int, guild_name: str) -> tuple[discord.Embed, list[dict]] | None:
    guild_cfg = storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    players, not_found = await pubg.get_mastery_report(guild_cfg["players"])
    return build_mastery_embed(guild_name, guild_cfg, players, not_found), players


def build_leaderboard_embed(
    guild_id: int, guild_name: str, guild_cfg: dict, found: dict[str, dict], checked: int, pages: int, queue: str
) -> discord.Embed:
    title = guild_cfg.get("clan_name") or guild_name
    embed = discord.Embed(
        title=f"{title} — Official Leaderboard ({queue.upper()} TPP)",
        description=(
            f"Checked the top {checked:,} ranked players ({pages} page(s)). "
            f"This is the official ladder — most players won't appear unless they're highly ranked."
        ),
        color=discord.Color.dark_gold(),
        timestamp=datetime.now(timezone.utc),
    )
    if not found:
        embed.add_field(name="No matches", value="Nobody on the roster is in the checked range.", inline=False)
        return embed

    ranked = sorted(found.values(), key=lambda e: e["rank"])
    lines = []
    for e in ranked:
        discord_id = storage.get_discord_id(guild_id, e["name"])
        who = f"<@{discord_id}>" if discord_id else f"**{e['name']}**"
        lines.append(f"#{e['rank']:,} — {who}")
    embed.add_field(name="Roster members found", value="\n".join(lines), inline=False)
    return embed


async def fetch_leaderboard_report(
    guild_id: int, guild_name: str, max_pages: int = 4
) -> tuple[discord.Embed, str | None, dict[str, dict]] | None:
    """Returns (embed, congrats_message_or_None, found_players). The congrats message is
    plain text (not embed content) because Discord only actually notifies
    @mentions when they're in a message's plain content — mentions inside
    an embed render as clickable but silent, no ping fires."""
    guild_cfg = storage.get_guild(guild_id)
    if not guild_cfg["players"]:
        return None
    queue = guild_cfg.get("leaderboard_queue", "squad")
    season_id = await pubg.get_current_season_id()
    found, checked = await pubg.get_leaderboard_placements(
        guild_cfg["players"], season_id, game_mode=queue,
        max_pages=max_pages, leaderboard_shard=guild_cfg.get("leaderboard_shard", "pc-na"),
    )
    embed = build_leaderboard_embed(guild_id, guild_name, guild_cfg, found, checked, max_pages, queue)

    mentions = [
        f"<@{discord_id}>"
        for name in found
        if (discord_id := storage.get_discord_id(guild_id, name)) is not None
    ]
    congrats = f"🎉👍 Congrats {' '.join(mentions)} — you're on the official leaderboard!" if mentions else None
    return embed, congrats, found


# ---------- lifecycle ----------

@bot.event
async def on_ready():
    try:
        if DEV_GUILD_ID:
            # While actively developing (DEV_GUILD_ID set), push commands to
            # ONLY this one guild, instantly, and skip the global push entirely
            # this run. Clearing first means each restart gets a completely
            # fresh guild-scoped copy — no leftover duplicates, no ~1hr wait
            # for new commands to show up while you're testing.
            #
            # This does mean OTHER servers won't see brand-new commands until
            # you do a "release" global sync — remove DEV_GUILD_ID from .env,
            # restart once (that pushes globally), then you can put it back.
            dev_guild = discord.Object(id=int(DEV_GUILD_ID))
            bot.tree.clear_commands(guild=dev_guild)
            bot.tree.copy_global_to(guild=dev_guild)
            synced = await bot.tree.sync(guild=dev_guild)
            print(f"Instantly synced {len(synced)} commands to dev guild {DEV_GUILD_ID} (guild-scoped only this run)")
        else:
            synced_global = await bot.tree.sync()
            print(f"Synced {len(synced_global)} commands globally (can take up to ~1hr to appear elsewhere)")
    except Exception as e:
        # A sync hiccup here should NEVER prevent the scheduled reports
        # below from starting — this used to be able to silently kill
        # every auto-post if this step threw, since the task-start code
        # was unreachable after an unhandled exception here.
        print(f"[on_ready] Command sync failed (scheduled reports will still start): {e}")
    if not auto_digest.is_running():
        auto_digest.start()
    if not auto_last_active.is_running():
        auto_last_active.start()
    if not auto_ranked.is_running():
        auto_ranked.start()
    if not auto_highlights.is_running():
        auto_highlights.start()
    print(f"Logged in as {bot.user} (id={bot.user.id})")


# ---------- scheduled task ----------

@tasks.loop(minutes=15)
async def auto_digest():
    """
    Every 15 minutes, checks whether each guild's digest is due — either
    a fixed Eastern-time hour (digest_hour_est) or the older interval-based
    behavior (post_interval_hours), depending on what's configured.
    """
    now = datetime.now(timezone.utc)
    for guild_id in storage.all_guild_ids():
        guild_cfg = storage.get_guild(guild_id)
        channel_id = guild_cfg.get("post_channel_id")
        if channel_id is None:
            continue
        if not _is_due(guild_cfg, "digest_hour_est", "digest_minute_est", "last_post_at", 6):
            continue

        guild = bot.get_guild(guild_id)
        channel = bot.get_channel(channel_id)
        if guild is None or channel is None:
            continue
        # Mark the attempt now, before making any API calls — so a failure
        # (e.g. a transient rate limit) waits for the next full interval
        # instead of retrying on every 15-min check, which is what was
        # causing bursts and repeated rate-limit errors.
        guild_cfg["last_post_at"] = now.isoformat()
        storage.save_guild(guild_id, guild_cfg)
        try:
            async with _scheduler_lock:
                result = await fetch_clan_report(guild_id, guild.name)
            if result:
                embed, congrats, players = result
                await channel.send(content=congrats, embed=embed, allowed_mentions=discord.AllowedMentions(users=True))
                await send_tupper_player_messages(channel, guild, guild_id, _clan_player_messages(players))
        except PubgApiError as e:
            print(f"[auto_digest] PUBG API error for guild {guild_id}: {e}")
        except Exception as e:
            print(f"[auto_digest] Unexpected error for guild {guild_id}: {e}")


@auto_digest.before_loop
async def before_auto_digest():
    await bot.wait_until_ready()


@tasks.loop(minutes=15)
async def auto_last_active():
    """Posts the 'last active' report every 24 hours, per guild, same
    interval-based pattern as auto_digest."""
    now = datetime.now(timezone.utc)
    for guild_id in storage.all_guild_ids():
        guild_cfg = storage.get_guild(guild_id)
        channel_id = guild_cfg.get("last_activity_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None:
            continue
        if not _is_due(guild_cfg, "activity_hour_est", "activity_minute_est", "last_activity_posted_at", 24):
            continue

        guild = bot.get_guild(guild_id)
        channel = bot.get_channel(channel_id)
        if guild is None or channel is None:
            continue
        guild_cfg["last_activity_posted_at"] = now.isoformat()
        storage.save_guild(guild_id, guild_cfg)
        try:
            async with _scheduler_lock:
                result = await fetch_last_active_report(guild_id, guild.name)
            if result:
                embed, players = result
                await channel.send(embed=embed)
                await send_tupper_player_messages(channel, guild, guild_id, _last_active_player_messages(players))
        except PubgApiError as e:
            print(f"[auto_last_active] PUBG API error for guild {guild_id}: {e}")
        except Exception as e:
            print(f"[auto_last_active] Unexpected error for guild {guild_id}: {e}")


@auto_last_active.before_loop
async def before_auto_last_active():
    await bot.wait_until_ready()


@tasks.loop(minutes=15)
async def auto_ranked():
    """Posts the ranked TPP report every 24 hours, per guild."""
    now = datetime.now(timezone.utc)
    for guild_id in storage.all_guild_ids():
        guild_cfg = storage.get_guild(guild_id)
        channel_id = guild_cfg.get("ranked_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None:
            continue
        if not _is_due(guild_cfg, "ranked_hour_est", "ranked_minute_est", "ranked_posted_at", 24):
            continue

        guild = bot.get_guild(guild_id)
        channel = bot.get_channel(channel_id)
        if guild is None or channel is None:
            continue
        guild_cfg["ranked_posted_at"] = now.isoformat()
        storage.save_guild(guild_id, guild_cfg)
        try:
            async with _scheduler_lock:
                result = await fetch_ranked_report(guild_id, guild.name)
            if result:
                embed, congrats, players = result
                await channel.send(content=congrats, embed=embed, allowed_mentions=discord.AllowedMentions(users=True))
                await send_tupper_player_messages(channel, guild, guild_id, _ranked_player_messages(players))
        except PubgApiError as e:
            print(f"[auto_ranked] PUBG API error for guild {guild_id}: {e}")
        except Exception as e:
            print(f"[auto_ranked] Unexpected error for guild {guild_id}: {e}")


@auto_ranked.before_loop
async def before_auto_ranked():
    await bot.wait_until_ready()


@tasks.loop(minutes=15)
async def auto_highlights():
    """
    Posts the 'last 24 hours' highlights report (fun titles + top 10 +
    human/bot kill split) every 24 hours, per guild. This is the heaviest
    report the bot runs (telemetry downloads), so it's worth giving it
    plenty of headroom rather than tightening the interval.
    """
    now = datetime.now(timezone.utc)
    for guild_id in storage.all_guild_ids():
        guild_cfg = storage.get_guild(guild_id)
        channel_id = guild_cfg.get("highlights_channel_id") or guild_cfg.get("post_channel_id")
        if channel_id is None:
            continue
        if not _is_due(guild_cfg, "highlights_hour_est", "highlights_minute_est", "highlights_posted_at", 24):
            continue

        guild = bot.get_guild(guild_id)
        channel = bot.get_channel(channel_id)
        if guild is None or channel is None:
            continue
        guild_cfg["highlights_posted_at"] = now.isoformat()
        storage.save_guild(guild_id, guild_cfg)
        try:
            async with _scheduler_lock:
                result = await fetch_highlights_report(guild_id, guild.name)
            if result:
                embed, congrats, players = result
                await channel.send(content=congrats, embed=embed, allowed_mentions=discord.AllowedMentions(users=True))
                await send_tupper_player_messages(channel, guild, guild_id, _highlight_player_messages(players))
        except PubgApiError as e:
            print(f"[auto_highlights] PUBG API error for guild {guild_id}: {e}")
        except Exception as e:
            print(f"[auto_highlights] Unexpected error for guild {guild_id}: {e}")


@auto_highlights.before_loop
async def before_auto_highlights():
    await bot.wait_until_ready()


# ---------- slash commands ----------

@bot.tree.command(description="Add a PUBG player name to this server's tracked clan roster")
@app_commands.describe(name="Exact in-game PUBG name (case-insensitive)")
async def addplayer(interaction: discord.Interaction, name: str):
    added = storage.add_player(interaction.guild_id, name)
    if added:
        await interaction.response.send_message(f"✅ Added **{name}** to the roster.")
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

    added, duplicates = storage.add_players(interaction.guild_id, candidates)

    lines = [f"✅ Added **{len(added)}** player(s) to the roster."]
    if added:
        lines.append(", ".join(added))
    if duplicates:
        lines.append(f"⚠️ Skipped {len(duplicates)} already on the roster: " + ", ".join(duplicates))
    await interaction.response.send_message("\n".join(lines))


@bot.tree.command(description="Remove a player from this server's tracked clan roster")
@app_commands.describe(name="PUBG name to remove")
async def removeplayer(interaction: discord.Interaction, name: str):
    removed = storage.remove_player(interaction.guild_id, name)
    if removed:
        await interaction.response.send_message(f"🗑️ Removed **{name}** from the roster.")
    else:
        await interaction.response.send_message(f"**{name}** wasn't on the roster.", ephemeral=True)


@bot.tree.command(description="List everyone currently tracked for this server's clan")
async def roster(interaction: discord.Interaction):
    guild_cfg = storage.get_guild(interaction.guild_id)
    players = guild_cfg["players"]
    if not players:
        await interaction.response.send_message("No players tracked yet. Add some with `/addplayer`.")
        return
    await interaction.response.send_message(
        f"**Tracked roster ({len(players)}):**\n" + ", ".join(players)
    )


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
    embed, congrats, players = result
    await interaction.followup.send(content=congrats, embed=embed, allowed_mentions=discord.AllowedMentions(users=True))
    await send_tupper_player_messages(interaction.channel, interaction.guild, interaction.guild_id, _clan_player_messages(players))


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
    guild_cfg = storage.get_guild(interaction.guild_id)
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
    guild_cfg = storage.get_guild(interaction.guild_id)
    guild_cfg["game_mode"] = mode.value
    storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"Game mode set to **{mode.value}**.")


@bot.tree.command(description="Set this channel as where the clan digest gets auto-posted")
async def setchannel(interaction: discord.Interaction):
    guild_cfg = storage.get_guild(interaction.guild_id)
    guild_cfg["post_channel_id"] = interaction.channel_id
    # Seed last_post_at to now so the first auto-post fires a full interval
    # from now, rather than immediately on the next 15-min check.
    guild_cfg["last_post_at"] = datetime.now(timezone.utc).isoformat()
    storage.save_guild(interaction.guild_id, guild_cfg)
    interval = guild_cfg.get("post_interval_hours", 6)
    await interaction.response.send_message(
        f"✅ Digest will auto-post in {interaction.channel.mention} every **{interval} hour(s)**. "
        f"Use `/postnow` any time for an immediate one."
    )


@bot.tree.command(description="Set how often (in hours) the digest auto-posts (ignored if a fixed time is set via /setdigesttime)")
@app_commands.describe(hours="e.g. 6 for every 6 hours")
async def setinterval(interaction: discord.Interaction, hours: app_commands.Range[int, 1, 24]):
    guild_cfg = storage.get_guild(interaction.guild_id)
    guild_cfg["post_interval_hours"] = hours
    storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Digest will now auto-post every **{hours} hour(s)**.")


QUARTER_HOUR_CHOICES = [
    app_commands.Choice(name=":00", value=0),
    app_commands.Choice(name=":15", value=15),
    app_commands.Choice(name=":30", value=30),
    app_commands.Choice(name=":45", value=45),
]


@bot.tree.command(description="Post the digest once a day at a fixed Eastern-time, instead of by interval")
@app_commands.describe(hour="0-23, Eastern time (e.g. 9 for 9am ET)", minute="Quarter-hour, defaults to :00")
@app_commands.choices(minute=QUARTER_HOUR_CHOICES)
async def setdigesttime(interaction: discord.Interaction, hour: app_commands.Range[int, 0, 23], minute: app_commands.Choice[int] = None):
    guild_cfg = storage.get_guild(interaction.guild_id)
    guild_cfg["digest_hour_est"] = hour
    guild_cfg["digest_minute_est"] = minute.value if minute else 0
    storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ Digest will now post once a day at **{hour:02d}:{guild_cfg['digest_minute_est']:02d} Eastern** (auto-adjusts for EST/EDT). "
        f"This overrides `/setinterval`."
    )


@bot.tree.command(description="Show when each roster player last played PUBG, right now")
async def lastactive(interaction: discord.Interaction):
    guild_cfg = storage.get_guild(interaction.guild_id)
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
    await send_tupper_player_messages(interaction.channel, interaction.guild, interaction.guild_id, _last_active_player_messages(players))


@bot.tree.command(description="Set this channel for the 24-hour 'last active' report (defaults to the digest channel)")
async def setactivitychannel(interaction: discord.Interaction):
    guild_cfg = storage.get_guild(interaction.guild_id)
    guild_cfg["last_activity_channel_id"] = interaction.channel_id
    guild_cfg["last_activity_posted_at"] = datetime.now(timezone.utc).isoformat()
    storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ Last-active report will post in {interaction.channel.mention} every 24 hours. "
        f"Use `/lastactive` any time for an immediate one."
    )


@bot.tree.command(description="Post the last-active report at a fixed Eastern-time each day")
@app_commands.describe(hour="0-23, Eastern time (e.g. 9 for 9am ET)", minute="Quarter-hour, defaults to :00")
@app_commands.choices(minute=QUARTER_HOUR_CHOICES)
async def setactivitytime(interaction: discord.Interaction, hour: app_commands.Range[int, 0, 23], minute: app_commands.Choice[int] = None):
    guild_cfg = storage.get_guild(interaction.guild_id)
    guild_cfg["activity_hour_est"] = hour
    guild_cfg["activity_minute_est"] = minute.value if minute else 0
    storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Last-active report will now post daily at **{hour:02d}:{guild_cfg['activity_minute_est']:02d} Eastern**.")


@bot.tree.command(description="Show current-season ranked TPP standings for the roster, right now")
async def rankedstats(interaction: discord.Interaction):
    guild_cfg = storage.get_guild(interaction.guild_id)
    if not guild_cfg["players"]:
        await interaction.response.send_message("No players tracked yet. Add some with `/addplayer`.")
        return
    await interaction.response.defer()
    try:
        result = await fetch_ranked_report(interaction.guild_id, interaction.guild.name)
    except PubgApiError as e:
        await interaction.followup.send(f"PUBG API error: {e}")
        return
    except Exception as e:
        await interaction.followup.send(f"Something went wrong generating this report: {e}")
        return
    embed, congrats, players = result
    await interaction.followup.send(content=congrats, embed=embed, allowed_mentions=discord.AllowedMentions(users=True))
    await send_tupper_player_messages(interaction.channel, interaction.guild, interaction.guild_id, _ranked_player_messages(players))


@bot.tree.command(description="Set this channel for the daily ranked TPP report (defaults to the digest channel)")
async def setrankedchannel(interaction: discord.Interaction):
    guild_cfg = storage.get_guild(interaction.guild_id)
    guild_cfg["ranked_channel_id"] = interaction.channel_id
    guild_cfg["ranked_posted_at"] = datetime.now(timezone.utc).isoformat()
    storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ Ranked TPP report will post in {interaction.channel.mention} every 24 hours. "
        f"Use `/rankedstats` any time for an immediate one."
    )


@bot.tree.command(description="Set which ranked TPP queue to track (squad, duo, or solo)")
@app_commands.choices(
    queue=[
        app_commands.Choice(name="Squad TPP", value="squad"),
        app_commands.Choice(name="Duo TPP", value="duo"),
        app_commands.Choice(name="Solo TPP", value="solo"),
    ]
)
async def setrankedqueue(interaction: discord.Interaction, queue: app_commands.Choice[str]):
    guild_cfg = storage.get_guild(interaction.guild_id)
    guild_cfg["ranked_queue"] = queue.value
    storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Ranked reports will now track **{queue.name}**.")


@bot.tree.command(description="Post the ranked TPP report at a fixed Eastern-time each day")
@app_commands.describe(hour="0-23, Eastern time (e.g. 9 for 9am ET)", minute="Quarter-hour, defaults to :00")
@app_commands.choices(minute=QUARTER_HOUR_CHOICES)
async def setrankedtime(interaction: discord.Interaction, hour: app_commands.Range[int, 0, 23], minute: app_commands.Choice[int] = None):
    guild_cfg = storage.get_guild(interaction.guild_id)
    guild_cfg["ranked_hour_est"] = hour
    guild_cfg["ranked_minute_est"] = minute.value if minute else 0
    storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Ranked report will now post daily at **{hour:02d}:{guild_cfg['ranked_minute_est']:02d} Eastern**.")


@bot.tree.command(description="Show the last-24h highlights (fun titles, top 10, human vs bot kills), right now")
async def dailyhighlights(interaction: discord.Interaction):
    guild_cfg = storage.get_guild(interaction.guild_id)
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
    embed, congrats, players = result
    await interaction.followup.send(content=congrats, embed=embed, allowed_mentions=discord.AllowedMentions(users=True))
    await send_tupper_player_messages(interaction.channel, interaction.guild, interaction.guild_id, _highlight_player_messages(players))


@bot.tree.command(description="Set this channel for the daily highlights report (defaults to the digest channel)")
async def sethighlightschannel(interaction: discord.Interaction):
    guild_cfg = storage.get_guild(interaction.guild_id)
    guild_cfg["highlights_channel_id"] = interaction.channel_id
    guild_cfg["highlights_posted_at"] = datetime.now(timezone.utc).isoformat()
    storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(
        f"✅ Daily highlights will post in {interaction.channel.mention} every 24 hours. "
        f"Use `/dailyhighlights` any time for an immediate one (it can take a minute — it reads match telemetry)."
    )


@bot.tree.command(description="Post the daily highlights report at a fixed Eastern-time each day")
@app_commands.describe(hour="0-23, Eastern time (e.g. 9 for 9am ET)", minute="Quarter-hour, defaults to :00")
@app_commands.choices(minute=QUARTER_HOUR_CHOICES)
async def sethighlightstime(interaction: discord.Interaction, hour: app_commands.Range[int, 0, 23], minute: app_commands.Choice[int] = None):
    guild_cfg = storage.get_guild(interaction.guild_id)
    guild_cfg["highlights_hour_est"] = hour
    guild_cfg["highlights_minute_est"] = minute.value if minute else 0
    storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Daily highlights will now post daily at **{hour:02d}:{guild_cfg['highlights_minute_est']:02d} Eastern**.")


@bot.tree.command(description="Show each player's top weapon mastery and survival level (slow — 2 calls/player)")
async def masterystats(interaction: discord.Interaction):
    guild_cfg = storage.get_guild(interaction.guild_id)
    if not guild_cfg["players"]:
        await interaction.response.send_message("No players tracked yet. Add some with `/addplayer`.")
        return
    await interaction.response.defer()
    try:
        result = await fetch_mastery_report(interaction.guild_id, interaction.guild.name)
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
    await send_tupper_player_messages(interaction.channel, interaction.guild, interaction.guild_id, _mastery_player_messages(players))


@bot.tree.command(description="Check the official leaderboard for roster placements (most won't appear — top ladder only)")
@app_commands.describe(pages="How many 500-player pages to check (default 4 = top 2000)")
async def leaderboardstats(interaction: discord.Interaction, pages: app_commands.Range[int, 1, 10] = 4):
    guild_cfg = storage.get_guild(interaction.guild_id)
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
    embed, congrats, found = result
    await interaction.followup.send(
        content=congrats,
        embed=embed,
        allowed_mentions=discord.AllowedMentions(users=True),
    )
    await send_tupper_player_messages(interaction.channel, interaction.guild, interaction.guild_id, _leaderboard_player_messages(interaction.guild_id, found))


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
    guild_cfg = storage.get_guild(interaction.guild_id)
    guild_cfg["leaderboard_shard"] = region.value
    storage.save_guild(interaction.guild_id, guild_cfg)
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
    guild_cfg = storage.get_guild(interaction.guild_id)
    guild_cfg["leaderboard_queue"] = queue.value
    storage.save_guild(interaction.guild_id, guild_cfg)
    await interaction.response.send_message(f"✅ Leaderboard checks will now use **{queue.name}**.")


@bot.tree.command(description="Link your Discord account to your PUBG name, so reports can @mention you")
@app_commands.describe(pubg_name="Your exact PUBG name, as tracked in /roster")
async def linkme(interaction: discord.Interaction, pubg_name: str):
    guild_cfg = storage.get_guild(interaction.guild_id)
    if not any(p.lower() == pubg_name.lower() for p in guild_cfg["players"]):
        await interaction.response.send_message(
            f"**{pubg_name}** isn't on the roster (`/roster` to check spelling). Add it with `/addplayer` first if it's missing.",
            ephemeral=True,
        )
        return
    storage.link_discord_account(interaction.guild_id, pubg_name, interaction.user.id)

    await interaction.response.send_message(
        f"✅ Linked {interaction.user.mention} to PUBG name **{pubg_name}**. "
        "Your Discord nickname was not changed; PUBG names are shown through the report webhook."
    )


@bot.tree.command(description="Link someone else's Discord account to a PUBG name (e.g. for members who don't run bot commands)")
@app_commands.describe(pubg_name="Exact PUBG name, as tracked in /roster", member="The Discord member to link")
async def linkplayer(interaction: discord.Interaction, pubg_name: str, member: discord.Member):
    guild_cfg = storage.get_guild(interaction.guild_id)
    if not any(p.lower() == pubg_name.lower() for p in guild_cfg["players"]):
        await interaction.response.send_message(
            f"**{pubg_name}** isn't on the roster (`/roster` to check spelling). Add it with `/addplayer` first if it's missing.",
            ephemeral=True,
        )
        return
    storage.link_discord_account(interaction.guild_id, pubg_name, member.id)

    await interaction.response.send_message(
        f"✅ Linked {member.mention} to PUBG name **{pubg_name}**. "
        "Their Discord nickname was not changed; PUBG names are shown through the report webhook."
    )


@bot.tree.command(description="Remove your Discord-to-PUBG-name link")
@app_commands.describe(pubg_name="The PUBG name to unlink")
async def unlinkme(interaction: discord.Interaction, pubg_name: str):
    removed = storage.unlink_discord_account(interaction.guild_id, pubg_name)
    if removed:
        await interaction.response.send_message(f"🗑️ Unlinked **{pubg_name}**.")
    else:
        await interaction.response.send_message(f"**{pubg_name}** wasn't linked to anyone.", ephemeral=True)


async def main():
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
