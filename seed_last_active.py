"""
seed_last_active.py - load the CORRECT "days since last active" list into the bot's saved data.

Run it once, right after you copy the list. From then on the bot keeps counting by itself
(15 days, 16 days, ...) until the player plays another match, and then restarts the count.

It does a DRY RUN by default: it only shows what it would change. Nothing is written until you
add --apply.

    python3 seed_last_active.py                              # preview
    pm2 stop pubg-bot
    python3 seed_last_active.py --apply --force Ajax2021,t5element
    pm2 start pubg-bot

Stop the bot first when you use --apply, so it cannot save over the file at the same moment.

--force NAME[,NAME]  for players whose last match the PUBG API gets wrong. Their date is held
                     until the player plays a match AFTER today, then the API takes over again.
"""
import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.utils import normalize_player_name  # same name matching the bot uses

DEFAULT_GUILD = "1274149985625182208"      # Clan ODIN

CORRECT_LIST = """
01. FreeHelmetChecks — Less than 1 hour ago
02. Salty-John — Less than 1 hour ago
03. MajScrewUp — Less than 1 hour ago
04. Ninjafrkn — 1 hour ago
05. DarkQueenkagome — 1 hour ago
06. TRdoesWhiff — 1 hour ago
07. Pirate_Christian — 1 hour ago
08. Acerouz — 1 hour ago
09. tookiekillyoass — 1 hour ago
10. hootsmccoy — 2 hours ago
11. slyonemaher — 2 hours ago
12. chinaqianggelao6 — 3 hours ago
13. Creighvan — 4 hours ago
14. MacNCheesing — 4 hours ago
15. OLd_Sko0L — 5 hours ago
16. sisyrus — 5 hours ago
17. Real_Major_Minor — 5 hours ago
18. NightSmoke47 — 5 hours ago
19. yrral58 — 6 hours ago
20. SoonDuBuSpicy — 7 hours ago
21. rustybones49801 — 9 hours ago
22. Reyounited — 10 hours ago
23. westpalm — 10 hours ago
24. wrckless — 18 hours ago
25. Mecha_spyro — 19 hours ago
26. Azimuth-360 — 23 hours ago
27. Darkwing-Mcduck — 23 hours ago
28. DrSquatch209 — 23 hours ago
29. CourteousCrab3 — 23 hours ago
30. keyuchehun — 1 day ago
31. AIRBORNE92R — 1 day ago
32. DanhoBang — 1 day ago
33. xKiLLiNiMx — 1 day ago
34. 2dope_ — 1 day ago
35. Pixelalice — 1 day ago
36. Krombopulos_Rio — 1 day ago
37. Scav___ — 1 day ago
38. Mackzeh — 1 day ago
39. Dak_Redbush — 1 day ago
40. KaldanThrom — 1 day ago
41. auriem_OG — 1 day ago
42. Toyota4Runner — 1 day ago
43. Cipher617 — 1 day ago
44. SGT_Flapjack — 1 day ago
45. ClueLess_Drunk — 2 days ago
46. RaymondH87 — 2 days ago
47. Ford-Man — 2 days ago
48. Hawk-Tuah-Boy — 4 days ago
49. Paint_1337ican — 5 days ago
50. xxIns4nExx — 5 days ago
51. xDankSh0t — 5 days ago
52. COLchaos01 — 6 days ago
53. StarLord0331 — 7 days ago
54. SkinnyTurtle88 — 7 days ago
55. SirScoobert — 8 days ago
56. t5element — 10 days ago
57. Luhzayy — 10 days ago
58. BigJGWentsworth — 13 days ago
59. kindadope — 13 days ago
60. El_Grundler23 — 14 days ago
61. 187jack187 — 18 days ago
62. Traingates — 19 days ago
63. C1iMaXOG — 20 days ago
64. FahimSarker — 22 days ago
65. Nitemare_84 — 27 days ago
66. TeeBeth — 28 days ago
67. Ajax2021 — 30 days ago
68. TheLegitCalico — 32 days ago
69. doyish_Lamb — 49 days ago
70. Ellicool — 58 days ago
71. Joker_C-137 — 68 days ago
72. UrShad0w — 76 days ago
73. 82ndAirborne1 — 146 days ago
74. Ajms32xx — 146 days ago
"""

