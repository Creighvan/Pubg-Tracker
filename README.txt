PUBG Clan Tracker Discord Bot
Tracks a list of PUBG player names per Discord server, pulls their lifetime
stats from the official PUBG API, and posts an aggregated "clan report"
(kills, wins, win rate, top fraggers) — both on a daily schedule and on
demand via slash commands.

Important limitation (same one PUBGLooker deals with)
The official PUBG API has no clan-roster endpoint. There's no way to
ask it "give me everyone in clan X." So this bot works the way every PUBG
stat site does: you manually add player names to a roster with
`/addplayer`, and the bot looks each one up individually and aggregates
the results.

What you'll need (all free)
A Discord bot token — https://discord.com/developers/applications
New Application → Bot → Reset Token → copy it
Under "Privileged Gateway Intents" you don't need any extra intents for this bot
Under OAuth2 → URL Generator, check `bot` and `applications.commands`
scopes, and permissions `Send Messages`, `Embed Links`, and
`Manage Webhooks` (needed so reports can post under each linked player's
PUBG name and avatar), then use the generated URL to invite the bot to
your server
A PUBG API key — https://developer.pubg.com/
Sign in, create an app, copy the API key
Free tier = 10 requests/minute, which this bot respects automatically
Somewhere to run it 24/7 — see hosting options below

Slash commands not showing up in Discord?
Discord syncs slash commands two ways:
Global sync (what happens by default) can take up to an hour to
actually appear in the `/` menu on every server the bot is in. This is
normal Discord behavior, not a bug.
Guild-specific sync is instant, but only for that one server.

This bot does one or the other on every restart, never both — check your
.env for a DEV_GUILD_ID line before you go looking for a bug:
- DEV_GUILD_ID set -> commands sync instantly to that one server only.
  Every other server the bot is in gets no command updates at all, not
  just slower ones, for as long as that line stays in .env.
- DEV_GUILD_ID not set -> commands sync globally, taking up to ~1hr to
  show up everywhere, but every server gets them eventually.

For instant testing on your main server:
In Discord, enable Developer Mode: User Settings → Advanced → Developer Mode
Right-click your server icon → Copy Server ID
Add it to `.env`:
```
   DEV_GUILD_ID=123456789012345678
   ```
Restart the bot — commands appear in that server immediately.

Before you actually need new commands live on every server (a "release"):
remove the DEV_GUILD_ID line from .env and restart once — watch for
"Synced N commands globally" in bot_output.log to confirm it took the
global-push branch. Add DEV_GUILD_ID back afterward for your next round
of local testing.

If commands still don't show after that, fully close and reopen Discord
(not just refresh) — the client caches the command list locally.

Auto-Restart on Windows (recommended for always-on use)
Running `python bot.py` directly means the bot goes down for good if it
ever crashes, your PC sleeps, or you close the terminal. run_bot.bat
fixes the "crashes" part by looping forever and restarting the bot
automatically. Task Scheduler fixes the "PC restarts" part by launching
that loop automatically when you log in.

Step 1 — Test the supervisor script
Double-click run_bot.bat in E:\BotFolder (or run it from PowerShell).
A window opens and the bot starts as usual. Two new log files appear in
the folder:
- bot_supervisor.log — restart events, with timestamps
- bot_output.log — everything the bot itself prints (what used to only
  show in the terminal)

To confirm the auto-restart actually works, close the bot with Ctrl+C
inside that window — within 10 seconds you should see it start back up
on its own and log a new "Starting..." line.

Step 2 — Stop it for real
Since the loop restarts the bot on any exit, closing the window or
Ctrl+C alone won't fully stop it — the supervisor just brings it back.
Run stop_bot.bat when you actually want it down (e.g. before editing
bot.py). Note: this kills all python.exe processes on your PC, so
close any other Python programs' output first if that matters to you.

Step 3 — Run it automatically at logon
Open Task Scheduler (search for it in the Start menu)
Click Create Basic Task... (right panel)
Name: PUBG Clan Bot, click Next
Trigger: When I log on, click Next
Action: Start a program, click Next
Program/script: browse to E:\BotFolder\run_bot.bat
Click Next, then Finish
Find the new task in the main list, right-click → Properties
On the General tab, check Run with highest privileges (avoids
random permission issues)
On the Settings tab, make sure "If the task is already running,
the following rule applies" is set to "Do not start a new
instance" — this stops you from accidentally running two bots at
once if you also double-click run_bot.bat manually sometime
Click OK

From now on, logging into Windows automatically starts the bot, and any
crash mid-session gets auto-restarted within 10 seconds. To pause it
long-term, open Task Scheduler and Disable the task, or delete it.

Local setup (for testing)
```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and fill in DISCORD_TOKEN and PUBG_API_KEY
# (PUBG_SHARD defaults to "steam" and DEV_GUILD_ID is optional - see
# .env.example and the "Slash commands not showing up" section above)
python bot.py
```
Then in your Discord server:
```
/addplayer  <pubg name>      (repeat for each clan member)
/setchannel                  (run this in the channel you want digests posted to)
/setgamemode squad-fpp       (optional, this is already the default)
/clanstats                   (test it immediately)
```

