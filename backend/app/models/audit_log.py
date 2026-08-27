# app/models/audit_log.py
import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class AuditLog(Base):
    """Trilha de atividade administrativa -- gravada a partir de agora em
    diante nos pontos de escrita que importam pro assessor (tarefas,
    interacoes, contato, status de alerta, thresholds, overrides de
    cadastro). Nao e' um backfill do que ja aconteceu."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    action_type = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
