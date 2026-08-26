# app/models/positivador_snapshot.py
import uuid
from sqlalchemy import Column, String, Numeric, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class PositivadorSnapshot(Base):
    __tablename__ = "positivador_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    advisor_id = Column(UUID(as_uuid=True), ForeignKey("advisors.id"), nullable=True)
    reference_date = Column(Date, nullable=False)
    status = Column(String, nullable=True)              # "ATIVO" | "INATIVO"
    activated_in_month = Column(String, nullable=True)
    churned_in_month = Column(String, nullable=True)
    net_capture_in_month = Column(Numeric, nullable=True)
    financial_applications = Column(Numeric, nullable=True)
    revenue_in_month = Column(Numeric, nullable=True)
    suitability = Column(String, nullable=True)