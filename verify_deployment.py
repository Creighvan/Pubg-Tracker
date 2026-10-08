#!/usr/bin/env python3
"""
Post-deployment verification script.
Run this after deploying to verify the bot is running correctly.
"""

import subprocess
import sys
import os

print("=" * 70)
print("PUBG Tracker Bot - Post-Deployment Verification")
print("=" * 70)

# Check if we're on production server
if os.path.exists("/home/ubuntu/pubg-bot"):
    print("[OK] Running on production server")
else:
    print("[INFO] Not on production server - skipping PM2 checks")
    sys.exit(0)

# Check PM2 status
print("\n[CHECK] PM2 Process Status")
print("-" * 70)
try:
    result = subprocess.run(
        ["pm2", "status"],
        capture_output=True,
        text=True,
        timeout=10
    )
    print(result.stdout)

    if "pubg-bot" not in result.stdout:
        print("[FAIL] pubg-bot process not found in PM2")
        sys.exit(1)
    else:
        print("[OK] pubg-bot process found")
except subprocess.TimeoutExpired:
    print("[FAIL] PM2 status command timed out")
    sys.exit(1)
except Exception as e:
    print(f"[FAIL] Error checking PM2 status: {e}")
    sys.exit(1)

# Check recent logs
print("\n[CHECK] Recent PM2 Logs")
print("-" * 70)
try:
    result = subprocess.run(
        ["pm2", "logs", "pubg-bot", "--lines", "30", "--nostream"],
        capture_output=True,
        text=True,
        timeout=10
    )
    print(result.stdout)

    # Check for errors
    if "ERROR" in result.stdout or "Exception" in result.stdout:
        print("[WARN] Errors found in recent logs")
    else:
        print("[OK] No obvious errors in recent logs")
except subprocess.TimeoutExpired:
    print("[FAIL] PM2 logs command timed out")
    sys.exit(1)
except Exception as e:
    print(f"[FAIL] Error checking PM2 logs: {e}")
    sys.exit(1)

# Check git status
print("\n[CHECK] Git Status")
print("-" * 70)
try:
    result = subprocess.run(
        ["git", "status"],
        capture_output=True,
        text=True,
        timeout=10,
        cwd="/home/ubuntu/pubg-bot"
    )
    print(result.stdout)

    if "working tree clean" in result.stdout.lower():
        print("[OK] Working tree clean")
    else:
        print("[WARN] Uncommitted changes present")
except subprocess.TimeoutExpired:
    print("[FAIL] Git status command timed out")
    sys.exit(1)
except Exception as e:
    print(f"[FAIL] Error checking git status: {e}")
    sys.exit(1)

# Check current commit
print("\n[CHECK] Current Commit")
print("-" * 70)
try:
    result = subprocess.run(
        ["git", "log", "-1", "--oneline"],
        capture_output=True,
        text=True,
        timeout=10,
        cwd="/home/ubuntu/pubg-bot"
    )
    print(result.stdout)
except Exception as e:
    print(f"[FAIL] Error checking git log: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
print("\nNext steps:")
print("1. Test commands in Discord channel 1552774618564005938")
print("2. Use DEPLOY-TEST-GUIDE.md for testing checklist")
print("3. Monitor PM2 logs: pm2 logs pubg-bot")
