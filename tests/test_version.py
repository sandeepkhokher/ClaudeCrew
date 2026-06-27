"""Tests for the GET /version endpoint."""


def test_version_returns_app_version(client):
    resp = client.get("/version")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body == {"version": "0.1.0"}


def test_version_rejects_post(client):
    resp = client.post("/version")
    assert resp.status_code == 405
