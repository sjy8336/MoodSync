# mood-sync

감정 기반 음악 추천 서비스를 위한 기본 프로젝트 구조입니다.

Spotify Web API를 활용해 트랙 메타데이터와 앨범 이미지를 제공하되,
Spotify Developer Policy 및 Design Guidelines에 따라
각 콘텐츠에 Spotify 출처와 원본 서비스 링크를 함께 제공했습니다.

## 프로젝트 구조

```text
mood-sync/
├── .gitignore
├── README.md
├── client/
│   ├── .gitignore
│   ├── eslint.config.js
│   ├── package-lock.json
│   ├── package.json
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── assets/
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── vite.config.js
├── server/
│   ├── app/             # 메인 애플리케이션 패키지
│   │   ├── __init__.py
│   │   ├── main.py      # 앱 실행 및 라우터 설정 (Entry point)
│   │   ├── api/         # 엔드포인트 모듈 (Controller 역할)
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── auth.py
│   │   │   │   │   └── mood.py
│   │   │   │   └── api.py
│   │   ├── core/        # 설정 및 보안 (Config, Security)
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── models/      # DB 모델 (SQLAlchemy, PostgreSQL 연동)
│   │   │   └── user.py
│   │   ├── schemas/     # Pydantic 데이터 검증 (DTO 역할)
│   │   │   └── mood.py
│   │   ├── services/    # 비즈니스 로직 (Spotify API 통신, 감정 분석 로직)
│   │   │   ├── spotify_service.py
│   │   │   └── analysis_service.py
│   │   └── db/          # DB 세션 설정
│   │       └── session.py
│   ├── .env             # 환경 변수
│   ├── requirements.txt # 의존성 라이브러리
│   └── alembic/         # DB 마이그레이션 (선택 사항)
```

## 실행 방법

1. 프론트엔드 의존성 설치
    - `cd client && npm install`
2. 백엔드 의존성 설치
    - `cd ../server && python3 -m pip install -r requirements.txt`
3. 백엔드 실행
    - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
4. 프론트엔드 실행
    - `cd ../client && npm run dev`

## 배포 체크

- `ENVIRONMENT=production`으로 설정하면 로그인 쿠키가 안전한 전송 조건에 맞춰집니다.
- `FRONTEND_URL`에는 실제 배포된 프론트엔드 주소를 넣어 주세요.
- `VITE_API_BASE_URL`은 프론트와 백엔드를 분리 배포할 때 백엔드 공개 주소를 가리켜야 합니다.
- `DATABASE_URL`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `OPENAI_API_KEY`, `GEMINI_API_KEY` 같은 비밀값은 배포 환경 변수로 주입하세요.
- 프론트와 백엔드의 도메인이 달라지면 CORS 허용 목록도 `FRONTEND_URL` 기준으로 맞아야 합니다.

## 컬러팔레트

| 역할                           | 색상명        | Hex     |
| ------------------------------ | ------------- | ------- |
| 배경                           | Cream         | #FAF8F4 |
| 배경 (소프트)                  | Warm Linen    | #F1ECE3 |
| 서피스                         | White         | #FFFFFF |
| 잉크 (주)                      | Deep Plum     | #211C26 |
| 잉크 (보조)                    | Dusty Mauve   | #6E6678 |
| 잉크 (희미)                    | Lavender Mist | #A39CAC |
| 선 (기본)                      | Parchment     | #E5DFD3 |
| 선 (강조)                      | Warm Stone    | #D6CFC1 |
| 감정 - 기쁨                    | Coral         | #FF6B5E |
| 감정 - 차분                    | Lavender      | #7B7FF0 |
| 감정 - 설렘                    | Amber         | #FFB648 |
| 기쁨 소프트                    | Blush         | #FFEAE6 |
| 차분 소프트                    | Periwinkle    | #ECEDFD |
| 설렘 소프트                    | Buttercup     | #FFF3DE |
| Spotify 그린 (공식, 변형 금지) | Spotify Green | #1ED760 |
| Spotify 블랙 (공식, 변형 금지) | Spotify Black | #191414 |
