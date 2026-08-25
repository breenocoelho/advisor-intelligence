# app/models/position.py
import uuid
from sqlalchemy import Column, Numeric, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class Position(Base):
    __tablename__ = "positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    quantity = Column(Numeric, nullable=False)
    market_value = Column(Numeric, nullable=False)
    position_date = Column(Date, nullable=False)