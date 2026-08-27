from fastapi import APIRouter, Depends, Query, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import (
    AuditLog, Client, ClientFieldOverride,
    ClientExtendedFieldDefinition, ClientExtendedFieldOption, ClientExtendedFieldAssignment,
)
from app.schemas import (
    AuditLogOut, FieldOverrideAdminOut, ExtendedFieldDefinitionOut, ExtendedFieldDefinitionIn,
    ExtendedFieldOptionOut, ExtendedFieldOptionIn, ExtendedFieldAssignmentIn,
)
from app.routers.clients import resolve_org_id
from app.services.audit import log_action

router = APIRouter()


@router.get("/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(
    limit: int = Query(default=100, le=500),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    if org_id is None:
        return []

    rows = (
        db.query(AuditLog, Client.name)
        .outerjoin(Client, AuditLog.client_id == Client.id)
        .filter(AuditLog.org_id == org_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    results = []
    for log, client_name in rows:
        item = AuditLogOut.model_validate(log)
        item.client_name = client_name
        results.append(item)
    return results


@router.get("/field-overrides", response_model=list[FieldOverrideAdminOut])
def list_all_field_overrides(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    if org_id is None:
        return []

    rows = (
        db.query(ClientFieldOverride, Client)
        .join(Client, ClientFieldOverride.client_id == Client.id)
        .filter(Client.org_id == org_id)
        .order_by(ClientFieldOverride.created_at.desc())
        .all()
    )
    return [
        FieldOverrideAdminOut(
            client_id=client.id, client_name=client.name, field_name=override.field_name,
            override_value=override.override_value, created_at=override.created_at,
        )
        for override, client in rows
    ]


@router.get("/extended-fields", response_model=list[ExtendedFieldDefinitionOut])
def list_extended_fields(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    if org_id is None:
        return []

    definitions = db.query(ClientExtendedFieldDefinition).filter(ClientExtendedFieldDefinition.org_id == org_id).all()
    results = []
    for definition in definitions:
        options = (
            db.query(ClientExtendedFieldOption)
            .filter(ClientExtendedFieldOption.field_definition_id == definition.id)
            .all()
        )
        results.append(ExtendedFieldDefinitionOut(
            id=definition.id, key=definition.key, label=definition.label,
            options=[ExtendedFieldOptionOut(id=o.id, value=o.value) for o in options],
        ))
    return results


@router.post("/extended-fields", response_model=ExtendedFieldDefinitionOut)
def create_extended_field(
    payload: ExtendedFieldDefinitionIn,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    if org_id is None:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Organização não encontrada")

    existing = (
        db.query(ClientExtendedFieldDefinition)
        .filter(ClientExtendedFieldDefinition.org_id == org_id, ClientExtendedFieldDefinition.key == payload.key)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Já existe um campo com essa chave")

    definition = ClientExtendedFieldDefinition(org_id=org_id, key=payload.key, label=payload.label)
    db.add(definition)
    log_action(db, org_id, "extended_field_created", f"Campo customizado '{payload.label}' criado")
    db.commit()
    db.refresh(definition)
    return ExtendedFieldDefinitionOut(id=definition.id, key=definition.key, label=definition.label, options=[])


@router.delete("/extended-fields/{field_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_extended_field(
    field_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    definition = (
        db.query(ClientExtendedFieldDefinition)
        .filter(ClientExtendedFieldDefinition.id == field_id, ClientExtendedFieldDefinition.org_id == org_id)
        .first()
    )
    if definition is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Campo não encontrado")

    option_ids = [
        o.id for o in db.query(ClientExtendedFieldOption).filter(ClientExtendedFieldOption.field_definition_id == definition.id).all()
    ]
    if option_ids:
        db.query(ClientExtendedFieldAssignment).filter(ClientExtendedFieldAssignment.option_id.in_(option_ids)).delete(synchronize_session=False)
        db.query(ClientExtendedFieldOption).filter(ClientExtendedFieldOption.id.in_(option_ids)).delete(synchronize_session=False)

    log_action(db, org_id, "extended_field_deleted", f"Campo customizado '{definition.label}' removido")
    db.delete(definition)
    db.commit()
    return None


@router.post("/extended-fields/{field_id}/options", response_model=ExtendedFieldOptionOut)
def create_extended_field_option(
    field_id: str,
    payload: ExtendedFieldOptionIn,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    definition = (
        db.query(ClientExtendedFieldDefinition)
        .filter(ClientExtendedFieldDefinition.id == field_id, ClientExtendedFieldDefinition.org_id == org_id)
        .first()
    )
    if definition is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Campo não encontrado")

    option = ClientExtendedFieldOption(field_definition_id=definition.id, value=payload.value)
    db.add(option)
    log_action(db, org_id, "extended_field_option_created", f"Opção '{payload.value}' adicionada ao campo '{definition.label}'")
    db.commit()
    db.refresh(option)
    return ExtendedFieldOptionOut(id=option.id, value=option.value)


@router.delete("/extended-fields/options/{option_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_extended_field_option(
    option_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    option = (
        db.query(ClientExtendedFieldOption)
        .join(ClientExtendedFieldDefinition, ClientExtendedFieldOption.field_definition_id == ClientExtendedFieldDefinition.id)
        .filter(ClientExtendedFieldOption.id == option_id, ClientExtendedFieldDefinition.org_id == org_id)
        .first()
    )
    if option is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Opção não encontrada")

    db.query(ClientExtendedFieldAssignment).filter(ClientExtendedFieldAssignment.option_id == option.id).delete(synchronize_session=False)
    log_action(db, org_id, "extended_field_option_deleted", f"Opção '{option.value}' removida")
    db.delete(option)
    db.commit()
    return None


@router.post("/extended-fields/assignments", status_code=http_status.HTTP_201_CREATED)
def assign_extended_field(
    payload: ExtendedFieldAssignmentIn,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    client_row = db.query(Client).filter(Client.id == payload.client_id, Client.org_id == org_id).first()
    if client_row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    option = (
        db.query(ClientExtendedFieldOption, ClientExtendedFieldDefinition)
        .join(ClientExtendedFieldDefinition, ClientExtendedFieldOption.field_definition_id == ClientExtendedFieldDefinition.id)
        .filter(ClientExtendedFieldOption.id == payload.option_id, ClientExtendedFieldDefinition.org_id == org_id)
        .first()
    )
    if option is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Opção não encontrada")
    option_row, definition = option

    existing = (
        db.query(ClientExtendedFieldAssignment)
        .filter(ClientExtendedFieldAssignment.client_id == client_row.id, ClientExtendedFieldAssignment.option_id == option_row.id)
        .first()
    )
    if existing is not None:
        return {"id": str(existing.id)}

    assignment = ClientExtendedFieldAssignment(client_id=client_row.id, option_id=option_row.id)
    db.add(assignment)
    log_action(
        db, org_id, "extended_field_assigned",
        f"{client_row.name} classificado como '{option_row.value}' em '{definition.label}'",
        client_id=client_row.id,
    )
    db.commit()
    db.refresh(assignment)
    return {"id": str(assignment.id)}


@router.delete("/extended-fields/assignments/{assignment_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def unassign_extended_field(
    assignment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    assignment = (
        db.query(ClientExtendedFieldAssignment, Client)
        .join(Client, ClientExtendedFieldAssignment.client_id == Client.id)
        .filter(ClientExtendedFieldAssignment.id == assignment_id, Client.org_id == org_id)
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Atribuição não encontrada")
    assignment_row, client_row = assignment

    log_action(db, org_id, "extended_field_unassigned", f"Classificação removida de {client_row.name}", client_id=client_row.id)
    db.delete(assignment_row)
    db.commit()
    return None
