from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


def sign_state(secret: str, nonce: str) -> str:
    s = URLSafeTimedSerializer(secret)
    return s.dumps(nonce)


def verify_state(secret: str, signed: str, max_age: int = 300) -> str | None:
    """Returns the nonce if valid, None if expired or tampered."""
    s = URLSafeTimedSerializer(secret)
    try:
        return s.loads(signed, max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
