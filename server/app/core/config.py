import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


class Settings:
    def __init__(self) -> None:
        self.project_name: str = os.getenv("PROJECT_NAME", "Mood Sync API")
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres:postgres@localhost:5432/MoodSync",
        )
        self.frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
        self.spotify_client_id: str = os.getenv("SPOTIFY_CLIENT_ID", "")
        self.spotify_client_secret: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")
        self.spotify_redirect_uri: str = os.getenv(
            "SPOTIFY_REDIRECT_URI",
            f"{self.frontend_url}/auth/spotify/callback",
        )
        default_scopes = os.getenv("SPOTIFY_SCOPES", "user-read-email user-read-private")
        self.spotify_scopes: str = " ".join(dict.fromkeys([scope for scope in default_scopes.split() if scope]))
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        self.gemini_copy_model: str = os.getenv("GEMINI_COPY_MODEL", "gemini-3.5-flash-lite")
        self.gemini_base_url: str = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
        self.gemini_embedding_model: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
        self.cookie_secure: bool = self.environment.lower() not in {"development", "test"}
        # Render may host the frontend and API on different HTTPS origins.
        self.cookie_samesite: str = "none" if self.cookie_secure else "lax"
        frontend_origin = self.frontend_url
        alternate_frontend_origin = frontend_origin.replace("127.0.0.1", "localhost")
        alternate_localhost_origin = frontend_origin.replace("localhost", "127.0.0.1")
        self.cors_origins: list[str] = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            frontend_origin,
            alternate_frontend_origin,
            alternate_localhost_origin,
        ]
        self.cors_origins = list(dict.fromkeys(self.cors_origins))


settings = Settings()
