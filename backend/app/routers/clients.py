import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.auth import get_current_user
from app.deps import get_db
from app.models import (
    Client, Organization, Advisor, ClientAdvisorHistory, Alert, Asset, Position, Task,
    Insight, ClientDailySnapshot, Account, ClientInteraction, ClientFieldOverride,
    ClientExtendedFieldAssignment, ClientExtendedFieldOption, ClientExtendedFieldDefinition,
    Opportunity,
)
from app.schemas import (
    ClientOut, ClientDetailOut, AlertOut, PositionOut, TaskOut, InsightOut, SnapshotPointOut,
    InteractionOut, RelationshipOverviewItem, ClientAnalyticsOut, PortfolioEvolutionItem,
    CashAnalyticsOut, FlowAnalyticsOut, AssetClassSeriesOut, ValueTrendPointOut, PerformanceAttributionItem,
    FieldOverrideOut, FieldOverrideIn, ClientExtendedFieldAssignmentOut,
    BehavioralFindingOut, SegmentOut, ChangeItemOut, KeyInsightOut, MaturityBucketOut,
    TopPositionOut, IssuerExposureOut,
)
from app.services.intelligence.position_queries import latest_positions_query
from app.services.intelligence.relationship_score import (
    compute_relationship_score, get_contact_cadence_days, score_breakdown, classify_contact_status,
)
from app.services.intelligence.health_score import health_score_breakdown
from app.services.intelligence.thresholds import preload_threshold_cache
from app.services.intelligence.behavioral_health import compute_behavioral_findings
from app.services.intelligence.segmentation import compute_segments
from app.services.intelligence.what_changed import compute_client_what_changed
from app.services.audit import log_action

router = APIRouter()

# peso de cada severidade no score de prioridade do cliente
SEVERITY_WEIGHT = {"critical": 3, "opportunity": 2, "follow_up": 1}

THRESHOLD_KEYS_FOR_SCORES = [
    "idle_cash", "concentration_issuer", "high_value_aum_threshold",
    "contact_cadence_high_value_days", "contact_cadence_standard_days", "contact_cadence_low_engagement_days",
    "relationship_score_good", "relationship_score_warn",
    "behavioral_anomaly_stdev_multiplier", "behavioral_anomaly_min_history_points", "segment_growth_pct",
    "opportunity_followup_stale_days",
]

LIQUIDITY_BUCKETS = ["Immediate", "Short Term", "Medium Term", "Long Term"]


def _liquidity_bucket(liquidity_days) -> str | None:
    if liquidity_days is None:
        return None
    days = float(liquidity_days)
    if days <= 0:
        return "Immediate"
    if days <= 30:
        return "Short Term"
    if days <= 180:
        return "Medium Term"
    return "Long Term"


def _aum_change_pct(snapshots: list) -> float | None:
    if len(snapshots) < 2 or not snapshots[0].aum or float(snapshots[0].aum) <= 0:
        return None
    return (float(snapshots[-1].aum or 0) - float(snapshots[0].aum)) / float(snapshots[0].aum)


def resolve_org_id(current_user: dict, db: Session) -> uuid.UUID | None:
    """
    TODO: Clerk hoje so tem login pessoal, sem Organizations ativas -- o
    token nao traz org_id. Como so existe uma organizacao piloto, cai de
    volta para ela. Revisar quando houver mais de um escritorio.
    """
    org_id = current_user.get("org_id")
    if org_id:
        return uuid.UUID(org_id)
    fallback_org = db.query(Organization).first()
    return fallback_org.id if fallback_org else None


def _build_position_out(position: Position, asset: Asset) -> PositionOut:
    return PositionOut(
        id=position.id,
        asset_id=asset.id,
        asset_name=asset.name,
        asset_class=asset.asset_class,
        market_value=float(position.market_value or 0),
        quantity=float(position.quantity) if position.quantity is not None else None,
        due_date=asset.due_date,
        issuer=asset.issuer,
        rate=float(asset.rate) if asset.rate is not None else None,
        index_description=asset.index_description,
        manager_name=asset.manager_name,
        risk_rating=asset.risk_rating,
        position_date=position.position_date,
        period_purchase_value=float(position.period_purchase_value or 0),
        period_sale_value=float(position.period_sale_value or 0),
    )


def get_current_advisor_name(db: Session, client_id) -> str | None:
    row = (
        db.query(Advisor.name)
        .join(ClientAdvisorHistory, ClientAdvisorHistory.advisor_id == Advisor.id)
        .filter(ClientAdvisorHistory.client_id == client_id, ClientAdvisorHistory.valid_to.is_(None))
        .first()
    )
    return row[0] if row else None


