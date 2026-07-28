import pytest

pytestmark = pytest.mark.integration


async def test_signup_login_me_flow(client):
    signup_resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": "alice@example.com", "password": "s3cure-password", "full_name": "Alice"},
    )
    assert signup_resp.status_code == 201
    tokens = signup_resp.json()
    assert tokens["user"]["email"] == "alice@example.com"

    me_resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "alice@example.com"

    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": "alice@example.com", "password": "s3cure-password"}
    )
    assert login_resp.status_code == 200


async def test_signup_rejects_duplicate_email(client):
    payload = {"email": "bob@example.com", "password": "s3cure-password"}
    first = await client.post("/api/v1/auth/signup", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/auth/signup", json=payload)
    assert second.status_code == 409


async def test_login_rejects_wrong_password(client):
    await client.post("/api/v1/auth/signup", json={"email": "carol@example.com", "password": "correct-password"})
    resp = await client.post("/api/v1/auth/login", json={"email": "carol@example.com", "password": "wrong-password"})
    assert resp.status_code == 401


async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_forgot_password_is_always_202(client):
    resp = await client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp.status_code == 202
