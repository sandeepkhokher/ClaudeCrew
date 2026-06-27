"""Tests for the auth endpoints."""

GOOD = {"username": "alice", "password": "supersecret"}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_register_success(client):
    resp = client.post("/register", json=GOOD)
    assert resp.status_code == 201
    assert resp.get_json()["username"] == "alice"


def test_register_requires_fields(client):
    resp = client.post("/register", json={"username": "x"})
    assert resp.status_code == 400


def test_register_short_password(client):
    resp = client.post("/register", json={"username": "bob", "password": "short"})
    assert resp.status_code == 400


def test_register_duplicate(client):
    client.post("/register", json=GOOD)
    resp = client.post("/register", json=GOOD)
    assert resp.status_code == 409


def test_login_success(client):
    client.post("/register", json=GOOD)
    resp = client.post("/login", json=GOOD)
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "login successful"


def test_login_wrong_password(client):
    client.post("/register", json=GOOD)
    resp = client.post("/login", json={"username": "alice", "password": "wrongpass1"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/login", json={"username": "ghost", "password": "supersecret"})
    assert resp.status_code == 401
