"""Signed OAuth ``state`` parameter.

The state must survive the round-trip to the OAuth provider and back, and
both validate that the callback is for a request we initiated (nonce) and
carry the post-login redirect target (``next``). It is signed with
:class:`itsdangerous.URLSafeTimedSerializer` keyed by ``SESSION_SECRET``.
"""

from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


def sign_state(secret: str, payload: Any) -> str:
    s = URLSafeTimedSerializer(secret)
    return s.dumps(payload)


def verify_state(secret: str, signed: str, max_age: int = 300) -> Any | None:
    """Return the signed payload if valid, ``None`` if expired or tampered."""
    s = URLSafeTimedSerializer(secret)
    try:
        return s.loads(signed, max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
