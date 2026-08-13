from __future__ import annotations

import json
import re
from collections import OrderedDict
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_SEARCH_URL = f"{SPOTIFY_API_BASE}/search"
PLAYLIST_DEBUG_LOG = Path(__file__).resolve().parents[3] / ".playlist-debug.log"


class SpotifyPlaylistError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _append_debug_log(message: str) -> None:
    try:
        PLAYLIST_DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        with PLAYLIST_DEBUG_LOG.open("a", encoding="utf-8") as fp:
            fp.write(f"{message}\n")
    except OSError:
        pass


def _spotify_request(
    url: str,
    access_token: str,
    method: str = "GET",
    params: dict[str, object] | None = None,
    payload: dict[str, object] | None = None,
) -> dict:
    request_url = url
    if params:
        query = urlencode({k: v for k, v in params.items() if v is not None})
        if query:
            request_url = f"{request_url}?{query}"

    data = None
    headers = {"Authorization": f"Bearer {access_token}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(request_url, data=data, headers=headers, method=method)

    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        auth_header = None
        try:
            auth_header = exc.headers.get("WWW-Authenticate") if exc.headers else None
        except Exception:
            auth_header = None
        _append_debug_log(
            json.dumps(
                {
                    "url": url,
                    "method": method,
                    "status": exc.code,
                    "error_body": error_body or exc.reason,
                    "www_authenticate": auth_header,
                    "payload_keys": sorted(payload.keys()) if isinstance(payload, dict) else None,
                },
                ensure_ascii=False,
            )
        )
        if auth_header and "insufficient_scope" in auth_header.lower():
            raise SpotifyPlaylistError(
                f"Spotify 권한이 부족해요: {auth_header}",
                status_code=exc.code,
            ) from exc
        raise SpotifyPlaylistError(f"Spotify request failed: {error_body or exc.reason}", status_code=exc.code) from exc
    except URLError as exc:
        _append_debug_log(
            json.dumps(
                {
                    "url": url,
                    "method": method,
                    "status": None,
                    "error_body": str(exc.reason),
                    "payload_keys": sorted(payload.keys()) if isinstance(payload, dict) else None,
                },
                ensure_ascii=False,
            )
        )
        raise SpotifyPlaylistError(f"Spotify request failed: {exc.reason}") from exc


def _extract_spotify_track_id(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = value.strip()
    if cleaned.startswith("spotify:track:"):
        candidate = cleaned.rsplit(":", 1)[-1]
        return candidate or None

    if "open.spotify.com/track/" in cleaned:
        parsed = urlparse(cleaned)
        path_bits = parsed.path.rstrip("/").split("/")
        if path_bits and path_bits[-1]:
            candidate = path_bits[-1]
            return candidate or None

    if re.fullmatch(r"[A-Za-z0-9]{22}", cleaned):
        return cleaned

    return None


def _extract_spotify_playlist_id(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if "open.spotify.com/playlist/" not in cleaned:
        return None
    parsed = urlparse(cleaned)
    path_bits = parsed.path.rstrip("/").split("/")
    if path_bits and path_bits[-1]:
        return path_bits[-1]
    return None


def _resolve_track_uri(track: dict[str, object], access_token: str) -> str | None:
    explicit_uri = str(track.get("uri") or "").strip()
    if explicit_uri.startswith("spotify:track:"):
        return explicit_uri

    track_id = _extract_spotify_track_id(str(track.get("track_id") or ""))
    if track_id:
        return f"spotify:track:{track_id}"

    spotify_url = str(track.get("spotify_url") or "").strip()
    track_id = _extract_spotify_track_id(spotify_url)
    if track_id:
        return f"spotify:track:{track_id}"

    name = str(track.get("name") or "").strip()
    artist_name = str(track.get("artist_name") or "").strip()
    if not name:
        return None

    queries = [
        f'track:"{name}" artist:"{artist_name}"'.strip(),
        f"{name} {artist_name}".strip(),
        f'track:"{name}"'.strip(),
        name,
    ]

    for query in queries:
        try:
            response = _spotify_request(
                SPOTIFY_SEARCH_URL,
                access_token,
                params={"q": query, "type": "track", "limit": 5},
            )
        except SpotifyPlaylistError:
            continue

        items = (((response or {}).get("tracks") or {}).get("items")) or []
        for item in items:
            if not isinstance(item, dict):
                continue
            candidate_id = _extract_spotify_track_id(str(item.get("id") or ""))
            if candidate_id:
                return f"spotify:track:{candidate_id}"

    return None


def _dedupe_uris(uris: list[str]) -> list[str]:
    return list(OrderedDict((uri, None) for uri in uris).keys())


def create_playlist_from_recommendation(
    access_token: str,
    spotify_user_id: str,
    recommendation_name: str,
    tracks: list[dict[str, object]],
    playlist_name: str | None = None,
    public: bool = False,
) -> dict[str, object]:
    resolved_uris: list[str] = []
    skipped_count = 0

    for track in tracks:
        uri = _resolve_track_uri(track, access_token)
        if uri:
            resolved_uris.append(uri)
        else:
            skipped_count += 1

    resolved_uris = _dedupe_uris(resolved_uris)
    if not resolved_uris:
        raise SpotifyPlaylistError("추천 결과에서 Spotify 트랙 URI를 찾지 못했어요.")

    title = (playlist_name or recommendation_name or "Mood Sync 추천 플레이리스트").strip()
    title = title[:100]
    description = "Mood Sync가 감정 추천 결과를 바탕으로 만든 플레이리스트예요."

    playlist_payload = {
        "name": title,
        "public": public,
        "description": description,
    }

    created_public = public
    try:
        playlist = _spotify_request(
            f"{SPOTIFY_API_BASE}/users/{spotify_user_id}/playlists",
            access_token,
            method="POST",
            payload=playlist_payload,
        )
    except SpotifyPlaylistError as exc:
        lowered_message = str(exc).lower()
        should_retry_public = (
            not public
            and exc.status_code == 403
            and (
                "scope" in lowered_message
                or "permission" in lowered_message
                or "forbidden" in lowered_message
                or "insufficient" in lowered_message
            )
        )
        if not should_retry_public:
            raise SpotifyPlaylistError(f"플레이리스트 생성 단계에서 실패했어요: {exc}", status_code=exc.status_code) from exc

        playlist_payload["public"] = True
        created_public = True
        try:
            playlist = _spotify_request(
                f"{SPOTIFY_API_BASE}/users/{spotify_user_id}/playlists",
                access_token,
                method="POST",
                payload=playlist_payload,
            )
        except SpotifyPlaylistError as retry_exc:
            raise SpotifyPlaylistError(
                f"플레이리스트 생성 단계에서 공개 재시도까지 실패했어요: {retry_exc}",
                status_code=retry_exc.status_code,
            ) from retry_exc

    playlist_id = str(playlist.get("id") or "").strip()
    if not playlist_id:
        playlist_id = _extract_spotify_playlist_id(str(playlist.get("external_urls", {}).get("spotify") or "")) or ""
    if not playlist_id:
        raise SpotifyPlaylistError("Spotify 플레이리스트를 만들었지만 ID를 확인하지 못했어요.")

    try:
        _spotify_request(
            f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks",
            access_token,
            method="POST",
            payload={"uris": resolved_uris},
        )
    except SpotifyPlaylistError as exc:
        raise SpotifyPlaylistError(
            f"플레이리스트에 곡을 추가하는 단계에서 실패했어요: {exc}",
            status_code=exc.status_code,
        ) from exc

    playlist_url = (playlist.get("external_urls") or {}).get("spotify")
    if not isinstance(playlist_url, str) or not playlist_url.strip():
        playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"

    return {
        "playlist_id": playlist_id,
        "playlist_url": playlist_url,
        "playlist_name": title,
        "track_count": len(resolved_uris),
        "skipped_track_count": skipped_count,
        "message": (
            f"Spotify 플레이리스트를 만들었어요. {len(resolved_uris)}곡을 담았고 "
            f"{skipped_count}곡은 URI를 찾지 못해 건너뛰었어요."
            + (" 비공개 생성이 막혀 공개 플레이리스트로 만들었어요." if created_public and not public else "")
        ),
        "is_public": created_public,
    }
