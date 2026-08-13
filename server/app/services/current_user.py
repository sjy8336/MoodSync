from fastapi import HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.auth import ACCESS_TOKEN_COOKIE_NAME, REFRESH_TOKEN_COOKIE_NAME, USER_ID_COOKIE_NAME
from app.core.config import settings
from app.services.spotify_oauth import SpotifyOAuthError, fetch_spotify_profile, refresh_access_token
from app.services.user_service import get_user_by_id, upsert_spotify_user


def _store_refreshed_token(request: Request, token_payload: dict) -> None:
    access_token = str(token_payload.get("access_token") or "").strip()
    if not access_token:
        return
    request.state.spotify_access_token = access_token
    request.state.spotify_access_token_expires_in = int(token_payload.get("expires_in", 3600))
    refresh_token = token_payload.get("refresh_token")
    if isinstance(refresh_token, str) and refresh_token.strip():
        request.state.spotify_refresh_token = refresh_token.strip()


def sync_spotify_token_cookies(response: Response, request: Request) -> None:
    access_token = getattr(request.state, "spotify_access_token", None)
    expires_in = getattr(request.state, "spotify_access_token_expires_in", None)
    refresh_token = getattr(request.state, "spotify_refresh_token", None)
    if access_token:
        response.set_cookie(
            key=ACCESS_TOKEN_COOKIE_NAME,
            value=str(access_token),
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=int(expires_in or 3600),
            path="/",
        )
    if refresh_token:
        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            value=str(refresh_token),
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=60 * 60 * 24 * 30,
            path="/",
        )


def get_spotify_access_token(request: Request, db: Session, allow_refresh: bool = True, validate: bool = False) -> str:
    access_token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if access_token:
        if validate:
            try:
                fetch_spotify_profile(access_token)
            except SpotifyOAuthError:
                access_token = ""
            else:
                request.state.spotify_access_token = access_token
                return access_token
        else:
            request.state.spotify_access_token = access_token
            return access_token

    if not allow_refresh:
        raise HTTPException(status_code=401, detail="Not authenticated")

    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        token_payload = refresh_access_token(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            refresh_token=refresh_token,
        )
    except SpotifyOAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    _store_refreshed_token(request, token_payload)
    refreshed_access_token = getattr(request.state, "spotify_access_token", None)
    if not refreshed_access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return str(refreshed_access_token)


def resolve_current_spotify_user(request: Request, db: Session):
    user_id_value = request.cookies.get(USER_ID_COOKIE_NAME)
    if user_id_value:
        try:
            user = get_user_by_id(db, int(user_id_value))
        except ValueError:
            user = None
        if user is not None and user.auth_provider == "demo":
            return user

    try:
        access_token = get_spotify_access_token(request, db, allow_refresh=True, validate=True)
        profile = fetch_spotify_profile(access_token)
        return upsert_spotify_user(db, profile)
    except HTTPException:
        pass
    except SpotifyOAuthError:
        pass

    if user_id_value:
        try:
            user = get_user_by_id(db, int(user_id_value))
        except ValueError:
            user = None
        if user is not None:
            access_token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
            if access_token:
                request.state.spotify_access_token = access_token
            else:
                try:
                    get_spotify_access_token(request, db, allow_refresh=True)
                except HTTPException:
                    pass
            return user

    raise HTTPException(status_code=401, detail="Not authenticated")
