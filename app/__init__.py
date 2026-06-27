"""Flask Auth API — application factory.

Creates and configures the Flask app. Keeping construction inside ``create_app``
(the *app-factory* pattern) lets tests spin up an isolated app with its own
throwaway database, and keeps import-time side effects to a minimum.
"""

import os

from flask import Flask

from . import db


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.environ.get("DATABASE", os.path.join(app.instance_path, "auth.db")),
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    # Register routes and lifecycle hooks.
    from .auth import bp as auth_bp
    from .version_routes import bp as version_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(version_bp)
    app.teardown_appcontext(db.close_db)

    # Ensure the schema exists before the first request.
    with app.app_context():
        db.init_db()

    return app
