"""
Office Dashboard (Prioridade 4, Fase 5). Sem gate de RBAC -- o app hoje nao
tem controle de acesso por papel em nenhuma tela (admin/advisor so' existem
como campo em User), entao essa pagina segue o mesmo padrao de acesso do
resto do produto. Controle de acesso continua pendente (ver CLAUDE.md).

Tudo aqui e' agregacao do que ja existe: reaproveita list_advisors (advisor
leaderboard) e list_clients (segmentos, pra derivar as flags de gestao) em
vez de recalcular health/relationship score do zero.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.auth import get_current_user
from app.deps import get_db
from app.models import Advisor, AdvisorDailySnapshot, ClientDailySnapshot, Client
from app.schemas import (
    OfficeSummaryOut, OfficePortfolioMixItem, OfficeSegmentFlagOut, OfficeAdvisorFlagOut, AdvisorSnapshotPointOut,
)
from app.routers.clients import resolve_org_id, list_clients
from app.routers.advisors import list_advisors

router = APIRouter()

SEGMENT_FLAG_LABELS = [("declining", "Declining"), ("at_risk", "At Risk"), ("dormant", "Dormant")]


@router.get("/summary", response_model=OfficeSummaryOut)
def get_office_summary(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    if org_id is None:
        return OfficeSummaryOut()

    advisor_ids = [a[0] for a in db.query(Advisor.id).filter(Advisor.org_id == org_id).all()]
    advisor_count = len(advisor_ids)

    # AUM/net flow do escritorio: soma do AdvisorDailySnapshot por data
    # (menos linhas que somar ClientDailySnapshot direto)
    rows = (
        db.query(
            AdvisorDailySnapshot.snapshot_date,
            func.sum(AdvisorDailySnapshot.aum),
            func.sum(AdvisorDailySnapshot.net_flow),
        )
        .filter(AdvisorDailySnapshot.advisor_id.in_(advisor_ids))
        .group_by(AdvisorDailySnapshot.snapshot_date)
        .order_by(AdvisorDailySnapshot.snapshot_date)
        .all()
        if advisor_ids else []
    )
    aum_trend = [
        AdvisorSnapshotPointOut(snapshot_date=d, aum=float(aum or 0), client_count=None, net_flow=float(net or 0))
        for d, aum, net in rows
    ]
    aum_total = aum_trend[-1].aum if aum_trend else 0.0
    aum_growth_pct = None
    if aum_trend and aum_trend[0].aum and aum_trend[0].aum > 0:
        aum_growth_pct = (aum_trend[-1].aum - aum_trend[0].aum) / aum_trend[0].aum * 100
    net_flow_total = sum(p.net_flow or 0 for p in aum_trend)

    # Advisor leaderboard + clientes/segmentos: reaproveita os endpoints ja
    # existentes em vez de recalcular score/segmento aqui
    advisor_leaderboard = list_advisors(current_user=current_user, db=db)
    clients_data = list_clients(segment=None, current_user=current_user, db=db)
    client_count = len(clients_data)

    avg_aum_per_client = aum_total / client_count if client_count else 0.0
    avg_aum_per_advisor = aum_total / advisor_count if advisor_count else 0.0

    # Portfolio mix org-wide: soma de allocation_json * aum do snapshot mais
    # recente de cada cliente (mesmo calculo do product mix por assessor)
    latest_dates_subq = (
        db.query(ClientDailySnapshot.client_id, func.max(ClientDailySnapshot.snapshot_date).label("max_date"))
        .join(Client, ClientDailySnapshot.client_id == Client.id)
        .filter(Client.org_id == org_id)
        .group_by(ClientDailySnapshot.client_id)
        .subquery()
    )
    latest_snapshots = (
        db.query(ClientDailySnapshot)
        .join(
            latest_dates_subq,
            (ClientDailySnapshot.client_id == latest_dates_subq.c.client_id)
            & (ClientDailySnapshot.snapshot_date == latest_dates_subq.c.max_date),
        )
        .all()
    )
    class_totals: dict[str, float] = {}
    grand_total = 0.0
    for snapshot in latest_snapshots:
        if not snapshot.allocation_json or not snapshot.aum:
            continue
        aum = float(snapshot.aum)
        for asset_class, pct in snapshot.allocation_json.items():
            value = float(pct or 0) * aum
            class_totals[asset_class] = class_totals.get(asset_class, 0.0) + value
            grand_total += value
    portfolio_mix = [
        OfficePortfolioMixItem(asset_class=k, value=v, pct=(v / grand_total * 100 if grand_total > 0 else 0.0))
        for k, v in sorted(class_totals.items(), key=lambda kv: kv[1], reverse=True)
    ]

    # Flags de gestao -- contagem de clientes por segmento de risco (ja
    # calculado em list_clients) + assessores com AUM em queda no periodo
    segment_counts: dict[str, int] = {}
    for client in clients_data:
        for segment in client.segments:
            segment_counts[segment.key] = segment_counts.get(segment.key, 0) + 1
    segment_flags = [
        OfficeSegmentFlagOut(segment_key=key, segment_label=label, count=segment_counts[key])
        for key, label in SEGMENT_FLAG_LABELS
        if segment_counts.get(key, 0) > 0
    ]

    advisors_declining = [
        OfficeAdvisorFlagOut(advisor_id=a.id, advisor_name=a.name, aum_growth_pct=a.aum_growth_pct)
        for a in advisor_leaderboard
        if a.aum_growth_pct is not None and a.aum_growth_pct < 0
    ]

    return OfficeSummaryOut(
        aum_total=aum_total,
        aum_growth_pct=aum_growth_pct,
        aum_trend=aum_trend,
        net_flow_total=net_flow_total,
        client_count=client_count,
        advisor_count=advisor_count,
        avg_aum_per_client=avg_aum_per_client,
        avg_aum_per_advisor=avg_aum_per_advisor,
        advisor_leaderboard=advisor_leaderboard,
        portfolio_mix=portfolio_mix,
        segment_flags=segment_flags,
        advisors_declining=advisors_declining,
    )
