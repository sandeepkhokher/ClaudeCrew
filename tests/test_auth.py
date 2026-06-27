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


RESET = {"username": "alice", "old_password": "supersecret", "new_password": "brandnew1"}


def test_reset_success(client):
    client.post("/register", json=GOOD)
    resp = client.post("/reset-password", json=RESET)
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "password reset successful"


def test_reset_then_login_with_new_password(client):
    client.post("/register", json=GOOD)
    client.post("/reset-password", json=RESET)
    resp = client.post("/login", json={"username": "alice", "password": "brandnew1"})
    assert resp.status_code == 200


def test_reset_then_login_with_old_password_fails(client):
    client.post("/register", json=GOOD)
    client.post("/reset-password", json=RESET)
    resp = client.post("/login", json={"username": "alice", "password": "supersecret"})
    assert resp.status_code == 401


def test_reset_wrong_old_password(client):
    client.post("/register", json=GOOD)
    resp = client.post(
        "/reset-password",
        json={"username": "alice", "old_password": "wrongpass1", "new_password": "brandnew1"},
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "invalid credentials"


def test_reset_unknown_user_does_not_leak(client):
    # Wrong old password (known user) and unknown user must be indistinguishable.
    client.post("/register", json=GOOD)
    wrong_old = client.post(
        "/reset-password",
        json={"username": "alice", "old_password": "wrongpass1", "new_password": "brandnew1"},
    )
    unknown = client.post(
        "/reset-password",
        json={"username": "ghost", "old_password": "supersecret", "new_password": "brandnew1"},
    )
    assert unknown.status_code == 401
    assert unknown.status_code == wrong_old.status_code
    assert unknown.get_json() == wrong_old.get_json()


def test_reset_short_new_password(client):
    client.post("/register", json=GOOD)
    resp = client.post(
        "/reset-password",
        json={"username": "alice", "old_password": "supersecret", "new_password": "short"},
    )
    assert resp.status_code == 400


def test_reset_new_equals_old(client):
    client.post("/register", json=GOOD)
    resp = client.post(
        "/reset-password",
        json={"username": "alice", "old_password": "supersecret", "new_password": "supersecret"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "new password must differ from old password"


def test_reset_missing_new_password(client):
    client.post("/register", json=GOOD)
    resp = client.post(
        "/reset-password",
        json={"username": "alice", "old_password": "supersecret"},
    )
    assert resp.status_code == 400


def test_reset_missing_username(client):
    client.post("/register", json=GOOD)
    resp = client.post(
        "/reset-password",
        json={"old_password": "supersecret", "new_password": "brandnew1"},
    )
    assert resp.status_code == 400


def test_reset_missing_old_password(client):
    client.post("/register", json=GOOD)
    resp = client.post(
        "/reset-password",
        json={"username": "alice", "new_password": "brandnew1"},
    )
    assert resp.status_code == 400


def test_reset_no_json_body(client):
    resp = client.post("/reset-password")
    assert resp.status_code == 400


def test_reset_does_not_affect_other_user(client):
    client.post("/register", json=GOOD)
    client.post("/register", json={"username": "bob", "password": "bobsecret1"})
    client.post("/reset-password", json=RESET)
    resp = client.post("/login", json={"username": "bob", "password": "bobsecret1"})
    assert resp.status_code == 200
