"""Tests for the /stats endpoint."""

GOOD = {"username": "alice", "password": "supersecret"}


def test_stats_empty(client):
    resp = client.get("/stats")
    assert resp.status_code == 200
    assert resp.get_json() == {"users": 0}


def test_stats_counts_registered_users(client):
    client.post("/register", json=GOOD)
    client.post("/register", json={"username": "bob", "password": "bobsecret1"})
    resp = client.get("/stats")
    assert resp.status_code == 200
    assert resp.get_json() == {"users": 2}


def test_stats_rejects_post(client):
    resp = client.post("/stats")
    assert resp.status_code == 405
