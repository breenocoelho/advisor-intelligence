# app/models/alert.py
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    alert_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    explanation = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="new")
    created_at = Column(DateTime(timezone=True), server_default=func.now())