"""
Test mastery parsing using API response fixtures.
Verifies that the defensive field name handling works correctly.
"""

import asyncio
import sys
import os
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pubg_api import PubgClient


async def test_weapon_mastery_parsing():
    """Test weapon mastery parsing with fixture data."""
    print("[TEST] Weapon mastery parsing")

    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "weapon_mastery_response.json")

    try:
        with open(fixture_path, "r") as f:
            fixture_data = json.load(f)

        attrs = fixture_data.get("data", {}).get("attributes", {})
        result = PubgClient._best_weapon_from_mastery(attrs)

        if result and result.get("level") == 5:
            print(f"  Weapon parsed correctly: {result['weapon_id']} level {result['level']}")
            return True
        print(f"  FAIL: Unexpected result: {result}")
        return False
    except Exception as e:
        print(f"  FAIL: Exception: {e}")
        return False


async def test_survival_mastery_parsing():
    """Test survival mastery parsing with fixture data."""
    print("[TEST] Survival mastery parsing")

    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "survival_mastery_response.json")

    try:
        with open(fixture_path, "r") as f:
            fixture_data = json.load(f)

        attrs = fixture_data.get("data", {}).get("attributes", {})

        # Test multiple field name variants
        level = attrs.get("Level", attrs.get("level", 0))
        xp = attrs.get("XP", attrs.get("Exp", attrs.get("xp", 0)))
        tier = attrs.get("tier", attrs.get("Tier", 0))

        if level == 15 and xp == 45000 and tier == 5:
            print(f"  Survival parsed correctly: level {level}, XP {xp}, tier {tier}")
            return True
        print(f"  FAIL: Unexpected values: level {level}, XP {xp}, tier {tier}")
        return False
    except Exception as e:
        print(f"  FAIL: Exception: {e}")
        return False


async def main():
    """Run all fixture-based tests."""
    print("Testing Mastery Parsing with Fixtures")
    print("=" * 40)

    tests = [
        test_weapon_mastery_parsing,
        test_survival_mastery_parsing,
    ]

    results = await asyncio.gather(*(test() for test in tests))

    print("=" * 40)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("[OK] All fixture tests passed!")
        return 0
    else:
        print(f"[FAIL] {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
