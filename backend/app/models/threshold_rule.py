# app/models/threshold_rule.py
import uuid
from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class ThresholdRule(Base):
    __tablename__ = "threshold_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    signal_key = Column(String, nullable=False)
    suitability_profile = Column(String, nullable=True)  # null = default da org para esse signal_key
    value = Column(Numeric, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String, nullable=True)
