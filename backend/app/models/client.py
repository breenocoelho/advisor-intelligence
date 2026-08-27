import uuid
from sqlalchemy import Column, String, Numeric, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    xp_client_id = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=False)

    birth_year = Column(Integer, nullable=True)
    birth_month = Column(Integer, nullable=True)
    marital_status = Column(String, nullable=True)
    activity = Column(String, nullable=True)
    suitability = Column(String, nullable=True)
    declared_wealth_total = Column(Numeric, nullable=True)
    qualified_investor = Column(String, nullable=True)
    professional_investor = Column(String, nullable=True)
    person_type = Column(String, nullable=True)  # "F" pessoa fisica | "J" pessoa juridica
    income_value = Column(Numeric, nullable=True)  # renda declarada
    registration_updated_at = Column(DateTime, nullable=True)  # ultima atualizacao do cadastro NA XP (campo "lastUpdate")

    aum = Column(Numeric, default=0)
    last_synced_at = Column(DateTime, nullable=True)  # quando NOSSO sync rodou por ultimo
    last_contact_at = Column(DateTime, nullable=True)  # registrado via botao no Client 360