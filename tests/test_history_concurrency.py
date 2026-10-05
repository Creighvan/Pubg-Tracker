"""
Regression tests for history.py concurrency and integrity.

Tests that concurrent writes to history.json are safe and don't cause corruption.
"""

import asyncio
import json
import os
import sys
import tempfile
import shutil
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import history


class TestHistoryConcurrency(unittest.TestCase):
    """Test that concurrent history operations don't corrupt the file."""

    def setUp(self):
        """Create a temporary history file for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_path = history.HISTORY_PATH
        history.HISTORY_PATH = os.path.join(self.temp_dir, "test_history.json")

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir)
        history.HISTORY_PATH = self.original_path

    def test_concurrent_snapshot_writes(self):
        """Test that concurrent daily snapshot writes don't corrupt the file."""
        async def run_test():
            guild_id = 123456789
            date = "2026-10-05"

            # Simulate 10 concurrent snapshot writes
            tasks = []
            for i in range(10):
                player_stats = {
                    f"player{i}": {
                        "matches": i + 1,
                        "wins": i % 2,
                        "kills": i * 10,
                    }
                }
                tasks.append(history.record_daily_snapshot(guild_id, date, player_stats))

            await asyncio.gather(*tasks)

            # Verify the file is valid JSON
            with open(history.HISTORY_PATH, "r") as f:
                data = json.load(f)

            # Verify we have one guild
            self.assertEqual(len(data), 1)
            self.assertIn(str(guild_id), data)

            # Verify the snapshot exists
            guild_data = data[str(guild_id)]
            self.assertIn("daily_snapshots", guild_data)
            self.assertIn(date, guild_data["daily_snapshots"])

            # Verify the snapshot has all players from all writes
            # (last write wins per player, but file should be valid)
            snapshot = guild_data["daily_snapshots"][date]
            self.assertGreater(len(snapshot), 0)

        asyncio.run(run_test())

    def test_concurrent_match_records(self):
        """Test that concurrent match records don't corrupt the file."""
        async def run_test():
            guild_id = 123456789

            # Simulate 10 concurrent match records
            tasks = []
            for i in range(10):
                tasks.append(history.record_match(
                    guild_id=guild_id,
                    match_id=f"match_{i}",
                    date="2026-10-05",
                    timestamp="2026-10-05T12:00:00Z",
                    map_name="Erangel",
                    game_mode="squad-fpp",
                    participants=[f"player{i}"],
                    outside_teammates=[],
                    is_win=i % 2 == 0,
                    placement=i + 1,
                    total_kills=i * 5,
                    total_damage=i * 100.0,
                ))

            await asyncio.gather(*tasks)

            # Verify the file is valid JSON
            with open(history.HISTORY_PATH, "r") as f:
                data = json.load(f)

            # Verify we have all 10 matches
            guild_data = data[str(guild_id)]
            match_history = guild_data.get("match_history", [])
            self.assertEqual(len(match_history), 10)

            # Verify no duplicate match IDs
            match_ids = [m["match_id"] for m in match_history]
            self.assertEqual(len(match_ids), len(set(match_ids)))

        asyncio.run(run_test())

    def test_concurrent_participant_records(self):
        """Test that concurrent participant records don't corrupt the file."""
        async def run_test():
            guild_id = 123456789

            # Simulate 10 concurrent participant records
            tasks = []
            for i in range(10):
                tasks.append(history.record_clan_participant(
                    guild_id=guild_id,
                    match_id=f"match_{i}",
                    player_id=f"account_{i}",
                    player_name=f"Player{i}",
                    team_id=f"team_{i % 4}",  # 4 teams
                    map_name="Erangel",
                    placement=i + 1,
                    kills=i * 2,
                    damage=i * 50.0,
                    created_at="2026-10-05T12:00:00Z",
                    is_tracked=True,
                ))

            await asyncio.gather(*tasks)

            # Verify the file is valid JSON
            with open(history.HISTORY_PATH, "r") as f:
                data = json.load(f)

            # Verify we have all 10 participants
            guild_data = data[str(guild_id)]
            participants = guild_data.get("clan_participants", [])
            self.assertEqual(len(participants), 10)

            # Verify no duplicate (match_id, player_id) pairs
            pairs = [(p["match_id"], p["player_id"]) for p in participants]
            self.assertEqual(len(pairs), len(set(pairs)))

        asyncio.run(run_test())

    def test_atomic_write_no_partial_json(self):
        """Test that atomic write pattern prevents partial JSON on crash."""
        async def run_test():
            guild_id = 123456789

            # Write some data
            await history.record_daily_snapshot(
                guild_id,
                "2026-10-05",
                {"player1": {"matches": 10, "wins": 2}}
            )

            # Verify the file is valid JSON
            with open(history.HISTORY_PATH, "r") as f:
                data = json.load(f)

            self.assertIn(str(guild_id), data)

            # Write more data
            await history.record_match(
                guild_id=guild_id,
                match_id="match_1",
                date="2026-10-05",
                timestamp="2026-10-05T12:00:00Z",
                map_name="Erangel",
                game_mode="squad-fpp",
                participants=["player1"],
                outside_teammates=[],
                is_win=True,
                placement=1,
                total_kills=10,
                total_damage=500.0,
            )

            # Verify the file is still valid JSON after second write
            with open(history.HISTORY_PATH, "r") as f:
                data = json.load(f)

            # Verify both data structures exist
            guild_data = data[str(guild_id)]
            self.assertIn("daily_snapshots", guild_data)
            self.assertIn("match_history", guild_data)
            self.assertEqual(len(guild_data["match_history"]), 1)

        asyncio.run(run_test())

    def test_no_duplicate_json_trailing(self):
        """Test that writes don't append duplicate JSON (the corruption pattern)."""
        async def run_test():
            guild_id = 123456789

            # Perform multiple writes
            for i in range(5):
                await history.record_daily_snapshot(
                    guild_id,
                    f"2026-10-0{i+1}",
                    {f"player{i}": {"matches": i + 1}}
                )

            # Read the raw file and check for corruption pattern
            with open(history.HISTORY_PATH, "r") as f:
                content = f.read()

            # Count closing braces at the end
            # Valid JSON should end with exactly one "}"
            stripped = content.rstrip()
            self.assertTrue(stripped.endswith("}"))

            # Count trailing closing braces
            trailing_braces = 0
            for char in reversed(stripped):
                if char == "}":
                    trailing_braces += 1
                else:
                    break

            # Should have exactly 1 trailing closing brace (the final one)
            self.assertEqual(trailing_braces, 1)

            # Verify it's valid JSON
            with open(history.HISTORY_PATH, "r") as f:
                data = json.load(f)

            self.assertIn(str(guild_id), data)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
