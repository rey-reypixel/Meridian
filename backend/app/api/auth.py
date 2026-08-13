from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from jose import jwt
from datetime import datetime, timedelta
from urllib.parse import quote
from app.config import settings
from app.db import models
from app.dependencies import get_db, get_current_user
from app.oauth.google import exchange_code_for_token, get_user_info
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login():
    """Get Google OAuth login URL"""
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.google_client_id}&"
        f"redirect_uri={settings.oauth_redirect_uri}&"
        f"response_type=code&"
        f"scope=openid%20profile%20email"
    )
    return {"auth_url": google_auth_url}


@router.get("/google/callback")
async def oauth_callback(code: str = Query(...), db: Session = Depends(get_db)):
    """
    Handle OAuth callback from Google. Deliberately not at /auth/callback -
    that path is the frontend SPA's own route (reads ?token= after this
    handler's redirect below). Same-origin deployments proxy /auth/* to
    this backend except for that one frontend-owned path, so Google's
    provider-facing callback needs a distinct path to avoid colliding
    with it.
    """
    try:
        # Exchange code for token
        token_response = await exchange_code_for_token(code)
        access_token = token_response.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get access token"
            )

        # Get user info
        user_info = await get_user_info(access_token)

        email = user_info.get("email")
        name = user_info.get("name")
        google_id = user_info.get("id")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not get email from Google"
            )

        # Create or update user in database
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            user = models.User(
                email=email,
                name=name,
                oauth_provider="google",
                oauth_id=google_id
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created new user: {email}")
        else:
            # Update existing user
            user.oauth_id = google_id
            db.commit()
            logger.info(f"Updated user: {email}")

        # Create JWT token
        jwt_token = create_access_token(email)

        # Hand off to the frontend, which reads ?token= and stores it -
        # a bare JSON response here has no real page for the browser to
        # land on after Google's redirect.
        redirect_url = f"{settings.frontend_url}/auth/callback?token={quote(jwt_token)}"
        return RedirectResponse(url=redirect_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/logout")
async def logout():
    """Logout endpoint"""
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_me(current_user: models.User = Depends(get_current_user)):
    """
    Resolve the current user from the stored JWT. Needed because the OAuth
    redirect only carries the token itself (see oauth_callback) - anything
    that reloads the page (not just the first login moment) needs a way to
    re-derive who's logged in from the token alone.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
    }


def create_access_token(email: str) -> str:
    """Create JWT access token"""
    expire = datetime.utcnow() + timedelta(days=7)
    payload = {
        "sub": email,
        "exp": expire
    }
    encoded_jwt = jwt.encode(
        payload,
        settings.secret_key,
        algorithm="HS256"
    )
    return encoded_jwt
