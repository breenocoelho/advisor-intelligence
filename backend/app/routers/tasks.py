from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import Task, Client, Alert
from app.schemas import TaskOut
from app.routers.clients import resolve_org_id

router = APIRouter()

# ordem de prioridade: alertas criticos primeiro, tarefas sem origem de alerta por ultimo
SEVERITY_ORDER = {"critical": 0, "opportunity": 1, "follow_up": 2}


@router.get("/", response_model=list[TaskOut])
def list_tasks(
    status: str | None = Query(default=None, description="pending | done"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    if org_id is None:
        return []

    query = (
        db.query(Task, Client.name.label("client_name"), Alert.severity)
        .join(Client, Task.client_id == Client.id)
        .outerjoin(Alert, Task.alert_id == Alert.id)
        .filter(Client.org_id == org_id)
    )
    if status:
        query = query.filter(Task.status == status)

    rows = query.all()

    results = []
    for task, client_name, severity in rows:
        item = TaskOut.model_validate(task)
        item.client_name = client_name
        item.severity = severity
        results.append(item)

    # prioridade (severidade de origem) primeiro, depois prazo mais proximo
    results.sort(key=lambda t: (SEVERITY_ORDER.get(t.severity, 3), t.due_date or date.max))
    return results


@router.patch("/{task_id}", response_model=TaskOut)
def update_task_status(
    task_id: str,
    new_status: str = Query(..., description="pending | done"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    task = (
        db.query(Task)
        .join(Client, Task.client_id == Client.id)
        .filter(Task.id == task_id, Client.org_id == org_id)
        .first()
    )
    if task is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada")

    task.status = new_status
    db.commit()
    db.refresh(task)

    client = db.query(Client).filter(Client.id == task.client_id).first()
    alert = db.query(Alert).filter(Alert.id == task.alert_id).first() if task.alert_id else None

    item = TaskOut.model_validate(task)
    item.client_name = client.name if client else None
    item.severity = alert.severity if alert else None
    return item