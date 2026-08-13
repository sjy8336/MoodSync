# Mood Sync API Spec

> 문서 기준일: 2026-06-27
>
> 현재 서버 구조와 MVP 우선순위를 기준으로 정리한 API 명세입니다.

## 1. Overview

- Base URL: `/api/v1`
- Health check: `/api/health`
- Content-Type: `application/json`
- Charset: `utf-8`

## 2. Common Conventions

### HTTP Status

- `200 OK`: 조회/추천 성공
- `201 Created`: 저장 성공
- `204 No Content`: 삭제 성공
- `400 Bad Request`: 요청값 검증 실패
- `401 Unauthorized`: 인증 실패 또는 토큰 만료
- `403 Forbidden`: 권한 없음
- `404 Not Found`: 리소스 없음
- `409 Conflict`: 중복 데이터
- `500 Internal Server Error`: 서버 오류

### Error Response

```json
{
  "detail": "유효하지 않은 요청입니다.",
  "code": "VALIDATION_ERROR"
}
```

### Auth Strategy

- MVP에서는 Spotify OAuth를 기준으로 한다.
- 프론트는 로그인 버튼 클릭 시 백엔드 로그인 시작 URL로 이동한다.
- 백엔드는 Spotify callback을 처리한 뒤 access token, refresh token 또는 세션을 저장한다.
- 이후 사용자 전용 API는 `Authorization: Bearer <token>` 또는 세션 쿠키를 사용한다.

> 현재 코드의 `POST /api/v1/auth/login`은 placeholder이므로, 실제 구현 시 Spotify OAuth 라우트로 대체하는 것을 권장한다.

## 3. Data Models

### Mood

권장 감정 값:

- `happy`
- `sad`
- `calm`
- `angry`
- `anxious`
- `neutral`

### Track Summary

```json
{
  "track_id": "spotify-track-id",
  "name": "Blinding Lights",
  "artist_name": "The Weeknd",
  "album_name": "After Hours",
  "album_image_url": "https://...",
  "spotify_url": "https://open.spotify.com/track/...",
  "preview_url": "https://p.scdn.co/mp3-preview/...",
  "duration_ms": 200040
}
```

---

## 4. MVP 1순위 APIs

### 4.1 Health Check

#### `GET /api/health`

- Purpose: 서버 상태 확인
- Auth: 없음

**Response 200**

```json
{
  "ok": "true",
  "message": "Mood Sync FastAPI server is running."
}
```

---

### 4.2 Spotify Login Start

#### `GET /api/v1/auth/spotify/login`

- Purpose: Spotify 로그인 페이지로 redirect
- Auth: 없음

**Behavior**

- 백엔드가 Spotify authorize URL로 redirect한다.
- `state` 값을 함께 생성해 CSRF를 방지한다.

**Response**

- `302 Found` redirect to Spotify authorization page

---

### 4.3 Spotify Callback

#### `GET /api/v1/auth/spotify/callback`

- Purpose: Spotify authorization code를 받아 access token 교환
- Auth: 없음

**Query Parameters**

- `code` string, required
- `state` string, required

**Response 200**

```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "display_name": "Mood Listener"
  },
  "message": "Spotify login success"
}
```

---

### 4.4 Current Placeholder Login

#### `POST /api/v1/auth/login`

- Purpose: 현재 서버에 존재하는 임시 로그인 엔드포인트
- Auth: 없음
- Status: temporary

**Request**

