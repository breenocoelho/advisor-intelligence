# app/models/client_extended_field.py
import uuid
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class ClientExtendedFieldDefinition(Base):
    """Campo customizado no cadastro do cliente, criado pelo proprio
    escritorio (nao vem da XP). Ex: 'family' -> 'Família'."""
    __tablename__ = "client_extended_field_definitions"
    __table_args__ = (UniqueConstraint("org_id", "key", name="uq_extended_field_org_key"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    key = Column(String, nullable=False)
    label = Column(String, nullable=False)


class ClientExtendedFieldOption(Base):
    """Um valor possivel dentro de um campo customizado. Ex: dentro de
    'Família', a opcao 'Família Fernandes'."""
    __tablename__ = "client_extended_field_options"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_definition_id = Column(UUID(as_uuid=True), ForeignKey("client_extended_field_definitions.id"), nullable=False)
    value = Column(String, nullable=False)


class ClientExtendedFieldAssignment(Base):
    """Liga um cliente a uma opcao de um campo customizado. Varios
    clientes podem compartilhar a mesma opcao (ex: os 2 irmaos da mesma
    familia)."""
    __tablename__ = "client_extended_field_assignments"
    __table_args__ = (UniqueConstraint("client_id", "option_id", name="uq_extended_field_assignment"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    option_id = Column(UUID(as_uuid=True), ForeignKey("client_extended_field_options.id"), nullable=False)
