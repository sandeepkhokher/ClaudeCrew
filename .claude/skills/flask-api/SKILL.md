---
name: flask-api
description: Conventions for this Flask Auth API — app-factory pattern, blueprints, JSON response shapes, and safe SQLite access. Use when adding or modifying API endpoints, routes, or database code.
---

# Flask API conventions

## Structure
- **App factory** lives in `app/__init__.py` (`create_app(test_config=None)`). Never construct a global `Flask()` at import time.
- **Routes** go in blueprints (`app/auth.py` → `bp = Blueprint(...)`). Register them inside `create_app`.
- **DB access** goes through `app/db.py` helpers (`get_db()`), which cache the connection on `g` and close it on teardown.

## Endpoints
- Use method decorators: `@bp.post("/x")`, `@bp.get("/x")`.
- Read JSON with `request.get_json(silent=True)` and validate before use.
- **Response shape is consistent:**
  - success → `jsonify({"message": ..., ...}), <2xx>`
  - error → `jsonify({"error": "<human readable>"}), <4xx>`

## Status codes
- `201` created · `200` ok · `400` bad input · `401` bad credentials · `409` conflict (duplicate).

## Security (non-negotiable)
- **Always** use parameterized SQL (`db.execute("... WHERE username = ?", (name,))`). Never f-string/`%`/`+` SQL.
- Hash passwords via `app/security.py` (`hash_password` / `verify_password`). Never store or log raw passwords.
- Login returns the **same** error for "unknown user" and "wrong password" — don't leak which usernames exist.

## When adding an endpoint
1. Add the route to the relevant blueprint following the shapes above.
2. Add validation (reuse `_validate` in `auth.py` where it fits).
3. Add tests (see the `python-testing` skill).
