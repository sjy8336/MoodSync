from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine
from app.schemas.system import DatabaseHealthResponse

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/db-health", response_model=DatabaseHealthResponse)
def db_health_check() -> DatabaseHealthResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return DatabaseHealthResponse(
            connected=True,
            message="Database connection successful.",
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {exc.__class__.__name__}",
        ) from exc

