# PUBG Server Maintenance Detection Module

## Overview

This module automatically detects when PUBG game servers go into or come out of maintenance and posts notifications to configured Discord channels.

## How It Works

The module uses multiple signals with debounce logic to avoid false positives:

1. **Steam Player Count**: Monitors concurrent players via Steam API (app ID 578080)
   - Normal: 50,000+ players
   - Suspicious: 10,000-50,000 players
   - Maintenance: <10,000 players

2. **PUBG API Status**: Checks the `/status` endpoint
3. **PUBG API Data Calls**: Tests actual data retrieval (shards list)

### Debounce Logic

- **Maintenance declared**: After 3 consecutive failures (6 minutes)
- **Back online declared**: After 2 consecutive successes (4 minutes)

This prevents transient errors from triggering false maintenance alerts.

## Features

- ✅ Automatic maintenance detection every 2 minutes
- ✅ Discord embed notifications with timestamps
- ✅ Downtime duration calculation
- ✅ Automatic "back online" notifications
- ✅ Pauses scheduled reports during maintenance
- ✅ **Immediately runs all paused scheduled tasks when servers come back online**
- ✅ Per-guild channel configuration
- ✅ Multi-signal approach for reliability
- ✅ **Scheduled maintenance notices for advance warning**
- ✅ **Manual scheduling with `/schedulemaintenance` command**
- ✅ **Auto-scheduling for known maintenance events**
- ✅ **30-minute advance warning before scheduled maintenance**

## Setup

### 1. Set Maintenance Channel

Use the `/setmaintenancechannel` command in the Discord channel where you want actual maintenance status updates (when servers go down/up):

```
/setmaintenancechannel
```

This command requires `Manage Server` permissions.

### 2. Set Scheduled Maintenance Channel (Optional)

Use the `/setscheduledmaintenancechannel` command in the Discord channel where you want advance warning announcements for planned maintenance:

```
/setscheduledmaintenancechannel
```

This command requires `Manage Server` permissions.

**Channel Separation:**
- **Maintenance Channel**: For actual status updates (servers down/back online)
- **Scheduled Maintenance Channel**: For advance warnings (30 minutes before planned maintenance)

If you only set one channel, both types of notifications will go to that channel. If you set both, they will be separated appropriately.

### 2. Automatic Operation

Once the maintenance channel is set, the bot will automatically:
- Check server status every 2 minutes
- Post a red embed when maintenance is detected
- Post a green embed when servers come back online
- Show downtime duration in the back online notification
- Pause scheduled reports (digest, chicken dinner, etc.) during maintenance
- **Immediately run all paused scheduled tasks when servers come back online**

### 3. Scheduled Maintenance Notices

For planned maintenance windows, you can schedule advance notices:

**Manual Scheduling:**
```
/schedulemaintenance <date> <hour> <duration>
```
- `<date>`: Start date in YYYY-MM-DD format (UTC)
- `<hour>`: Start hour 0-23 (UTC)
- `<duration>`: Duration in hours (supports decimals, e.g., 8.5)

Example:
```
/schedulemaintenance 2026-10-14 0 8.5
```

This will:
- Post a yellow embed 30 minutes before the scheduled start time
- Show expected start/end times and duration
- Display the source (Manual or Auto-scheduled)
- Continue automatic detection to confirm actual maintenance

**Clear Scheduled Notice:**
```
/clearmaintenance
```

**Auto-Scheduling:**
The bot automatically schedules known maintenance events when running within 48 hours of the event. For example, the October 14, 2026 maintenance (00:00 UTC, 8.5 hours) will be auto-scheduled if the bot is running between October 12 and October 14.

## Notification Examples

### Scheduled Maintenance (30-minute warning)

```
📅 Scheduled PUBG Server Maintenance
PUBG servers will undergo maintenance starting soon.

Start Time: 2026-10-14 00:00:00 UTC
Expected End: 2026-10-14 08:30:00 UTC
Duration: 8.5 hours
Source: Auto-scheduled (Oct 14)
Status: ⏳ Scheduled
```

### Maintenance Started

```
⚠️ PUBG Servers Under Maintenance
PUBG game servers are currently under maintenance. Scheduled reports are paused.

Steam Players: 8,234
Status: 🔴 Maintenance
Scheduled Reports: ⏸️ Paused
```

### Back Online

```
✅ PUBG Servers Back Online
PUBG game servers are back online. Running all paused scheduled reports now.

Steam Players: 326,004
Status: 🟢 Online
Downtime: 2h 15m
Scheduled Reports: ▶️ Running now
```

## Configuration

The module stores the maintenance channel ID per guild in the database:

```json
{
  "maintenance_channel_id": 123456789012345678
}
```

## Integration with Scheduler

The maintenance module integrates with the existing scheduler to pause operations:

- `auto_digest` - Skipped during maintenance
- `auto_chicken_dinner` - Skipped during maintenance
- Other scheduled tasks - Can be extended similarly

## Technical Details

### Check Interval
- Every 2 minutes (120 seconds)

### Failure Threshold
- 3 consecutive failures before declaring maintenance

### Success Threshold
- 2 consecutive successes before declaring back online

### Player Count Thresholds
- `NORMAL_PLAYER_COUNT_MIN`: 50,000
- `MAINTENANCE_PLAYER_COUNT_MAX`: 10,000

### State Management

Global state dictionary tracks:
- `is_maintenance`: Current maintenance status
- `down_since`: Timestamp when maintenance started
- `consecutive_failures`: Current failure count
- `consecutive_successes`: Current success count
- `last_check`: Timestamp of last check

## API Dependencies

- **Steam API**: Public endpoint, no API key required
- **PUBG API**: Uses existing `pubg_api.py` client
- **aiohttp**: For HTTP requests

## Troubleshooting

### Notifications Not Appearing

1. Check that `/setmaintenancechannel` has been run
2. Verify the bot has permission to send messages in that channel
3. Check PM2 logs for errors: `pm2 logs pubg-bot --lines 100`

### False Maintenance Alerts

The debounce logic (3 consecutive failures) should prevent false positives. If you're still seeing them:

1. Check the logs: `[maintenance] Check: steam=X, api_status=X, api_data=X, is_down=X`
2. Adjust thresholds in `modules/maintenance.py`:
   - `FAILURE_THRESHOLD` (default: 3)
   - `SUCCESS_THRESHOLD` (default: 2)
   - `NORMAL_PLAYER_COUNT_MIN` (default: 50000)
   - `MAINTENANCE_PLAYER_COUNT_MAX` (default: 10000)

### Module Not Starting

Check `bot.py` on_ready event logs:
```
[on_ready] Maintenance monitoring started
```

If missing, check for import errors in the logs.

## Future Enhancements

Potential improvements:
- Steam news integration for advance warning of scheduled maintenance
- Console server detection (currently PC-only)
- Per-platform status monitoring
- Customizable thresholds per guild
- Maintenance prediction based on patterns

## Files Modified

- `modules/maintenance.py` - New module
- `commands/settings.py` - Added `setmaintenancechannel_impl`
- `bot.py` - Added command import and startup integration
- `modules/scheduler.py` - Added maintenance checks to scheduled tasks
