"""
Simple test for the historical data storage system.
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import history


async def test_basic_operations():
    """Test basic history operations."""
    print("[TEST] Basic history operations")

    guild_id = 999999999  # Use a different guild ID to avoid conflicts
    date = "2026-10-05"

    player_stats = {
        "testplayer": {
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

    try:
        # Test recording
        await history.record_daily_snapshot(guild_id, date, player_stats)
        print("  [OK] Snapshot recorded")

        # Test retrieval
        snapshots = await history.get_player_snapshots(guild_id, "testplayer", days=30)
        if len(snapshots) > 0:
            print(f"  [OK] Retrieved {len(snapshots)} snapshot(s)")
            return True
        else:
            print("  [FAIL] No snapshots retrieved")
            return False
    except Exception as e:
        print(f"  [FAIL] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run simple history test."""
    print("Testing Historical Data Storage (Simple)")
    print("=" * 40)

    result = await test_basic_operations()

    print("=" * 40)
    if result:
        print("[OK] History module works!")
        return 0
    else:
        print("[FAIL] History module test failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
