# app/models/advisor_daily_snapshot.py
import uuid
from sqlalchemy import Column, Numeric, Integer, Date, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class AdvisorDailySnapshot(Base):
    __tablename__ = "advisor_daily_snapshot"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    advisor_id = Column(UUID(as_uuid=True), ForeignKey("advisors.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False)

    aum = Column(Numeric, nullable=True)
    client_count = Column(Integer, nullable=True)
    net_flow = Column(Numeric, nullable=True)  # soma de (purchase - sale) dos clientes do assessor naquele dia

    created_at = Column(DateTime(timezone=True), server_default=func.now())
