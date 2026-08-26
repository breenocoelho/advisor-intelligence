# app/models/client_daily_snapshot.py
import uuid
from sqlalchemy import Column, String, Numeric, Integer, Date, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base

class ClientDailySnapshot(Base):
    __tablename__ = "client_daily_snapshot"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False)

    aum = Column(Numeric, nullable=True)
    allocation_json = Column(JSONB, nullable=True)  # {"fixedIncome": 0.55, "equities": 0.20, ...}
    top_issuer_concentration = Column(Numeric, nullable=True)
    liquidity_pct = Column(Numeric, nullable=True)
    monthly_purchase_value = Column(Numeric, nullable=True)
    monthly_sale_value = Column(Numeric, nullable=True)
    health_score = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
