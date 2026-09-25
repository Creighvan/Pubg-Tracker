"""
Basic smoke test to verify the bot imports cleanly.
Run with: python test_import.py
"""

def test_imports():
    """Test that all core modules import without errors."""
    try:
        import bot
        import pubg_api
        import storage
        print("[OK] All imports successful")
        return True
    except ImportError as e:
        print(f"[X] Import failed: {e}")
        return False
    except Exception as e:
        print(f"[X] Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    exit(0 if success else 1)
