from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ScoreBreakdownItem(BaseModel):
    direction: Literal["up", "down"]
    label: str
    detail: str


class BehavioralFindingOut(BaseModel):
    finding_type: str
    severity: str
    label: str
    detail: str


class SegmentOut(BaseModel):
    key: str
    label: str
    category: str  # "financial" | "relationship" | "behavioral"
    reason: str


class ChangeItemOut(BaseModel):
    label: str
    direction: str  # "up" | "down" | "neutral"
    value_display: str


class KeyInsightOut(BaseModel):
    text: str
    severity: str
    link_tab: str


class MaturityBucketOut(BaseModel):
    bucket: str  # "0-30" | "31-90" | "91-180" | "180+"
    value: float


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    xp_client_id: str | None
    name: str
    aum: float | None
    suitability: str | None
    person_type: str | None = None
    income_value: float | None = None
    registration_updated_at: datetime | None = None
    last_synced_at: datetime | None
    last_contact_at: datetime | None = None
    advisor_name: str | None = None
    active_alerts_count: int = 0
    priority_score: int = 0
    health_score: int | None = None
    health_score_breakdown: list[ScoreBreakdownItem] = []
    relationship_score: int | None = None
    relationship_score_band: str | None = None
    relationship_score_breakdown: list[ScoreBreakdownItem] = []
    behavioral_findings: list[BehavioralFindingOut] = []
    segments: list[SegmentOut] = []


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    client_name: str | None = None
    client_suitability: str | None = None
    asset_id: UUID | None = None
    alert_type: str
    severity: str
    explanation: str | None
    status: str
    resolution_note: str | None = None
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
    manager_name: str | None = None
    risk_rating: str | None = None
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
    asset_id: UUID | None = None
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
    client_suitability: str | None = None
    insight_type: str
    asset_class: str | None
    severity: str
    title: str
    explanation: str | None
    evidence: dict | None
    status: str
    resolution_note: str | None = None
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


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    asset_class: str
    issuer: str | None
    isin_code: str | None
    cnpj_code: str | None
    asset_code: str | None
    due_date: date | None
    rate: float | None
    index_description: str | None = None
    manager_name: str | None = None
    payment_frequency: str | None = None
    liquidity_days: float | None = None
    minimum_investment: float | None = None
    risk_rating: str | None = None
    total_exposure: float = 0.0
    client_count: int = 0


class AssetSnapshotPointOut(BaseModel):
    snapshot_date: date
    total_value: float


class AssetClientPositionOut(BaseModel):
    client_id: UUID
    client_name: str
    market_value: float
    quantity: float | None
    pct_of_client_aum: float | None


class AssetPriceTrendPointOut(BaseModel):
    value_date: date
    unit_price: float


class AssetFlowItemOut(BaseModel):
    client_id: UUID
    client_name: str
    quantity_start: float | None
    quantity_end: float | None
    quantity_delta: float | None
    purchase_value: float
    sale_value: float
    net_value: float


class AssetAdvisorExposureOut(BaseModel):
    advisor_id: UUID
    advisor_name: str
    total_exposure: float
    client_count: int


class AssetDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    asset_class: str
    issuer: str | None
    isin_code: str | None
    cnpj_code: str | None
    asset_code: str | None
    due_date: date | None
    rate: float | None
    index_description: str | None
    manager_name: str | None = None
    payment_frequency: str | None = None
    liquidity_days: float | None = None
    minimum_investment: float | None = None
    risk_rating: str | None = None
    aum_trend: list[AssetSnapshotPointOut] = []
    alerts: list[AlertOut] = []
    tasks: list[TaskOut] = []
    client_positions: list[AssetClientPositionOut] = []
    distribution_by_advisor: list[AssetAdvisorExposureOut] = []


class InteractionCreate(BaseModel):
    interaction_type: str  # Meeting | Phone | Email | WhatsApp | Other
    interaction_date: date
    subject: str | None = None
    notes: str | None = None


class InteractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    advisor_id: UUID | None
    interaction_type: str
    interaction_date: date
    subject: str | None
    notes: str | None
    created_at: datetime | None


class RelationshipScoreOut(BaseModel):
    score: int
    band: str
    components: dict
    explanation: list[str]


class RelationshipOverviewItem(BaseModel):
    id: UUID
    name: str
    days_since_contact: int | None
    cadence_days: int
    status: str  # overdue | approaching | ok


