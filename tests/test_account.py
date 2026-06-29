"""Tests for the account-delete endpoint."""

GOOD = {"username": "alice", "password": "supersecret"}


def test_delete_account_success(client):
    client.post("/register", json=GOOD)
    resp = client.delete("/account", json=GOOD)
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "account deleted"
    # The user is gone: login now fails.
    assert client.post("/login", json=GOOD).status_code == 401


def test_delete_account_requires_fields(client):
    resp = client.delete("/account", json={"username": "alice"})
    assert resp.status_code == 400


def test_delete_account_wrong_password(client):
    client.post("/register", json=GOOD)
    resp = client.delete("/account", json={"username": "alice", "password": "wrongpass1"})
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "invalid credentials"
    # The account still exists after a failed delete.
    assert client.post("/login", json=GOOD).status_code == 200


def test_delete_account_unknown_user(client):
    resp = client.delete("/account", json={"username": "ghost", "password": "supersecret"})
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "invalid credentials"