Commands
Command	What it does
`/addplayer <name>`	Add a player to the roster
`/addplayers <names>`	Bulk-add players — paste names separated by commas or newlines
`/removeplayer <name>`	Remove a player
`/roster`	List tracked players
`/clanstats`	Post aggregated stats right now
`/postnow`	Manually post today's digest to the current channel, on demand
`/leaderboard [sort_by]`	Roster ranked by kills/wins/damage
`/leaderboardstats [pages]`	Check the official PUBG leaderboard for roster placements (top ladder only)
`/setleaderboardregion`	Platform/region shard the leaderboard check uses (default pc-na)
`/setleaderboardqueue`	squad / duo / solo — TPP queue for the leaderboard check
`/setgamemode <mode>`	squad-fpp, squad, duo-fpp, duo, solo-fpp, solo
`/setchannel`	Set current channel as the auto-post destination
`/setinterval <1-24>`	How often (hours) the digest auto-posts — ignored if /setdigesttime is set
`/setdigesttime <0-23>`	Post the digest once/day at a fixed Eastern-time hour instead
`/lastactive`	Show when each roster player last played, right now
`/setactivitychannel`	Set channel for the 24h "last active" report (defaults to digest channel)
`/setactivitytime <0-23>`	Fixed Eastern-time hour for the last-active report
`/rankedstats`	Show current-season ranked TPP standings, right now
`/setrankedchannel`	Set channel for the daily ranked TPP report (defaults to digest channel)
`/setrankedqueue <queue>`	squad / duo / solo — TPP ranked queue to track
`/setrankedtime <0-23>`	Fixed Eastern-time hour for the ranked report
`/dailyhighlights`	Show last-24h fun-title awards + top 10 + human/bot kills, right now
`/sethighlightschannel`	Set channel for the daily highlights report (defaults to digest channel)
`/sethighlightstime <0-23>`	Fixed Eastern-time hour for the highlights report
`/masterystats`	Each player's top weapon mastery + survival level (slow — 2 API calls per player)
`/unlinkme <pubg_name>`	Remove a Discord-to-PUBG-name link

Player identity in reports
Scheduled and on-demand reports show linked players through a channel
webhook, using their PUBG name and their linked Discord avatar. This
needs Manage Webhooks in the report channel, and never touches a
member's actual server nickname — it's a webhook-level display only.

There's currently no slash command that creates a link — that used to be
/linkme and /linkplayer, which also tried to rename members' server
nicknames to match. That didn't work reliably across the whole clan (it
depends on the bot's role sitting above every member's roles, which
doesn't hold in practice for anyone with an elevated/officer role), so
both commands were removed. /unlinkme still works, for clearing out any
links already on record.

Free 24/7 hosting — recommended: Oracle Cloud "Always Free" VM
This is the most reliable genuinely-free option that doesn't sleep, doesn't
expire, and doesn't require you to leave your own PC on. Everything below
is done in the cloud — nothing stays on your computer once it's deployed.
Sign up at https://www.oracle.com/cloud/free/ (a card is required for
identity verification, but the "Always Free" tier is not a trial and
doesn't get billed as long as you stay within the always-free shapes)
Create a VM.Standard.A1.Flex instance (ARM, free tier) running
Ubuntu
SSH into it, then:
```bash
   sudo apt update && sudo apt install -y python3-pip python3-venv git
   git clone <your-repo-or-upload-these-files>
   cd pubg-clan-bot
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   nano .env   # paste in your real tokens
   ```
Keep it running permanently with a systemd service:
```bash
   sudo tee /etc/systemd/system/pubgbot.service <<EOF
   [Unit]
   Description=PUBG Clan Discord Bot
   After=network.target

   [Service]
   WorkingDirectory=/home/ubuntu/pubg-clan-bot
   ExecStart=/home/ubuntu/pubg-clan-bot/venv/bin/python bot.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   EOF

   sudo systemctl daemon-reload
   sudo systemctl enable --now pubgbot
   sudo systemctl status pubgbot   # confirm it's running
   ```
The bot now survives reboots and restarts automatically if it crashes.

Alternatives if Oracle account approval is being difficult
Railway (railway.app) — gives free monthly credit; a bot this small
typically costs a couple dollars/month in usage, so the free credit
covers it until you add heavier services like a database
Fly.io — free small VM allowance, needs a card on file
Avoid random "100% free forever Discord bot hosting" sites that show up
in search results — many are unreliable or ask for your bot token on an
unvetted panel. Oracle/Railway/Fly are the trustworthy free-tier options.

Notes on accuracy
Stats are lifetime, per game mode (not per-season) unless you extend
`pubg_api.py` to hit the season-specific endpoint.
"Win rate" and K/D in the digest are computed from `roundsPlayed` and
`wins`/`kills`, matching how the in-game stats screen defines them.
If a name is misspelled or the player hasn't played that game mode, the
bot flags it under "Not found" rather than silently skipping it.
/leaderboardstats only checks the official ladder's top pages (default
top 2000) — most rostered players won't have a high enough rank to show
up there, that's expected, not a bug.
/masterystats makes 2 PUBG API calls per player, so it's noticeably
slower than the other on-demand commands, especially on a large roster.
