"""
Regression tests for ranked progression and historical data integrity.
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from history import calculate_rank_progression


class TestRankedProgression(unittest.TestCase):
    """Test rank progression calculation with various edge cases."""

    def test_same_season_valid_rp(self):
        """Test normal progression within the same season."""
        previous = {
            "ranked_points": 2910,
            "ranked_tier": "Diamond III",
            "season_id": "season.2024.01",
            "ranked_status": "ok"
        }
        current = {
            "ranked_points": 3421,
            "ranked_tier": "Diamond II",
            "season_id": "season.2024.01",
            "ranked_status": "ok"
        }

        result = calculate_rank_progression(previous, current)

        self.assertEqual(result["status"], "delta")
        self.assertEqual(result["point_change"], 511)
        self.assertEqual(result["previous_points"], 2910)
        self.assertEqual(result["current_points"], 3421)
        self.assertEqual(result["previous_tier"], "Diamond III")
        self.assertEqual(result["current_tier"], "Diamond II")

    def test_season_reset(self):
        """Test season transition doesn't show false negative progression."""
        previous = {
            "ranked_points": 4800,
            "ranked_tier": "Conqueror",
            "season_id": "season.2023.20",
            "ranked_status": "ok"
        }
        current = {
            "ranked_points": 1200,
            "ranked_tier": "Diamond II",
            "season_id": "season.2024.01",
            "ranked_status": "ok"
        }

        result = calculate_rank_progression(previous, current)

        self.assertEqual(result["status"], "season_reset")
        self.assertEqual(result["previous_season"], "season.2023.20")
        self.assertEqual(result["current_season"], "season.2024.01")
        # Should NOT calculate negative delta
        self.assertNotIn("point_change", result)

    def test_missing_previous_data(self):
        """Test missing previous snapshot data."""
        previous = {
            "ranked_points": None,
            "ranked_tier": None,
            "season_id": None,
            "ranked_status": "no_data"
        }
        current = {
            "ranked_points": 3421,
            "ranked_tier": "Diamond II",
            "season_id": "season.2024.01",
            "ranked_status": "ok"
        }

        result = calculate_rank_progression(previous, current)

        self.assertEqual(result["status"], "insufficient_history")
        self.assertIn("missing ranked data", result["reason"])

    def test_missing_current_data(self):
        """Test missing current snapshot data."""
        previous = {
            "ranked_points": 2910,
            "ranked_tier": "Diamond III",
            "season_id": "season.2024.01",
            "ranked_status": "ok"
        }
        current = {
            "ranked_points": None,
            "ranked_tier": None,
            "season_id": "season.2024.01",
            "ranked_status": "no_data"
        }

        result = calculate_rank_progression(previous, current)

        self.assertEqual(result["status"], "insufficient_history")
        self.assertIn("missing ranked data", result["reason"])

    def test_api_error_current(self):
        """Test API error on current snapshot."""
        previous = {
            "ranked_points": 2910,
            "ranked_tier": "Diamond III",
            "season_id": "season.2024.01",
            "ranked_status": "ok"
        }
        current = {
            "ranked_points": None,
            "ranked_tier": None,
            "season_id": "season.2024.01",
            "ranked_status": "error"
        }

        result = calculate_rank_progression(previous, current)

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("API error", result["reason"])

    def test_api_error_previous(self):
        """Test API error on previous snapshot."""
        previous = {
            "ranked_points": None,
            "ranked_tier": None,
            "season_id": "season.2024.01",
            "ranked_status": "error"
        }
        current = {
            "ranked_points": 3421,
            "ranked_tier": "Diamond II",
            "season_id": "season.2024.01",
            "ranked_status": "ok"
        }

        result = calculate_rank_progression(previous, current)

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("API error", result["reason"])

    def test_tier_change_same_season(self):
        """Test tier change still calculates progression."""
        previous = {
            "ranked_points": 2910,
            "ranked_tier": "Diamond III",
            "season_id": "season.2024.01",
            "ranked_status": "ok"
        }
        current = {
            "ranked_points": 3421,
            "ranked_tier": "Diamond II",
            "season_id": "season.2024.01",
            "ranked_status": "ok"
        }

        result = calculate_rank_progression(previous, current)

        self.assertEqual(result["status"], "delta")
        self.assertEqual(result["point_change"], 511)
        self.assertEqual(result["previous_tier"], "Diamond III")
        self.assertEqual(result["current_tier"], "Diamond II")

    def test_zero_rp_legitimate(self):
        """Test legitimate 0 RP is handled correctly."""
        previous = {
            "ranked_points": 0,
            "ranked_tier": "Unranked",
            "season_id": "season.2024.01",
            "ranked_status": "ok"
        }
        current = {
            "ranked_points": 100,
            "ranked_tier": "Bronze",
            "season_id": "season.2024.01",
            "ranked_status": "ok"
        }

        result = calculate_rank_progression(previous, current)

        self.assertEqual(result["status"], "delta")
        self.assertEqual(result["point_change"], 100)

    def test_no_change(self):
        """Test no change in RP."""
        previous = {
            "ranked_points": 3000,
            "ranked_tier": "Diamond III",
            "season_id": "season.2024.01",
            "ranked_status": "ok"
        }
        current = {
            "ranked_points": 3000,
            "ranked_tier": "Diamond III",
            "season_id": "season.2024.01",
            "ranked_status": "ok"
        }

        result = calculate_rank_progression(previous, current)

        self.assertEqual(result["status"], "delta")
        self.assertEqual(result["point_change"], 0)


if __name__ == "__main__":
    unittest.main()
