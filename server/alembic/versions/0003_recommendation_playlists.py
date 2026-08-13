"""add recommendation playlists

Revision ID: 0003_recommendation_playlists
Revises: 0002_spotify_user_fields
Create Date: 2026-06-28 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_recommendation_playlists"
down_revision = "0002_spotify_user_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_playlists",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("recommendation_id", sa.Integer(), nullable=False),
        sa.Column("playlist_id", sa.String(length=128), nullable=False),
        sa.Column("playlist_url", sa.String(length=512), nullable=True),
        sa.Column("playlist_name", sa.String(length=255), nullable=False),
        sa.Column("track_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_track_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recommendations.id"]),
        sa.UniqueConstraint("playlist_id", name="uq_recommendation_playlists_playlist_id"),
    )
    op.create_index(op.f("ix_recommendation_playlists_id"), "recommendation_playlists", ["id"], unique=False)
    op.create_index(
        op.f("ix_recommendation_playlists_user_id"),
        "recommendation_playlists",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recommendation_playlists_recommendation_id"),
        "recommendation_playlists",
        ["recommendation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recommendation_playlists_playlist_id"),
        "recommendation_playlists",
        ["playlist_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_recommendation_playlists_playlist_id"), table_name="recommendation_playlists")
    op.drop_index(op.f("ix_recommendation_playlists_recommendation_id"), table_name="recommendation_playlists")
    op.drop_index(op.f("ix_recommendation_playlists_user_id"), table_name="recommendation_playlists")
    op.drop_index(op.f("ix_recommendation_playlists_id"), table_name="recommendation_playlists")
    op.drop_table("recommendation_playlists")
