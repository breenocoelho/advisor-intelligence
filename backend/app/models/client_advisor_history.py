# app/models/client_advisor_history.py
import uuid
from sqlalchemy import Column, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class ClientAdvisorHistory(Base):
    __tablename__ = "client_advisor_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    advisor_id = Column(UUID(as_uuid=True), ForeignKey("advisors.id"), nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)  # null = vínculo vigente