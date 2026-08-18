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
scopes, and permissions `Send Messages` + `Embed Links`, then use the
generated URL to invite the bot to your server
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
For instant testing, set `DEV_GUILD_ID` in your `.env` to your server's ID:
In Discord, enable Developer Mode: User Settings → Advanced → Developer Mode
Right-click your server icon → Copy Server ID
Add it to `.env`:
```
   DEV_GUILD_ID=123456789012345678
   ```
Restart the bot — commands appear in that server immediately. Other
servers the bot is in still get commands via the slower global sync.
If commands still don't show after that, fully close and reopen Discord
(not just refresh) — the client caches the command list locally.
Local setup (for testing)
```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and fill in DISCORD_TOKEN and PUBG_API_KEY
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
`/removeplayer <name>`	Remove a player
`/roster`	List tracked players
`/clanstats`	Post aggregated stats right now
`/leaderboard [sort_by]`	Roster ranked by kills/wins/damage
`/setgamemode <mode>`	squad-fpp, squad, duo-fpp, duo, solo-fpp, solo
`/setchannel`	Set current channel as the auto-post destination
`/setinterval <1-24>`	How often (hours) the digest auto-posts (default every 6 hours)
`/lastactive`	Show when each roster player last played, right now
`/setactivitychannel`	Set channel for the 24h "last active" report (defaults to digest channel)
`/rankedstats`	Show current-season ranked TPP standings, right now
`/setrankedchannel`	Set channel for the daily ranked TPP report (defaults to digest channel)
`/setrankedqueue <queue>`	squad / duo / solo — TPP ranked queue to track
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