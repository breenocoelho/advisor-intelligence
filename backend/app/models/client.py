# app/models/client.py
import uuid
from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    advisor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    xp_client_id = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=False)
    aum = Column(Numeric, default=0)
    last_synced_at = Column(DateTime, nullable=True)