# app/models/opportunity.py
import uuid
from sqlalchemy import Column, String, Numeric, Integer, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class Opportunity(Base):
    """Promovida a partir de alertas com severity='opportunity' (idle_cash,
    upcoming_maturity) pelo opportunity_engine -- nao e' um sinal novo, e' o
    mesmo sinal ganhando um lifecycle proprio (detected -> ... -> closed)
    em vez de so' aparecer como alerta na lista."""
    __tablename__ = "opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    source_alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=True)
    opportunity_type = Column(String, nullable=False)  # mesmo valor do alert_type de origem
    status = Column(String, nullable=False, default="detected")
    # detected | reviewed | assigned | contacted | proposal | executed | won | lost | closed
    potential_value = Column(Numeric, nullable=True)
    urgency = Column(Integer, nullable=True)  # 0-100, heuristica v1
    confidence = Column(Integer, nullable=True)  # 0-100, heuristica v1
    score = Column(Integer, nullable=True)  # 0-100, composicao explicavel das 3 acima
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
