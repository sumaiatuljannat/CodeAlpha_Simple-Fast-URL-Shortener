"""
Tests for user registration, login, logout, and authenticated link management.
"""


def test_user_registration_and_login(client):
    # 1. Register
    reg_res = client.post("/api/auth/register", json={
        "username": "developer",
        "email": "dev@example.com",
        "password": "securepassword123"
    })
    assert reg_res.status_code == 201
    assert reg_res.get_json()["success"] is True

    # 2. Check /api/auth/me
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.get_json()["authenticated"] is True
    assert me_res.get_json()["user"]["username"] == "developer"

    # 3. Logout
    client.post("/api/auth/logout")
    me_res2 = client.get("/api/auth/me")
    assert me_res2.get_json()["authenticated"] is False

    # 4. Login
    login_res = client.post("/api/auth/login", json={
        "username": "developer",
        "password": "securepassword123"
    })
    assert login_res.status_code == 200
    assert login_res.get_json()["success"] is True


def test_duplicate_user_conflict(client):
    # Attempt registering same username
    res = client.post("/api/auth/register", json={
        "username": "developer",
        "email": "another@example.com",
        "password": "securepassword123"
    })
    assert res.status_code == 409
    assert res.get_json()["success"] is False
