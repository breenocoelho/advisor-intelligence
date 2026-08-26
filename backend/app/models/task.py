import uuid
from sqlalchemy import Column, String, Date, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN alert_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN insight_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN opportunity_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="chk_tasks_exactly_one_origin",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=True)
    insight_id = Column(UUID(as_uuid=True), ForeignKey("insights.id"), nullable=True)
    opportunity_id = Column(UUID(as_uuid=True), nullable=True)  # FK a adicionar quando "opportunities" existir (Phase 4)
    description = Column(String, nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending | done
    created_at = Column(DateTime(timezone=True), server_default=func.now())