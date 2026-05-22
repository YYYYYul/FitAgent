import uuid
from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, JSON, Index
from app.db.base import Base, TimestampMixin


class AgentTrace(Base, TimestampMixin):
    __tablename__ = "agent_trace"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(36), nullable=False)
    intent = Column(String(50))
    intent_confidence = Column(Float)
    plan_steps = Column(JSON)
    tools_called = Column(JSON)
    replan_reason = Column(Text)
    rag_queries = Column(JSON)
    final_response = Column(Text)
    latency_total_ms = Column(Integer)

    __table_args__ = (
        Index("idx_trace_user_session", "user_id", "session_id"),
        Index("idx_trace_created", "created_at"),
    )
