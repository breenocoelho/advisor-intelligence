from datetime import date
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import Advisor, AdvisorDailySnapshot, ClientAdvisorHistory, Position, Asset, Account
from app.schemas import (
    AdvisorOut, AdvisorDetailOut, AdvisorSnapshotPointOut, AdvisorProductMixItem, AdvisorProductMixAssetItem,
    ChangeItemOut,
)
from app.routers.clients import resolve_org_id
from app.services.intelligence.what_changed import compute_advisor_what_changed

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

    results = []
    for advisor in advisors:
        snapshots = (
            db.query(AdvisorDailySnapshot)
            .filter(AdvisorDailySnapshot.advisor_id == advisor.id)
            .order_by(AdvisorDailySnapshot.snapshot_date)
            .all()
        )
        if not snapshots:
            results.append(AdvisorOut(id=advisor.id, name=advisor.name))
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

    # product mix: posicoes reais (nao so' allocation_json) dos clientes do
    # assessor na data mais recente -- da' $ e quebra por ativo dentro de
    # cada classe, nao so' %
    product_mix: list[AdvisorProductMixItem] = []
    if latest is not None:
        client_ids = (
            db.query(ClientAdvisorHistory.client_id)
            .filter(ClientAdvisorHistory.advisor_id == advisor.id, ClientAdvisorHistory.valid_to.is_(None))
            .all()
        )
        client_ids = [c[0] for c in client_ids]

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

    return AdvisorDetailOut(
        id=advisor.id,
        name=advisor.name,
        aum=aum,
        client_count=client_count,
        net_flow=net_flow,
        avg_aum_per_client=avg_aum,
        trend=trend,
        product_mix=product_mix,
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
