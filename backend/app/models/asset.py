# app/models/asset.py
import uuid
from sqlalchemy import Column, String, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    xp_asset_id = Column(String, unique=True, nullable=True)  # UUID do "assetId" da XP
    asset_code = Column(String, nullable=True)
    isin_code = Column(String, nullable=True)
    cnpj_code = Column(String, nullable=True)
    asset_class = Column(String, nullable=False)  # coe|funds|fixedIncome|treasury|stock|tradedFunds|pensionFunds|repo|checkingAccount
    name = Column(String, nullable=False)
    issuer = Column(String, nullable=True)
    due_date = Column(Date, nullable=True)
    index_description = Column(String, nullable=True)
    rate = Column(Numeric, nullable=True)
    manager_name = Column(String, nullable=True)  # gestora (fundos/previdencia/tesouro) -- null p/ RF direta/acoes
    payment_frequency = Column(String, nullable=True)  # "Mensal" | "Semestral" | "No vencimento" | "Variavel (dividendos)" | "No resgate"
    liquidity_days = Column(Numeric, nullable=True)  # prazo de resgate em dias (D+X); null = nao aplicavel/desconhecido
    minimum_investment = Column(Numeric, nullable=True)
    risk_rating = Column(String, nullable=True)  # "Baixo" | "Medio" | "Alto"