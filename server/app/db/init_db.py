from app.db.base import Base
from app.db.session import engine
from app.models import Favorite, MoodRecord, Recommendation, RecommendationPlaylist, User  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
