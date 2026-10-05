"""
Regression tests for clan match participant dataset.

Tests the canonical participant dataset that enables chemistry analytics:
- /clanmatches
- /chemistry
- /bestduo
- /bestsquad

Critical invariant: match_id + team_id → actual teammates in that match
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from history import are_teammates


class TestClanParticipants(unittest.TestCase):
    """Test clan participant dataset and teammate identification."""

    def test_same_team_id_teammates(self):
        """Test same team_id → teammates."""
        participant_a = {
            "match_id": "match123",
            "player_id": "player1",
            "player_name": "Creighvan",
            "team_id": "team7",
            "placement": 1,
            "kills": 5,
        }
        participant_b = {
            "match_id": "match123",
            "player_id": "player2",
            "player_name": "Cipher617",
            "team_id": "team7",
            "placement": 1,
            "kills": 7,
        }

        result = are_teammates(participant_a, participant_b)
        self.assertTrue(result)

    def test_different_team_id_not_teammates(self):
        """Test different team_id → not teammates."""
        participant_a = {
            "match_id": "match123",
            "player_id": "player1",
            "player_name": "Creighvan",
            "team_id": "team7",
            "placement": 1,
            "kills": 5,
        }
        participant_b = {
            "match_id": "match123",
            "player_id": "player2",
            "player_name": "Cipher617",
            "team_id": "team8",
            "placement": 10,
            "kills": 3,
        }

        result = are_teammates(participant_a, participant_b)
        self.assertFalse(result)

    def test_same_match_different_teams_correctly_separated(self):
        """Test same match but different teams → correctly separated."""
        participant_a = {
            "match_id": "match123",
            "player_id": "player1",
            "player_name": "Creighvan",
            "team_id": "team7",
            "placement": 1,
            "kills": 5,
        }
        participant_b = {
            "match_id": "match123",
            "player_id": "player2",
            "player_name": "Cipher617",
            "team_id": "team8",
            "placement": 5,
            "kills": 4,
        }

        result = are_teammates(participant_a, participant_b)
        self.assertFalse(result)

    def test_different_match_not_teammates(self):
        """Test different match → not teammates."""
        participant_a = {
            "match_id": "match123",
            "player_id": "player1",
            "player_name": "Creighvan",
            "team_id": "team7",
            "placement": 1,
            "kills": 5,
        }
        participant_b = {
            "match_id": "match456",
            "player_id": "player2",
            "player_name": "Cipher617",
            "team_id": "team7",
            "placement": 1,
            "kills": 7,
        }

        result = are_teammates(participant_a, participant_b)
        self.assertFalse(result)

    def test_missing_team_id_not_teammates(self):
        """Test missing team_id → not teammates."""
        participant_a = {
            "match_id": "match123",
            "player_id": "player1",
            "player_name": "Creighvan",
            "team_id": None,
            "placement": 1,
            "kills": 5,
        }
        participant_b = {
            "match_id": "match123",
            "player_id": "player2",
            "player_name": "Cipher617",
            "team_id": "team7",
            "placement": 1,
            "kills": 7,
        }

        result = are_teammates(participant_a, participant_b)
        self.assertFalse(result)

    def test_invalid_team_id_not_teammates(self):
        """Test invalid team_id → not teammates."""
        participant_a = {
            "match_id": "match123",
            "player_id": "player1",
            "player_name": "Creighvan",
            "team_id": "",
            "placement": 1,
            "kills": 5,
        }
        participant_b = {
            "match_id": "match123",
            "player_id": "player2",
            "player_name": "Cipher617",
            "team_id": "team7",
            "placement": 1,
            "kills": 7,
        }

        result = are_teammates(participant_a, participant_b)
        self.assertFalse(result)

    def test_both_missing_team_id_not_teammates(self):
        """Test both missing team_id → not teammates."""
        participant_a = {
            "match_id": "match123",
            "player_id": "player1",
            "player_name": "Creighvan",
            "team_id": None,
            "placement": 1,
            "kills": 5,
        }
        participant_b = {
            "match_id": "match123",
            "player_id": "player2",
            "player_name": "Cipher617",
            "team_id": None,
            "placement": 1,
            "kills": 7,
        }

        result = are_teammates(participant_a, participant_b)
        self.assertFalse(result)

    def test_solo_match_no_false_teammates(self):
        """Test solo match doesn't manufacture teammates."""
        participant_a = {
            "match_id": "match123",
            "player_id": "player1",
            "player_name": "Creighvan",
            "team_id": "team1",  # Solo team
            "placement": 5,
            "kills": 3,
        }
        participant_b = {
            "match_id": "match123",
            "player_id": "player2",
            "player_name": "Cipher617",
            "team_id": "team2",  # Different solo team
            "placement": 15,
            "kills": 1,
        }

        result = are_teammates(participant_a, participant_b)
        self.assertFalse(result)

    def test_four_clan_members_together(self):
        """Test four clan members together correctly identified as teammates."""
        participants = [
            {
                "match_id": "match123",
                "player_id": "player1",
                "player_name": "Creighvan",
                "team_id": "team7",
                "placement": 1,
                "kills": 5,
            },
            {
                "match_id": "match123",
                "player_id": "player2",
                "player_name": "Cipher617",
                "team_id": "team7",
                "placement": 1,
                "kills": 7,
            },
            {
                "match_id": "match123",
                "player_id": "player3",
                "player_name": "Azimuth-360",
                "team_id": "team7",
                "placement": 1,
                "kills": 4,
            },
            {
                "match_id": "match123",
                "player_id": "player4",
                "player_name": "2dope_",
                "team_id": "team7",
                "placement": 1,
                "kills": 6,
            },
        ]

        # All should be teammates with each other
        for i in range(len(participants)):
            for j in range(i + 1, len(participants)):
                result = are_teammates(participants[i], participants[j])
                self.assertTrue(result, f"Participants {i} and {j} should be teammates")

    def test_multiple_clan_squads_independent(self):
        """Test multiple clan squads in same match handled independently."""
        squad_a = [
            {
                "match_id": "match123",
                "player_id": "player1",
                "player_name": "Creighvan",
                "team_id": "team7",
                "placement": 1,
                "kills": 5,
            },
            {
                "match_id": "match123",
                "player_id": "player2",
                "player_name": "Cipher617",
                "team_id": "team7",
                "placement": 1,
                "kills": 7,
            },
        ]
        squad_b = [
            {
                "match_id": "match123",
                "player_id": "player3",
                "player_name": "Azimuth-360",
                "team_id": "team8",
                "placement": 5,
                "kills": 4,
            },
            {
                "match_id": "match123",
                "player_id": "player4",
                "player_name": "2dope_",
                "team_id": "team8",
                "placement": 5,
                "kills": 6,
            },
        ]

        # Within each squad, should be teammates
        self.assertTrue(are_teammates(squad_a[0], squad_a[1]))
        self.assertTrue(are_teammates(squad_b[0], squad_b[1]))

        # Across squads, should NOT be teammates
        self.assertFalse(are_teammates(squad_a[0], squad_b[0]))
        self.assertFalse(are_teammates(squad_a[0], squad_b[1]))
        self.assertFalse(are_teammates(squad_a[1], squad_b[0]))
        self.assertFalse(are_teammates(squad_a[1], squad_b[1]))


if __name__ == "__main__":
    unittest.main()
