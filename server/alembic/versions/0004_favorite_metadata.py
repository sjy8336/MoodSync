"""add favorite metadata columns

Revision ID: 0004_favorite_metadata
Revises: 0003_recommendation_playlists
Create Date: 2026-06-28 00:00:00.000000
"""

from alembic import op
from sqlalchemy import text


revision = "0004_favorite_metadata"
down_revision = "0003_recommendation_playlists"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(text("ALTER TABLE favorites ADD COLUMN IF NOT EXISTS album_name VARCHAR(255)"))
    op.execute(text("ALTER TABLE favorites ADD COLUMN IF NOT EXISTS album_image_url VARCHAR(1024)"))
    op.execute(text("ALTER TABLE favorites ADD COLUMN IF NOT EXISTS spotify_url VARCHAR(1024)"))
    op.execute(text("ALTER TABLE favorites ADD COLUMN IF NOT EXISTS duration_ms INTEGER"))
    op.execute(text("ALTER TABLE favorites ADD COLUMN IF NOT EXISTS mood VARCHAR(64)"))
    op.execute(text("ALTER TABLE favorites ADD COLUMN IF NOT EXISTS reason VARCHAR(1000)"))


def downgrade() -> None:
    op.execute(text("ALTER TABLE favorites DROP COLUMN IF EXISTS reason"))
    op.execute(text("ALTER TABLE favorites DROP COLUMN IF EXISTS mood"))
    op.execute(text("ALTER TABLE favorites DROP COLUMN IF EXISTS duration_ms"))
    op.execute(text("ALTER TABLE favorites DROP COLUMN IF EXISTS spotify_url"))
    op.execute(text("ALTER TABLE favorites DROP COLUMN IF EXISTS album_image_url"))
    op.execute(text("ALTER TABLE favorites DROP COLUMN IF EXISTS album_name"))
