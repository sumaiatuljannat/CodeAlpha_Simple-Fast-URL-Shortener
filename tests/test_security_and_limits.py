"""
Additional tests covering rate limiting, expiration validation, and security edge cases.
"""
from datetime import datetime, timezone, timedelta
from security import SlidingWindowRateLimiter


def test_sliding_window_rate_limiter_unit():
    limiter = SlidingWindowRateLimiter()
    key = "test-ip-client"
    # First 5 should succeed
    for _ in range(5):
        allowed, retry_after = limiter.is_allowed(key, limit=5, window=10)
        assert allowed is True
        assert retry_after == 0

    # 6th request should be blocked
    allowed, retry_after = limiter.is_allowed(key, limit=5, window=10)
    assert allowed is False
    assert retry_after > 0


def test_future_expiration_validation(client):
    # Expired date in the past
    past_iso = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    res = client.post("/api/shorten", json={
        "original_url": "https://example.com/test-exp",
        "expires_at": past_iso
    })
    assert res.status_code == 400
    assert "future" in res.get_json()["error"]

    # Valid future expiration date
    future_iso = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    res2 = client.post("/api/shorten", json={
        "original_url": "https://example.com/test-exp-ok",
        "expires_at": future_iso
    })
    assert res2.status_code == 201
    assert res2.get_json()["link"]["expires_at"] is not None
