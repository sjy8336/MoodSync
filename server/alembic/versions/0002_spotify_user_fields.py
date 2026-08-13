"""add spotify user fields

Revision ID: 0002_spotify_user_fields
Revises: 0001_initial_schema
Create Date: 2026-06-28 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_spotify_user_fields"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auth_provider", sa.String(length=32), server_default=sa.text("'spotify'"), nullable=False),
    )
    op.add_column("users", sa.Column("provider_user_id", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("display_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=512), nullable=True))

    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=True)
    op.alter_column("users", "hashed_password", existing_type=sa.String(length=255), nullable=True)

    op.create_index(op.f("ix_users_auth_provider"), "users", ["auth_provider"], unique=False)
    op.create_index(op.f("ix_users_provider_user_id"), "users", ["provider_user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_provider_user_id"), table_name="users")
    op.drop_index(op.f("ix_users_auth_provider"), table_name="users")

    op.alter_column("users", "hashed_password", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=False)

    op.drop_column("users", "avatar_url")
    op.drop_column("users", "display_name")
    op.drop_column("users", "provider_user_id")
    op.drop_column("users", "auth_provider")
