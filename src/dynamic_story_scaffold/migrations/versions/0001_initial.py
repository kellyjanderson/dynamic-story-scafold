"""Initial application database.

Revision ID: 0001
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "installations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("package_version", sa.String(length=64), nullable=False),
        sa.Column("python_version", sa.String(length=64), nullable=False),
        sa.Column("os_name", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("database_path", sa.String(), nullable=False),
        sa.Column("installed_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "builds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("package_version", sa.String(length=64), nullable=False),
        sa.Column("git_commit", sa.String(length=64), nullable=True),
        sa.Column("git_branch", sa.String(length=255), nullable=True),
        sa.Column("output_dir", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "settings",
        sa.Column("key", sa.String(length=255), primary_key=True),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("build_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["build_id"], ["builds.id"]),
    )


def downgrade() -> None:
    op.drop_table("artifacts")
    op.drop_table("settings")
    op.drop_table("builds")
    op.drop_table("installations")
