"""
Tests for URL shortening, custom code generation, and validation security.
"""
import pytest


def test_shorten_valid_url(client):
    res = client.post("/api/shorten", json={
        "original_url": "https://example.com/blog/article-1",
        "title": "Example Blog",
        "tags": "news, technology"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert "short_code" in data["link"]
    assert len(data["link"]["short_code"]) == 6
    assert data["link"]["title"] == "Example Blog"
    assert "news" in data["link"]["tags"]
    assert data["link"]["click_count"] == 0


def test_shorten_custom_code(client):
    res = client.post("/api/shorten", json={
        "original_url": "https://python.org",
        "custom_code": "python-rocks",
        "title": "Python Language"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["link"]["short_code"] == "python-rocks"


def test_shorten_custom_code_conflict(client):
    # First creation
    client.post("/api/shorten", json={
        "original_url": "https://google.com",
        "custom_code": "duplicate-test"
    })
    # Duplicate attempt
    res = client.post("/api/shorten", json={
        "original_url": "https://bing.com",
        "custom_code": "duplicate-test"
    })
    assert res.status_code == 409
    data = res.get_json()
    assert data["success"] is False
    assert "already taken" in data["error"]


def test_shorten_reserved_keyword(client):
    res = client.post("/api/shorten", json={
        "original_url": "https://wikipedia.org",
        "custom_code": "api"
    })
    assert res.status_code == 400
    data = res.get_json()
    assert "reserved" in data["error"]


def test_shorten_invalid_urls(client):
    invalid_cases = [
        "",  # Empty
        "ftp://files.example.com",  # Forbidden scheme
        "javascript:alert(1)",  # XSS scheme
        "http://localhost:8000/secret",  # SSRF Loopback
        "http://127.0.0.1/admin",  # Loopback IP
        "http://192.168.1.1/router",  # Private RFC1918
        "http://10.0.0.1/internal",  # Private Class A
        "just-a-plain-string",  # No protocol or valid domain
    ]
    for url in invalid_cases:
        res = client.post("/api/shorten", json={"original_url": url})
        assert res.status_code == 400
        data = res.get_json()
        assert data["success"] is False
