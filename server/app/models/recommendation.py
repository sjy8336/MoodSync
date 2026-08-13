from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mood: Mapped[str] = mapped_column(String(32), index=True)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_vibes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    context_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    rag_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_profile: Mapped[dict] = mapped_column(JSONB, default=dict)
    tracks: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
