"""
AutoBug AI — Auth API (GitHub OAuth)
"""

from __future__ import annotations

import secrets

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


@router.get("/github")
async def github_login():
    """Redirect to GitHub OAuth authorization page."""
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "repo read:user user:email",
        "state": state,
    }
    from urllib.parse import urlencode
    url = f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/github/callback")
async def github_callback(code: str, state: str | None = None):
    """Handle GitHub OAuth callback and return JWT."""
    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        gh_access_token = token_data.get("access_token")
        if not gh_access_token:
            raise HTTPException(status_code=400, detail="GitHub OAuth failed")

        # Fetch user info
        user_resp = await client.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {gh_access_token}"},
        )
        user_data = user_resp.json()

    # Create JWT
    jwt_token = create_access_token(
        data={
            "sub": str(user_data.get("id")),
            "login": user_data.get("login"),
            "name": user_data.get("name"),
            "avatar": user_data.get("avatar_url"),
            "gh_token": gh_access_token,
        }
    )

    # Redirect frontend with token
    return RedirectResponse(
        url=f"{settings.frontend_url}/auth/callback?token={jwt_token}"
    )


@router.get("/me")
async def get_current_user_info(request: Request):
    """Return current user info from JWT (if authenticated)."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth.split(" ", 1)[1]
    from app.core.security import verify_token
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload
