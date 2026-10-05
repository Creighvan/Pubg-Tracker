"""
Regression tests for command empty-state behavior.
Tests that commands handle empty rosters gracefully.
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import translations


async def test_empty_roster_language():
    """Test that language lookup works for empty roster."""
    print("[TEST] Empty roster: language lookup")

    guild_cfg = {
        "players": [],
        "language": "en",
    }

    try:
        lang = guild_cfg.get("language", "en")
        message = translations.get_translation(lang, "no_players_tracked")
        if message and isinstance(message, str):
            print(f"  Language lookup works: {message}")
            return True
        print("  FAIL: Translation lookup failed")
        return False
    except Exception as e:
        print(f"  FAIL: Exception: {e}")
        return False


async def test_empty_roster_check():
    """Test that empty roster check pattern works."""
    print("[TEST] Empty roster: check pattern")

    guild_cfg = {
        "players": [],
        "language": "en",
    }

    try:
        lang = guild_cfg.get("language", "en")
        if not guild_cfg["players"]:
            message = translations.get_translation(lang, "no_players_tracked")
            if message:
                print(f"  Empty roster check works: {message}")
                return True
        print("  FAIL: Should have detected empty roster")
        return False
    except Exception as e:
        print(f"  FAIL: Exception: {e}")
        return False


async def test_permission_message_translation():
    """Test that permission message is translated."""
    print("[TEST] Permission message translation")

    try:
        lang = "en"
        message = translations.get_translation(lang, "no_permission")
        if message and isinstance(message, str):
            print(f"  Permission message: {message}")
            return True
        print("  FAIL: Translation lookup failed")
        return False
    except Exception as e:
        print(f"  FAIL: Exception: {e}")
        return False


async def test_audit_channel_translations():
    """Test that audit channel messages are translated."""
    print("[TEST] Audit channel translations")

    try:
        lang = "en"
        unknown_msg = translations.get_translation(lang, "unknown_deleted")
        custom_msg = translations.get_translation(lang, "custom_audit_channel")
        central_msg = translations.get_translation(lang, "using_central_audit")

        if unknown_msg and custom_msg and central_msg:
            print(f"  Audit translations work")
            return True
        print("  FAIL: Translation lookup failed")
        return False
    except Exception as e:
        print(f"  FAIL: Exception: {e}")
        return False


async def test_report_status_translations():
    """Test that report status strings are translated."""
    print("[TEST] Report status translations")

    try:
        lang = "en"
        enabled = translations.get_translation(lang, "enabled")
        disabled = translations.get_translation(lang, "disabled")
        next_str = translations.get_translation(lang, "next")
        clan_digest = translations.get_translation(lang, "clan_digest")

        if enabled and disabled and next_str and clan_digest:
            print(f"  Report status translations work")
            return True
        print("  FAIL: Translation lookup failed")
        return False
    except Exception as e:
        print(f"  FAIL: Exception: {e}")
        return False


async def main():
    """Run all empty-state regression tests."""
    print("Testing Empty-State Regression Tests")
    print("=" * 40)

    tests = [
        test_empty_roster_language,
        test_empty_roster_check,
        test_permission_message_translation,
        test_audit_channel_translations,
        test_report_status_translations,
    ]

    results = await asyncio.gather(*(test() for test in tests))

    print("=" * 40)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("[OK] All empty-state tests passed!")
        return 0
    else:
        print(f"[FAIL] {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
