"""Stats routes: aggregate information about the API.

All responses are JSON with the consistent success shape used across the app.
"""

from flask import Blueprint, jsonify

from .db import get_db

bp = Blueprint("stats", __name__)


@bp.get("/stats")
def stats():
    db = get_db()
    count = db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    return jsonify({"users": count}), 200
