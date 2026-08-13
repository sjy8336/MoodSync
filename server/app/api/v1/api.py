from fastapi import APIRouter

from app.api.v1.endpoints import auth, favorites, mood, system

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(favorites.router)
api_router.include_router(mood.router)
api_router.include_router(system.router)
