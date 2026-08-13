from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(description="User email")
    password: str = Field(description="User password")


class LoginResponse(BaseModel):
    message: str


class DemoLoginRequest(BaseModel):
    preset: str | None = Field(default=None, description="Optional demo preset name")


class DemoLoginResponse(BaseModel):
    message: str
    mode: str = "demo"
    preset: str | None = None
    user: SpotifyUser


class SpotifyLoginResponse(BaseModel):
    authorize_url: str
    state: str


class SpotifyUser(BaseModel):
    id: int
    auth_provider: str | None = None
    provider_user_id: str | None = None
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None


class SpotifyCallbackResponse(BaseModel):
    message: str
    user: SpotifyUser


class SpotifyMeResponse(BaseModel):
    user: SpotifyUser


class SpotifyLogoutResponse(BaseModel):
    message: str
