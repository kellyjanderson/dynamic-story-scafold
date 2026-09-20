"""persist scene payload for deterministic replay

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("simulation_runs") as batch_op:
        batch_op.add_column(sa.Column("scene_data", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("simulation_runs") as batch_op:
        batch_op.drop_column("scene_data")
