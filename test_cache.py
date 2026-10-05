"""
Simple tests for the PUBG API response cache.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from pubg_api import ResponseCache


async def test_cache_basic():
    """Test basic cache get/set operations."""
    cache = ResponseCache()

    # Test that cache miss returns None
    result = await cache.get("test_key")
    assert result is None, "Cache miss should return None"

    # Test set and get
    await cache.set("test_key", {"data": "test_value"}, ttl_minutes=30)
    result = await cache.get("test_key")
    assert result == {"data": "test_value"}, "Cache hit should return stored value"

    print("[OK] Basic cache operations work")


async def test_cache_expiration():
    """Test that cache entries expire after TTL."""
    cache = ResponseCache()

    # Set a value with 1 minute TTL
    await cache.set("expiring_key", {"data": "expires_soon"}, ttl_minutes=1)

    # Should be available immediately
    result = await cache.get("expiring_key")
    assert result is not None, "Value should be available before expiration"

    # Clear expired entries manually (simulating time passing)
    await cache.clear_expired()

    # Manually expire by setting a very short TTL
    await cache.set("fast_expire", {"data": "gone"}, ttl_minutes=0)
    await cache.clear_expired()

    # The fast_expire key should be gone
    result = await cache.get("fast_expire")
    assert result is None, "Expired entry should be None after cleanup"

    print("[OK] Cache expiration works")


async def test_cache_key_format():
    """Test that cache keys are formatted correctly."""
    cache = ResponseCache()

    # Test the _make_key method
    key1 = cache._make_key("players", "steam", "player1,player2")
    key2 = cache._make_key("players", "steam", "player1,player2")
    key3 = cache._make_key("players", "steam", "player1,player3")

    assert key1 == key2, "Same inputs should produce same key"
    assert key1 != key3, "Different inputs should produce different keys"

    print("[OK] Cache key formatting works")


async def test_cache_concurrent_access():
    """Test that cache handles concurrent access safely."""
    cache = ResponseCache()

    async def set_many():
        for i in range(10):
            await cache.set(f"key_{i}", {"value": i}, ttl_minutes=30)

    async def get_many():
        for i in range(10):
            await cache.get(f"key_{i}")

    # Run concurrent operations
    await asyncio.gather(set_many(), get_many())

    # Verify all values were set
    for i in range(10):
        result = await cache.get(f"key_{i}")
        assert result == {"value": i}, f"Value for key_{i} should be preserved"

    print("[OK] Concurrent cache access works")


async def main():
    """Run all cache tests."""
    print("Testing PUBG API Response Cache")
    print("=" * 40)

    await test_cache_basic()
    await test_cache_expiration()
    await test_cache_key_format()
    await test_cache_concurrent_access()

    print("=" * 40)
    print("[OK] All cache tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
