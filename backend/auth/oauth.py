"""OAuth provider implementations for Google, GitHub, and Microsoft."""

import secrets
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

import httpx

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class OAuthUserInfo:
    """Standardized user info from OAuth providers."""

    provider: str
    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None


class OAuthProvider(ABC):
    """Abstract base class for OAuth providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'google', 'github')."""
        pass

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Get the OAuth authorization URL."""
        pass

    @abstractmethod
    async def exchange_code(self, code: str) -> Optional[str]:
        """Exchange authorization code for access token."""
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> Optional[OAuthUserInfo]:
        """Get user info using the access token."""
        pass

    def generate_state(self) -> str:
        """Generate a secure state parameter for CSRF protection."""
        return secrets.token_urlsafe(32)


class GoogleOAuth(OAuthProvider):
    """Google OAuth 2.0 implementation."""

    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    @property
    def name(self) -> str:
        return "google"

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": settings.effective_google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "select_account",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> Optional[str]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "client_id": settings.effective_google_client_id,
                        "client_secret": settings.effective_google_client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": settings.google_redirect_uri,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("access_token")
            except httpx.HTTPError as e:
                logger.error(f"Google token exchange failed: {e}")
                return None

    async def get_user_info(self, access_token: str) -> Optional[OAuthUserInfo]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                data = response.json()

                return OAuthUserInfo(
                    provider="google",
                    id=data["id"],
                    email=data["email"],
                    name=data.get("name", data["email"].split("@")[0]),
                    avatar_url=data.get("picture"),
                )
            except httpx.HTTPError as e:
                logger.error(f"Google userinfo failed: {e}")
                return None


class GitHubOAuth(OAuthProvider):
    """GitHub OAuth 2.0 implementation."""

    AUTH_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USERINFO_URL = "https://api.github.com/user"
    EMAILS_URL = "https://api.github.com/user/emails"

    @property
    def name(self) -> str:
        return "github"

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": settings.effective_github_client_id,
            "redirect_uri": settings.github_redirect_uri,
            "scope": "user:email read:user",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> Optional[str]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.TOKEN_URL,
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": settings.effective_github_client_id,
                        "client_secret": settings.effective_github_client_secret,
                        "code": code,
                        "redirect_uri": settings.github_redirect_uri,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("access_token")
            except httpx.HTTPError as e:
                logger.error(f"GitHub token exchange failed: {e}")
                return None

    async def get_user_info(self, access_token: str) -> Optional[OAuthUserInfo]:
        async with httpx.AsyncClient() as client:
            try:
                # Get user profile
                response = await client.get(
                    self.USERINFO_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                response.raise_for_status()
                user_data = response.json()

                # Get primary email (may be private)
                email = user_data.get("email")
                if not email:
                    email = await self._get_primary_email(client, access_token)

                if not email:
                    logger.error("GitHub user has no email")
                    return None

                return OAuthUserInfo(
                    provider="github",
                    id=str(user_data["id"]),
                    email=email,
                    name=user_data.get("name") or user_data["login"],
                    avatar_url=user_data.get("avatar_url"),
                )
            except httpx.HTTPError as e:
                logger.error(f"GitHub userinfo failed: {e}")
                return None

    async def _get_primary_email(self, client: httpx.AsyncClient, access_token: str) -> Optional[str]:
        """Get the user's primary email from GitHub."""
        try:
            response = await client.get(
                self.EMAILS_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            response.raise_for_status()
            emails = response.json()

            # Find primary email
            for email_info in emails:
                if email_info.get("primary") and email_info.get("verified"):
                    return email_info["email"]

            # Fallback to first verified email
            for email_info in emails:
                if email_info.get("verified"):
                    return email_info["email"]

            return None
        except httpx.HTTPError as e:
            logger.error(f"GitHub emails failed: {e}")
            return None


class MicrosoftOAuth(OAuthProvider):
    """Microsoft OAuth 2.0 implementation using Microsoft Entra ID."""

    AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    USERINFO_URL = "https://graph.microsoft.com/v1.0/me"

    @property
    def name(self) -> str:
        return "microsoft"

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": settings.effective_microsoft_client_id,
            "redirect_uri": settings.microsoft_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile User.Read",
            "state": state,
            "prompt": "select_account",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> Optional[str]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "client_id": settings.effective_microsoft_client_id,
                        "client_secret": settings.effective_microsoft_client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": settings.microsoft_redirect_uri,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("access_token")
            except httpx.HTTPError as e:
                logger.error(f"Microsoft token exchange failed: {e}")
                return None

    async def get_user_info(self, access_token: str) -> Optional[OAuthUserInfo]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                data = response.json()

                email = data.get("mail") or data.get("userPrincipalName")
                if not email:
                    logger.error("Microsoft user has no email")
                    return None

                return OAuthUserInfo(
                    provider="microsoft",
                    id=data["id"],
                    email=email,
                    name=data.get("displayName", email.split("@")[0]),
                    avatar_url=None,
                )
            except httpx.HTTPError as e:
                logger.error(f"Microsoft userinfo failed: {e}")
                return None


# Provider registry
OAUTH_PROVIDERS = {
    "google": GoogleOAuth(),
    "github": GitHubOAuth(),
    "microsoft": MicrosoftOAuth(),
}


def get_oauth_provider(provider_name: str) -> Optional[OAuthProvider]:
    """Get an OAuth provider by name."""
    return OAUTH_PROVIDERS.get(provider_name.lower())
