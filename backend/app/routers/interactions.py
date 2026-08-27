from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import Client, ClientInteraction, ClientAdvisorHistory
from app.schemas import InteractionOut, InteractionCreate
from app.routers.clients import resolve_org_id
from app.services.audit import log_action

router = APIRouter()


def _current_advisor_id(db: Session, client_id):
    row = (
        db.query(ClientAdvisorHistory.advisor_id)
        .filter(ClientAdvisorHistory.client_id == client_id, ClientAdvisorHistory.valid_to.is_(None))
        .first()
    )
    return row[0] if row else None


@router.get("/{client_id}/interactions", response_model=list[InteractionOut])
def list_interactions(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    rows = (
        db.query(ClientInteraction)
        .filter(ClientInteraction.client_id == client_id)
        .order_by(ClientInteraction.interaction_date.desc())
        .all()
    )
    return rows


@router.post("/{client_id}/interactions", response_model=InteractionOut)
def create_interaction(
    client_id: str,
    payload: InteractionCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    interaction = ClientInteraction(
        client_id=client_row.id,
        advisor_id=_current_advisor_id(db, client_row.id),
        interaction_type=payload.interaction_type,
        interaction_date=payload.interaction_date,
        subject=payload.subject,
        notes=payload.notes,
    )
    db.add(interaction)
    log_action(
        db, org_id, "interaction_created",
        f"Interação registrada para {client_row.name}: {payload.interaction_type}" + (f" — {payload.subject}" if payload.subject else ""),
        client_id=client_row.id,
    )
    db.commit()
    db.refresh(interaction)
    return interaction


@router.put("/{client_id}/interactions/{interaction_id}", response_model=InteractionOut)
def update_interaction(
    client_id: str,
    interaction_id: str,
    payload: InteractionCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    interaction = (
        db.query(ClientInteraction)
        .filter(ClientInteraction.id == interaction_id, ClientInteraction.client_id == client_row.id)
        .first()
    )
    if interaction is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Interação não encontrada")

    interaction.interaction_type = payload.interaction_type
    interaction.interaction_date = payload.interaction_date
    interaction.subject = payload.subject
    interaction.notes = payload.notes
    log_action(db, org_id, "interaction_updated", f"Interação de {client_row.name} editada", client_id=client_row.id)
    db.commit()
    db.refresh(interaction)
    return interaction


@router.delete("/{client_id}/interactions/{interaction_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_interaction(
    client_id: str,
    interaction_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    interaction = (
        db.query(ClientInteraction)
        .filter(ClientInteraction.id == interaction_id, ClientInteraction.client_id == client_row.id)
        .first()
    )
    if interaction is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Interação não encontrada")

    db.delete(interaction)
    log_action(db, org_id, "interaction_deleted", f"Interação de {client_row.name} removida", client_id=client_row.id)
    db.commit()
    return None
