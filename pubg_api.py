"""
Thin wrapper around the official PUBG Developer API.

Docs: https://documentation.pubg.com/
Get a free API key at: https://developer.pubg.com/

Notes:
- The official API has NO clan-roster endpoint. There is no way to ask
  "give me all members of clan X". Instead, you maintain your own list of
  player names (the roster) and this bot looks up each of those players
  individually, then aggregates the results. This is the same approach
  sites like PUBGLooker use under the hood.
- Default API keys are rate-limited to 10 requests/minute. This wrapper
  batches player lookups (up to 10 names per call) to stay well under that.
- Shard = platform. For Steam/PC players this is "steam".
  Other values: "psn", "xbox", "kakao", "stadia" (see PUBG docs for the
  full/updated list if you're tracking non-PC players).
"""

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp

BASE_URL = "https://api.pubg.com"


class PubgApiError(Exception):
    pass


class RateLimiter:
    """Very small sliding-window limiter so we never exceed N calls/60s."""

    def __init__(self, max_calls: int = 10, period_seconds: int = 60):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def wait(self):
        async with self._lock:
            now = time.monotonic()
            self._timestamps = [t for t in self._timestamps if now - t < self.period_seconds]
            if len(self._timestamps) >= self.max_calls:
                sleep_for = self.period_seconds - (now - self._timestamps[0]) + 0.1
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
            self._timestamps.append(time.monotonic())


