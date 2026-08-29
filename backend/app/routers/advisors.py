from datetime import date
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status as http_status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.auth import get_current_user
from app.deps import get_db
from app.models import (
    Advisor, AdvisorDailySnapshot, ClientAdvisorHistory, Position, Asset, Account,
    Client, ClientInteraction, Opportunity, Alert,
)
from app.schemas import (
    AdvisorOut, AdvisorDetailOut, AdvisorSnapshotPointOut, AdvisorProductMixItem, AdvisorProductMixAssetItem,
    ChangeItemOut, AdvisorOpportunityDistributionItem, AdvisorKeyInsightOut,
)
from app.routers.clients import resolve_org_id, THRESHOLD_KEYS_FOR_SCORES
from app.services.intelligence.what_changed import compute_advisor_what_changed
from app.services.intelligence.relationship_score import (
    get_contact_cadence_days, classify_contact_status, batch_compute_relationship_scores,
)
from app.services.intelligence.thresholds import preload_threshold_cache

OPEN_OPPORTUNITY_STATUSES_EXCLUDED = ["won", "lost", "closed"]

router = APIRouter()


@router.get("/", response_model=list[AdvisorOut])
def list_advisors(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    if org_id is None:
        return []

    advisors = db.query(Advisor).filter(Advisor.org_id == org_id).all()

    # oportunidades abertas por assessor (vinculo vigente) numa query so,
    # em vez de 1 por assessor
    opp_rows = (
        db.query(ClientAdvisorHistory.advisor_id, func.count(Opportunity.id))
        .join(Opportunity, Opportunity.client_id == ClientAdvisorHistory.client_id)
        .filter(
            ClientAdvisorHistory.valid_to.is_(None),
            Opportunity.status.notin_(OPEN_OPPORTUNITY_STATUSES_EXCLUDED),
        )
        .group_by(ClientAdvisorHistory.advisor_id)
        .all()
    )
    opp_count_by_advisor = {advisor_id: count for advisor_id, count in opp_rows}

    results = []
    for advisor in advisors:
        snapshots = (
            db.query(AdvisorDailySnapshot)
            .filter(AdvisorDailySnapshot.advisor_id == advisor.id)
            .order_by(AdvisorDailySnapshot.snapshot_date)
            .all()
        )
        opportunity_count = opp_count_by_advisor.get(advisor.id, 0)
        if not snapshots:
            results.append(AdvisorOut(id=advisor.id, name=advisor.name, opportunity_count=opportunity_count))
            continue

        latest = snapshots[-1]
        earliest = snapshots[0]
        growth_pct = None
        if earliest.aum and float(earliest.aum) > 0:
            growth_pct = (float(latest.aum or 0) - float(earliest.aum)) / float(earliest.aum) * 100

        results.append(AdvisorOut(
            id=advisor.id,
            name=advisor.name,
            aum=float(latest.aum or 0),
            client_count=latest.client_count or 0,
            net_flow=float(sum((s.net_flow or 0) for s in snapshots)),
            aum_growth_pct=growth_pct,
            opportunity_count=opportunity_count,
        ))

    results.sort(key=lambda a: a.aum, reverse=True)
    return results


@router.get("/{advisor_id}", response_model=AdvisorDetailOut)
def get_advisor_detail(
    advisor_id: str,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    advisor = db.query(Advisor).filter(Advisor.id == advisor_id, Advisor.org_id == org_id).first()
    if advisor is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Assessor não encontrado")

    query = db.query(AdvisorDailySnapshot).filter(AdvisorDailySnapshot.advisor_id == advisor.id)
    if from_date:
        query = query.filter(AdvisorDailySnapshot.snapshot_date >= from_date)
    if to_date:
        query = query.filter(AdvisorDailySnapshot.snapshot_date <= to_date)
    snapshots = query.order_by(AdvisorDailySnapshot.snapshot_date).all()

    trend = [
        AdvisorSnapshotPointOut(
            snapshot_date=s.snapshot_date,
            aum=float(s.aum) if s.aum is not None else None,
            client_count=s.client_count,
            net_flow=float(s.net_flow) if s.net_flow is not None else None,
        )
        for s in snapshots
    ]

    latest = snapshots[-1] if snapshots else None
    aum = float(latest.aum or 0) if latest else 0.0
    client_count = latest.client_count or 0 if latest else 0
    net_flow = float(sum((s.net_flow or 0) for s in snapshots))
    avg_aum = aum / client_count if client_count else 0.0

    client_ids = [
        c[0] for c in
        db.query(ClientAdvisorHistory.client_id)
        .filter(ClientAdvisorHistory.advisor_id == advisor.id, ClientAdvisorHistory.valid_to.is_(None))
        .all()
    ]

    # product mix: posicoes reais (nao so' allocation_json) dos clientes do
    # assessor na data mais recente -- da' $ e quebra por ativo dentro de
    # cada classe, nao so' %
    product_mix: list[AdvisorProductMixItem] = []
    if latest is not None:
        rows = (
            db.query(Position, Asset)
            .join(Asset, Position.asset_id == Asset.id)
            .join(Account, Position.account_id == Account.id)
            .filter(Account.client_id.in_(client_ids), Position.position_date == latest.snapshot_date)
            .all()
        )

        class_totals: dict[str, Decimal] = {}
        asset_totals: dict[str, dict[UUID, tuple[str, Decimal]]] = {}
        grand_total = Decimal(0)
        for position, asset in rows:
            value = Decimal(position.market_value or 0)
            if value <= 0:
                continue
            class_totals[asset.asset_class] = class_totals.get(asset.asset_class, Decimal(0)) + value
            grand_total += value
            by_asset = asset_totals.setdefault(asset.asset_class, {})
            name, prev = by_asset.get(asset.id, (asset.name, Decimal(0)))
            by_asset[asset.id] = (name, prev + value)

        if grand_total > 0:
            for asset_class, class_value in sorted(class_totals.items(), key=lambda kv: kv[1], reverse=True):
                assets = [
                    AdvisorProductMixAssetItem(
                        asset_id=asset_id, asset_name=name, value=float(value),
                        pct_of_class=float(value / class_value * 100) if class_value > 0 else 0.0,
                    )
                    for asset_id, (name, value) in sorted(
                        asset_totals.get(asset_class, {}).items(), key=lambda kv: kv[1][1], reverse=True
                    )
                ]
                product_mix.append(AdvisorProductMixItem(
                    asset_class=asset_class, value=float(class_value),
                    pct=float(class_value / grand_total * 100), assets=assets,
                ))

    # Contact coverage e Relationship coverage (Advisor Analytics, Fase 5) --
    # % dos clientes vigentes do assessor em dia com a cadencia / com
    # relationship band saudavel. Reaproveita classify_contact_status
    # (extraido de relationship_overview) e o batch de relationship score
    # ja usado em list_clients.
    contact_coverage_pct = None
    relationship_coverage_pct = None
    if client_ids:
        threshold_cache = preload_threshold_cache(db, org_id, THRESHOLD_KEYS_FOR_SCORES)
        clients_rows = db.query(Client).filter(Client.id.in_(client_ids)).all()
        client_ids_with_interaction = {
            row[0] for row in
            db.query(ClientInteraction.client_id).filter(ClientInteraction.client_id.in_(client_ids)).distinct().all()
        }
        today = date.today()
        not_overdue = 0
        for client in clients_rows:
            has_interaction = client.id in client_ids_with_interaction
            cadence_days = int(get_contact_cadence_days(db, org_id, client, has_any_interaction=has_interaction, cache=threshold_cache))
            days_since = (today - client.last_contact_at.date()).days if client.last_contact_at else None
            if classify_contact_status(days_since, cadence_days) != "overdue":
                not_overdue += 1
        contact_coverage_pct = not_overdue / len(client_ids) * 100

        relationship_by_client = batch_compute_relationship_scores(db, org_id, client_ids, cache=threshold_cache)
        healthy = sum(1 for r in relationship_by_client.values() if r.band != "At risk")
        relationship_coverage_pct = healthy / len(client_ids) * 100 if relationship_by_client else None

    # Retention -- clientes vigentes com o assessor no inicio do periodo que
    # continuam vigentes no fim, sobre o total vigente no inicio
    reference_start = from_date or (trend[0].snapshot_date if trend else None)
    reference_end = to_date or date.today()
    retention_pct = None
    if reference_start is not None:
        started = (
            db.query(ClientAdvisorHistory)
            .filter(
                ClientAdvisorHistory.advisor_id == advisor.id,
                ClientAdvisorHistory.valid_from <= reference_start,
                or_(ClientAdvisorHistory.valid_to.is_(None), ClientAdvisorHistory.valid_to >= reference_start),
            )
            .count()
        )
        if started > 0:
            retained = (
                db.query(ClientAdvisorHistory)
                .filter(
                    ClientAdvisorHistory.advisor_id == advisor.id,
                    ClientAdvisorHistory.valid_from <= reference_start,
                    or_(ClientAdvisorHistory.valid_to.is_(None), ClientAdvisorHistory.valid_to >= reference_end),
                )
                .count()
            )
            retention_pct = retained / started * 100

    opportunity_distribution = []
    if client_ids:
        dist_rows = (
            db.query(Opportunity.opportunity_type, func.count(Opportunity.id))
            .filter(
                Opportunity.client_id.in_(client_ids),
                Opportunity.status.notin_(OPEN_OPPORTUNITY_STATUSES_EXCLUDED),
            )
            .group_by(Opportunity.opportunity_type)
            .all()
        )
        opportunity_distribution = [
            AdvisorOpportunityDistributionItem(opportunity_type=t, count=c) for t, c in dist_rows
        ]

    # Key Insights cross-client (Prioridade 9, nivel Assessor) -- top
    # alertas criticos + oportunidades de maior score entre os clientes do
    # assessor, cada item linkando pro Client 360 correspondente
    key_insights: list[AdvisorKeyInsightOut] = []
    if client_ids:
        critical_alerts = (
            db.query(Alert, Client.name)
            .join(Client, Alert.client_id == Client.id)
            .filter(Alert.client_id.in_(client_ids), Alert.status == "new", Alert.severity == "critical")
            .order_by(Alert.created_at.desc())
            .limit(5)
            .all()
        )
        for alert, client_name in critical_alerts:
            key_insights.append(AdvisorKeyInsightOut(
                text=alert.explanation or alert.alert_type, severity="critical",
                client_id=alert.client_id, client_name=client_name,
            ))

        top_opportunities = (
            db.query(Opportunity, Client.name)
            .join(Client, Opportunity.client_id == Client.id)
            .filter(Opportunity.client_id.in_(client_ids), Opportunity.status.notin_(OPEN_OPPORTUNITY_STATUSES_EXCLUDED))
            .order_by(Opportunity.score.desc().nullslast())
            .limit(5)
            .all()
        )
        for opportunity, client_name in top_opportunities:
            key_insights.append(AdvisorKeyInsightOut(
                text=opportunity.explanation or opportunity.opportunity_type, severity="opportunity",
                client_id=opportunity.client_id, client_name=client_name,
            ))

        severity_rank = {"critical": 0, "opportunity": 1, "follow_up": 2}
        key_insights.sort(key=lambda k: severity_rank.get(k.severity, 3))
        key_insights = key_insights[:5]

    return AdvisorDetailOut(
        id=advisor.id,
        name=advisor.name,
        aum=aum,
        client_count=client_count,
        net_flow=net_flow,
        avg_aum_per_client=avg_aum,
        trend=trend,
        product_mix=product_mix,
        contact_coverage_pct=contact_coverage_pct,
        relationship_coverage_pct=relationship_coverage_pct,
        retention_pct=retention_pct,
        opportunity_distribution=opportunity_distribution,
        key_insights=key_insights,
    )


@router.get("/{advisor_id}/what-changed", response_model=list[ChangeItemOut])
def get_advisor_what_changed(
    advisor_id: str,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    advisor = db.query(Advisor).filter(Advisor.id == advisor_id, Advisor.org_id == org_id).first()
    if advisor is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Assessor não encontrado")

    items = compute_advisor_what_changed(db, org_id, advisor, from_date, to_date)
    return [ChangeItemOut(label=i.label, direction=i.direction, value_display=i.value_display) for i in items]
