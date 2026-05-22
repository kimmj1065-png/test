import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_token


def test_password_hash_and_verify():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_create_and_decode_token():
    token = create_access_token({"sub": "user-id-123"})
    user_id = decode_token(token)
    assert user_id == "user-id-123"


def test_decode_invalid_token():
    result = decode_token("invalid.token.here")
    assert result is None


def test_register_success(client):
    resp = client.post("/auth/register", json={"email": "new@test.com", "password": "pass123"})
    assert resp.status_code == 201
    assert resp.json()["email"] == "new@test.com"


def test_register_duplicate_email(client):
    client.post("/auth/register", json={"email": "dup@test.com", "password": "pass123"})
    resp = client.post("/auth/register", json={"email": "dup@test.com", "password": "pass123"})
    assert resp.status_code == 400


def test_login_success(client):
    client.post("/auth/register", json={"email": "login@test.com", "password": "pass123"})
    resp = client.post("/auth/login", json={"email": "login@test.com", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "wp@test.com", "password": "pass123"})
    resp = client.post("/auth/login", json={"email": "wp@test.com", "password": "wrong"})
    assert resp.status_code == 401
