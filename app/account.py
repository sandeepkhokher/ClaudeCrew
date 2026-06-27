"""Account management routes: delete account.

Responses follow the repo-wide JSON shape:
    success -> {"message": ...}
    error   -> {"error": "<human readable reason>"}
"""

from flask import Blueprint, jsonify, request

from .db import get_db
from .security import verify_password

bp = Blueprint("account", __name__)


@bp.delete("/account")
def delete_account():
    data = request.get_json(silent=True)
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "username and password are required"}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (data["username"],)).fetchone()
    if user is None or not verify_password(user["password_hash"], data["password"]):
        # Same response for unknown user and wrong password — avoids leaking
        # which usernames exist.
        return jsonify({"error": "invalid credentials"}), 401

    # SQLite has foreign keys off by default, so ON DELETE CASCADE won't fire —
    # remove the user's reset tokens explicitly to avoid orphaned, redeemable rows.
    db.execute("DELETE FROM password_reset_tokens WHERE user_id = ?", (user["id"],))
    db.execute("DELETE FROM users WHERE username = ?", (data["username"],))
    db.commit()
    return jsonify({"message": "account deleted"}), 200
