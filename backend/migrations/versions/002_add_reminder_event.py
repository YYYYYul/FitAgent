"""add_reminder_event

Revision ID: 002
Revises: 001
Create Date: 2026-05-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reminder_event",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("reminder_job_id", sa.String(36), sa.ForeignKey("reminder_job.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("training_plan.id", ondelete="SET NULL"), nullable=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), default="sent"),
        sa.Column("triggered_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reminder_event")