class PortfolioEvolutionItem(BaseModel):
    asset_class: str
    pct_start: float
    pct_end: float
    delta_pp: float


class CashAnalyticsOut(BaseModel):
    current: float
    average: float
    max: float
    pct_of_aum_current: float | None


class FlowAnalyticsOut(BaseModel):
    gross_inflow: float
    gross_outflow: float
    net_flow: float


class AssetClassSeriesOut(BaseModel):
    asset_class: str
    points: list[SnapshotPointOut] = []  # aum reaproveitado como "valor da classe" nesse snapshot


class ClientAnalyticsOut(BaseModel):
    aum_trend: list[SnapshotPointOut] = []
    aum_change_pct: float | None = None
    portfolio_evolution: list[PortfolioEvolutionItem] = []
    class_series: list[AssetClassSeriesOut] = []
    cash_analytics: CashAnalyticsOut | None = None
    flow_analytics: FlowAnalyticsOut | None = None
    maturity_profile: list[MaturityBucketOut] = []


class ValueTrendPointOut(BaseModel):
    value_date: date
    value: float


class PerformanceAttributionItem(BaseModel):
    asset_id: UUID
    asset_name: str
    asset_class: str
    value_start: float
    value_end: float
    net_flow: float
    performance_value: float
    contribution_pct: float  # sobre o PL total na data inicial


class BenchmarkOut(BaseModel):
    key: str
    name: str


class BenchmarkSeriesPointOut(BaseModel):
    value_date: date
    index_value: float


class AdvisorOut(BaseModel):
    id: UUID
    name: str
    aum: float = 0.0
    client_count: int = 0
    net_flow: float = 0.0
    aum_growth_pct: float | None = None


class AdvisorSnapshotPointOut(BaseModel):
    snapshot_date: date
    aum: float | None
    client_count: int | None
    net_flow: float | None


class AdvisorProductMixAssetItem(BaseModel):
    asset_id: UUID
    asset_name: str
    value: float
    pct_of_class: float


class AdvisorProductMixItem(BaseModel):
    asset_class: str
    value: float
    pct: float
    assets: list[AdvisorProductMixAssetItem] = []


class AdvisorDetailOut(BaseModel):
    id: UUID
    name: str
    aum: float = 0.0
    client_count: int = 0
    net_flow: float = 0.0
    avg_aum_per_client: float = 0.0
    trend: list[AdvisorSnapshotPointOut] = []
    product_mix: list[AdvisorProductMixItem] = []


class ClientExtendedFieldAssignmentOut(BaseModel):
    assignment_id: UUID
    field_key: str
    field_label: str
    option_id: UUID
    option_value: str


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
    aum_trend: list[SnapshotPointOut] = []
    interactions: list[InteractionOut] = []
    relationship_score_components: dict | None = None
    relationship_score_explanation: list[str] = []
    field_overrides: dict[str, str] = {}
    extended_fields: list[ClientExtendedFieldAssignmentOut] = []
    key_insights: list[KeyInsightOut] = []


class OpportunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    client_name: str | None = None
    opportunity_type: str
    status: str
    potential_value: float | None
    urgency: int | None
    confidence: int | None
    score: int | None
    explanation: str | None
    created_at: datetime | None
    updated_at: datetime | None


class OpportunityStatusIn(BaseModel):
    status: str


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID | None
    client_name: str | None = None
    action_type: str
    summary: str
    created_at: datetime | None


class FieldOverrideOut(BaseModel):
    field_name: str
    override_value: str
    created_at: datetime | None = None


class FieldOverrideAdminOut(BaseModel):
    client_id: UUID
    client_name: str
    field_name: str
    override_value: str
    created_at: datetime | None = None


class FieldOverrideIn(BaseModel):
    value: str


class ExtendedFieldOptionOut(BaseModel):
    id: UUID
    value: str


class ExtendedFieldDefinitionOut(BaseModel):
    id: UUID
    key: str
    label: str
    options: list[ExtendedFieldOptionOut] = []


class ExtendedFieldDefinitionIn(BaseModel):
    key: str
    label: str


class ExtendedFieldOptionIn(BaseModel):
    value: str


class ExtendedFieldAssignmentIn(BaseModel):
    client_id: UUID
    option_id: UUID