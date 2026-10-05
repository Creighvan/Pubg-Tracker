"""
Test the historical data storage system.
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import history


async def test_daily_snapshot():
    """Test recording and retrieving daily snapshots."""
    print("[TEST] Daily snapshot recording")

    guild_id = 123456789
    date = "2026-10-05"

    player_stats = {
        "testplayer1": {
            "matches": 100,
            "wins": 10,
            "kills": 250,
            "deaths": 100,
            "damage": 50000,
            "top10": 40,
            "win_rate": 10.0,
            "kd": 2.5,
            "avg_placement": 12.5,
        },
        "testplayer2": {
            "matches": 50,
            "wins": 5,
            "kills": 120,
            "deaths": 50,
            "damage": 25000,
            "top10": 20,
            "win_rate": 10.0,
            "kd": 2.4,
            "avg_placement": 13.0,
        },
    }

    try:
        await history.record_daily_snapshot(guild_id, date, player_stats)
        print("  Snapshot recorded successfully")

        # Retrieve snapshots
        snapshots = await history.get_player_snapshots(guild_id, "testplayer1", days=30)
        if len(snapshots) == 1 and snapshots[0]["date"] == date:
            print(f"  Retrieved 1 snapshot for testplayer1: {snapshots[0]['stats']['kills']} kills")
            return True
        else:
            print(f"  FAIL: Expected 1 snapshot, got {len(snapshots)}")
            return False
    except Exception as e:
        print(f"  FAIL: Exception: {e}")
        return False


async def test_trend_calculation():
    """Test trend calculation for a player."""
    print("[TEST] Trend calculation")

    guild_id = 123456789

    # Record two snapshots
    date1 = "2026-10-01"
    date2 = "2026-10-05"

    player_stats1 = {
        "testplayer1": {
            "matches": 100,
            "wins": 10,
            "kills": 250,
            "deaths": 100,
            "damage": 50000,
            "top10": 40,
            "win_rate": 10.0,
            "kd": 2.5,
            "avg_placement": 12.5,
        },
    }

    player_stats2 = {
        "testplayer1": {
            "matches": 150,
            "wins": 20,
            "kills": 400,
            "deaths": 150,
            "damage": 80000,
            "top10": 60,
            "win_rate": 13.33,
            "kd": 2.67,
            "avg_placement": 10.0,
        },
    }

    try:
        await history.record_daily_snapshot(guild_id, date1, player_stats1)
        await history.record_daily_snapshot(guild_id, date2, player_stats2)

        # Calculate trend
        trend = await history.calculate_trend(guild_id, "testplayer1", days=10)

        if "error" in trend:
            print(f"  FAIL: Trend calculation returned error: {trend['error']}")
            return False

        delta = trend["delta"]
        if delta["kills"] == 150 and delta["wins"] == 10:
            print(f"  Trend calculated correctly: +{delta['kills']} kills, +{delta['wins']} wins")
            print(f"  K/D change: {trend['percent_change']['kd']:.1f}%")
            return True
        else:
            print(f"  FAIL: Unexpected delta: {delta}")
            return False
    except Exception as e:
        print(f"  FAIL: Exception: {e}")
        return False


async def test_match_recording():
    """Test recording and retrieving match history."""
    print("[TEST] Match history recording")

    guild_id = 123456789

    match_data = {
        "match_id": "test-match-123",
        "date": "2026-10-05",
        "timestamp": "2026-10-05T12:00:00Z",
        "map": "Erangel",
        "game_mode": "squad-fpp",
        "participants": ["testplayer1", "testplayer2"],
        "outside_teammates": ["randomplayer"],
        "is_win": True,
        "placement": 1,
        "total_kills": 15,
        "total_damage": 2500,
    }

    try:
        await history.record_match(
            guild_id,
            match_data["match_id"],
            match_data["date"],
            match_data["timestamp"],
            match_data["map"],
            match_data["game_mode"],
            match_data["participants"],
            match_data["outside_teammates"],
            match_data["is_win"],
            match_data["placement"],
            match_data["total_kills"],
            match_data["total_damage"],
        )
        print("  Match recorded successfully")

        # Retrieve matches
        matches = await history.get_guild_matches(guild_id, days=7)
        if len(matches) == 1 and matches[0]["match_id"] == "test-match-123":
            print(f"  Retrieved 1 match: {matches[0]['total_kills']} kills, {'WIN' if matches[0]['is_win'] else 'LOSS'}")
            return True
        else:
            print(f"  FAIL: Expected 1 match, got {len(matches)}")
            return False
    except Exception as e:
        print(f"  FAIL: Exception: {e}")
        return False


async def main():
    """Run all history tests."""
    print("Testing Historical Data Storage")
    print("=" * 40)

    tests = [
        test_daily_snapshot,
        test_trend_calculation,
        test_match_recording,
    ]

    results = await asyncio.gather(*(test() for test in tests))

    print("=" * 40)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("[OK] All history tests passed!")
        return 0
    else:
        print(f"[FAIL] {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
