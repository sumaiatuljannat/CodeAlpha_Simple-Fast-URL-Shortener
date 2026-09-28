"""
Tests for REST API endpoints: listing, metadata, patch updates, delete, stats, and QR codes.
"""


def test_api_list_and_search_links(client):
    client.post("/api/shorten", json={
        "original_url": "https://github.com/flask/flask",
        "custom_code": "flask-repo",
        "title": "Flask Source Code",
        "tags": "opensource, python"
    })
    client.post("/api/shorten", json={
        "original_url": "https://react.dev",
        "custom_code": "react-docs",
        "title": "React Frontend",
        "tags": "frontend, javascript"
    })

    # 1. Fetch all
    res = client.get("/api/links")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["links"]) >= 2

    # 2. Search query
    search_res = client.get("/api/links?search=React")
    sdata = search_res.get_json()
    assert len(sdata["links"]) == 1
    assert sdata["links"][0]["short_code"] == "react-docs"

    # 3. Tag filter
    tag_res = client.get("/api/links?tag=opensource")
    tdata = tag_res.get_json()
    assert len(tdata["links"]) == 1
    assert tdata["links"][0]["short_code"] == "flask-repo"


def test_api_patch_update_link(client):
    client.post("/api/shorten", json={
        "original_url": "https://example.com/v1",
        "custom_code": "patch-test",
        "title": "Version 1"
    })

    # Update original_url and title
    patch_res = client.patch("/api/links/patch-test", json={
        "original_url": "https://example.com/v2-updated",
        "title": "Version 2 Updated",
        "tags": "updated, v2"
    })
    assert patch_res.status_code == 200
    data = patch_res.get_json()
    assert data["link"]["original_url"] == "https://example.com/v2-updated"
    assert data["link"]["title"] == "Version 2 Updated"
    assert "v2" in data["link"]["tags"]


def test_api_delete_link(client):
    client.post("/api/shorten", json={
        "original_url": "https://example.com/to-delete",
        "custom_code": "delete-me"
    })

    # Delete
    del_res = client.delete("/api/links/delete-me")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True

    # Verify not found
    get_res = client.get("/api/links/delete-me")
    assert get_res.status_code == 404


def test_api_qr_generation(client):
    client.post("/api/shorten", json={
        "original_url": "https://example.com/qr-test",
        "custom_code": "qr-link"
    })

    # 1. Test SVG
    svg_res = client.get("/api/links/qr-link/qr?format=svg")
    assert svg_res.status_code == 200
    assert svg_res.headers["Content-Type"].startswith("image/svg+xml")
    assert b"<svg" in svg_res.data

    # 2. Test PNG
    png_res = client.get("/api/links/qr-link/qr?format=png")
    assert png_res.status_code == 200
    assert png_res.headers["Content-Type"] == "image/png"
    assert png_res.data.startswith(b"\x89PNG")
