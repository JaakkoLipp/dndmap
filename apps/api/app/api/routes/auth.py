import secrets

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookie import clear_auth_cookie, set_auth_cookie
from app.auth.dependencies import CurrentUser
from app.auth.jwt import mint_token
from app.auth.providers import get_provider
from app.auth.state import sign_state, verify_state
from app.core.config import Settings
from app.core.rate_limit import AuthRateLimit
from app.db import models as orm
from app.db.session import DbSession
from app.domain.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_provider_credentials(settings: Settings, provider_name: str) -> tuple[str, str]:
    client_id = getattr(settings, f"oauth_{provider_name}_client_id", None)
    client_secret = getattr(settings, f"oauth_{provider_name}_client_secret", None)
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"{provider_name} OAuth is not configured",
        )
    return client_id, client_secret


@router.get("/{provider}/login")
async def oauth_login(provider: str, request: Request) -> RedirectResponse:
    settings: Settings = request.app.state.settings
    provider_adapter = get_provider(provider)
    if not provider_adapter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown OAuth provider")

    if not settings.session_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="session_secret not configured")

    client_id, _ = _get_provider_credentials(settings, provider)
    nonce = secrets.token_urlsafe(16)
    state = sign_state(settings.session_secret, nonce)
    redirect_uri = f"{settings.oauth_redirect_base_url}/{provider}/callback"
    url = provider_adapter.build_authorization_url(client_id, redirect_uri, state)
    return RedirectResponse(url)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    response: Response,
    db: DbSession,
    _limit: AuthRateLimit = None,
) -> RedirectResponse:
    settings: Settings = request.app.state.settings

    if not settings.session_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="session_secret not configured")

    if not verify_state(settings.session_secret, state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

    provider_adapter = get_provider(provider)
    if not provider_adapter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown OAuth provider")

    client_id, client_secret = _get_provider_credentials(settings, provider)
    redirect_uri = f"{settings.oauth_redirect_base_url}/{provider}/callback"

    try:
        tokens = await provider_adapter.exchange_code(code, redirect_uri, client_id, client_secret)
        access_token = tokens.get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="No access token from provider")
        profile = await provider_adapter.get_user_profile(access_token)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OAuth provider error") from exc

    user = await _upsert_user(db, provider, profile, tokens)

    if not settings.jwt_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="jwt_secret not configured")

    jwt_token = mint_token(user.id, settings)
    redirect_resp = RedirectResponse(url="/campaigns", status_code=302)
    set_auth_cookie(
        redirect_resp,
        jwt_token,
        settings.jwt_expire_minutes,
        settings.environment == "production",
    )
    return redirect_resp


@router.post("/logout")
async def logout(response: Response) -> dict:
    clear_auth_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUser) -> orm.User:
    return user


async def _upsert_user(
    db: AsyncSession,
    provider: str,
    profile: object,
    tokens: dict,
) -> orm.User:
    result = await db.execute(
        select(orm.OAuthIdentity).where(
            orm.OAuthIdentity.provider == provider,
            orm.OAuthIdentity.provider_user_id == profile.provider_user_id,
        )
    )
    identity = result.scalar_one_or_none()

    if identity:
        identity.access_token = tokens.get("access_token")
        identity.refresh_token = tokens.get("refresh_token")
        identity.raw_profile = tokens
        user = await db.get(orm.User, identity.user_id)
        user.display_name = profile.display_name
        user.avatar_url = profile.avatar_url
        await db.commit()
        await db.refresh(user)
        return user

    user = orm.User(display_name=profile.display_name, avatar_url=profile.avatar_url)
    db.add(user)
    await db.flush()

    identity = orm.OAuthIdentity(
        user_id=user.id,
        provider=provider,
        provider_user_id=profile.provider_user_id,
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        raw_profile=tokens,
    )
    db.add(identity)
    await db.commit()
    await db.refresh(user)
    return user
