"""
Three kinds of protection for tracked players. All three keep a player from being flagged
for inactivity; they are kept apart so the list shows WHY someone is protected.

  LEADERSHIP - guild_cfg["leadership_protected"]: clan leaders and managers. Shown with LEADERSHIP_ICON.
               Managed with /addleadership and /removeleadership. Protected because of
               their role, so this is neither a "permanent" nor a "temporary" exception.

  PERMANENT  - guild_cfg["protected_players"], a plain list of names. Shown as 🛡️.
               Managed with /addprotected and /removeprotected. Never expires.

  TEMPORARY  - guild_cfg["temporary_protected_players"], for members who reached out
               (vacation, a break, a deployment...). Shown as ⏳. Managed with
               /addtempprotected and /removetempprotected. It can end on a date
               (the player is then listed normally again) or stay until removed.

A player on more than one list is shown by the first that applies: leadership icon, then 🛡️, then ⏳.
These helpers contain no Discord or file code, so they are easy to test.
"""
from datetime import datetime, timedelta, timezone

from modules.utils import normalize_player_name

TEMP_KEY = "temporary_protected_players"
LEAD_KEY = "leadership_protected"
# The icon for clan leaders and managers. This is the ONLY place it is chosen: change this one
# character and the list, the counts, the footer legend, /listprotected and the command replies
# all follow. (Any emoji works.)
LEADERSHIP_ICON = "⭐"
LEAD_ROLES = ("Leader", "Manager")
REASON_MAX = 100


def _parse(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _until(entry):
    return _parse(entry.get("until")) if isinstance(entry, dict) else None


def is_permanent(guild_cfg: dict, name: str) -> bool:
    wanted = normalize_player_name(name)
    return any(normalize_player_name(p) == wanted for p in guild_cfg.get("protected_players", []))


def active_temporary_protected(guild_cfg: dict, now: datetime | None = None) -> dict:
    """{normalized name: entry} for temporary protections that have not ended."""
    now = now or datetime.now(timezone.utc)
    active = {}
    for key, entry in (guild_cfg.get(TEMP_KEY) or {}).items():
        until = _until(entry)
        if until is not None and until <= now:
            continue
        active[key] = entry
    return active


def purge_expired_temporary(guild_cfg: dict, now: datetime | None = None) -> list[str]:
    """Delete temporary protections whose end date has passed. Returns the names that ended."""
    now = now or datetime.now(timezone.utc)
    store = guild_cfg.get(TEMP_KEY) or {}
    ended = []
    for key, entry in list(store.items()):
        until = _until(entry)
        if until is not None and until <= now:
            ended.append(entry.get("name", key) if isinstance(entry, dict) else key)
            del store[key]
    return ended


def set_temporary(guild_cfg: dict, display_name: str, days: int | None = None, reason: str = "",
                  now: datetime | None = None) -> dict:
    """Mark a player temporarily protected (for `days` days, or until removed when days is None)."""
    now = now or datetime.now(timezone.utc)
    entry = {
        "name": display_name,
        "set_at": now.isoformat(),
        "until": (now + timedelta(days=days)).isoformat() if days else None,
        "reason": (reason or "").strip()[:REASON_MAX],
    }
    guild_cfg.setdefault(TEMP_KEY, {})[normalize_player_name(display_name)] = entry
    return entry


def get_leadership(guild_cfg: dict) -> dict:
    """{normalized name: {"name", "role", "set_at"}} for clan leaders and managers."""
    return dict(guild_cfg.get(LEAD_KEY) or {})


def is_leadership(guild_cfg: dict, name: str) -> bool:
    return normalize_player_name(name) in (guild_cfg.get(LEAD_KEY) or {})


def set_leadership(guild_cfg: dict, display_name: str, role: str = "Leader", now: datetime | None = None) -> dict:
    """Record a clan leader or manager."""
    now = now or datetime.now(timezone.utc)
    entry = {"name": display_name, "role": role if role in LEAD_ROLES else "Leader", "set_at": now.isoformat()}
    guild_cfg.setdefault(LEAD_KEY, {})[normalize_player_name(display_name)] = entry
    return entry


def protection_kind(guild_cfg: dict, name: str, now: datetime | None = None) -> str | None:
    """'leadership', 'permanent', 'temporary' or None, in that order of priority."""
    if is_leadership(guild_cfg, name):
        return "leadership"
    if is_permanent(guild_cfg, name):
        return "permanent"
    if normalize_player_name(name) in active_temporary_protected(guild_cfg, now):
        return "temporary"
    return None
