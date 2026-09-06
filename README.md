# PUBG Clan Tracker Discord Bot

Tracks a list of PUBG player names per Discord server, pulls their lifetime
stats from the official PUBG API, and posts an aggregated "clan report"
(kills, wins, win rate, top fraggers) — both on a daily schedule and on
demand via slash commands.

**Perfect for roster cleanup** — Track inactive clan members who have been
removed from the actual PUBG clan but still have Discord server access.
Use the protected player list to keep key members while tracking others
for removal decisions.

## Support server

For Bot help, bug reports, feature requests, and service updates, join the
[Game Tracker Bot Discord Support Server](https://discord.gg/KEUWmwBYV4).

## Important limitation (same one PUBGLooker deals with)

The official PUBG API has **no clan-roster endpoint**. There's no way to
ask it "give me everyone in clan X." So this bot works the way every PUBG
stat site does: you manually add player names to a roster with
`/addplayer`, and the bot looks each one up individually and aggregates
the results.

## Data retention limitation

The official PUBG API only retains match data for 14 days. Players with no
recent matches will show "No recent matches found" which indicates they haven't
played in the last 14 days according to the PUBG API. This is a hard limit
imposed by PUBG's API and cannot be extended.

## Manual inactive date override

For players beyond the 14-day PUBG API limit, you can manually set their
last played date using the `/setinactivedate` command. This is useful when
you have historical data from other sources (like OP.GG manual lookup).

- `/setinactivedate <name> <days_ago>` - Set manual inactive date (1-365 days)
- `/removeinactivedate <name>` - Remove manual override
- Players with manual dates show with *(manual)* marker in reports

## Protected player list

You can protect certain players from being flagged for removal due to
inactivity:

- Use `/addprotected <name>` to add players to the protected list
- Use `/removeprotected <name>` to remove protection
- Use `/listprotected` to see all protected players
- Protected players show with a 🛡️ shield icon in the last active report
- This is useful for clan leaders, long-term members, or players on extended breaks

### Roster Cleanup Workflow

This feature is designed for managing inactive clan members who have been
removed from the actual PUBG clan but still have Discord server access:

1. **Protect key players first:**
   ```
   /addprotected ClanLeaderName
   /addprotected Officers
   /addprotected LongTermMembersOnBreak
   ```

2. **Monitor the rest:**
   ```
   /lastactive                    # Review inactivity regularly
   ```

3. **Clean up inactive members:**
   ```
   /removeplayer InactiveMember   # Remove from tracker
   ```

Protected players stay on the tracker regardless of inactivity, while
non-protected players can be identified and removed for roster cleanup.

## What you'll need (all free)

1. **A Discord bot token** — https://discord.com/developers/applications
   - New Application → Bot → Reset Token → copy it
   - Under "Privileged Gateway Intents" enable **Server Members Intent** (required for avatar functionality)
   - Under OAuth2 → URL Generator, check `bot` and `applications.commands`
     scopes, and permissions `Send Messages` and `Embed Links`, then use
     the generated URL to invite the bot to your server
2. **A PUBG API key** — https://developer.pubg.com/
   - Sign in, create an app, copy the API key
   - Free tier = 10 requests/minute, which this bot respects automatically
3. **Somewhere to run it 24/7** — see hosting options below

## Slash commands not showing up in Discord?

On every restart, the bot publishes the complete command list directly to
every Discord server it is currently in. Guild-specific commands are available
immediately. The bot also clears its old global command list, so Discord does
not show a delayed global copy alongside the current guild command.

For a newly invited server, restart the bot once after inviting it. The startup
log will show `Instantly synced ... commands to guild ...` for every server.

If commands still don't show after that, fully close and reopen Discord
(not just refresh) — the client caches the command list locally.

## Auto-Restart on Windows (recommended for always-on use)

Running `python bot.py` directly means the bot goes down for good if it
ever crashes, your PC sleeps, or you close the terminal. `run_bot.bat`
fixes the "crashes" part by looping forever and restarting the bot
automatically. Task Scheduler fixes the "PC restarts" part by launching
that loop automatically when you log in.

### Step 1 — Test the supervisor script

Double-click `run_bot.bat` in `E:\BotFolder` (or run it from PowerShell).
A window opens and the bot starts as usual. Two new log files appear in
the folder:
- `bot_supervisor.log` — restart events, with timestamps
- `bot_output.log` — everything the bot itself prints (what used to only
  show in the terminal)

To confirm the auto-restart actually works, close the bot with **Ctrl+C
inside that window** — within 10 seconds you should see it start back up
on its own and log a new "Starting..." line.

### Step 2 — Stop it for real

Since the loop restarts the bot on any exit, closing the window or
Ctrl+C alone won't fully stop it — the supervisor just brings it back.
Run `stop_bot.bat` when you actually want it down (e.g. before editing
`bot.py`). Note: this kills *all* `python.exe` processes on your PC, so
close any other Python programs' output first if that matters to you.

### Step 3 — Run it automatically at logon

1. Open **Task Scheduler** (search for it in the Start menu)
2. Click **Create Basic Task...** (right panel)
3. Name: `PUBG Clan Bot`, click Next
4. Trigger: **When I log on**, click Next
5. Action: **Start a program**, click Next
6. Program/script: browse to `E:\BotFolder\run_bot.bat`
7. Click Next, then **Finish**
8. Find the new task in the main list, right-click → **Properties**
9. On the **General** tab, check **Run with highest privileges** (avoids
   random permission issues)
10. On the **Settings** tab, make sure **"If the task is already running,
    the following rule applies"** is set to **"Do not start a new
    instance"** — this stops you from accidentally running two bots at
    once if you also double-click `run_bot.bat` manually sometime
11. Click OK

From now on, logging into Windows automatically starts the bot, and any
crash mid-session gets auto-restarted within 10 seconds. To pause it
long-term, open Task Scheduler and **Disable** the task, or delete it.

## Local setup (for testing)

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and fill in DISCORD_TOKEN and PUBG_API_KEY
# (PUBG_SHARD defaults to "steam")
# IMPORTANT: Enable Server Members Intent in Discord Developer Portal
python bot.py
```

Then in your Discord server:
```
/addplayer  <pubg name>      (repeat for each clan member)
/setchannel                  (run this in the channel you want digests posted to)
/setgamemode squad-fpp       (optional, this is already the default)
/clanstats                   (test it immediately)
/addprotected ClanLeader     (protect key members from inactivity removal)
/lastactive                  (check inactivity for roster cleanup)
```


### Survival Mastery weekly report

The bot can post a weekly Survival Mastery report grouped by PUBG tier, with **Tier 5 first and Tier 1 last**. Players inside each tier are sorted by **Survival Level highest to lowest**, then XP. The five tier icons are included in the `assets/` folder and are attached to the Discord embeds.

Commands:
- `/survivalstats` — post the report immediately.
- `/setsurvivalchannel` — choose the weekly report channel.
- `/setsurvivaltime <day> <hour> [minute]` — choose the weekly Eastern-time schedule.
- `/reporttoggle` → `Survival Mastery` → On/Off — enable or disable the scheduled report without losing its settings.

The official PUBG API now exposes the Survival Mastery `tier` field, so the bot reads the tier directly rather than guessing it from the level.

## Commands

| Command | What it does |
|---|---|
| `/addplayer <name>` | Add a player to the roster |
| `/addplayers <names>` | Bulk-add players — paste names separated by commas or newlines |
| `/removeplayer <name>` | Remove a player |
| `/roster` | List tracked players |
| `/addprotected <name>` | Add a player to the protected list (immune to inactivity removal) |
| `/removeprotected <name>` | Remove a player from the protected list |
| `/listprotected` | List all protected players |
| `/setinactivedate <name> <days_ago>` | Set manual inactive date for a player (beyond 14-day API limit) |
| `/removeinactivedate <name>` | Remove manual inactive date for a player |
| `/clanstats` | Post aggregated stats right now |
| `/postnow` | Manually post today's digest to the current channel, on demand |
| `/leaderboard [sort_by]` | Roster ranked by kills/wins/damage |
| `/leaderboardstats [pages]` | Check the official PUBG leaderboard for roster placements (top ladder only — most players won't appear; default checks top 2000) |
| `/setleaderboardregion` | Platform/region shard the leaderboard check uses (default `pc-na`) |
| `/setleaderboardqueue` | squad / duo / solo — TPP queue for the leaderboard check |
| `/setgamemode <mode>` | squad-fpp, squad, duo-fpp, duo, solo-fpp, solo |
| `/setclan <member_name>` | Choose the clan through the exact PUBG name of one of its current members |
| `/clanlevel` | Show current clan level, member count, and weekly change |
| `/setclanchannel` | Set the channel for the weekly clan-level report |
| `/setclantime <day> <hour> [minute]` | Schedule the clan-level report once a week, Eastern time |
| `/help` | Get assistance and the official Discord support-server link |
| `/reportstatus` | Show enabled automatic reports, destination channels, schedules, and next run times |
| `/reporttoggle <report> <on/off>` | Administrator: turn a scheduled report on or off without clearing its settings |
| `/setstatuschannel` | Set this channel to show live bot status — updates only when something happens, never on a timer |
| `/donate` | Show the optional donation links (Ko-Fi and Buy Me a Coffee) |
| `/setdonationchannel` | Enable the optional weekly Sunday donation post in the current channel |
| `/setdonationtime <0-23>` | Choose the Sunday Eastern-time donation post time (defaults to noon) |
| `/setchannel` | Set current channel as the auto-post destination |
| `/setinterval <1-24>` | How often (hours) the digest auto-posts — ignored if `/setdigesttime` is set |
| `/setdigesttime <0-23>` | Post the digest once/day at a fixed Eastern-time hour instead |
| `/lastactive` | Show when each roster player last played, right now |
| `/setactivitychannel` | Set channel for the 24h "last active" report (defaults to digest channel) |
| `/setactivitytime <0-23>` | Fixed Eastern-time hour for the last-active report |
| `/rankedsquad`, `/rankedduo`, `/rankedsolo` | Show current-season ranked TPP standings for that queue |
| `/rankedsquadfpp`, `/rankedduofpp`, `/rankedsolofpp` | Show current-season ranked FPP standings for that queue |
| `/refreshrankedcache` | Make the next ranked check scan the full roster again |
| `/setrankedchannel` | Set channel for the daily ranked report (defaults to digest channel) |
| `/setrankedqueue <queue>` | Choose the single TPP or FPP queue used by the daily ranked report |
| `/setrankedtime <0-23>` | Fixed Eastern-time hour for the ranked report |
| `/dailyhighlights` | Show last-24h fun-title awards + top 10 + human/bot kills, right now |
| `/sethighlightschannel` | Set channel for the daily highlights report (defaults to digest channel) |
| `/sethighlightstime <0-23>` | Fixed Eastern-time hour for the highlights report |
| `/masterystats` | Each player's top weapon mastery + survival level (slow — 2 API calls per player) |
| `/linkme <pubg_name>` | Link your Discord account to a PUBG name (shows as a mention on `/leaderboardstats` results) |
| `/linkplayer <member> <pubg_name>` | Link another member's Discord account to a PUBG name on their behalf (open to anyone) |
| `/unlinkme <pubg_name>` | Remove a Discord-to-PUBG-name link |
| `/links` | Show every PUBG-name-to-Discord link currently set for this server |
| `/chickendinner` | Check the roster's most recent matches for wins right now |
| `/setchickendinnerchannel` | Set the channel for automatic Chicken Dinner win alerts (defaults to the digest channel; checks every 15 minutes) |
| `/pingtoggle <on/off>` | Toggle mention notifications for achievement awards in reports (default: on) |
| `/botservers [secret_key]` | **Admin/Owner**: List all servers the bot is in, member counts, and tracked player counts (ephemeral) |
| `/askfeedback [channel] [secret_key]` | **Admin/Owner**: Post an interactive feedback & suggestions prompt embed with a submission popup modal |

### Chicken Dinner win alerts

`/chickendinner` checks each roster player's most recent match right now
and reports anyone who won it. `/setchickendinnerchannel` opts a channel
into automatic alerts: every 15 minutes the bot re-checks the roster and
posts only *new* wins — it remembers the last match already alerted per
player, so the same win isn't reposted on every tick just because nobody
has queued up again yet. Toggle it on/off without losing the channel via
`/reporttoggle` → `Chicken Dinner Alerts`.

### Live bot status

`/setstatuschannel` points a channel at a single status message that the
bot keeps up to date by *editing it in place* — it never spams a new
message. Unlike every other report, it isn't on a timer: it only updates
when something actually happens —

- the bot connects, disconnects, or reconnects to Discord
- the bot is added to or removed from a server
- a scheduled report fails (PUBG API error or unexpected error)
- PUBG actually rate-limits the bot (a real 429, not the bot's own
  routine pacing, which happens constantly and isn't an issue)

The event log is in-memory and resets on restart — it's a live feed, not
a persisted audit trail. Bursts of events (e.g. several reports failing
within a few seconds of each other) collapse into a single edit rather
than triggering one edit per event.

### Player identity in reports

Reports never post a separate per-player message and never @mention or
ping anyone by default. Linking affects one thing: on `/leaderboardstats`, a
linked player's name is shown as a non-pinging `@mention` instead of the
plain PUBG name.

- `/linkme <pubg_name>` — link your own Discord account.
- `/linkplayer <member> <pubg_name>` — link someone else's account for
  them (open to anyone, e.g. a member who won't run the command
  themselves).
- `/unlinkme <pubg_name>` — remove a link (your own, or — for a server
  manager — anyone's).
- `/links` — list every current PUBG-name-to-Discord link for the server.
- `/pingtoggle <on/off>` — enable or disable mention notifications for achievement awards in reports (default: on). Avatar links still work regardless of this setting.

### Fixed-time scheduling (Eastern)

By default every auto-post uses an "every N hours since last post" model,
which drifts around depending on when you last restarted the bot. If you'd
rather everything post at a predictable, specific time — e.g. every report
at 9:15am Eastern — use the four `/set*time` commands above. They take an
hour (required) and an optional quarter-hour minute (:00/:15/:30/:45,
defaults to :00), and use the real `America/New_York` timezone, so they
automatically shift between EST and EDT with daylight saving, rather than
being off by an hour half the year. Setting a fixed time for a report
overrides its interval-based settings.

### Weekly clan-level report

Set the PUBG clan once with `/setclan <current clan member>`, choose the destination with
`/setclanchannel`, then use `/setclantime` to select a weekday and Eastern-time
hour. The report posts once per week and records the clan level and member-count
change since its previous successful scheduled post. PUBG does not provide the
XP remaining to the next clan level, so the weekly progress value is the actual
level change rather than an XP estimate.

### 14-Day Automatic Feedback & Modal System

Every 14 days, the bot automatically posts an interactive feedback prompt in every server's designated announcements/digest channel.
- Includes an interactive button: **`💬 Submit Feedback / Suggestions`**
- Clicking the button pops up a native Discord Modal form for users to enter their suggestions, questions, or bug reports.
- Upon submission, the bot forwards the feedback directly into your **Support Server** (`1539320166318481459`) with the user's name, Discord ID, and origin server information.
- You can also trigger this prompt manually at any time with `/askfeedback [channel]`.

### Admin & Owner Secret Commands

- **`/botservers [secret_key]`**: Lists all Discord servers the bot is currently in, total member reach, and number of tracked players per server.
- **`/askfeedback [channel] [secret_key]`**: Manually posts the interactive feedback prompt to any channel.

#### Access & Permissions:
- Both commands use `default_permissions(administrator=True)` to hide them from regular server members in Discord's slash command picker.
- Automatically accessible by the **Bot Application Owner**.
- Accessible by authorized users specified in `ADMIN_USER_IDS` or anyone with the `BOT_ADMIN_KEY` password in `.env`.

## Free 24/7 hosting — Oracle Cloud "Always Free" VM + PM2

This is the most reliable genuinely-free option that doesn't sleep, doesn't
expire, and doesn't require you to leave your own PC on.

1. Create a **VM.Standard.A1.Flex** (ARM) or **VM.Standard.E2.1.Micro** instance running **Ubuntu 24.04**.
2. Connect via SSH:
   ```bash
   ssh -i "path/to/private-key.key" ubuntu@YOUR_PUBLIC_IP
   ```
3. Install dependencies and PM2:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y python3 python3-pip python3-venv git npm
   sudo npm install -g pm2
   ```
4. Transfer bot files, configure `.env`, and start with PM2:
   ```bash
   cd ~/pubg-bot
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   nano .env
   # IMPORTANT: Before starting, enable Server Members Intent in Discord Developer Portal
   pm2 start bot.py --name "pubg-bot" --interpreter ./venv/bin/python3
   pm2 startup
   pm2 save
   ```

### Alternatives if Oracle account approval is being difficult
- **Railway** (railway.app) — gives free monthly credit; a bot this small
  typically costs a couple dollars/month in usage, so the free credit
  covers it until you add heavier services like a database
- **Fly.io** — free small VM allowance, needs a card on file
- Avoid random "100% free forever Discord bot hosting" sites that show up
  in search results — many are unreliable or ask for your bot token on an
  unvetted panel. Oracle/Railway/Fly are the trustworthy free-tier options.

## Notes on accuracy

- Stats are **lifetime**, per game mode (not per-season) unless you extend
  `pubg_api.py` to hit the season-specific endpoint.
- "Win rate" and K/D in the digest are computed from `roundsPlayed` and
  `wins`/`kills`, matching how the in-game stats screen defines them.
- If a name is misspelled or the player hasn't played that game mode, the
  bot flags it under "Not found" rather than silently skipping it.
- `/leaderboardstats` only checks the official ladder's top pages (default
  top 2000) — most rostered players won't have a high enough rank to show
  up there, that's expected, not a bug.
- `/masterystats` makes 2 PUBG API calls per player, so it's noticeably
  slower than the other on-demand commands, especially on a large roster.
- `/dailyhighlights` requires match telemetry data, which PUBG only keeps
  available for the last 14 days. If players haven't played in 15+ days,
  the bot will show a clear "No matches found in the last 14 days" message
  instead of a generic error.

## Daily Highlights Awards

The `/dailyhighlights` command includes fun achievement awards:

- 🌳 **Tactical Shrub** — Awarded to the player with the best placement
  in a single match with 0 kills (e.g., placed #5 with 0 kills)
- Other awards for top 10 placements, human vs bot kills, and achievement stats

**Note:** The "Tactical Shrub" award was previously known as "Bush Wookiee"
and has been renamed for a more tactical-sounding designation.
