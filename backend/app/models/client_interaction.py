# app/models/client_interaction.py
import uuid
from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class ClientInteraction(Base):
    __tablename__ = "client_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    advisor_id = Column(UUID(as_uuid=True), ForeignKey("advisors.id"), nullable=True)
    interaction_type = Column(String, nullable=False)  # Meeting | Phone | Email | WhatsApp | Other
    interaction_date = Column(Date, nullable=False)
    subject = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
