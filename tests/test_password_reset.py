"""Tests for the token-based forgot-password flow (/password/forgot, /password/reset).

Distinct from the change-password flow in test_auth.py (/reset-password).
"""

import os
import tempfile

from app import create_app
from app.db import get_db
from app.security import hash_token

ALICE = {"username": "alice", "password": "supersecret"}
BOB = {"username": "bob", "password": "bobsecret1"}

FORGOT_MESSAGE = "if that account exists, a password reset token has been issued"
TOKEN_ERROR = {"error": "invalid or expired reset token"}


def _request_token(client, username="alice"):
    """Run /password/forgot and return its raw reset_token."""
    resp = client.post("/password/forgot", json={"username": username})
    assert resp.status_code == 200
    return resp.get_json()["reset_token"]


# --- Happy path -----------------------------------------------------------


def test_forgot_returns_token(client):
    client.post("/register", json=ALICE)
    resp = client.post("/password/forgot", json={"username": "alice"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["message"] == FORGOT_MESSAGE
    assert body["reset_token"]


def test_reset_with_token_success(client):
    client.post("/register", json=ALICE)
    token = _request_token(client)
    resp = client.post("/password/reset", json={"token": token, "new_password": "brandnew1"})
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "password reset successful"


def test_reset_then_login_with_new_password(client):
    client.post("/register", json=ALICE)
    token = _request_token(client)
    client.post("/password/reset", json={"token": token, "new_password": "brandnew1"})
    resp = client.post("/login", json={"username": "alice", "password": "brandnew1"})
    assert resp.status_code == 200


def test_reset_then_login_with_old_password_fails(client):
    client.post("/register", json=ALICE)
    token = _request_token(client)
    client.post("/password/reset", json={"token": token, "new_password": "brandnew1"})
    resp = client.post("/login", json={"username": "alice", "password": "supersecret"})
    assert resp.status_code == 401


# --- Validation: /password/forgot -----------------------------------------


def test_forgot_missing_username(client):
    resp = client.post("/password/forgot", json={})
    assert resp.status_code == 400


def test_forgot_no_json_body(client):
    resp = client.post("/password/forgot")
    assert resp.status_code == 400


# --- Validation: /password/reset ------------------------------------------


def test_reset_missing_token(client):
    resp = client.post("/password/reset", json={"new_password": "brandnew1"})
    assert resp.status_code == 400


def test_reset_missing_new_password(client):
    resp = client.post("/password/reset", json={"token": "whatever"})
    assert resp.status_code == 400


def test_reset_no_json_body(client):
    resp = client.post("/password/reset")
    assert resp.status_code == 400


def test_reset_short_new_password(client):
    client.post("/register", json=ALICE)
    token = _request_token(client)
    resp = client.post("/password/reset", json={"token": token, "new_password": "short"})
    assert resp.status_code == 400


# --- Security -------------------------------------------------------------


def test_forgot_unknown_user_same_body_shape(client):
    # No registered users; response must still look like a known-user response.
    resp = client.post("/password/forgot", json={"username": "ghost"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["message"] == FORGOT_MESSAGE
    assert body["reset_token"]


def test_token_for_unknown_user_does_not_redeem(client):
    # A token handed out for a non-existent account has no DB row, so it fails.
    token = _request_token(client, username="ghost")
    resp = client.post("/password/reset", json={"token": token, "new_password": "brandnew1"})
    assert resp.status_code == 401
    assert resp.get_json() == TOKEN_ERROR


def test_token_is_single_use(client):
    client.post("/register", json=ALICE)
    token = _request_token(client)
    first = client.post("/password/reset", json={"token": token, "new_password": "brandnew1"})
    assert first.status_code == 200
    second = client.post("/password/reset", json={"token": token, "new_password": "another12"})
    assert second.status_code == 401
    assert second.get_json() == TOKEN_ERROR


def test_expired_token_rejected(client, app):
    client.post("/register", json=ALICE)
    # Issue a token that is already expired.
    app.config["RESET_TOKEN_TTL_SECONDS"] = -10
    token = _request_token(client)
    resp = client.post("/password/reset", json={"token": token, "new_password": "brandnew1"})
    assert resp.status_code == 401
    assert resp.get_json() == TOKEN_ERROR


def test_expired_token_via_db_mutation(client, app):
    client.post("/register", json=ALICE)
    token = _request_token(client)
    # Force the stored row to be in the past.
    with app.app_context():
        db = get_db()
        db.execute("UPDATE password_reset_tokens SET expires_at = 0")
        db.commit()
    resp = client.post("/password/reset", json={"token": token, "new_password": "brandnew1"})
    assert resp.status_code == 401
    assert resp.get_json() == TOKEN_ERROR


def test_reissue_invalidates_old_token(client):
    client.post("/register", json=ALICE)
    old_token = _request_token(client)
    new_token = _request_token(client)
    assert old_token != new_token
    old = client.post("/password/reset", json={"token": old_token, "new_password": "brandnew1"})
    assert old.status_code == 401
    assert old.get_json() == TOKEN_ERROR
    new = client.post("/password/reset", json={"token": new_token, "new_password": "brandnew1"})
    assert new.status_code == 200


def test_forged_token_rejected(client):
    client.post("/register", json=ALICE)
    resp = client.post(
        "/password/reset",
        json={"token": "totally-made-up-token", "new_password": "brandnew1"},
    )
    assert resp.status_code == 401
    assert resp.get_json() == TOKEN_ERROR


def test_reset_does_not_affect_other_user(client):
    client.post("/register", json=ALICE)
    client.post("/register", json=BOB)
    token = _request_token(client, username="alice")
    client.post("/password/reset", json={"token": token, "new_password": "brandnew1"})
    resp = client.post("/login", json=BOB)
    assert resp.status_code == 200


def test_all_token_failures_share_body_and_status(client):
    client.post("/register", json=ALICE)
    used_token = _request_token(client)
    client.post("/password/reset", json={"token": used_token, "new_password": "brandnew1"})

    failures = [
        client.post("/password/reset", json={"token": "garbage", "new_password": "brandnew1"}),
        client.post("/password/reset", json={"token": used_token, "new_password": "brandnew1"}),
        client.post(
            "/password/reset",
            json={"token": _request_token(client, username="ghost"), "new_password": "brandnew1"},
        ),
    ]
    for resp in failures:
        assert resp.status_code == 401
        assert resp.get_json() == TOKEN_ERROR


# --- Hardening: orphaned tokens & account deletion ------------------------


def _delete_account(client, creds):
    """Delete an account via DELETE /account (requires password verification)."""
    return client.delete("/account", json=creds)


def test_orphaned_token_after_account_delete_returns_401(client):
    # Key bug guard: a token still held after the account is deleted must NOT
    # redeem (no false 200) — the user no longer exists.
    client.post("/register", json=ALICE)
    token = _request_token(client)

    deleted = _delete_account(client, ALICE)
    assert deleted.status_code == 200

    resp = client.post("/password/reset", json={"token": token, "new_password": "brandnew1"})
    assert resp.status_code == 401
    assert resp.get_json() == TOKEN_ERROR


def test_account_delete_removes_reset_tokens(client, app):
    client.post("/register", json=ALICE)
    _request_token(client)

    # Sanity: a token row exists before deletion.
    with app.app_context():
        db = get_db()
        before = db.execute("SELECT COUNT(*) AS n FROM password_reset_tokens").fetchone()
        assert before["n"] == 1

    assert _delete_account(client, ALICE).status_code == 200

    # The user's tokens are gone, leaving nothing orphaned and redeemable.
    with app.app_context():
        db = get_db()
        after = db.execute("SELECT COUNT(*) AS n FROM password_reset_tokens").fetchone()
        assert after["n"] == 0


# --- Hardening: at-rest token secrecy -------------------------------------


def test_raw_token_never_stored_plaintext(client, app):
    client.post("/register", json=ALICE)
    token = _request_token(client)

    with app.app_context():
        db = get_db()
        rows = db.execute("SELECT token_hash FROM password_reset_tokens").fetchall()

    assert rows, "expected a stored reset-token row"
    stored = [r["token_hash"] for r in rows]
    # The raw token must never appear verbatim at rest...
    assert token not in stored
    # ...and what is stored must be exactly its SHA-256 digest.
    assert stored == [hash_token(token)]


# --- Hardening: RESET_TOKEN_IN_RESPONSE fail-closed -----------------------


def test_forgot_fail_closed_omits_token():
    # Build a dedicated app with the production default (False): the response
    # must carry the generic message but NO reset_token field.
    fd, path = tempfile.mkstemp(suffix=".db")
    try:
        app = create_app({"TESTING": True, "DATABASE": path, "RESET_TOKEN_IN_RESPONSE": False})
        client = app.test_client()
        client.post("/register", json=ALICE)

        resp = client.post("/password/forgot", json={"username": "alice"})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["message"] == FORGOT_MESSAGE
        assert "reset_token" not in body

        # The flow is still drivable by reading the hash-matched token from the DB.
        with app.app_context():
            db = get_db()
            row = db.execute("SELECT token_hash FROM password_reset_tokens").fetchone()
        assert row is not None and row["token_hash"]
    finally:
        os.close(fd)
        os.unlink(path)
