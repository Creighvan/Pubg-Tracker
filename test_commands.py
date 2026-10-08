#!/usr/bin/env python3
"""
Comprehensive command test script for PUBG Tracker bot.
Tests all command implementations for syntax, imports, and basic structure.
"""

import sys
import os
import importlib
import inspect
import asyncio
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("PUBG Tracker Bot - Command Verification Test")
print("=" * 70)

# Expected command implementations
EXPECTED_COMMANDS = {
    "commands.roster": [
        "addplayer_impl",
        "addplayers_impl",
        "removeplayer_impl",
        "roster_impl",
    ],
    "commands.protected": [
        "addprotected_impl",
        "addprotectedbulk_impl",
        "removeprotected_impl",
        "listprotected_impl",
        "cleanprotected_impl",
        "resetprotected_impl",
    ],
    "commands.settings": [
        "setgamemode_impl",
        "setchannel_impl",
        "setinterval_impl",
        "setdigesttime_impl",
        "setactivitychannel_impl",
        "setrankedchannel_impl",
        "setrankedqueue_impl",
        "sethighlightschannel_impl",
        "setsurvivalchannel_impl",
        "setsurvivaltime_impl",
        "setstatuschannel_impl",
        "setauditchannel_impl",
        "clearauditchannel_impl",
        "showauditconfig_impl",
        "setlanguage_impl",
        "language_impl",
        "reportstatus_impl",
        "reporttoggle_impl",
        "donate_impl",
    ],
    "commands.highlights": [
        "dailyhighlights_impl",
    ],
    "commands.reports": [
        "clanstats_impl",
        "postnow_impl",
        "leaderboard_impl",
        "lastactive_impl",
    ],
    "commands.ranked": [
        "rankedsquad_impl",
        "rankedduo_impl",
        "rankedsolo_impl",
        "rankedsquadfpp_impl",
        "rankedduofpp_impl",
        "rankedsolofpp_impl",
        "refreshranked_impl",
        "updateranked_impl",
    ],
    "commands.leaderboard": [
        "leaderboardstats_impl",
        "setleaderboardregion_impl",
        "setleaderboardqueue_impl",
    ],
    "commands.chicken_dinner": [
        "chickendinner_impl",
        "setchickendinnerchannel_impl",
        "pingtoggle_impl",
    ],
    "commands.admin": [
        "reportcheater_impl",
        "askfeedback_impl",
        "botservers_impl",
    ],
    "commands.clan": [
        "setclan_impl",
        "clanlevel_impl",
        "setclanchannel_impl",
        "setclantime_impl",
    ],
    "commands.inactive": [
        "setinactivedate_impl",
        "removeinactivedate_impl",
        "resetinactivecount_impl",
    ],
    "commands.links": [
        "linkme_impl",
        "linkplayer_impl",
        "unlinkme_impl",
        "links_impl",
    ],
    "commands.analytics": [
        "playertrend_impl",
        "compare_impl",
    ],
    "commands.achievements": [
        "achievements_impl",
    ],
    "commands.streaks": [
        "streaks_impl",
    ],
    "commands.chemistry": [
        "chemistry_impl",
        "bestsquad_impl",
    ],
    "commands.mapstats": [
        "mapstats_impl",
    ],
    "commands.season": [
        "season_impl",
    ],
    "commands.matches": [
        "matches_impl",
    ],
    "commands.weaponstats": [
        "weaponstats_impl",
    ],
    "commands.weeklyawards": [
        "weeklyawards_impl",
    ],
    "commands.clan_intelligence": [
        "clantrend_impl",
        "rosterhealth_impl",
    ],
    "commands.profile": [
        "profile_impl",
    ],
    "commands.mastery": [
        "masterystats_impl",
        "survivalstats_impl",
    ],
}

results = {
    "passed": [],
    "failed": [],
    "missing": [],
    "errors": []
}

# Test each module
for module_name, expected_functions in EXPECTED_COMMANDS.items():
    print(f"\n[TEST] Module: {module_name}")
    print("-" * 70)

    try:
        # Import the module
        module = importlib.import_module(module_name)
        print(f"  [OK] Module imported successfully")

        # Check each expected function
        for func_name in expected_functions:
            if not hasattr(module, func_name):
                error_msg = f"  [FAIL] Missing function: {func_name}"
                print(error_msg)
                results["missing"].append(f"{module_name}.{func_name}")
                continue

            func = getattr(module, func_name)

            # Check if it's a coroutine function
            if not inspect.iscoroutinefunction(func):
                error_msg = f"  [FAIL] Not async: {func_name}"
                print(error_msg)
                results["failed"].append(f"{module_name}.{func_name} (not async)")
                continue

            # Check signature
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())

            # All command impls should have 'interaction' as first parameter
            if not params or params[0] != "interaction":
                error_msg = f"  [FAIL] Invalid signature: {func_name} - params: {params}"
                print(error_msg)
                results["failed"].append(f"{module_name}.{func_name} (invalid signature)")
                continue

            print(f"  [OK] {func_name}: async, valid signature")
            results["passed"].append(f"{module_name}.{func_name}")

    except ImportError as e:
        error_msg = f"  [ERROR] Import failed: {e}"
        print(error_msg)
        results["errors"].append(f"{module_name}: {e}")
    except Exception as e:
        error_msg = f"  [ERROR] Unexpected error: {e}"
        print(error_msg)
        results["errors"].append(f"{module_name}: {e}")

# Summary
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"[PASS] Passed: {len(results['passed'])}")
print(f"[FAIL] Failed: {len(results['failed'])}")
print(f"[MISS] Missing: {len(results['missing'])}")
print(f"[ERR] Errors: {len(results['errors'])}")
print(f"[TOTAL] Total Expected: {sum(len(funcs) for funcs in EXPECTED_COMMANDS.values())}")

if results["failed"]:
    print("\n[FAILED COMMANDS]:")
    for item in results["failed"]:
        print(f"  - {item}")

if results["missing"]:
    print("\n[MISSING COMMANDS]:")
    for item in results["missing"]:
        print(f"  - {item}")

if results["errors"]:
    print("\n[MODULE ERRORS]:")
    for item in results["errors"]:
        print(f"  - {item}")

if not results["failed"] and not results["missing"] and not results["errors"]:
    print("\n[SUCCESS] ALL COMMANDS PASSED VERIFICATION")
    sys.exit(0)
else:
    print("\n[FAILURE] SOME COMMANDS FAILED VERIFICATION")
    sys.exit(1)
