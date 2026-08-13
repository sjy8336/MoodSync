from __future__ import annotations

import base64
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_ME_URL = "https://api.spotify.com/v1/me"


class SpotifyOAuthError(RuntimeError):
    pass


def build_authorize_url(*, client_id: str, redirect_uri: str, state: str, scopes: str) -> str:
    query = urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "state": state,
            "show_dialog": "true",
        }
    )
    return f"{SPOTIFY_AUTHORIZE_URL}?{query}"


def exchange_code_for_token(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    payload = urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
    ).encode("utf-8")
    request = Request(
        SPOTIFY_TOKEN_URL,
        data=payload,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        raise SpotifyOAuthError(f"Spotify token exchange failed: {error_body or exc.reason}") from exc
    except URLError as exc:
        raise SpotifyOAuthError(f"Spotify token exchange failed: {exc.reason}") from exc


def refresh_access_token(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> dict:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    payload = urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")
    request = Request(
        SPOTIFY_TOKEN_URL,
        data=payload,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        raise SpotifyOAuthError(f"Spotify token refresh failed: {error_body or exc.reason}") from exc
    except URLError as exc:
        raise SpotifyOAuthError(f"Spotify token refresh failed: {exc.reason}") from exc


def fetch_spotify_profile(access_token: str) -> dict:
    request = Request(
        SPOTIFY_ME_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )

    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        raise SpotifyOAuthError(f"Spotify profile request failed: {error_body or exc.reason}") from exc
    except URLError as exc:
        raise SpotifyOAuthError(f"Spotify profile request failed: {exc.reason}") from exc
