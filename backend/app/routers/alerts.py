from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, Body, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import Alert, Client, Task
from app.schemas import AlertOut, TaskOut, TaskCreate
from app.routers.clients import resolve_org_id
from app.services.audit import log_action

router = APIRouter()


@router.get("/", response_model=list[AlertOut])
def list_alerts(
    status: str | None = Query(default=None, description="new | viewed | dismissed | actioned"),
    severity: str | None = Query(default=None, description="critical | opportunity | follow_up"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    if org_id is None:
        return []

    query = (
        db.query(Alert, Client.name, Client.suitability)
        .join(Client, Alert.client_id == Client.id)
        .filter(Client.org_id == org_id)
    )

    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)

    rows = query.order_by(Alert.severity, Alert.created_at.desc()).all()

    results = []
    for alert, client_name, client_suitability in rows:
        item = AlertOut.model_validate(alert)
        item.client_name = client_name
        item.client_suitability = client_suitability
        results.append(item)
    return results


@router.patch("/{alert_id}", response_model=AlertOut)
def update_alert_status(
    alert_id: str,
    new_status: str = Query(..., description="new | viewed | dismissed | actioned"),
    note: str | None = Query(default=None, description="por que foi acionado/descartado"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    alert = (
        db.query(Alert)
        .join(Client, Alert.client_id == Client.id)
        .filter(Alert.id == alert_id, Client.org_id == org_id)
        .first()
    )
    if alert is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado")

    alert.status = new_status
    if note is not None:
        alert.resolution_note = note
    db.commit()
    db.refresh(alert)

    client = db.query(Client).filter(Client.id == alert.client_id).first()
    item = AlertOut.model_validate(alert)
    item.client_name = client.name if client else None
    return item


@router.post("/{alert_id}/tasks", response_model=TaskOut)
def create_task_from_alert(
    alert_id: str,
    payload: TaskCreate = Body(default_factory=TaskCreate),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cria uma tarefa de follow-up a partir de um alerta. O frontend
    (modal) normalmente envia description/due_date preenchidos; se
    algum vier vazio, cai para os defaults (explicacao do alerta,
    prazo de 7 dias)."""
    org_id = resolve_org_id(current_user, db)
    alert = (
        db.query(Alert)
        .join(Client, Alert.client_id == Client.id)
        .filter(Alert.id == alert_id, Client.org_id == org_id)
        .first()
    )
    if alert is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado")

    task = Task(
        client_id=alert.client_id,
        alert_id=alert.id,
        asset_id=alert.asset_id,
        description=(payload.description or alert.explanation or f"Follow-up: {alert.alert_type}"),
        due_date=(payload.due_date or (date.today() + timedelta(days=7))),
        status="pending",
    )
    db.add(task)

    client = db.query(Client).filter(Client.id == alert.client_id).first()
    log_action(
        db, org_id, "task_created",
        f"Tarefa criada para {client.name if client else 'cliente'} a partir de alerta ({alert.alert_type}): \"{task.description}\"",
        client_id=alert.client_id,
    )
    db.commit()
    db.refresh(task)

    item = TaskOut.model_validate(task)
    item.severity = alert.severity
    return item