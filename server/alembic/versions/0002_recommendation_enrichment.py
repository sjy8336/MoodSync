"""enrich recommendation storage

Revision ID: 0002_recommendation_enrichment
Revises: 0001_initial_schema
Create Date: 2026-08-12 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_recommendation_enrichment"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recommendations",
        sa.Column("message", sa.Text(), nullable=True),
    )
    op.add_column(
        "recommendations",
        sa.Column(
            "selected_vibes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "recommendations",
        sa.Column(
            "context_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "recommendations",
        sa.Column("rag_context", sa.Text(), nullable=True),
    )
    op.add_column(
        "recommendations",
        sa.Column("llm_context", sa.Text(), nullable=True),
    )
    op.add_column(
        "recommendations",
        sa.Column(
            "generation_profile",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("recommendations", "generation_profile")
    op.drop_column("recommendations", "llm_context")
    op.drop_column("recommendations", "rag_context")
    op.drop_column("recommendations", "context_snapshot")
    op.drop_column("recommendations", "selected_vibes")
    op.drop_column("recommendations", "message")
