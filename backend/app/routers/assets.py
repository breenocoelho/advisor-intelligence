from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException, status as http_status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.auth import get_current_user
from app.deps import get_db
from app.models import Asset, Alert, Task, Client, Account, Position, Advisor, ClientAdvisorHistory
from app.schemas import (
    AssetOut, AssetDetailOut, AssetSnapshotPointOut, AssetClientPositionOut, AlertOut, TaskOut,
    AssetPriceTrendPointOut, AssetFlowItemOut, AssetAdvisorExposureOut,
)
from app.routers.clients import resolve_org_id
from app.services.intelligence.position_queries import latest_positions_query_for_asset

router = APIRouter()


@router.get("/", response_model=list[AssetOut])
def list_assets(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Antes fazia 3 queries POR ativo distinto (Asset, posicoes, contagem
    de clientes) -- com dezenas de ativos isso vira centenas de round-trips
    sequenciais. Agora busca a 'ultima posicao por conta' da org inteira
    numa query so' e agrega exposicao/clientes em memoria."""
    org_id = resolve_org_id(current_user, db)
    if org_id is None:
        return []

    latest_dates = (
        db.query(Position.account_id.label("account_id"), func.max(Position.position_date).label("max_date"))
        .join(Account, Position.account_id == Account.id)
        .join(Client, Account.client_id == Client.id)
        .filter(Client.org_id == org_id)
        .group_by(Position.account_id)
        .subquery()
    )

    rows = (
        db.query(Position.asset_id, Account.client_id, Position.market_value)
        .join(Account, Position.account_id == Account.id)
        .join(
            latest_dates,
            (Position.account_id == latest_dates.c.account_id) & (Position.position_date == latest_dates.c.max_date),
        )
        .all()
    )

    exposure: dict = {}
    clients_by_asset: dict = {}
    for asset_id, client_id, market_value in rows:
        exposure[asset_id] = exposure.get(asset_id, 0.0) + float(market_value or 0)
        clients_by_asset.setdefault(asset_id, set()).add(client_id)

    if not exposure:
        return []

    assets = db.query(Asset).filter(Asset.id.in_(exposure.keys())).all()
    results = []
    for asset in assets:
        item = AssetOut.model_validate(asset)
        item.total_exposure = exposure.get(asset.id, 0.0)
        item.client_count = len(clients_by_asset.get(asset.id, set()))
        results.append(item)

    results.sort(key=lambda a: a.total_exposure, reverse=True)
    return results


@router.get("/{asset_id}", response_model=AssetDetailOut)
def get_asset_detail(
    asset_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Ativo não encontrado")

    item = AssetDetailOut.model_validate(asset)

    trend_rows = (
        db.query(Position.position_date, func.sum(Position.market_value))
        .join(Account, Position.account_id == Account.id)
        .join(Client, Account.client_id == Client.id)
        .filter(Position.asset_id == asset_id, Client.org_id == org_id)
        .group_by(Position.position_date)
        .order_by(Position.position_date)
        .all()
    )
    item.aum_trend = [
        AssetSnapshotPointOut(snapshot_date=d, total_value=float(v or 0)) for d, v in trend_rows
    ]

    alert_rows = (
        db.query(Alert, Client.name)
        .join(Client, Alert.client_id == Client.id)
        .filter(Alert.asset_id == asset_id, Client.org_id == org_id)
        .order_by(Alert.created_at.desc())
        .all()
    )
    item.alerts = []
    for alert, client_name in alert_rows:
        alert_out = AlertOut.model_validate(alert)
        alert_out.client_name = client_name
        item.alerts.append(alert_out)

    task_rows = (
        db.query(Task, Client.name)
        .join(Client, Task.client_id == Client.id)
        .filter(Task.asset_id == asset_id, Client.org_id == org_id)
        .order_by(Task.due_date)
        .all()
    )
    item.tasks = []
    for task, client_name in task_rows:
        task_out = TaskOut.model_validate(task)
        task_out.client_name = client_name
        item.tasks.append(task_out)

    latest_rows = (
        db.query(Position, Client)
        .join(Account, Position.account_id == Account.id)
        .join(Client, Account.client_id == Client.id)
        .filter(Position.id.in_([p.id for p in latest_positions_query_for_asset(db, asset_id, org_id).all()]))
        .order_by(Position.market_value.desc())
        .all()
    )
    item.client_positions = [
        AssetClientPositionOut(
            client_id=client.id,
            client_name=client.name,
            market_value=float(position.market_value or 0),
            quantity=float(position.quantity) if position.quantity is not None else None,
            pct_of_client_aum=(
                float(position.market_value) / float(client.aum) * 100
                if position.market_value and client.aum else None
            ),
        )
        for position, client in latest_rows
    ]

    # Distribution by advisor (Prioridade 10 -- Cross-Client/Asset
    # Intelligence): mesmos latest_rows ja buscados, so' agrupados pelo
    # assessor atual de cada cliente em vez de por cliente.
    client_ids = [client.id for _, client in latest_rows]
    advisor_by_client = {
        client_id: (advisor_id, advisor_name)
        for client_id, advisor_id, advisor_name in (
            db.query(ClientAdvisorHistory.client_id, Advisor.id, Advisor.name)
            .join(Advisor, ClientAdvisorHistory.advisor_id == Advisor.id)
            .filter(ClientAdvisorHistory.client_id.in_(client_ids), ClientAdvisorHistory.valid_to.is_(None))
            .all()
        )
    } if client_ids else {}

    exposure_by_advisor: dict = {}
    clients_by_advisor: dict = {}
    for position, client in latest_rows:
        advisor_info = advisor_by_client.get(client.id)
        if advisor_info is None:
            continue
        advisor_id, advisor_name = advisor_info
        exposure_by_advisor[advisor_id] = exposure_by_advisor.get(advisor_id, 0.0) + float(position.market_value or 0)
        clients_by_advisor.setdefault(advisor_id, set()).add(client.id)

    advisor_names = {aid: name for aid, name in advisor_by_client.values()}
    item.distribution_by_advisor = sorted(
        [
            AssetAdvisorExposureOut(
                advisor_id=advisor_id, advisor_name=advisor_names.get(advisor_id, "—"),
                total_exposure=exposure, client_count=len(clients_by_advisor.get(advisor_id, set())),
            )
            for advisor_id, exposure in exposure_by_advisor.items()
        ],
        key=lambda a: a.total_exposure, reverse=True,
    )

    return item


@router.get("/{asset_id}/price-trend", response_model=list[AssetPriceTrendPointOut])
def get_asset_price_trend(
    asset_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preco unitario do ativo no tempo (soma do PL / soma da quantidade,
    entre todos os clientes que o possuem em cada data) -- serve pra
    distinguir se o AUM do ativo cresceu por valorizacao ou por
    aporte/resgate (mesmas posicoes historicas, sem tabela nova)."""
    org_id = resolve_org_id(current_user, db)

    rows = (
        db.query(Position.position_date, func.sum(Position.market_value), func.sum(Position.quantity))
        .join(Account, Position.account_id == Account.id)
        .join(Client, Account.client_id == Client.id)
        .filter(Position.asset_id == asset_id, Client.org_id == org_id, Position.quantity.isnot(None))
        .group_by(Position.position_date)
        .order_by(Position.position_date)
        .all()
    )
    return [
        AssetPriceTrendPointOut(value_date=d, unit_price=float(total_value) / float(total_qty))
        for d, total_value, total_qty in rows
        if total_qty and float(total_qty) != 0
    ]


@router.get("/{asset_id}/flows", response_model=list[AssetFlowItemOut])
def get_asset_flows(
    asset_id: str,
    date_a: date = Query(..., alias="from"),
    date_b: date = Query(..., alias="to"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compras/vendas desse ativo por cliente num periodo escolhido pelo
    usuario -- em quantidade (delta de posicao) e em valor (soma do
    aporte/resgate 'do periodo' registrado em cada sincronizacao entre as
    duas datas)."""
    org_id = resolve_org_id(current_user, db)

    def positions_at(on_date: date) -> dict:
        rows = (
            db.query(Position, Client)
            .join(Account, Position.account_id == Account.id)
            .join(Client, Account.client_id == Client.id)
            .filter(Position.asset_id == asset_id, Client.org_id == org_id, Position.position_date == on_date)
            .all()
        )
        return {client.id: (position, client) for position, client in rows}

    start_map = positions_at(date_a)
    end_map = positions_at(date_b)

    flow_rows = (
        db.query(Account.client_id, Client.name, func.sum(Position.period_purchase_value), func.sum(Position.period_sale_value))
        .join(Account, Position.account_id == Account.id)
        .join(Client, Account.client_id == Client.id)
        .filter(
            Position.asset_id == asset_id, Client.org_id == org_id,
            Position.position_date > date_a, Position.position_date <= date_b,
        )
        .group_by(Account.client_id, Client.name)
        .all()
    )

    items = {}
    for client_id, client_name, purchase, sale in flow_rows:
        purchase = float(purchase or 0)
        sale = float(sale or 0)
        items[client_id] = AssetFlowItemOut(
            client_id=client_id, client_name=client_name,
            quantity_start=None, quantity_end=None, quantity_delta=None,
            purchase_value=purchase, sale_value=sale, net_value=purchase - sale,
        )

    for client_id, (position, client) in {**start_map, **end_map}.items():
        qty_start = float(start_map[client_id][0].quantity) if client_id in start_map and start_map[client_id][0].quantity is not None else None
        qty_end = float(end_map[client_id][0].quantity) if client_id in end_map and end_map[client_id][0].quantity is not None else None
        qty_delta = (qty_end or 0) - (qty_start or 0) if qty_start is not None or qty_end is not None else None
        if client_id in items:
            items[client_id].quantity_start = qty_start
            items[client_id].quantity_end = qty_end
            items[client_id].quantity_delta = qty_delta
        else:
            items[client_id] = AssetFlowItemOut(
                client_id=client_id, client_name=client.name,
                quantity_start=qty_start, quantity_end=qty_end, quantity_delta=qty_delta,
                purchase_value=0.0, sale_value=0.0, net_value=0.0,
            )

    results = list(items.values())
    results.sort(key=lambda i: abs(i.net_value) + abs(i.quantity_delta or 0), reverse=True)
    return results


@router.get("/{asset_id}/positions-at", response_model=list[AssetClientPositionOut])
def get_asset_positions_at(
    asset_id: str,
    on_date: date = Query(..., alias="date"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Posicoes desse ativo em todos os clientes da org numa data especifica
    -- espelha clients/{id}/positions-at, so que o eixo variavel e' cliente
    em vez de ativo (base da comparacao de datas no Asset 360)."""
    org_id = resolve_org_id(current_user, db)

    rows = (
        db.query(Position, Client)
        .join(Account, Position.account_id == Account.id)
        .join(Client, Account.client_id == Client.id)
        .filter(Position.asset_id == asset_id, Client.org_id == org_id, Position.position_date == on_date)
        .order_by(Position.market_value.desc())
        .all()
    )
    return [
        AssetClientPositionOut(
            client_id=client.id,
            client_name=client.name,
            market_value=float(position.market_value or 0),
            quantity=float(position.quantity) if position.quantity is not None else None,
            pct_of_client_aum=(
                float(position.market_value) / float(client.aum) * 100
                if position.market_value and client.aum else None
            ),
        )
        for position, client in rows
    ]
