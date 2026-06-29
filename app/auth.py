"""Authentication routes: register, login, health.

All responses are JSON with a consistent shape:
    success -> {"message": ..., ...}
    error   -> {"error": "<human readable reason>"}
"""

from flask import Blueprint, jsonify, request

from .db import get_db
from .security import MIN_PASSWORD_LENGTH, dummy_verify, hash_password, verify_password

bp = Blueprint("auth", __name__)


def _validate(data: dict | None) -> str | None:
    """Return an error string if the payload is invalid, else None."""
    if not data:
        return "request body must be JSON"
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return "username and password are required"
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"password must be at least {MIN_PASSWORD_LENGTH} characters"
    return None


def _validate_reset(data: dict | None) -> str | None:
    """Return an error string if the reset payload is invalid, else None."""
    if not data:
        return "request body must be JSON"
    username = data.get("username")
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    if not username or not old_password or not new_password:
        return "username, old_password and new_password are required"
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return f"password must be at least {MIN_PASSWORD_LENGTH} characters"
    if new_password == old_password:
        return "new password must differ from old password"
    return None


@bp.post("/register")
def register():
    data = request.get_json(silent=True)
    if error := _validate(data):
        return jsonify({"error": error}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE username = ?", (data["username"],)).fetchone()
    if existing:
        return jsonify({"error": "username already exists"}), 409

    db.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (data["username"], hash_password(data["password"])),
    )
    db.commit()
    return jsonify({"message": "user registered", "username": data["username"]}), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True)
    if error := _validate(data):
        return jsonify({"error": error}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (data["username"],)).fetchone()
    if user is None:
        # Spend equivalent hashing time so an unknown user can't be
        # distinguished from a wrong password by response latency.
        dummy_verify(data["password"])
        return jsonify({"error": "invalid credentials"}), 401
    if not verify_password(user["password_hash"], data["password"]):
        # Same response for unknown user and wrong password — avoids leaking
        # which usernames exist.
        return jsonify({"error": "invalid credentials"}), 401

    return jsonify({"message": "login successful", "username": data["username"]}), 200


@bp.post("/reset-password")
def reset_password():
    data = request.get_json(silent=True)
    if error := _validate_reset(data):
        return jsonify({"error": error}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (data["username"],)).fetchone()
    if user is None:
        # Spend equivalent hashing time so an unknown user can't be
        # distinguished from a wrong password by response latency.
        dummy_verify(data["old_password"])
        return jsonify({"error": "invalid credentials"}), 401
    if not verify_password(user["password_hash"], data["old_password"]):
        # Same response for unknown user and wrong password — avoids leaking
        # which usernames exist.
        return jsonify({"error": "invalid credentials"}), 401

    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (hash_password(data["new_password"]), user["id"]),
    )
    db.commit()
    return (
        jsonify({"message": "password reset successful", "username": data["username"]}),
        200,
    )


@bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
