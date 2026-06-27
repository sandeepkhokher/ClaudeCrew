"""Version endpoint blueprint.

Exposes the running application's version as JSON. The version is read from the
project's ``pyproject.toml`` when available, falling back to a hardcoded default
so the endpoint stays functional even outside an installed/source checkout.
"""

import tomllib
from pathlib import Path

from flask import Blueprint, jsonify

bp = Blueprint("version", __name__)

_DEFAULT_VERSION = "0.1.0"
_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _read_version() -> str:
    """Return the project version from pyproject.toml, or the default."""
    try:
        with _PYPROJECT.open("rb") as fh:
            data = tomllib.load(fh)
        return data["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return _DEFAULT_VERSION


@bp.get("/version")
def version():
    return jsonify({"version": _read_version()}), 200
