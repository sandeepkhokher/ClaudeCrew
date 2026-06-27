"""Password hashing and basic credential validation.

We never store raw passwords — only salted hashes produced by Werkzeug
(PBKDF2 by default).
"""

from werkzeug.security import check_password_hash, generate_password_hash

MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)
