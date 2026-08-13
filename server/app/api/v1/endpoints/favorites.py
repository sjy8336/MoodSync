from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.favorite import FavoriteActionResponse, FavoriteCreate, FavoriteListResponse, FavoriteRead
from app.services.current_user import resolve_current_spotify_user
from app.services.favorite_service import list_favorites, remove_favorite, upsert_favorite

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=FavoriteListResponse)
def read_favorites(request: Request, db: Session = Depends(get_db)) -> FavoriteListResponse:
    user = resolve_current_spotify_user(request, db)
    items = list_favorites(db, user.id)
    return FavoriteListResponse(items=items, total=len(items))


@router.post("", response_model=FavoriteRead, status_code=201)
def save_favorite(
    payload: FavoriteCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> FavoriteRead:
    user = resolve_current_spotify_user(request, db)
    return upsert_favorite(db, user.id, payload)


@router.delete("/{track_id}", response_model=FavoriteActionResponse)
def delete_favorite(
    track_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> FavoriteActionResponse:
    user = resolve_current_spotify_user(request, db)
    remove_favorite(db, user.id, track_id)
    return FavoriteActionResponse(message="Favorite removed")