@router.get("/", response_model=list[ClientOut])
def list_clients(
    segment: str | None = Query(default=None, description="filtra por segments[].key, ex: high_aum"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    if org_id is None:
        return []

    current_advisor = (
        db.query(ClientAdvisorHistory.client_id, Advisor.name.label("advisor_name"))
        .join(Advisor, ClientAdvisorHistory.advisor_id == Advisor.id)
        .filter(ClientAdvisorHistory.valid_to.is_(None))
        .subquery()
    )

    # contagem de alertas "new" por cliente E por severidade -- base do score
    severity_rows = (
        db.query(Alert.client_id, Alert.severity, func.count(Alert.id).label("count"))
        .filter(Alert.status == "new")
        .group_by(Alert.client_id, Alert.severity)
        .all()
    )
    counts_by_client: dict[uuid.UUID, dict[str, int]] = {}
    for client_id, severity, count in severity_rows:
        counts_by_client.setdefault(client_id, {})[severity] = count

    clients = (
        db.query(Client, current_advisor.c.advisor_name)
        .outerjoin(current_advisor, current_advisor.c.client_id == Client.id)
        .filter(Client.org_id == org_id)
        .all()
    )
    client_ids = [c.id for c, _ in clients]

    # historico de snapshots (health score + estabilidade de AUM p/ relationship score),
    # buscado uma vez so' e agrupado em memoria -- evita 1 query por cliente
    all_snapshots = (
        db.query(ClientDailySnapshot)
        .filter(ClientDailySnapshot.org_id == org_id)
        .order_by(ClientDailySnapshot.client_id, ClientDailySnapshot.snapshot_date)
        .all()
    )
    snapshots_by_client: dict[uuid.UUID, list] = {}
    for s in all_snapshots:
        snapshots_by_client.setdefault(s.client_id, []).append(s)

    all_interactions = (
        db.query(ClientInteraction).filter(ClientInteraction.client_id.in_(client_ids)).all()
        if client_ids else []
    )
    interactions_by_client: dict[uuid.UUID, list] = {}
    for i in all_interactions:
        interactions_by_client.setdefault(i.client_id, []).append(i)

    all_tasks = (
        db.query(Task).filter(Task.client_id.in_(client_ids)).all()
        if client_ids else []
    )
    tasks_by_client: dict[uuid.UUID, list] = {}
    for t in all_tasks:
        tasks_by_client.setdefault(t.client_id, []).append(t)

    all_opportunities = (
        db.query(Opportunity).filter(Opportunity.client_id.in_(client_ids)).all()
        if client_ids else []
    )
    opportunities_by_client: dict[uuid.UUID, list] = {}
    for o in all_opportunities:
        opportunities_by_client.setdefault(o.client_id, []).append(o)

    # 1 query pra todos os thresholds usados no health/relationship score,
    # em vez de ~8 por cliente -- era o gargalo desse endpoint (centenas de
    # round-trips sequenciais pro Postgres do Railway)
    threshold_cache = preload_threshold_cache(db, org_id, THRESHOLD_KEYS_FOR_SCORES)

    results = []
    for client, advisor_name in clients:
        severities = counts_by_client.get(client.id, {})
        active_alerts_count = sum(severities.values())
        priority_score = sum(SEVERITY_WEIGHT.get(sev, 0) * cnt for sev, cnt in severities.items())

        client_snapshots = snapshots_by_client.get(client.id, [])
        latest_snapshot = client_snapshots[-1] if client_snapshots else None
        has_interaction = client.id in interactions_by_client

        item = ClientOut.model_validate(client)
        item.advisor_name = advisor_name
        item.active_alerts_count = active_alerts_count
        item.priority_score = priority_score

        item.health_score = latest_snapshot.health_score if latest_snapshot else None
        item.health_score_breakdown = health_score_breakdown(db, org_id, client, latest_snapshot, cache=threshold_cache)

        relationship = compute_relationship_score(
            db, org_id, client,
            interactions=interactions_by_client.get(client.id, []),
            tasks=tasks_by_client.get(client.id, []),
            aum_history=[s.aum for s in client_snapshots],
            open_opportunities=opportunities_by_client.get(client.id, []),
            cache=threshold_cache,
        )
        item.relationship_score = relationship.score
        item.relationship_score_band = relationship.band
        item.relationship_score_breakdown = score_breakdown(relationship)

        behavioral_findings = compute_behavioral_findings(db, org_id, client, client_snapshots, cache=threshold_cache)
        item.behavioral_findings = [BehavioralFindingOut(
            finding_type=f.finding_type, severity=f.severity, label=f.label, detail=f.detail,
        ) for f in behavioral_findings]

        segments = compute_segments(
            db, org_id, client, latest_snapshot, _aum_change_pct(client_snapshots),
            relationship.band, relationship.score, behavioral_findings, has_interaction, cache=threshold_cache,
        )
        item.segments = [SegmentOut(key=s.key, label=s.label, category=s.category, reason=s.reason) for s in segments]

        results.append(item)

    if segment:
        results = [c for c in results if any(s.key == segment for s in c.segments)]

    # ordena por prioridade, nao mais so por AUM -- "diga quem merece atencao primeiro"
    results.sort(key=lambda c: c.priority_score, reverse=True)
    return results


@router.get("/relationship-overview", response_model=list[RelationshipOverviewItem])
def relationship_overview(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Base do bloco 'Relationship' no Today e da contagem 🔴🟡🟢 -- por
    cliente, ha quanto tempo sem contato vs a cadencia esperada pro tier
    dele (Relationship Intelligence, Etapa 3)."""
    org_id = resolve_org_id(current_user, db)
    if org_id is None:
        return []

    today = date.today()
    clients = db.query(Client).filter(Client.org_id == org_id).all()

    client_ids_with_interaction = {
        row[0] for row in
        db.query(ClientInteraction.client_id).filter(ClientInteraction.client_id.in_([c.id for c in clients])).distinct().all()
    }
    threshold_cache = preload_threshold_cache(db, org_id, [
        "high_value_aum_threshold", "contact_cadence_high_value_days",
        "contact_cadence_standard_days", "contact_cadence_low_engagement_days",
    ])

    results = []
    for client in clients:
        has_interaction = client.id in client_ids_with_interaction
        cadence_days = int(get_contact_cadence_days(db, org_id, client, has_any_interaction=has_interaction, cache=threshold_cache))
        days_since = (today - client.last_contact_at.date()).days if client.last_contact_at else None
        item_status = classify_contact_status(days_since, cadence_days)

        results.append(RelationshipOverviewItem(
            id=client.id, name=client.name, days_since_contact=days_since,
            cadence_days=cadence_days, status=item_status,
        ))

    # nunca contatado vem primeiro (mais urgente), depois por dias sem contato desc
    results.sort(key=lambda r: (0 if r.days_since_contact is None else 1, -(r.days_since_contact or 0)))
    return results


@router.get("/{client_id}", response_model=ClientDetailOut)
def get_client_detail(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)

    client_row = (
        db.query(Client)
        .filter(Client.id == client_id, Client.org_id == org_id)
        .first()
    )
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    advisor_name = get_current_advisor_name(db, client_row.id)

    alerts_rows = (
        db.query(Alert)
        .filter(Alert.client_id == client_row.id)
        .order_by(Alert.created_at.desc())
        .all()
    )
    active_alerts = [a for a in alerts_rows if a.status == "new"]
    active_alerts_count = len(active_alerts)
    priority_score = sum(SEVERITY_WEIGHT.get(a.severity, 0) for a in active_alerts)

    latest_ids = [p.id for p in latest_positions_query(db, client_row.id).all()]
    positions_rows = (
        db.query(Position, Asset)
        .join(Asset, Position.asset_id == Asset.id)
        .filter(Position.id.in_(latest_ids))
        .order_by(Position.market_value.desc())
        .all()
    )

    tasks_rows = (
        db.query(Task)
        .filter(Task.client_id == client_row.id)
        .order_by(Task.due_date)
        .all()
    )

    item = ClientDetailOut.model_validate(client_row)
    item.advisor_name = advisor_name
    item.active_alerts_count = active_alerts_count
    item.priority_score = priority_score

    item.positions = [_build_position_out(position, asset) for position, asset in positions_rows]

    # Top posições e emissores (Client Health, Fase 5) -- derivados dos
    # mesmos positions_rows acima (ja ordenados por market_value desc),
    # zero query nova
    aum_for_pct = float(client_row.aum) if client_row.aum else 0.0
    if aum_for_pct > 0:
        item.top_positions = [
            TopPositionOut(
                asset_name=asset.name, market_value=float(position.market_value or 0),
                pct_of_aum=float(position.market_value or 0) / aum_for_pct * 100,
            )
            for position, asset in positions_rows[:3]
        ]
        issuer_totals: dict[str, float] = {}
        for position, asset in positions_rows:
            if not asset.issuer:
                continue
            issuer_totals[asset.issuer] = issuer_totals.get(asset.issuer, 0.0) + float(position.market_value or 0)
        top_issuers = sorted(issuer_totals.items(), key=lambda kv: kv[1], reverse=True)[:3]
        item.issuer_breakdown = [
            IssuerExposureOut(issuer=issuer, value=value, pct_of_aum=value / aum_for_pct * 100)
            for issuer, value in top_issuers
        ]

    item.alerts = []
    for alert in alerts_rows:
        alert_out = AlertOut.model_validate(alert)
        alert_out.client_name = client_row.name
        item.alerts.append(alert_out)

    item.tasks = [TaskOut.model_validate(t) for t in tasks_rows]

    insights_rows = (
        db.query(Insight)
        .filter(Insight.client_id == client_row.id)
        .order_by(Insight.severity, Insight.created_at.desc())
        .all()
    )
    item.insights = []
    for insight in insights_rows:
        insight_out = InsightOut.model_validate(insight)
        insight_out.client_name = client_row.name
        item.insights.append(insight_out)

    snapshot_rows = (
        db.query(ClientDailySnapshot)
        .filter(ClientDailySnapshot.client_id == client_row.id)
        .order_by(ClientDailySnapshot.snapshot_date)
        .all()
    )
    item.aum_trend = [
        SnapshotPointOut(
            snapshot_date=s.snapshot_date,
            aum=float(s.aum) if s.aum is not None else None,
            health_score=s.health_score,
        )
        for s in snapshot_rows
    ]
    latest_snapshot = snapshot_rows[-1] if snapshot_rows else None
    item.health_score = latest_snapshot.health_score if latest_snapshot else None
    item.health_score_breakdown = health_score_breakdown(db, org_id, client_row, latest_snapshot)

    interactions_rows = (
        db.query(ClientInteraction)
        .filter(ClientInteraction.client_id == client_row.id)
        .order_by(ClientInteraction.interaction_date.desc())
        .all()
    )
    item.interactions = [InteractionOut.model_validate(i) for i in interactions_rows]

    opportunities_rows = db.query(Opportunity).filter(Opportunity.client_id == client_row.id).all()

    relationship = compute_relationship_score(
        db, org_id, client_row,
        interactions=interactions_rows,
        tasks=tasks_rows,
        aum_history=[s.aum for s in snapshot_rows],
        open_opportunities=opportunities_rows,
    )
    item.relationship_score = relationship.score
    item.relationship_score_band = relationship.band
    item.relationship_score_breakdown = score_breakdown(relationship)
    item.relationship_score_components = relationship.components
    item.relationship_score_explanation = relationship.explanation

    behavioral_findings = compute_behavioral_findings(db, org_id, client_row, snapshot_rows)
    item.behavioral_findings = [BehavioralFindingOut(
        finding_type=f.finding_type, severity=f.severity, label=f.label, detail=f.detail,
    ) for f in behavioral_findings]

    has_interaction = len(interactions_rows) > 0
    segments = compute_segments(
        db, org_id, client_row, latest_snapshot, _aum_change_pct(snapshot_rows),
        relationship.band, relationship.score, behavioral_findings, has_interaction,
    )
    item.segments = [SegmentOut(key=s.key, label=s.label, category=s.category, reason=s.reason) for s in segments]

    # Client Intelligence Summary (Prioridade 9) -- consolida os itens mais
    # relevantes ja calculados nesta mesma request (zero query nova):
    # alertas criticos abertos, insights novos, findings comportamentais e
    # status de contato fora da cadencia.
    key_insights: list[KeyInsightOut] = []
    for alert in active_alerts:
        # alertas "behavioral_*" sao o mesmo sinal que ja aparece via
        # behavioral_findings logo abaixo -- nao duplica
        if alert.severity == "critical" and not alert.alert_type.startswith("behavioral_"):
            key_insights.append(KeyInsightOut(text=alert.explanation or alert.alert_type, severity="critical", link_tab="Alertas"))
    for insight in insights_rows:
        if insight.status == "new":
            key_insights.append(KeyInsightOut(text=insight.title, severity=insight.severity, link_tab="Alertas"))
    for finding in behavioral_findings:
        key_insights.append(KeyInsightOut(text=f"{finding.label}: {finding.detail}", severity=finding.severity, link_tab="Overview"))
    if client_row.last_contact_at is not None:
        cadence_days = int(get_contact_cadence_days(db, org_id, client_row, has_any_interaction=has_interaction))
        days_since = (date.today() - client_row.last_contact_at.date()).days
        if days_since > cadence_days:
            key_insights.append(KeyInsightOut(
                text=f"Sem contato há {days_since} dias (cadência esperada: {cadence_days} dias)",
                severity="follow_up", link_tab="Relationship",
            ))
    severity_rank = {"critical": 0, "opportunity": 1, "follow_up": 2}
    key_insights.sort(key=lambda k: severity_rank.get(k.severity, 3))
    item.key_insights = key_insights[:5]

    overrides = db.query(ClientFieldOverride).filter(ClientFieldOverride.client_id == client_row.id).all()
    item.field_overrides = {o.field_name: o.override_value for o in overrides}

    extended_rows = (
        db.query(ClientExtendedFieldAssignment, ClientExtendedFieldOption, ClientExtendedFieldDefinition)
        .join(ClientExtendedFieldOption, ClientExtendedFieldAssignment.option_id == ClientExtendedFieldOption.id)
        .join(ClientExtendedFieldDefinition, ClientExtendedFieldOption.field_definition_id == ClientExtendedFieldDefinition.id)
        .filter(ClientExtendedFieldAssignment.client_id == client_row.id)
        .all()
    )
    item.extended_fields = [
        ClientExtendedFieldAssignmentOut(
            assignment_id=assignment.id, field_key=definition.key, field_label=definition.label,
            option_id=option.id, option_value=option.value,
        )
        for assignment, option, definition in extended_rows
    ]

    return item


@router.get("/{client_id}/field-overrides", response_model=list[FieldOverrideOut])
def list_field_overrides(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    rows = db.query(ClientFieldOverride).filter(ClientFieldOverride.client_id == client_row.id).all()
    return [FieldOverrideOut(field_name=r.field_name, override_value=r.override_value, created_at=r.created_at) for r in rows]


@router.put("/{client_id}/field-overrides/{field_name}", response_model=FieldOverrideOut)
def set_field_override(
    client_id: str,
    field_name: str,
    payload: FieldOverrideIn,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    override = (
        db.query(ClientFieldOverride)
        .filter(ClientFieldOverride.client_id == client_row.id, ClientFieldOverride.field_name == field_name)
        .first()
    )
    if override is None:
        override = ClientFieldOverride(client_id=client_row.id, field_name=field_name, override_value=payload.value)
        db.add(override)
    else:
        override.override_value = payload.value

    log_action(
        db, org_id, "field_override_set",
        f"Campo '{field_name}' de {client_row.name} sobrescrito para \"{payload.value}\"",
        client_id=client_row.id,
    )
    db.commit()
    db.refresh(override)
    return FieldOverrideOut(field_name=override.field_name, override_value=override.override_value, created_at=override.created_at)


@router.delete("/{client_id}/field-overrides/{field_name}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_field_override(
    client_id: str,
    field_name: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    override = (
        db.query(ClientFieldOverride)
        .filter(ClientFieldOverride.client_id == client_row.id, ClientFieldOverride.field_name == field_name)
        .first()
    )
    if override is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Override não encontrado")

    db.delete(override)
    log_action(db, org_id, "field_override_removed", f"Override do campo '{field_name}' de {client_row.name} removido", client_id=client_row.id)
    db.commit()
    return None


@router.get("/{client_id}/analytics", response_model=ClientAnalyticsOut)
def get_client_analytics(
    client_id: str,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Consolida AUM evolution, portfolio evolution (em pp), cash e flow
    analytics numa resposta so -- reaproveita client_daily_snapshot como
    fonte unica, filtrado por from/to (Analytics, Etapa 2)."""
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    query = db.query(ClientDailySnapshot).filter(ClientDailySnapshot.client_id == client_row.id)
    if from_date:
        query = query.filter(ClientDailySnapshot.snapshot_date >= from_date)
    if to_date:
        query = query.filter(ClientDailySnapshot.snapshot_date <= to_date)
    snapshots = query.order_by(ClientDailySnapshot.snapshot_date).all()

    aum_trend = [
        SnapshotPointOut(
            snapshot_date=s.snapshot_date,
            aum=float(s.aum) if s.aum is not None else None,
            health_score=s.health_score,
        )
        for s in snapshots
    ]

    aum_change_pct = None
    if snapshots and snapshots[0].aum and float(snapshots[0].aum) > 0:
        aum_change_pct = (float(snapshots[-1].aum or 0) - float(snapshots[0].aum)) / float(snapshots[0].aum) * 100

    portfolio_evolution: list[PortfolioEvolutionItem] = []
    if len(snapshots) >= 2 and snapshots[0].allocation_json and snapshots[-1].allocation_json:
        start_alloc = snapshots[0].allocation_json
        end_alloc = snapshots[-1].allocation_json
        for asset_class in sorted(set(start_alloc) | set(end_alloc)):
            pct_start = float(start_alloc.get(asset_class, 0)) * 100
            pct_end = float(end_alloc.get(asset_class, 0)) * 100
            portfolio_evolution.append(PortfolioEvolutionItem(
                asset_class=asset_class, pct_start=pct_start, pct_end=pct_end, delta_pp=pct_end - pct_start,
            ))
        portfolio_evolution.sort(key=lambda p: abs(p.delta_pp), reverse=True)

    # serie completa por classe (nao so' inicio/fim) -- alimenta o grafico
    # de tendencia ao lado da tabela de Portfolio Evolution
    class_series_map: dict[str, list[SnapshotPointOut]] = {}
    for s in snapshots:
        if not s.allocation_json or s.aum is None:
            continue
        for asset_class, pct in s.allocation_json.items():
            class_series_map.setdefault(asset_class, []).append(
                SnapshotPointOut(snapshot_date=s.snapshot_date, aum=float(pct) * float(s.aum), health_score=None)
            )
    class_series = [
        AssetClassSeriesOut(asset_class=asset_class, points=points)
        for asset_class, points in sorted(class_series_map.items())
    ]

    cash_analytics = None
    if snapshots:
        cash_values = [float(s.liquidity_pct or 0) * float(s.aum or 0) for s in snapshots]
        latest_liquidity_pct = snapshots[-1].liquidity_pct
        cash_analytics = CashAnalyticsOut(
            current=cash_values[-1],
            average=sum(cash_values) / len(cash_values),
            max=max(cash_values),
            pct_of_aum_current=float(latest_liquidity_pct) * 100 if latest_liquidity_pct is not None else None,
        )

    flow_analytics = None
    if snapshots:
        gross_inflow = sum(float(s.monthly_purchase_value or 0) for s in snapshots)
        gross_outflow = sum(float(s.monthly_sale_value or 0) for s in snapshots)
        flow_analytics = FlowAnalyticsOut(
            gross_inflow=gross_inflow, gross_outflow=gross_outflow, net_flow=gross_inflow - gross_outflow,
        )

    # Maturity Profile -- posicoes atuais de RF/produtos com due_date,
    # organizadas nos 4 buckets da spec. Nao infere liquidez de ativos sem
    # due_date (ex: acoes, caixa) -- simplesmente ficam de fora do perfil.
    today = date.today()
    latest_ids = [p.id for p in latest_positions_query(db, client_row.id).all()]
    maturity_buckets = {"0-30": 0.0, "31-90": 0.0, "91-180": 0.0, "180+": 0.0}
    if latest_ids:
        maturity_rows = (
            db.query(Position.market_value, Asset.due_date)
            .join(Asset, Position.asset_id == Asset.id)
            .filter(Position.id.in_(latest_ids), Asset.due_date.isnot(None), Asset.due_date >= today)
            .all()
        )
        for market_value, due_date in maturity_rows:
            days = (due_date - today).days
            bucket = "0-30" if days <= 30 else "31-90" if days <= 90 else "91-180" if days <= 180 else "180+"
            maturity_buckets[bucket] += float(market_value or 0)
    maturity_profile = [MaturityBucketOut(bucket=b, value=v) for b, v in maturity_buckets.items()]

    # Liquidity Profile (distinto do Maturity Profile acima: usa
    # liquidity_days -- prazo de resgate -- em vez de due_date -- vencimento
    # do titulo). So' entra quem tem o dado; sem inferencia.
    liquidity_buckets = {b: 0.0 for b in LIQUIDITY_BUCKETS}
    if latest_ids:
        liquidity_rows = (
            db.query(Position.market_value, Asset.liquidity_days)
            .join(Asset, Position.asset_id == Asset.id)
            .filter(Position.id.in_(latest_ids))
            .all()
        )
        for market_value, liquidity_days in liquidity_rows:
            bucket = _liquidity_bucket(liquidity_days)
            if bucket:
                liquidity_buckets[bucket] += float(market_value or 0)
    liquidity_profile = [MaturityBucketOut(bucket=b, value=v) for b, v in liquidity_buckets.items()]

    # Mix por emissor/indexador ao longo do tempo -- direto de Position
    # historico (nao do allocation_json do snapshot, que so tem granularidade
    # de classe). Limitado aos 8 maiores pra nao virar sopa de linhas no grafico.
    def _grouped_series(group_col):
        rows_query = (
            db.query(Position.position_date, group_col, func.sum(Position.market_value))
            .join(Asset, Position.asset_id == Asset.id)
            .join(Account, Position.account_id == Account.id)
            .filter(Account.client_id == client_row.id, group_col.isnot(None))
            .group_by(Position.position_date, group_col)
        )
        if from_date:
            rows_query = rows_query.filter(Position.position_date >= from_date)
        if to_date:
            rows_query = rows_query.filter(Position.position_date <= to_date)

        series_map: dict[str, list[SnapshotPointOut]] = {}
        totals: dict[str, float] = {}
        for pos_date, label, total in rows_query.all():
            value = float(total or 0)
            series_map.setdefault(label, []).append(SnapshotPointOut(snapshot_date=pos_date, aum=value, health_score=None))
            totals[label] = totals.get(label, 0.0) + value

        top_labels = {label for label, _ in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:8]}
        return [
            AssetClassSeriesOut(asset_class=label, points=sorted(points, key=lambda p: p.snapshot_date))
            for label, points in sorted(series_map.items())
            if label in top_labels
        ]

    issuer_series = _grouped_series(Asset.issuer)
    indexer_series = _grouped_series(Asset.index_description)

    portfolio_drift_pp = sum(abs(item.delta_pp) for item in portfolio_evolution)

    return ClientAnalyticsOut(
        aum_trend=aum_trend,
        aum_change_pct=aum_change_pct,
        portfolio_evolution=portfolio_evolution,
        class_series=class_series,
        cash_analytics=cash_analytics,
        flow_analytics=flow_analytics,
        maturity_profile=maturity_profile,
        liquidity_profile=liquidity_profile,
        issuer_series=issuer_series,
        indexer_series=indexer_series,
        portfolio_drift_pp=portfolio_drift_pp,
    )


@router.get("/{client_id}/what-changed", response_model=list[ChangeItemOut])
def get_client_what_changed(
    client_id: str,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """'What Changed?' (Prioridade 7) -- mesma fonte de verdade do
    /analytics, so' que filtrando e formatando apenas as variacoes
    materiais no periodo."""
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    has_interaction = db.query(ClientInteraction).filter(ClientInteraction.client_id == client_row.id).first() is not None
    items = compute_client_what_changed(db, org_id, client_row, from_date, to_date, has_interaction=has_interaction)
    return [ChangeItemOut(label=i.label, direction=i.direction, value_display=i.value_display) for i in items]


@router.get("/{client_id}/value-trend", response_model=list[ValueTrendPointOut])
def get_value_trend(
    client_id: str,
    scope: str = Query(..., pattern="^(aum|class|asset)$"),
    key: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Serie de valor no tempo para o grafico de evolucao do Portfolio
    Analytics -- AUM total, uma classe de ativo, ou um ativo especifico
    (comparavel a um benchmark no frontend). Reaproveita
    client_daily_snapshot para AUM/classe e Position historico (por
    position_date) para um ativo especifico."""
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    if scope == "aum":
        rows = (
            db.query(ClientDailySnapshot.snapshot_date, ClientDailySnapshot.aum)
            .filter(ClientDailySnapshot.client_id == client_row.id)
            .order_by(ClientDailySnapshot.snapshot_date)
            .all()
        )
        return [ValueTrendPointOut(value_date=d, value=float(v or 0)) for d, v in rows]

    if scope == "class":
        if not key:
            return []
        rows = (
            db.query(ClientDailySnapshot.snapshot_date, ClientDailySnapshot.allocation_json, ClientDailySnapshot.aum)
            .filter(ClientDailySnapshot.client_id == client_row.id)
            .order_by(ClientDailySnapshot.snapshot_date)
            .all()
        )
        return [
            ValueTrendPointOut(value_date=d, value=float((alloc or {}).get(key, 0)) * float(aum or 0))
            for d, alloc, aum in rows
        ]

    # scope == "asset"
    if not key:
        return []
    rows = (
        db.query(Position.position_date, func.sum(Position.market_value))
        .join(Account, Position.account_id == Account.id)
        .filter(Account.client_id == client_row.id, Position.asset_id == key)
        .group_by(Position.position_date)
        .order_by(Position.position_date)
        .all()
    )
    return [ValueTrendPointOut(value_date=d, value=float(v or 0)) for d, v in rows]


@router.get("/{client_id}/performance-attribution", response_model=list[PerformanceAttributionItem])
def get_performance_attribution(
    client_id: str,
    date_a: date = Query(..., alias="from"),
    date_b: date = Query(..., alias="to"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Quanto cada ativo contribuiu para a variacao do patrimonio no
    periodo. Heuristica simples e explicavel (nao um modelo de
    atribuicao formal): performance = variacao de valor menos o fluxo
    (aporte/resgate) registrado no periodo em cada posicao, contribuicao
    = performance sobre o PL total no inicio do periodo."""
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    def positions_at(on_date: date):
        return (
            db.query(Position, Asset)
            .join(Asset, Position.asset_id == Asset.id)
            .join(Account, Position.account_id == Account.id)
            .filter(Account.client_id == client_row.id, Position.position_date == on_date)
            .all()
        )

    rows_a = {asset.id: (position, asset) for position, asset in positions_at(date_a)}
    rows_b = {asset.id: (position, asset) for position, asset in positions_at(date_b)}
    total_a = sum(float(p.market_value or 0) for p, _ in rows_a.values())
    if total_a <= 0:
        return []

    items = []
    for asset_id in set(rows_a) | set(rows_b):
        pos_a, asset_a = rows_a.get(asset_id, (None, None))
        pos_b, asset_b = rows_b.get(asset_id, (None, None))
        asset = asset_b or asset_a
        value_a = float(pos_a.market_value) if pos_a and pos_a.market_value else 0.0
        value_b = float(pos_b.market_value) if pos_b and pos_b.market_value else 0.0
        net_flow = float((pos_b.period_purchase_value or 0) - (pos_b.period_sale_value or 0)) if pos_b else 0.0
        performance_value = (value_b - value_a) - net_flow
        items.append(PerformanceAttributionItem(
            asset_id=asset_id,
            asset_name=asset.name,
            asset_class=asset.asset_class,
            value_start=value_a,
            value_end=value_b,
            net_flow=net_flow,
            performance_value=performance_value,
            contribution_pct=performance_value / total_a * 100,
        ))

    items.sort(key=lambda i: abs(i.contribution_pct), reverse=True)
    return items


@router.get("/{client_id}/position-dates", response_model=list[date])
def list_position_dates(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Datas distintas com posicoes sincronizadas para o cliente (para
    montar os seletores de comparacao na tela)."""
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    rows = (
        db.query(Position.position_date)
        .join(Account, Position.account_id == Account.id)
        .filter(Account.client_id == client_row.id)
        .distinct()
        .order_by(Position.position_date)
        .all()
    )
    return [r[0] for r in rows]


@router.get("/{client_id}/positions-at", response_model=list[PositionOut])
def get_positions_at(
    client_id: str,
    on_date: date = Query(..., alias="date"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Posicoes do cliente numa data especifica (nao necessariamente a mais
    recente) -- base para a comparacao data x vs data y no Client 360."""
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    rows = (
        db.query(Position, Asset)
        .join(Asset, Position.asset_id == Asset.id)
        .join(Account, Position.account_id == Account.id)
        .filter(Account.client_id == client_row.id, Position.position_date == on_date)
        .order_by(Position.market_value.desc())
        .all()
    )
    return [_build_position_out(position, asset) for position, asset in rows]


@router.post("/{client_id}/contact", response_model=ClientDetailOut)
def register_contact(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Registra 'agora' como o momento do ultimo contato com o cliente.
    Fonte interna (nao depende de CRM externo) -- alimenta a regra
    rule_no_recent_contact do motor de alertas."""
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    current_advisor_id = (
        db.query(ClientAdvisorHistory.advisor_id)
        .filter(ClientAdvisorHistory.client_id == client_row.id, ClientAdvisorHistory.valid_to.is_(None))
        .scalar()
    )

    client_row.last_contact_at = datetime.utcnow()
    db.add(ClientInteraction(
        client_id=client_row.id,
        advisor_id=current_advisor_id,
        interaction_type="Other",
        interaction_date=date.today(),
        subject="Contato rápido",
    ))
    log_action(db, org_id, "contact_registered", f"Contato rápido registrado com {client_row.name}", client_id=client_row.id)
    db.commit()

    return get_client_detail(client_id, current_user, db)