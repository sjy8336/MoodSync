from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import SpotifyUser

DEMO_PROVIDER_USER_ID_PREFIX = "demo:"


def upsert_spotify_user(db: Session, profile: dict) -> User:
    spotify_id = str(profile.get("id") or "").strip()
    if not spotify_id:
        raise ValueError("Spotify profile id is required")

    email = profile.get("email")
    display_name = profile.get("display_name") or profile.get("id") or "Spotify Listener"
    avatar_url = None
    images = profile.get("images")
    if isinstance(images, list) and images:
        first_image = images[0]
        if isinstance(first_image, dict):
            avatar_url = first_image.get("url")

    user = db.scalar(select(User).where(User.provider_user_id == spotify_id))

    if user is None and email:
        user = db.scalar(select(User).where(User.email == email))

    if user is None:
        user = User(
            auth_provider="spotify",
            provider_user_id=spotify_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            hashed_password=None,
        )
        db.add(user)
    else:
        user.auth_provider = "spotify"
        user.provider_user_id = spotify_id
        user.email = email or user.email
        user.display_name = display_name or user.display_name
        user.avatar_url = avatar_url or user.avatar_url

    db.commit()
    db.refresh(user)
    return user


def get_or_create_demo_user(db: Session, preset: str | None = None) -> User:
    preset_key = (preset or "default").strip().lower() or "default"
    provider_user_id = f"{DEMO_PROVIDER_USER_ID_PREFIX}{preset_key}"
    display_name = "Demo User" if preset_key == "default" else f"Demo User ({preset_key})"

    user = db.scalar(select(User).where(User.provider_user_id == provider_user_id))
    if user is None:
        user = User(
            auth_provider="demo",
            provider_user_id=provider_user_id,
            email=None,
            display_name=display_name,
            avatar_url=None,
            hashed_password=None,
        )
        db.add(user)
    else:
        user.auth_provider = "demo"
        user.display_name = display_name or user.display_name
        user.email = None
        user.avatar_url = None
        user.hashed_password = None

    db.commit()
    db.refresh(user)
    return user


def serialize_spotify_user(user: User) -> SpotifyUser:
    return SpotifyUser(
        id=user.id,
        auth_provider=user.auth_provider,
        provider_user_id=user.provider_user_id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
    )


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)