_LINE = re.compile(r"^\s*\d+\.\s*(.+?)\s+[—-]\s+(.+?)\s*$")


def parse_list(text: str) -> list[tuple[str, int | None]]:
    """[(name, whole_days_ago)]. Entries newer than one day give None (the API is precise for those)."""
    entries = []
    for line in text.strip().splitlines():
        match = _LINE.match(line)
        if not match:
            continue
        name, age = match.group(1), match.group(2).lower()
        days = re.search(r"(\d+)\s+day", age)
        entries.append((name, int(days.group(1)) if days else None))
    return entries


def seed(cfg: dict, entries, ref: datetime, force: set[str]) -> list[str]:
    """Write the corrected values into one server's settings. Returns a readable action log."""
    last_seen = cfg.setdefault("last_seen_at", {})
    since_all = cfg.setdefault("inactive_since_dates", {})
    manual_all = cfg.setdefault("manual_inactive_dates", {})
    roster = {normalize_player_name(p): p for p in cfg.get("players", [])}
    forced = {normalize_player_name(n) for n in force}
    actions = []

    for name, days in entries:
        norm = normalize_player_name(name)
        if norm not in roster:
            actions.append(f"?? {name}: not in this server's roster, skipped")
            continue
        if days is None:
            actions.append(f"-- {name}: played in the last day, the API handles this one")
            continue

        # "N days ago" means N full days plus part of a day; the middle of that range
        # keeps the count right whichever way the real time falls.
        last = ref - timedelta(days=days, hours=12)
        existing = last_seen.get(norm)
        existing_dt = datetime.fromisoformat(existing) if existing else None

        if norm in forced:
            last_seen[norm] = last.isoformat()
            manual_all[norm] = {"date": last.isoformat(), "set_at": ref.isoformat()}
            since_all.pop(norm, None)
            actions.append(f"** {name}: {days} day(s), HELD until they play again (API value ignored)")
            continue

        if existing_dt is not None and existing_dt > last:
            last = existing_dt                      # the bot already saw a newer match: never go back
        last_seen[norm] = last.isoformat()
        manual_all.pop(norm, None)
        if days >= 14:
            since_all[norm] = (last + timedelta(days=14)).isoformat()
            actions.append(f"ok {name}: {days} day(s), counting on from here")
        else:
            since_all.pop(norm, None)
            actions.append(f"ok {name}: {days} day(s) (floor under the API's own value)")
    return actions


def _guild_block(data: dict, guild_id: str) -> dict:
    guilds = data["guilds"] if "guilds" in data else data
    if guild_id not in guilds:
        raise SystemExit(f"Server {guild_id} was not found in the data file.")
    return guilds[guild_id]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--guild", default=DEFAULT_GUILD)
    ap.add_argument("--data", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json"))
    ap.add_argument("--force", default="", help="comma-separated names whose API date is wrong")
    ap.add_argument("--apply", action="store_true", help="actually write the changes (default: preview only)")
    args = ap.parse_args()

    entries = parse_list(CORRECT_LIST)
    force = {n.strip() for n in args.force.split(",") if n.strip()}
    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)
    cfg = _guild_block(data, args.guild)
    ref = datetime.now(timezone.utc)

    print(f"Entries in the corrected list: {len(entries)}   Roster size: {len(cfg.get('players', []))}")
    for line in seed(cfg, entries, ref, force):
        print(line)

    if not args.apply:
        print("\nPREVIEW ONLY - nothing was written. Stop the bot, then run again with --apply.")
        return
    backup = args.data + ".bak-before-lastactive-" + ref.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(args.data, backup)
    tmp = args.data + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, args.data)
    print(f"\nSaved. Backup of the old file: {backup}\nNow start the bot again:  pm2 start pubg-bot")


if __name__ == "__main__":
    main()
