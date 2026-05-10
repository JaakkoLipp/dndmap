from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode

import httpx


@dataclass
class OAuthProfile:
    provider_user_id: str
    display_name: str
    avatar_url: str | None


class OAuthProvider(Protocol):
    provider_name: str

    def build_authorization_url(self, client_id: str, redirect_uri: str, state: str) -> str: ...

    async def exchange_code(self, code: str, redirect_uri: str, client_id: str, client_secret: str) -> dict: ...

    async def get_user_profile(self, access_token: str) -> OAuthProfile: ...


class DiscordOAuthProvider:
    provider_name = "discord"
    _AUTH_URL = "https://discord.com/api/oauth2/authorize"
    _TOKEN_URL = "https://discord.com/api/oauth2/token"
    _USER_URL = "https://discord.com/api/users/@me"

    def build_authorization_url(self, client_id: str, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "identify",
            "state": state,
        }
        return self._AUTH_URL + "?" + urlencode(params)

    async def exchange_code(self, code: str, redirect_uri: str, client_id: str, client_secret: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_user_profile(self, access_token: str) -> OAuthProfile:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self._USER_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
        avatar = None
        if data.get("avatar"):
            avatar = f"https://cdn.discordapp.com/avatars/{data['id']}/{data['avatar']}.png"
        return OAuthProfile(
            provider_user_id=str(data["id"]),
            display_name=data.get("global_name") or data.get("username") or str(data["id"]),
            avatar_url=avatar,
        )


class GoogleOAuthProvider:
    provider_name = "google"
    _AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    _TOKEN_URL = "https://oauth2.googleapis.com/token"
    _USER_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

    def build_authorization_url(self, client_id: str, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid profile",
            "state": state,
            "access_type": "offline",
        }
        return self._AUTH_URL + "?" + urlencode(params)

    async def exchange_code(self, code: str, redirect_uri: str, client_id: str, client_secret: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_user_profile(self, access_token: str) -> OAuthProfile:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self._USER_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
        return OAuthProfile(
            provider_user_id=data["sub"],
            display_name=data.get("name") or data.get("email") or data["sub"],
            avatar_url=data.get("picture"),
        )


class GitHubOAuthProvider:
    provider_name = "github"
    _AUTH_URL = "https://github.com/login/oauth/authorize"
    _TOKEN_URL = "https://github.com/login/oauth/access_token"
    _USER_URL = "https://api.github.com/user"

    def build_authorization_url(self, client_id: str, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:user",
            "state": state,
        }
        return self._AUTH_URL + "?" + urlencode(params)

    async def exchange_code(self, code: str, redirect_uri: str, client_id: str, client_secret: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_user_profile(self, access_token: str) -> OAuthProfile:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self._USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        return OAuthProfile(
            provider_user_id=str(data["id"]),
            display_name=data.get("name") or data.get("login") or str(data["id"]),
            avatar_url=data.get("avatar_url"),
        )


_PROVIDERS: dict[str, DiscordOAuthProvider | GoogleOAuthProvider | GitHubOAuthProvider] = {
    "discord": DiscordOAuthProvider(),
    "google": GoogleOAuthProvider(),
    "github": GitHubOAuthProvider(),
}


def get_provider(name: str) -> DiscordOAuthProvider | GoogleOAuthProvider | GitHubOAuthProvider | None:
    return _PROVIDERS.get(name)
