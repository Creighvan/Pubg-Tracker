"""
Simple smoke test for PUBG Tracker bot.

This test verifies basic functionality without requiring a full test environment.
It checks that:
- The bot can import without errors
- The translation system loads correctly
- The storage module can be imported
- Basic configuration is accessible
"""

import sys


def test_imports():
    """Test that all main modules can be imported."""
    print("Testing imports...")
    
    try:
        import storage
        print("[OK] storage module imported")
    except Exception as e:
        print(f"[FAIL] storage module failed: {e}")
        return False
    
    try:
        import pubg_api
        print("[OK] pubg_api module imported")
    except Exception as e:
        print(f"[FAIL] pubg_api module failed: {e}")
        return False
    
    try:
        import translations
        print("[OK] translations module imported")
    except Exception as e:
        print(f"[FAIL] translations module failed: {e}")
        return False
    
    try:
        from modules import config
        print("[OK] modules.config imported")
    except Exception as e:
        print(f"[FAIL] modules.config failed: {e}")
        return False
    
    try:
        from modules import utils
        print("[OK] modules.utils imported")
    except Exception as e:
        print(f"[FAIL] modules.utils failed: {e}")
        return False
    
    try:
        from modules import scheduler
        print("[OK] modules.scheduler imported")
    except Exception as e:
        print(f"[FAIL] modules.scheduler failed: {e}")
        return False
    
    try:
        from modules import embeds
        print("[OK] modules.embeds imported")
    except Exception as e:
        print(f"[FAIL] modules.embeds failed: {e}")
        return False
    
    return True


def test_translations():
    """Test that translation system works."""
    print("\nTesting translations...")
    
    try:
        import translations
        
        # Test English translation
        text = translations.get_translation("en", "player_added_success")
        if text and "{name}" in text:
            # Don't print the actual text to avoid Unicode issues
            print("[OK] English translation works")
        else:
            print("[FAIL] English translation missing or invalid")
            return False
        
        # Test another language
        text = translations.get_translation("es", "player_added_success")
        if text and "{name}" in text:
            print("[OK] Spanish translation works")
        else:
            print("[FAIL] Spanish translation missing or invalid")
            return False
        
        return True
    except Exception as e:
        print(f"[FAIL] Translation test failed: {e}")
        return False


def test_storage_constants():
    """Test that storage module has expected constants."""
    print("\nTesting storage constants...")
    
    try:
        import storage
        
        if hasattr(storage, 'DATA_PATH'):
            print(f"[OK] DATA_PATH defined: {storage.DATA_PATH}")
        else:
            print("[FAIL] DATA_PATH not defined")
            return False
        
        if hasattr(storage, 'DatabaseCorruptionError'):
            print("[OK] DatabaseCorruptionError defined")
        else:
            print("[FAIL] DatabaseCorruptionError not defined")
            return False
        
        return True
    except Exception as e:
        print(f"[FAIL] Storage constants test failed: {e}")
        return False


def test_pubg_api():
    """Test that PUBG API client can be instantiated."""
    print("\nTesting PUBG API client...")
    
    try:
        from pubg_api import PubgClient, PubgApiError
        
        # Create a client with dummy credentials
        client = PubgClient(api_key="test_key", shard="pc-na")
        print("[OK] PubgClient instantiated")
        
        if hasattr(client, 'get_players_by_name'):
            print("[OK] get_players_by_name method exists")
        else:
            print("[FAIL] get_players_by_name method missing")
            return False
        
        if hasattr(client, 'get_players_and_stats'):
            print("[OK] get_players_and_stats method exists")
        else:
            print("[FAIL] get_players_and_stats method missing")
            return False
        
        return True
    except Exception as e:
        print(f"[FAIL] PUBG API test failed: {e}")
        return False


def main():
    """Run all smoke tests."""
    print("=" * 50)
    print("PUBG Tracker Smoke Test")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Translations", test_translations),
        ("Storage Constants", test_storage_constants),
        ("PUBG API", test_pubg_api),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[FAIL] {name} test crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("Results:")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[OK] All smoke tests passed!")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
