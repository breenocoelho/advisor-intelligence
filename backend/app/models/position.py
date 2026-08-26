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
    quantity = Column(Numeric, nullable=True)
    market_value = Column(Numeric, nullable=False)          # closingValue
    period_purchase_value = Column(Numeric, default=0)      # purchaseValue
    period_sale_value = Column(Numeric, default=0)          # saleValue
    position_date = Column(Date, nullable=False)