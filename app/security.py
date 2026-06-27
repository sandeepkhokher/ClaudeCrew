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


# Precomputed once at import so we can spend the same PBKDF2 work when a user
# is not found — keeps login/reset timing constant and avoids username
# enumeration via latency.
_DUMMY_HASH = generate_password_hash("dummy-password-for-timing")


def dummy_verify(password: str) -> bool:
    """Verify against a throwaway hash to match real-verify timing. Always False."""
    check_password_hash(_DUMMY_HASH, password)
    return False
