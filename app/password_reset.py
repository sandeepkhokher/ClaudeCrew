"""Token-based forgot-password routes: request a reset token, then redeem it.

This is distinct from ``/reset-password`` (a change-password flow that requires
the old password). Responses follow the repo-wide JSON shape:
    success -> {"message": ...}
    error   -> {"error": "<human readable reason>"}

Only the SHA-256 hash of a reset token is ever persisted; the raw token is
returned to the requester once (gated by ``RESET_TOKEN_IN_RESPONSE`` — dev only).
"""

import time

from flask import Blueprint, current_app, jsonify, request

from .db import get_db
from .security import (
    MIN_PASSWORD_LENGTH,
    generate_reset_token,
    hash_password,
    hash_token,
)

bp = Blueprint("password_reset", __name__)


def _validate_forgot(data: dict | None) -> str | None:
    """Return an error string if the forgot-password payload is invalid, else None."""
    if not data:
        return "request body must be JSON"
    if not data.get("username"):
        return "username is required"
    return None


def _validate_reset(data: dict | None) -> str | None:
    """Return an error string if the reset payload is invalid, else None."""
    if not data:
        return "request body must be JSON"
    token = data.get("token")
    new_password = data.get("new_password")
    if not token or not new_password:
        return "token and new_password are required"
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return f"password must be at least {MIN_PASSWORD_LENGTH} characters"
    return None


@bp.post("/password/forgot")
def forgot_password():
    data = request.get_json(silent=True)
    if error := _validate_forgot(data):
        return jsonify({"error": error}), 400

    # Generate and hash unconditionally so the response — and the work done — is
    # identical whether or not the account exists, avoiding username enumeration.
    token = generate_reset_token()
    token_hash = hash_token(token)
    expires_at = int(time.time()) + current_app.config["RESET_TOKEN_TTL_SECONDS"]

    db = get_db()
    user = db.execute("SELECT id FROM users WHERE username = ?", (data["username"],)).fetchone()
    if user is not None:
        # One active token per user: drop any prior tokens before issuing.
        db.execute("DELETE FROM password_reset_tokens WHERE user_id = ?", (user["id"],))
        db.execute(
            "INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (user["id"], token_hash, expires_at),
        )
        db.commit()
    else:
        # Spend an equivalent write + commit so an unknown username can't be
        # distinguished by response latency. user_id 0 never matches a real
        # account, so this DELETE affects nothing and nothing is persisted.
        db.execute("DELETE FROM password_reset_tokens WHERE user_id = ?", (0,))
        db.commit()

    body = {"message": "if that account exists, a password reset token has been issued"}
    if current_app.config["RESET_TOKEN_IN_RESPONSE"]:
        body["reset_token"] = token
    return jsonify(body), 200


@bp.post("/password/reset")
def reset_with_token():
    data = request.get_json(silent=True)
    if error := _validate_reset(data):
        return jsonify({"error": error}), 400

    token_hash = hash_token(data["token"])
    db = get_db()

    # Atomically claim the token: the row is marked used only if it currently
    # exists, is unused and unexpired. Checking rowcount avoids a read-then-write
    # race where two requests could both redeem the same token.
    claim = db.execute(
        "UPDATE password_reset_tokens SET used = 1 "
        "WHERE token_hash = ? AND used = 0 AND expires_at >= ?",
        (token_hash, int(time.time())),
    )
    if claim.rowcount == 0:
        # One generic message for every token failure (unknown, used, expired).
        db.rollback()
        return jsonify({"error": "invalid or expired reset token"}), 401

    row = db.execute(
        "SELECT user_id FROM password_reset_tokens WHERE token_hash = ?",
        (token_hash,),
    ).fetchone()
    update = db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (hash_password(data["new_password"]), row["user_id"]),
    )
    if update.rowcount == 0:
        # Orphaned token (e.g. the account was deleted): the user no longer
        # exists, so the claim is void — undo it and report the generic failure.
        db.rollback()
        return jsonify({"error": "invalid or expired reset token"}), 401

    db.commit()
    return jsonify({"message": "password reset successful"}), 200
