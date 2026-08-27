from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, Body, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import Insight, Client, Task
from app.schemas import InsightOut, TaskOut, TaskCreate
from app.routers.clients import resolve_org_id

router = APIRouter()


@router.get("/", response_model=list[InsightOut])
def list_insights(
    status: str | None = Query(default=None, description="new | viewed | dismissed | actioned"),
    severity: str | None = Query(default=None, description="critical | opportunity | follow_up"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    if org_id is None:
        return []

    query = (
        db.query(Insight, Client.name.label("client_name"))
        .join(Client, Insight.client_id == Client.id)
        .filter(Insight.org_id == org_id)
    )

    if status:
        query = query.filter(Insight.status == status)
    if severity:
        query = query.filter(Insight.severity == severity)

    rows = query.order_by(Insight.severity, Insight.created_at.desc()).all()

    results = []
    for insight, client_name in rows:
        item = InsightOut.model_validate(insight)
        item.client_name = client_name
        results.append(item)
    return results


@router.patch("/{insight_id}", response_model=InsightOut)
def update_insight_status(
    insight_id: str,
    new_status: str = Query(..., description="new | viewed | dismissed | actioned"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    insight = (
        db.query(Insight)
        .filter(Insight.id == insight_id, Insight.org_id == org_id)
        .first()
    )
    if insight is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Insight não encontrado")

    insight.status = new_status
    db.commit()
    db.refresh(insight)

    client = db.query(Client).filter(Client.id == insight.client_id).first()
    item = InsightOut.model_validate(insight)
    item.client_name = client.name if client else None
    return item


@router.post("/{insight_id}/tasks", response_model=TaskOut)
def create_task_from_insight(
    insight_id: str,
    payload: TaskCreate = Body(default_factory=TaskCreate),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    insight = (
        db.query(Insight)
        .filter(Insight.id == insight_id, Insight.org_id == org_id)
        .first()
    )
    if insight is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Insight não encontrado")

    task = Task(
        client_id=insight.client_id,
        insight_id=insight.id,
        description=(payload.description or insight.explanation or f"Follow-up: {insight.insight_type}"),
        due_date=(payload.due_date or (date.today() + timedelta(days=7))),
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    item = TaskOut.model_validate(task)
    item.severity = insight.severity
    return item
