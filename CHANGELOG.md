# Changelog

All notable changes to the PUBG Clan Tracker Bot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Automatic PUBG server maintenance detection module
  - Monitors Steam player count and PUBG API status
  - Debounce logic to prevent false positives (3 failures to declare maintenance, 2 successes to recover)
  - Discord embed notifications for maintenance start/end
  - Automatic pausing of scheduled reports during maintenance
  - Immediate execution of paused tasks when servers come back online
  - `/setmaintenancechannel` command to configure notification channel
- Maintenance recovery system
  - Tracks which scheduled tasks were skipped during maintenance
  - Automatically triggers skipped tasks (digest, chicken dinner) when servers recover
  - No waiting for next scheduled interval
- Comprehensive documentation
  - MAINTENANCE-MODULE.md - Complete maintenance detection guide
  - CONTRIBUTING.md - Development and contribution guidelines
  - CHANGELOG.md - This changelog file

### Fixed
- Maintenance module API method calls
  - Changed `get_status()` to `get_api_status()` (correct method in pubg_api.py)
  - Changed `get_shards()` to `get_players_by_name()` (exists in pubg_api.py)
  - Fixed import statement for PubgApiError
- Database corruption handling
  - Added `/resetcorruption` admin command to reset corruption flag
  - Fixed double-response error in `/resetcorruption` command
  - Authorization handling now properly uses follow-up instead of defer after response
- Analytics command error handling
  - Added comprehensive error handling to `/playertrend` and `/compare`
  - Now shows specific error messages instead of generic error codes
- Invalid snapshot data
  - Fixed percentage calculations for rate-based stats (win_rate, K/D)
  - Filtered invalid snapshots from trend calculations
  - Fixed snapshot migration function to be synchronous
  - Auto-deleted invalid snapshots with no valid data
- Discord interaction timeouts
  - Added defer handling to all 78 command implementations
  - Graceful handling of expired interactions
  - All commands now use followup.send() after defer
- Scheduler startup
  - Command sync errors no longer prevent scheduled tasks from starting
  - Chicken Dinner task now starts reliably on bot startup
  - Added comprehensive logging to scheduler for debugging

### Changed
- Fixed schedule times (non-configurable)
  - Ranked report: fixed at 04:30 UTC
  - Highlights report: fixed at 02:00 UTC
  - Removed deprecated `/sethighlightstime` command
- Updated README.md
  - Added maintenance detection feature description
  - Added `/setmaintenancechannel` to command list
  - Added maintenance detection section with examples

## [1.0.0] - 2026-10-05

### Added
- Historical data layer with 90-day daily snapshots
- Match history with participant tracking
- Player analytics (profiles, trends, comparisons, season summaries)
- Clan analytics (clan trends, roster health, map analytics)
- Team intelligence (chemistry analysis, team relationships)
- Achievement system with automatic detection
- Streak tracking system
- Weekly clan awards command
- Weapon analytics command
- Map analytics command
- Squad chemistry commands
- Rank progression tracking
- Inactivity tracking with auto-counting beyond 14 days
- Manual inactive date override
- Protected player list system
- Audit logging (central admin server)
- Scheduled reports (digest, highlights, ranked, chicken dinner)
- 10-language support (English, Chinese, Hindi, Spanish, Arabic, French, Bengali, Portuguese, Indonesian, Urdu)
- Discord slash commands for all features
- PM2 deployment support
- Oracle Cloud hosting guide

### Security
- Terms of Service
- Privacy Policy
- Secure environment variable handling
- Admin-only commands with authorization checks

## [0.9.0] - 2026-09-15

### Added
- Basic roster tracking
- Clan statistics
- Leaderboard
- Inactivity tracking
- Daily digest reports
- Survival mastery reports
- Ranked standings
- Chicken dinner alerts
- Discord bot integration

### Known Issues
- No historical data
- No trend analysis
- No team chemistry
- Limited inactivity tracking (14-day API limit)
