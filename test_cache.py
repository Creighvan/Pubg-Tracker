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


async def test_in_flight_deduplication():
    """Test that in-flight requests are deduplicated to prevent cache stampedes."""
    cache = ResponseCache()
    request_count = 0

    async def slow_fetch():
        nonlocal request_count
        request_count += 1
        await asyncio.sleep(0.1)  # Simulate slow network request
        return {"data": "fetched_value"}

    # Simulate 5 concurrent requests for the same key
    cache_key = "test:deduplication"
    tasks = [
        cache.get_or_fetch(cache_key, slow_fetch, ttl_minutes=30)
        for _ in range(5)
    ]

    results = await asyncio.gather(*tasks)

    # All should return the same value
    assert all(r == {"data": "fetched_value"} for r in results), "All requests should return same value"

    # Only one actual fetch should have occurred
    assert request_count == 1, f"Expected 1 fetch, got {request_count}"

    print("[OK] In-flight request deduplication works")


async def test_get_or_fetch():
    """Test get_or_fetch combines cache check and fetch logic."""
    cache = ResponseCache()
    fetch_count = 0

    async def fetch_func():
        nonlocal fetch_count
        fetch_count += 1
        return {"count": fetch_count}

    cache_key = "test:get_or_fetch"

    # First call should fetch
    result1 = await cache.get_or_fetch(cache_key, fetch_func, ttl_minutes=30)
    assert result1 == {"count": 1}, "First call should fetch"
    assert fetch_count == 1, "Fetch should have been called once"

    # Second call should use cache
    result2 = await cache.get_or_fetch(cache_key, fetch_func, ttl_minutes=30)
    assert result2 == {"count": 1}, "Second call should use cached value"
    assert fetch_count == 1, "Fetch should not have been called again"

    print("[OK] get_or_fetch works correctly")


async def main():
    """Run all cache tests."""
    print("Testing PUBG API Response Cache")
    print("=" * 40)

    await test_cache_basic()
    await test_cache_expiration()
    await test_cache_key_format()
    await test_cache_concurrent_access()
    await test_in_flight_deduplication()
    await test_get_or_fetch()

    print("=" * 40)
    print("[OK] All cache tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
