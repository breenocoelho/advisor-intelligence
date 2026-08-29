from fastapi import APIRouter, Depends, Query, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import Opportunity, Client
from app.schemas import OpportunityOut, OpportunityStatusIn
from app.routers.clients import resolve_org_id
from app.services.audit import log_action
from app.services.intelligence.opportunity_engine import RECOMMENDED_ACTION_BY_TYPE

VALID_STATUSES = {
    "detected", "reviewed", "assigned", "contacted", "proposal", "executed", "won", "lost", "closed",
}

router = APIRouter()


def _build_opportunity_out(opportunity: Opportunity, client_name: str | None) -> OpportunityOut:
    item = OpportunityOut.model_validate(opportunity)
    item.client_name = client_name
    item.recommended_action = RECOMMENDED_ACTION_BY_TYPE.get(opportunity.opportunity_type)
    return item


@router.get("/", response_model=list[OpportunityOut])
def list_opportunities(
    status: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    if org_id is None:
        return []

    query = (
        db.query(Opportunity, Client.name)
        .join(Client, Opportunity.client_id == Client.id)
        .filter(Opportunity.org_id == org_id)
    )
    if status:
        query = query.filter(Opportunity.status == status)

    rows = query.order_by(Opportunity.score.desc().nullslast()).all()

    return [_build_opportunity_out(opportunity, client_name) for opportunity, client_name in rows]


@router.get("/{opportunity_id}", response_model=OpportunityOut)
def get_opportunity(
    opportunity_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    row = (
        db.query(Opportunity, Client.name)
        .join(Client, Opportunity.client_id == Client.id)
        .filter(Opportunity.id == opportunity_id, Opportunity.org_id == org_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Oportunidade não encontrada")

    opportunity, client_name = row
    return _build_opportunity_out(opportunity, client_name)


@router.patch("/{opportunity_id}", response_model=OpportunityOut)
def update_opportunity_status(
    opportunity_id: str,
    payload: OpportunityStatusIn,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Muda o status no lifecycle (detected -> ... -> won/lost/closed).
    Nao valida transicoes (MVP) -- so' que o valor esta na lista conhecida."""
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Status inválido")

    org_id = resolve_org_id(current_user, db)
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.id == opportunity_id, Opportunity.org_id == org_id)
        .first()
    )
    if opportunity is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Oportunidade não encontrada")

    opportunity.status = payload.status
    client = db.query(Client).filter(Client.id == opportunity.client_id).first()
    log_action(
        db, org_id, "opportunity_status_changed",
        f"Oportunidade '{opportunity.opportunity_type}' de {client.name if client else 'cliente'} movida para \"{payload.status}\"",
        client_id=opportunity.client_id,
    )
    db.commit()
    db.refresh(opportunity)

    return _build_opportunity_out(opportunity, client.name if client else None)
