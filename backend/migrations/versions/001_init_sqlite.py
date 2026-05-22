"""init_sqlite

Revision ID: 001
Revises:
Create Date: 2026-05-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_profile",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100)),
        sa.Column("height_cm", sa.Float),
        sa.Column("weight_kg", sa.Float),
        sa.Column("goal", sa.String(50)),
        sa.Column("training_location", sa.String(50)),
        sa.Column("weekly_days", sa.Integer),
        sa.Column("experience_level", sa.String(50)),
        sa.Column("preferred_time", sa.String(5)),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "training_plan",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(20), default="active"),
        sa.Column("goal", sa.String(50)),
        sa.Column("weekly_days", sa.Integer),
        sa.Column("plan_data", sa.JSON, nullable=False),
        sa.Column("plan_summary", sa.Text),
        sa.Column("version", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "reminder_job",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("training_plan.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day_of_week", sa.Integer, nullable=False),
        sa.Column("remind_time", sa.String(5), nullable=False),
        sa.Column("channel", sa.String(50), default="web"),
        sa.Column("status", sa.String(20), default="active"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "workout_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("training_plan.id", ondelete="SET NULL"), nullable=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("parsed_record", sa.JSON),
        sa.Column("duration_min", sa.Integer),
        sa.Column("rpe", sa.Integer),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_workout_user_date", "workout_log", ["user_id", "date"])

    op.create_table(
        "agent_trace",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("intent", sa.String(50)),
        sa.Column("intent_confidence", sa.Float),
        sa.Column("plan_steps", sa.JSON),
        sa.Column("tools_called", sa.JSON),
        sa.Column("replan_reason", sa.Text),
        sa.Column("rag_queries", sa.JSON),
        sa.Column("final_response", sa.Text),
        sa.Column("latency_total_ms", sa.Integer),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_trace_user_session", "agent_trace", ["user_id", "session_id"])
    op.create_index("idx_trace_created", "agent_trace", ["created_at"])


def downgrade() -> None:
    op.drop_table("agent_trace")
    op.drop_table("workout_log")
    op.drop_table("reminder_job")
    op.drop_table("training_plan")
    op.drop_table("user_profile")
