import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.auth import get_current_user
from app.deps import get_db
from app.models import (
    Client, Organization, Advisor, ClientAdvisorHistory, Alert, Asset, Position, Task,
    Insight, ClientDailySnapshot, Account,
)
from app.schemas import (
    ClientOut, ClientDetailOut, AlertOut, PositionOut, TaskOut, InsightOut, SnapshotPointOut,
)
from app.services.intelligence.position_queries import latest_positions_query

router = APIRouter()

# peso de cada severidade no score de prioridade do cliente
SEVERITY_WEIGHT = {"critical": 3, "opportunity": 2, "follow_up": 1}


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

    results = []
    for client, advisor_name in clients:
        severities = counts_by_client.get(client.id, {})
        active_alerts_count = sum(severities.values())
        priority_score = sum(SEVERITY_WEIGHT.get(sev, 0) * cnt for sev, cnt in severities.items())

        item = ClientOut.model_validate(client)
        item.advisor_name = advisor_name
        item.active_alerts_count = active_alerts_count
        item.priority_score = priority_score
        results.append(item)

    # ordena por prioridade, nao mais so por AUM -- "diga quem merece atencao primeiro"
    results.sort(key=lambda c: c.priority_score, reverse=True)
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
    item.health_score = snapshot_rows[-1].health_score if snapshot_rows else None

    return item


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

    client_row.last_contact_at = datetime.utcnow()
    db.commit()

    return get_client_detail(client_id, current_user, db)