```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

**Response 200**

```json
{
  "message": "Login requested for user@example.com"
}
```

---

### 4.5 Mood Recommendation

#### `POST /api/v1/mood/recommend`

- Purpose: 감정을 기반으로 추천 트랙 반환
- Auth: optional for early MVP, required later when 저장 기능 연결

**Request**

```json
{
  "text": "오늘은 기분이 좋아요",
  "mood": "happy"
}
```

**Request Fields**

- `text` string, optional
- `mood` string, optional

**Behavior**

- `mood`가 있으면 그 값을 우선 사용한다.
- `mood`가 없으면 `text` 기반 감정 추론을 수행한다.
- 현재는 Spotify API 대신 추천 서비스의 임시 catalog를 반환한다.

**Response 200**

```json
{
  "mood": "happy",
  "tracks": [
    "Happy - Pharrell Williams",
    "Good as Hell - Lizzo"
  ]
}
```

---

## 5. 2순위 APIs

### 5.1 감정 기록 저장

#### `POST /api/v1/moods`

- Purpose: 사용자가 선택하거나 분석된 감정을 저장
- Auth: required

**Request**

```json
{
  "mood": "happy",
  "text": "오늘은 기분이 좋아요",
  "source": "manual"
}
```

**Response 201**

```json
{
  "id": 10,
  "mood": "happy",
  "text": "오늘은 기분이 좋아요",
  "source": "manual",
  "created_at": "2026-06-27T10:05:00+09:00"
}
```

---

### 5.2 추천 결과 저장

#### `POST /api/v1/recommendations`

- Purpose: 추천된 트랙 묶음을 저장
- Auth: required

**Request**

```json
{
  "mood": "happy",
  "query": "오늘 기분",
  "tracks": [
    {
      "track_id": "spotify-track-id",
      "name": "Blinding Lights",
      "artist_name": "The Weeknd",
      "album_name": "After Hours",
      "album_image_url": "https://...",
      "spotify_url": "https://open.spotify.com/track/...",
      "preview_url": "https://...",
      "duration_ms": 200040
    }
  ]
}
```

**Response 201**

```json
{
  "recommendation_id": 1,
  "message": "Recommendation saved"
}
```

---

### 5.3 좋아요 / 즐겨찾기

#### `POST /api/v1/favorites`

- Purpose: 특정 트랙을 즐겨찾기로 저장
- Auth: required

**Request**

```json
{
  "track_id": "spotify-track-id",
  "track_name": "Blinding Lights",
  "artist_name": "The Weeknd"
}
```

**Response 201**

```json
{
  "id": 1,
  "track_id": "spotify-track-id",
  "is_favorite": true
}
```

#### `DELETE /api/v1/favorites/{track_id}`

- Purpose: 즐겨찾기 해제
- Auth: required

**Response 204**

---

### 5.4 추천 히스토리

#### `GET /api/v1/history/recommendations`

- Purpose: 사용자의 추천 히스토리 조회
- Auth: required

**Query Parameters**

- `limit` integer, optional, default `20`
- `offset` integer, optional, default `0`

**Response 200**

```json
{
  "items": [
    {
      "recommendation_id": 1,
      "mood": "happy",
      "query": "오늘 기분",
      "created_at": "2026-06-27T10:00:00+09:00"
    }
  ],
  "total": 1
}
```

---

## 6. 3순위 APIs

### 6.1 Text Mood Analysis

#### `POST /api/v1/analysis/mood`

- Purpose: 텍스트를 감정으로 분류
- Auth: optional

**Request**

```json
{
  "text": "요즘 좀 지치고 우울해"
}
```

**Response 200**

```json
{
  "mood": "sad",
  "confidence": 0.87
}
```

---

### 6.2 User Taste Recommendation

#### `POST /api/v1/recommendations/personalized`

- Purpose: 감정 + 사용자 취향을 결합한 추천
- Auth: required

**Request**

```json
{
  "mood": "calm",
  "seed_tracks": ["spotify-track-id-1"],
  "limit": 10
}
```

**Response 200**

```json
{
  "mood": "calm",
  "tracks": []
}
```

---

### 6.3 Recent Mood Stats

#### `GET /api/v1/stats/moods`

- Purpose: 최근 감정 통계 조회
- Auth: required

**Query Parameters**

- `period` string, optional, values: `7d`, `30d`, `90d`

**Response 200**

```json
{
  "period": "7d",
  "summary": {
    "happy": 3,
    "sad": 1,
    "calm": 2
  }
}
```

---

### 6.4 Mood Calendar

#### `GET /api/v1/calendar/moods`

- Purpose: 날짜별 감정 기록 조회
- Auth: required

**Query Parameters**

- `from` string, required, `YYYY-MM-DD`
- `to` string, required, `YYYY-MM-DD`

**Response 200**

```json
{
  "items": [
    {
      "date": "2026-06-27",
      "mood": "happy"
    }
  ]
}
```

---

### 6.5 Playlist Generation

#### `POST /api/v1/playlists`

- Purpose: 추천 결과를 기반으로 Spotify 플레이리스트 생성
- Auth: required

**Request**

```json
{
  "name": "Mood Sync - Happy Mix",
  "track_ids": ["spotify-track-id-1", "spotify-track-id-2"]
}
```

**Response 201**

```json
{
  "playlist_id": "spotify-playlist-id",
  "playlist_url": "https://open.spotify.com/playlist/..."
}
```

---

## 7. 4순위 APIs

### 7.1 OpenAI-based Mood Analysis

#### `POST /api/v1/analysis/mood/advanced`

- Purpose: OpenAI API 기반 정교한 감정 분석
- Auth: optional or required depending on product policy

**Request**

```json
{
  "text": "오늘 발표가 끝나서 긴장이 풀렸어"
}
```

**Response 200**

```json
{
  "mood": "relieved",
  "confidence": 0.92,
  "reason": "stress relief and positive sentiment"
}
```

---

### 7.2 Advanced Recommendation

#### `POST /api/v1/recommendations/advanced`

- Purpose: 감정, 최근 히스토리, 선호도, 플레이리스트 반응을 모두 반영한 추천
- Auth: required

**Response 200**

```json
{
  "mood": "happy",
  "tracks": []
}
```

---

### 7.3 Deployment Automation

- health check 강화
- CI에서 테스트 실행
- migration 자동화
- 환경변수 검증

## 8. Suggested Backend File Mapping

- `server/app/main.py`
- `server/app/api/v1/api.py`
- `server/app/api/v1/endpoints/auth.py`
- `server/app/api/v1/endpoints/mood.py`
- `server/app/schemas/*`
- `server/app/models/*`
- `server/app/services/*`

## 9. MVP Implementation Order

1. `GET /api/health`
2. `GET /api/v1/auth/spotify/login`
3. `GET /api/v1/auth/spotify/callback`
4. `POST /api/v1/mood/recommend`
5. `POST /api/v1/moods`
6. `POST /api/v1/recommendations`
7. `GET /api/v1/history/recommendations`

## 10. Notes

- 현재 `POST /api/v1/auth/login`은 실제 Spotify 인증이 아니라 placeholder다.
- 현재 `POST /api/v1/mood/recommend`는 임시 추천 카탈로그를 반환한다.
- MVP가 안정화되면 응답을 더 엄격한 DTO 구조로 정리하는 것을 추천한다.

