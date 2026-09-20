"""Add branch-capable simulation persistence.

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("root_seed", sa.String(length=20), nullable=False),
        sa.Column("scene_id", sa.String(length=255), nullable=False),
        sa.Column("scene_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "timeline_branches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("parent_branch_id", sa.String(length=36), nullable=True),
        sa.Column("parent_checkpoint_id", sa.String(length=36), nullable=True),
        sa.Column("active_head_checkpoint_id", sa.String(length=36), nullable=True),
        sa.Column("entropy_salt", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["simulation_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_branch_id"],
            ["timeline_branches.id"],
        ),
        sa.ForeignKeyConstraint(
            ["parent_checkpoint_id"],
            ["checkpoints.id"],
        ),
        sa.ForeignKeyConstraint(
            ["active_head_checkpoint_id"],
            ["checkpoints.id"],
        ),
    )
    op.create_index(
        "ix_timeline_branches_run_id",
        "timeline_branches",
        ["run_id"],
    )
    op.create_table(
        "checkpoints",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("branch_id", sa.String(length=36), nullable=False),
        sa.Column("previous_checkpoint_id", sa.String(length=36), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("snapshot_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["timeline_branches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["previous_checkpoint_id"],
            ["checkpoints.id"],
        ),
    )
    op.create_index(
        "ix_checkpoints_branch_id",
        "checkpoints",
        ["branch_id"],
    )
    op.create_table(
        "simulation_rounds",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("branch_id", sa.String(length=36), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("input_checkpoint_id", sa.String(length=36), nullable=False),
        sa.Column("output_checkpoint_id", sa.String(length=36), nullable=False),
        sa.Column("audit", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["timeline_branches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["input_checkpoint_id"],
            ["checkpoints.id"],
        ),
        sa.ForeignKeyConstraint(
            ["output_checkpoint_id"],
            ["checkpoints.id"],
        ),
        sa.UniqueConstraint(
            "branch_id",
            "round_number",
            name="uq_simulation_round_branch_number",
        ),
        sa.UniqueConstraint("output_checkpoint_id"),
    )
    op.create_index(
        "ix_simulation_rounds_branch_id",
        "simulation_rounds",
        ["branch_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_simulation_rounds_branch_id",
        table_name="simulation_rounds",
    )
    op.drop_table("simulation_rounds")
    op.drop_index("ix_checkpoints_branch_id", table_name="checkpoints")
    op.drop_table("checkpoints")
    op.drop_index(
        "ix_timeline_branches_run_id",
        table_name="timeline_branches",
    )
    op.drop_table("timeline_branches")
    op.drop_table("simulation_runs")
