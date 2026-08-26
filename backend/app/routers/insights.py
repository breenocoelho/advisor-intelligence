from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import Insight, Client
from app.schemas import InsightOut
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
