from fastapi import Request, Response

COOKIE_NAME = "access_token"


def set_auth_cookie(response: Response, token: str, expire_minutes: int, is_production: bool) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=expire_minutes * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


def get_token_from_cookie(request: Request) -> str | None:
    return request.cookies.get(COOKIE_NAME)
