"""initial schema: users, api_requests

Revision ID: 0001
Revises:
Create Date: 2026-08-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("oauth_provider", sa.String(), nullable=True),
        sa.Column("oauth_id", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "api_requests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("original_model", sa.String(), nullable=True),
        sa.Column("routed_model", sa.String(), nullable=True),
        sa.Column("original_cost", sa.Float(), nullable=True),
        sa.Column("optimized_cost", sa.Float(), nullable=True),
        sa.Column("savings", sa.Float(), nullable=True),
        sa.Column("optimizations_applied", sa.JSON(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_api_requests_id", "api_requests", ["id"])
    op.create_index("ix_api_requests_user_id", "api_requests", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_api_requests_user_id", table_name="api_requests")
    op.drop_index("ix_api_requests_id", table_name="api_requests")
    op.drop_table("api_requests")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
