# app/models/client_field_override.py
import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class ClientFieldOverride(Base):
    """Override manual de um campo cadastral que veio da XP (ex: XP diz
    email X, assessor sabe que mudou pra Y). O valor original continua
    vindo do sync normal -- aqui so' guardamos o override e o cadastro
    sinaliza os campos com override ativo."""
    __tablename__ = "client_field_overrides"
    __table_args__ = (UniqueConstraint("client_id", "field_name", name="uq_client_field_override"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    field_name = Column(String, nullable=False)
    override_value = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
