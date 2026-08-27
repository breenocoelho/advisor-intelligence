from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    xp_client_id: str | None
    name: str
    aum: float | None
    suitability: str | None
    last_synced_at: datetime | None
    last_contact_at: datetime | None = None
    advisor_name: str | None = None
    active_alerts_count: int = 0
    priority_score: int = 0


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    client_name: str | None = None
    alert_type: str
    severity: str
    explanation: str | None
    status: str
    created_at: datetime | None


class PositionOut(BaseModel):
    id: UUID
    asset_id: UUID
    asset_name: str
    asset_class: str
    market_value: float
    quantity: float | None
    due_date: date | None
    issuer: str | None
    rate: float | None
    index_description: str | None
    position_date: date
    period_purchase_value: float = 0.0
    period_sale_value: float = 0.0


class TaskCreate(BaseModel):
    """Body opcional do POST /alerts/{id}/tasks -- preenchido pelo modal
    do frontend. Se omitido, o backend usa defaults (explicacao do
    alerta + prazo de 7 dias)."""
    description: str | None = None
    due_date: date | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    client_name: str | None = None
    alert_id: UUID | None = None
    insight_id: UUID | None = None
    opportunity_id: UUID | None = None
    description: str
    due_date: date | None
    status: str
    created_at: datetime | None
    severity: str | None = None  # da origem (alerta/insight), se houver -- usado para ordenar por prioridade


class InsightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    client_name: str | None = None
    insight_type: str
    asset_class: str | None
    severity: str
    title: str
    explanation: str | None
    evidence: dict | None
    status: str
    created_at: datetime | None
    updated_at: datetime | None


class ThresholdRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    signal_key: str
    suitability_profile: str | None
    value: float
    updated_at: datetime | None
    updated_by: str | None


class ThresholdRuleIn(BaseModel):
    signal_key: str
    suitability_profile: str | None = None
    value: float


class SnapshotPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_date: date
    aum: float | None
    health_score: int | None


class ClientDetailOut(ClientOut):
    birth_year: int | None = None
    birth_month: int | None = None
    marital_status: str | None = None
    activity: str | None = None
    declared_wealth_total: float | None = None
    qualified_investor: str | None = None
    professional_investor: str | None = None
    positions: list[PositionOut] = []
    alerts: list[AlertOut] = []
    tasks: list[TaskOut] = []
    insights: list[InsightOut] = []
    health_score: int | None = None
    aum_trend: list[SnapshotPointOut] = []