class PubgClient:
    def __init__(self, api_key: str, shard: str = "steam"):
        self.api_key = api_key
        self.shard = shard
        self._limiter = RateLimiter(max_calls=9, period_seconds=60)  # leave 1 call headroom
        self._session: aiohttp.ClientSession | None = None
        self._current_season_id: str | None = None  # cached for the process lifetime

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/vnd.api+json",
                }
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, path: str, params: dict[str, Any] | None = None, rate_limited: bool = True) -> dict:
        if rate_limited:
            await self._limiter.wait()
        session = await self._get_session()
        url = f"{BASE_URL}{path}"
        async with session.get(url, params=params) as resp:
            if resp.status == 404:
                raise PubgApiError(f"Not found: {path}")
            if resp.status == 429:
                raise PubgApiError("Rate limited by PUBG API. Try again shortly.")
            if resp.status >= 400:
                text = await resp.text()
                raise PubgApiError(f"PUBG API error {resp.status}: {text[:300]}")
            return await resp.json()

    async def _get_telemetry(self, telemetry_url: str) -> list[dict]:
        """
        Telemetry lives on a separate CDN, not api.pubg.com, and match/
        telemetry calls are exempt from the 10/min rate limit — so this
        bypasses the limiter entirely.
        """
        session = await self._get_session()
        async with session.get(telemetry_url, headers={"Accept": "application/json"}) as resp:
            if resp.status >= 400:
                raise PubgApiError(f"Telemetry fetch failed: {resp.status}")
            return await resp.json()

    async def get_players_by_name(self, names: list[str]) -> list[dict]:
        """
        Look up up to 10 player names at once.
        Returns list of {"id": ..., "name": ..., "match_ids": [...]} for
        players that were found. match_ids are their recent matches
        (last ~14 days), most-recent-first per the PUBG API.
        Unknown/misspelled names are silently dropped from the result (caller
        should diff against the input list to report ones not found).
        """
        if not names:
            return []
        if len(names) > 10:
            raise ValueError("PUBG API allows at most 10 player names per lookup call")

        data = await self._request(
            f"/shards/{self.shard}/players",
            params={"filter[playerNames]": ",".join(names)},
        )
        results = []
        for entry in data.get("data", []):
            match_refs = entry.get("relationships", {}).get("matches", {}).get("data", [])
            results.append(
                {
                    "id": entry["id"],
                    "name": entry["attributes"]["name"],
                    "match_ids": [m["id"] for m in match_refs],
                }
            )
        return results

    async def get_lifetime_stats_batch(self, player_ids: list[str], game_mode: str = "squad-fpp") -> dict[str, dict]:
        """
        Batch lifetime stats for up to 10 player IDs, for a single game mode.
        Returns {player_id: stats_dict}.
        """
        if not player_ids:
            return {}
        if len(player_ids) > 10:
            raise ValueError("PUBG API allows at most 10 player IDs per stats batch call")

        data = await self._request(
            f"/shards/{self.shard}/seasons/lifetime/gameMode/{game_mode}/players",
            params={"filter[playerIds]": ",".join(player_ids)},
        )
        out: dict[str, dict] = {}
        for entry in data.get("data", []):
            player_id = entry["relationships"]["player"]["data"]["id"]
            out[player_id] = entry["attributes"]["gameModeStats"].get(game_mode, {})
        return out

    async def get_players_and_stats(self, names: list[str], game_mode: str = "squad-fpp") -> tuple[list[dict], list[str]]:
        """
        Convenience: resolve a list of player names to IDs, fetch lifetime
        stats for that game mode, and merge everything together.

        Returns (players, not_found) where players is a list of:
          {"name": ..., "id": ..., "stats": {...}}
        and not_found is the list of input names that couldn't be resolved.
        """
        found: list[dict] = []
        not_found: list[str] = []

        for chunk in _chunk(names, 10):
            resolved = await self.get_players_by_name(chunk)
            resolved_names_lower = {p["name"].lower() for p in resolved}
            for n in chunk:
                if n.lower() not in resolved_names_lower:
                    not_found.append(n)
            found.extend(resolved)

        for chunk in _chunk(found, 10):
            ids = [p["id"] for p in chunk]
            stats_map = await self.get_lifetime_stats_batch(ids, game_mode=game_mode)
            for p in chunk:
                p["stats"] = stats_map.get(p["id"], {})

        return found, not_found

    async def get_match_created_at(self, match_id: str) -> str | None:
        """
        Returns the ISO-8601 createdAt timestamp for a match, or None if it
        can't be fetched. Match-endpoint calls do not count against the
        10/min rate limit, so these are cheap to make per-player.
        """
        try:
            data = await self._request(f"/shards/{self.shard}/matches/{match_id}", rate_limited=False)
        except PubgApiError:
            return None
        return data.get("data", {}).get("attributes", {}).get("createdAt")

    async def get_last_active_times(self, names: list[str]) -> tuple[list[dict], list[str]]:
        """
        The PUBG API has no concept of "last login" — it only knows about
        matches played. This uses each player's most recent match as the
        best available proxy for "last time they played."

        Returns (players, not_found) where players is a list of:
          {"name": ..., "id": ..., "last_match_at": iso_str_or_None}
        sorted most-recently-active first (players with no recent match
        data sort last).
        """
        found: list[dict] = []
        not_found: list[str] = []

        for chunk in _chunk(names, 10):
            resolved = await self.get_players_by_name(chunk)
            resolved_names_lower = {p["name"].lower() for p in resolved}
            for n in chunk:
                if n.lower() not in resolved_names_lower:
                    not_found.append(n)
            found.extend(resolved)

        async def resolve_one(p: dict):
            if p["match_ids"]:
                p["last_match_at"] = await self.get_match_created_at(p["match_ids"][0])
            else:
                p["last_match_at"] = None

        await asyncio.gather(*(resolve_one(p) for p in found))

        found.sort(key=lambda p: p["last_match_at"] or "", reverse=True)
        return found, not_found

    async def get_current_season_id(self) -> str:
        """Cached for the life of the process. Restart the bot after a new
        PUBG season starts to pick up the new season id."""
        if self._current_season_id:
            return self._current_season_id
        data = await self._request(f"/shards/{self.shard}/seasons")
        for entry in data.get("data", []):
            if entry.get("attributes", {}).get("isCurrentSeason"):
                self._current_season_id = entry["id"]
                return self._current_season_id
        raise PubgApiError("Could not determine the current PUBG season")

    async def get_player_ranked_stats(self, player_id: str, game_mode: str = "squad") -> dict:
        """
        Ranked stats for one player, one queue, current season. game_mode
        should be the TPP name with no '-fpp' suffix (e.g. 'squad', 'duo',
        'solo') unless you specifically want ranked FPP.
        Note: unlike lifetime stats, ranked has NO batch endpoint — this is
        one API call per player.
        """
        season_id = await self.get_current_season_id()
        data = await self._request(f"/shards/{self.shard}/players/{player_id}/seasons/{season_id}/ranked")
        ranked_modes = data.get("data", {}).get("attributes", {}).get("rankedGameModeStats", {})
        return ranked_modes.get(game_mode, {})

    async def get_ranked_report(self, names: list[str], game_mode: str = "squad") -> tuple[list[dict], list[str]]:
        """
        Convenience: resolve names to IDs then fetch current-season ranked
        stats for each, for the given TPP queue.

        Returns (players, not_found) where players is a list of:
          {"name": ..., "id": ..., "ranked": {...}}
        sorted by current rank points, highest first.
        """
        found: list[dict] = []
        not_found: list[str] = []

        for chunk in _chunk(names, 10):
            resolved = await self.get_players_by_name(chunk)
            resolved_names_lower = {p["name"].lower() for p in resolved}
            for n in chunk:
                if n.lower() not in resolved_names_lower:
                    not_found.append(n)
            found.extend(resolved)

        async def resolve_one(p: dict):
            p["ranked"] = await self.get_player_ranked_stats(p["id"], game_mode=game_mode)

        await asyncio.gather(*(resolve_one(p) for p in found))

        found.sort(key=lambda p: p["ranked"].get("currentRankPoint", 0), reverse=True)
        return found, not_found

    async def _get_match_details(self, match_id: str) -> dict:
        """
        Fetches a match and extracts just what we need: when it happened,
        each participant's stats keyed by their account id, and the
        telemetry asset URL (if present). Rate-limit exempt, like
        get_match_created_at.
        """
        data = await self._request(f"/shards/{self.shard}/matches/{match_id}", rate_limited=False)
        attrs = data.get("data", {}).get("attributes", {})
        participants: dict[str, dict] = {}
        telemetry_url = None
        for inc in data.get("included", []):
            if inc.get("type") == "participant":
                s = inc.get("attributes", {}).get("stats", {})
                pid = s.get("playerId")
                if pid:
                    participants[pid] = s
            elif inc.get("type") == "asset":
                telemetry_url = inc.get("attributes", {}).get("URL")
        return {"created_at": attrs.get("createdAt"), "participants": participants, "telemetry_url": telemetry_url}

    async def get_daily_activity_report(
        self, names: list[str], hours: int = 24, max_matches_checked: int = 20
    ) -> tuple[list[dict], list[str]]:
        """
        For each roster player, aggregates kills/damage/headshots/revives/
        assists/wins from all matches played in the last `hours` hours, and
        — via match telemetry — splits kills into human vs AI-bot kills.
        PUBG tags bot accounts with an "ai." accountId prefix; there's no
        stats-endpoint field for this, it only shows up in telemetry.

        This is much heavier than the other reports: it downloads full
        match telemetry (can be a few MB per match). Matches shared by
        multiple squadmates are only fetched and parsed once, and match_ids
        are assumed most-recent-first (per PUBG API behavior) so we stop
        walking a player's match history as soon as we pass the time window.

        Returns (players, not_found) where each player dict has a "daily"
        sub-dict: {kills, damageDealt, headshotKills, revives, assists,
        wins, matches, human_kills, bot_kills, self_kills, team_kills,
        stooge_kills, boosts, heals, road_kills, swim_distance,
        weapons_acquired, loot_ratio, best_zero_kill_placement}.
        stooge_kills = self_kills + team_kills. loot_ratio = weapons
        acquired per kill. best_zero_kill_placement = the best (lowest)
        winPlace achieved in a match where they got 0 kills, or None if
        every match had at least 1 kill. Sorted by kills, highest first.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        found: list[dict] = []
        not_found: list[str] = []
        for chunk in _chunk(names, 10):
            resolved = await self.get_players_by_name(chunk)
            resolved_lower = {p["name"].lower() for p in resolved}
            for n in chunk:
                if n.lower() not in resolved_lower:
                    not_found.append(n)
            found.extend(resolved)

        match_cache: dict[str, dict] = {}
        kill_breakdown_cache: dict[str, dict[str, tuple[int, int]]] = {}
        cache_lock = asyncio.Lock()
        sem = asyncio.Semaphore(5)  # cap concurrent match/telemetry fetches

        async def get_match(match_id: str) -> dict:
            async with cache_lock:
                if match_id in match_cache:
                    return match_cache[match_id]
            async with sem:
                details = await self._get_match_details(match_id)
            async with cache_lock:
                match_cache[match_id] = details
            return details

        async def get_kill_breakdown(match_id: str, telemetry_url: str | None) -> dict[str, tuple[int, int, int]]:
            """Returns {account_id: (human_kills, bot_kills, self_kills)} for
            a match. Self-kills (e.g. own grenade/vehicle) show up in
            telemetry as a kill event where killer and victim are the same
            account — there's no stats-endpoint field for this."""
            async with cache_lock:
                if match_id in kill_breakdown_cache:
                    return kill_breakdown_cache[match_id]
            tally: dict[str, list[int]] = {}
            if telemetry_url:
                async with sem:
                    try:
                        events = await self._get_telemetry(telemetry_url)
                    except PubgApiError:
                        events = []
                for e in events:
                    if e.get("_T") not in ("LogPlayerKillV2", "LogPlayerKill"):
                        continue
                    killer_id = (e.get("killer") or {}).get("accountId")
                    if not killer_id:
                        continue
                    victim_id = (e.get("victim") or {}).get("accountId") or ""
                    counts = tally.setdefault(killer_id, [0, 0, 0])
                    if victim_id == killer_id:
                        counts[2] += 1  # self-kill
                    elif victim_id.startswith("ai."):
                        counts[1] += 1  # bot kill
                    else:
                        counts[0] += 1  # human kill
            result = {k: (v[0], v[1], v[2]) for k, v in tally.items()}
            async with cache_lock:
                kill_breakdown_cache[match_id] = result
            return result

        async def process_player(p: dict):
            totals = {
                "kills": 0, "damageDealt": 0.0, "headshotKills": 0,
                "revives": 0, "assists": 0, "wins": 0, "matches": 0,
                "human_kills": 0, "bot_kills": 0, "self_kills": 0,
                "team_kills": 0, "stooge_kills": 0, "boosts": 0, "heals": 0,
                "road_kills": 0, "swim_distance": 0.0, "weapons_acquired": 0,
                "best_zero_kill_placement": None, "loot_ratio": 0.0,
            }
            for match_id in p.get("match_ids", [])[:max_matches_checked]:
                details = await get_match(match_id)
                created_at = details.get("created_at")
                if not created_at:
                    continue
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if created_dt < cutoff:
                    break  # newest-first assumption: nothing after this is in-window either
                stats = details["participants"].get(p["id"])
                if not stats:
                    continue
                totals["kills"] += stats.get("kills", 0)
                totals["damageDealt"] += stats.get("damageDealt", 0.0)
                totals["headshotKills"] += stats.get("headshotKills", 0)
                totals["revives"] += stats.get("revives", 0)
                totals["assists"] += stats.get("assists", 0)
                totals["wins"] += 1 if stats.get("winPlace") == 1 else 0
                totals["matches"] += 1
                totals["team_kills"] += stats.get("teamKills", 0)
                totals["boosts"] += stats.get("boosts", 0)
                totals["heals"] += stats.get("heals", 0)
                totals["road_kills"] += stats.get("roadKills", 0)
                totals["swim_distance"] += stats.get("swimDistance", 0.0)
                totals["weapons_acquired"] += stats.get("weaponsAcquired", 0)

                match_kills = stats.get("kills", 0)
                win_place = stats.get("winPlace")
                if match_kills == 0 and win_place:
                    if totals["best_zero_kill_placement"] is None or win_place < totals["best_zero_kill_placement"]:
                        totals["best_zero_kill_placement"] = win_place

                breakdown = await get_kill_breakdown(match_id, details.get("telemetry_url"))
                human, bot, self_kills = breakdown.get(p["id"], (0, 0, 0))
                totals["human_kills"] += human
                totals["bot_kills"] += bot
                totals["self_kills"] += self_kills
            totals["stooge_kills"] = totals["self_kills"] + totals["team_kills"]
            totals["loot_ratio"] = round(totals["weapons_acquired"] / max(totals["kills"], 1), 2)
            p["daily"] = totals

        await asyncio.gather(*(process_player(p) for p in found))
        found.sort(key=lambda p: p["daily"]["kills"], reverse=True)
        return found, not_found

    # ---------- Weapon / Survival Mastery ----------

    async def get_weapon_mastery(self, player_id: str) -> dict:
        """Raw attributes from the weapon_mastery endpoint for one player."""
        data = await self._request(f"/shards/{self.shard}/players/{player_id}/weapon_mastery")
        return data.get("data", {}).get("attributes", {})

    async def get_survival_mastery(self, player_id: str) -> dict:
        """Raw attributes from the survival_mastery endpoint for one player."""
        data = await self._request(f"/shards/{self.shard}/players/{player_id}/survival_mastery")
        return data.get("data", {}).get("attributes", {})

    @staticmethod
    def _best_weapon_from_mastery(attrs: dict) -> dict | None:
        """
        Picks the player's highest-level weapon out of their mastery
        summary. NOTE: PUBG's public docs don't fully spell out the exact
        field casing here, so this reads several plausible field-name
        variants defensively. If this consistently comes back empty against
        a real response, the field names need adjusting against what the
        live API actually returns.
        """
        summaries = attrs.get("weaponSummaries")
        if not summaries:
            summaries = attrs.get("weaponMasterySummary", {}).get("weaponSummaries", {})
        if not summaries:
            return None

        best = None
        for weapon_id, block in summaries.items():
            stats = (
                block.get("OfficialStatsTotal")
                or block.get("StatsTotal")
                or block.get("CompetitiveStatsTotal")
                or {}
            )
            level = stats.get("Level", stats.get("level", 0)) or 0
            xp = stats.get("XP", stats.get("Exp", stats.get("xp", 0))) or 0
            if best is None or (level, xp) > (best["level"], best["xp"]):
                best = {
                    "weapon_id": weapon_id,
                    "level": level,
                    "xp": xp,
                    "kills": stats.get("Kills", stats.get("kills", 0)) or 0,
                    "headshot_kills": stats.get("HeadShotKills", stats.get("headshotKills", 0)) or 0,
                }
        return best

    async def get_mastery_report(self, names: list[str]) -> tuple[list[dict], list[str]]:
        """
        For each roster player: their highest-level weapon (mastery level,
        XP, kills with it) and their overall survival mastery level/XP.
        Two API calls per player (no batch endpoint exists for mastery),
        so this is slow for a big roster — it's on-demand only, not part
        of the scheduled reports.

        Returns (players, not_found). Each player dict gets a "mastery"
        sub-dict: {best_weapon, best_weapon_level, best_weapon_xp,
        best_weapon_kills, survival_level, survival_xp}.
        Sorted by best_weapon_level, highest first.
        """
        found: list[dict] = []
        not_found: list[str] = []
        for chunk in _chunk(names, 10):
            resolved = await self.get_players_by_name(chunk)
            resolved_lower = {p["name"].lower() for p in resolved}
            for n in chunk:
                if n.lower() not in resolved_lower:
                    not_found.append(n)
            found.extend(resolved)

        async def process(p: dict):
            try:
                weapon_attrs = await self.get_weapon_mastery(p["id"])
            except PubgApiError:
                weapon_attrs = {}
            try:
                survival_attrs = await self.get_survival_mastery(p["id"])
            except PubgApiError:
                survival_attrs = {}

            best = self._best_weapon_from_mastery(weapon_attrs)
            p["mastery"] = {
                "best_weapon": best["weapon_id"] if best else None,
                "best_weapon_level": best["level"] if best else 0,
                "best_weapon_xp": best["xp"] if best else 0,
                "best_weapon_kills": best["kills"] if best else 0,
                "survival_level": survival_attrs.get("Level", survival_attrs.get("level", 0)) or 0,
                "survival_xp": survival_attrs.get("XP", survival_attrs.get("Exp", survival_attrs.get("xp", 0))) or 0,
            }

        await asyncio.gather(*(process(p) for p in found))
        found.sort(key=lambda p: p["mastery"]["best_weapon_level"], reverse=True)
        return found, not_found

    # ---------- Official Leaderboards ----------

    async def get_leaderboard_page(self, season_id: str, game_mode: str, page: int, leaderboard_shard: str) -> list[dict]:
        """
        One page (500 entries) of the official season leaderboard.
        IMPORTANT: leaderboards use a platform-REGION shard (e.g. 'pc-na'),
        not the plain platform shard ('steam') used everywhere else in
        this client — that's a real quirk of this specific endpoint.

        Real response shape (confirmed against a live key — PUBG's own
        docs for this endpoint are thin): the top-level "data" is a SINGLE
        object (the leaderboard itself, not a list of ranked entries).
        The ordered list of players lives at
        data.relationships.players.data, as an array of {"type":"player",
        "id":...} references — there's no explicit rank field; the
        position in that array IS the rank, offset by the page number
        (PUBG returns 500 per page).

        Returns list of {"rank": int, "player_id": str}.
        """
        data = await self._request(
            f"/shards/{leaderboard_shard}/leaderboards/{season_id}/{game_mode}",
            params={"page[number]": page},
        )
        try:
            root = data.get("data") if isinstance(data, dict) else None
            if not isinstance(root, dict):
                raise TypeError(f"expected top-level 'data' to be an object, got {type(root).__name__}")

            players_rel = (root.get("relationships") or {}).get("players")
            player_refs = players_rel.get("data") if isinstance(players_rel, dict) else None
            if not isinstance(player_refs, list):
                raise TypeError(
                    f"expected relationships.players.data to be a list, got {type(player_refs).__name__}"
                )

            base_rank = page * 500
            entries = []
            for i, ref in enumerate(player_refs):
                if not isinstance(ref, dict):
                    continue
                entries.append({"rank": base_rank + i + 1, "player_id": ref.get("id")})
            return entries
        except (AttributeError, TypeError, KeyError) as e:
            # Surface the actual shape if this ever breaks again, rather
            # than crashing opaquely.
            try:
                preview = json.dumps(data, indent=2)[:600]
            except (TypeError, ValueError):
                preview = repr(data)[:600]
            raise PubgApiError(
                f"Leaderboard response didn't match the expected format "
                f"({type(e).__name__}: {e}). Raw response preview:\n{preview}"
            )

    async def get_leaderboard_placements(
        self, names: list[str], season_id: str, game_mode: str = "squad",
        max_pages: int = 4, leaderboard_shard: str = "pc-na",
    ) -> tuple[dict[str, dict], int]:
        """
        Checks the top `max_pages * 500` leaderboard entries for any of the
        given roster names. Most players will NOT appear here — this is
        the official top-of-the-ladder leaderboard, not a general lookup.

        Matches by account ID rather than name — the leaderboard response
        doesn't reliably expose player names directly, and ID matching is
        exact anyway (no case-sensitivity or typo risk). Roster names are
        resolved to IDs first via the regular player-lookup endpoint.

        Returns ({matched_name: {"rank", "name"}}, total_entries_checked).
        """
        id_to_name: dict[str, str] = {}
        for chunk in _chunk(names, 10):
            resolved = await self.get_players_by_name(chunk)
            for p in resolved:
                id_to_name[p["id"]] = p["name"]

        found: dict[str, dict] = {}
        checked = 0
        for page in range(max_pages):
            entries = await self.get_leaderboard_page(season_id, game_mode, page, leaderboard_shard)
            if not entries:
                break
            checked += len(entries)
            for e in entries:
                pid = e.get("player_id")
                if pid in id_to_name:
                    name = id_to_name[pid]
                    found[name] = {"rank": e["rank"], "name": name}
        return found, checked


def _chunk(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]
