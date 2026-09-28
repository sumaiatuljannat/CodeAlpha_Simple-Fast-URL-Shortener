"""
Tests for link resolution, HTTP 302 redirection, click tracking, expiration, and status checks.
"""
from datetime import datetime, timezone, timedelta


def test_redirect_success_and_click_tracking(client):
    # 1. Create a link
    res = client.post("/api/shorten", json={
        "original_url": "https://docs.python.org/3/",
        "custom_code": "py-docs"
    })
    assert res.status_code == 201

    # 2. Perform redirection
    redir = client.get(
        "/py-docs",
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
            "Referer": "https://news.ycombinator.com/item?id=123"
        }
    )
    assert redir.status_code == 302
    assert redir.headers["Location"] == "https://docs.python.org/3/"

    # 3. Check analytics updated
    stats = client.get("/api/links/py-docs/stats").get_json()
    assert stats["analytics"]["total_clicks"] == 1
    assert stats["analytics"]["devices"][0]["name"] == "Mobile"
    assert stats["analytics"]["operating_systems"][0]["name"] == "iOS"


def test_redirect_missing_link_404(client):
    res = client.get("/non-existent-link-999")
    assert res.status_code == 404
    assert b"Link Not Found" in res.data


def test_redirect_disabled_link_403(client):
    # Create link
    client.post("/api/shorten", json={
        "original_url": "https://example.com/inactive",
        "custom_code": "disabled-link"
    })
    # Disable it
    client.patch("/api/links/disabled-link", json={"is_active": False})

    # Attempt to visit
    res = client.get("/disabled-link")
    assert res.status_code == 403
    assert b"Inactive" in res.data


def test_redirect_expired_link_410(client):
    # Create link with past expiration using ISO format
    past_date = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    
    # We update expires_at directly or bypass future check in update for testing
    client.post("/api/shorten", json={
        "original_url": "https://example.com/expired",
        "custom_code": "expired-link"
    })
    
    # Directly set past expiration in db
    from database import get_db_connection
    with get_db_connection() as conn:
        conn.execute("UPDATE links SET expires_at = ? WHERE short_code = ?", (past_date, "expired-link"))
        conn.commit()

    # Attempt visit
    res = client.get("/expired-link")
    assert res.status_code == 410
    assert b"Expired" in res.data
