# app/models/insight.py
import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base

class Insight(Base):
    __tablename__ = "insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    insight_type = Column(String, nullable=False)
    asset_class = Column(String, nullable=True)  # null para insights nao especificos de classe de ativo
    severity = Column(String, nullable=False)
    title = Column(String, nullable=False)
    explanation = Column(Text, nullable=True)
    evidence = Column(JSONB, nullable=True)  # JSON estruturado, nunca gerado por LLM
    status = Column(String, nullable=False, default="new")  # new | viewed | dismissed | actioned
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
