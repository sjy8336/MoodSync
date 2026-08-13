from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from urllib.parse import urlparse

from app.core.auth import ACCESS_TOKEN_COOKIE_NAME, AUTH_MODE_COOKIE_NAME, REFRESH_TOKEN_COOKIE_NAME, USER_ID_COOKIE_NAME
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    DemoLoginRequest,
    DemoLoginResponse,
    LoginRequest,
    LoginResponse,
    SpotifyCallbackResponse,
    SpotifyLoginResponse,
    SpotifyMeResponse,
    SpotifyLogoutResponse,
)
from app.services.spotify_oauth import (
    SpotifyOAuthError,
    build_authorize_url,
    exchange_code_for_token,
    fetch_spotify_profile,
)
from app.services.user_service import get_or_create_demo_user, serialize_spotify_user, upsert_spotify_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _resolve_frontend_origin(frontend_origin: str | None) -> str:
    candidate = (frontend_origin or settings.frontend_url).strip()
    parsed = urlparse(candidate)
    if not parsed.scheme or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid frontend origin")

    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in settings.cors_origins:
        raise HTTPException(status_code=400, detail="Frontend origin is not allowed")
    return origin


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    return LoginResponse(message=f"Login requested for {payload.email}")


@router.post("/demo/start", response_model=DemoLoginResponse)
def demo_start(
    payload: DemoLoginRequest | None = None,
    db: Session = Depends(get_db),
) -> JSONResponse:
    demo_user = get_or_create_demo_user(db, preset=payload.preset if payload else None)
    response = JSONResponse(
        content=DemoLoginResponse(
            message="Demo session started",
            preset=payload.preset if payload else None,
            user=serialize_spotify_user(demo_user),
        ).model_dump()
    )
    response.set_cookie(
        key=USER_ID_COOKIE_NAME,
        value=str(demo_user.id),
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
    response.set_cookie(
        key=AUTH_MODE_COOKIE_NAME,
        value="demo",
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE_NAME, path="/")
    return response


@router.get("/demo/me", response_model=DemoLoginResponse)
def demo_me(
    request: Request,
    db: Session = Depends(get_db),
) -> DemoLoginResponse:
    user_id_value = request.cookies.get(USER_ID_COOKIE_NAME)
    if not user_id_value:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_record = db.get(User, int(user_id_value))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Not authenticated") from exc

    if user_record is None or user_record.auth_provider != "demo":
        raise HTTPException(status_code=401, detail="Not authenticated")

    return DemoLoginResponse(message="Demo session active", user=serialize_spotify_user(user_record))


@router.post("/demo/logout", response_model=SpotifyLogoutResponse)
def demo_logout() -> JSONResponse:
    response = JSONResponse(content=SpotifyLogoutResponse(message="Demo session cleared").model_dump())
    response.delete_cookie(USER_ID_COOKIE_NAME, path="/")
    response.delete_cookie(AUTH_MODE_COOKIE_NAME, path="/")
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE_NAME, path="/")
    return response


@router.get("/spotify/login")
def spotify_login(
    state: str | None = Query(default=None, description="OAuth state value"),
    frontend_origin: str | None = Query(default=None, description="Frontend origin"),
) -> RedirectResponse:
    if not settings.spotify_client_id:
        raise HTTPException(status_code=500, detail="Spotify client id is not configured")

    state_value = state or token_urlsafe(16)
    resolved_frontend_origin = _resolve_frontend_origin(frontend_origin)
    authorize_url = build_authorize_url(
        client_id=settings.spotify_client_id,
        redirect_uri=f"{resolved_frontend_origin}/auth/spotify/callback",
        state=state_value,
        scopes=settings.spotify_scopes,
    )
    return RedirectResponse(authorize_url, status_code=302)


@router.get("/spotify/login/preview", response_model=SpotifyLoginResponse)
def spotify_login_preview(state: str | None = Query(default=None, description="OAuth state value")) -> SpotifyLoginResponse:
    state_value = state or token_urlsafe(16)
    resolved_frontend_origin = _resolve_frontend_origin(None)
    authorize_url = build_authorize_url(
        client_id=settings.spotify_client_id,
        redirect_uri=f"{resolved_frontend_origin}/auth/spotify/callback",
        state=state_value,
        scopes=settings.spotify_scopes,
    )
    return SpotifyLoginResponse(authorize_url=authorize_url, state=state_value)


@router.get("/spotify/callback", response_model=SpotifyCallbackResponse)
def spotify_callback(
    db: Session = Depends(get_db),
    code: str = Query(..., description="Spotify authorization code"),
    state: str = Query(..., description="OAuth state value"),
    frontend_origin: str | None = Query(default=None, description="Frontend origin"),
) -> JSONResponse:
    if not settings.spotify_client_id or not settings.spotify_client_secret:
        raise HTTPException(status_code=500, detail="Spotify OAuth is not configured")

    try:
        resolved_frontend_origin = _resolve_frontend_origin(frontend_origin)
        token_payload = exchange_code_for_token(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            code=code,
            redirect_uri=f"{resolved_frontend_origin}/auth/spotify/callback",
        )
        profile = fetch_spotify_profile(token_payload["access_token"])
        user_record = upsert_spotify_user(db, profile)
    except SpotifyOAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except OperationalError as exc:
        raise HTTPException(status_code=503, detail="Database connection failed") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payload = SpotifyCallbackResponse(message="Spotify login success", user=serialize_spotify_user(user_record))
    response = JSONResponse(content=payload.model_dump())
    response.set_cookie(
        key=USER_ID_COOKIE_NAME,
        value=str(user_record.id),
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
    response.set_cookie(
        key=AUTH_MODE_COOKIE_NAME,
        value="spotify",
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=token_payload["access_token"],
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=int(token_payload.get("expires_in", 3600)),
        path="/",
    )
    refresh_token = token_payload.get("refresh_token")
    if refresh_token:
        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            value=refresh_token,
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=60 * 60 * 24 * 30,
            path="/",
        )
    return response


@router.get("/me", response_model=SpotifyMeResponse)
def me(
    request: Request,
    db: Session = Depends(get_db),
) -> SpotifyMeResponse:
    user_id_value = request.cookies.get(USER_ID_COOKIE_NAME)
    user_record = None
    if user_id_value:
        try:
            user_record = db.get(User, int(user_id_value))
        except ValueError:
            user_record = None

    if user_id_value and user_record is not None:
        return SpotifyMeResponse(user=serialize_spotify_user(user_record))

    access_token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        profile = fetch_spotify_profile(access_token)
        user_record = upsert_spotify_user(db, profile)
    except SpotifyOAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except OperationalError as exc:
        raise HTTPException(status_code=503, detail="Database connection failed") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SpotifyMeResponse(user=serialize_spotify_user(user_record))


@router.post("/logout", response_model=SpotifyLogoutResponse)
def logout() -> JSONResponse:
    response = JSONResponse(content=SpotifyLogoutResponse(message="Logged out successfully").model_dump())
    response.delete_cookie(USER_ID_COOKIE_NAME, path="/")
    response.delete_cookie(AUTH_MODE_COOKIE_NAME, path="/")
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE_NAME, path="/")
    return response
