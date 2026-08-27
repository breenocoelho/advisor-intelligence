import uuid
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import ThresholdRule
from app.schemas import ThresholdRuleOut, ThresholdRuleIn
from app.routers.clients import resolve_org_id
from app.services.intelligence.thresholds import DEFAULT_THRESHOLDS
from app.services.audit import log_action

router = APIRouter()


@router.get("/")
def list_threshold_rules(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    rules = (
        db.query(ThresholdRule)
        .filter(ThresholdRule.org_id == org_id)
        .order_by(ThresholdRule.signal_key, ThresholdRule.suitability_profile)
        .all()
        if org_id is not None
        else []
    )
    return {
        "defaults": {k: float(v) for k, v in DEFAULT_THRESHOLDS.items()},
        "rules": [ThresholdRuleOut.model_validate(r) for r in rules],
    }


@router.put("/", response_model=ThresholdRuleOut)
def upsert_threshold_rule(
    payload: ThresholdRuleIn,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    if org_id is None:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Organização não encontrada")
    if payload.signal_key not in DEFAULT_THRESHOLDS:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="signal_key desconhecido")

    rule = (
        db.query(ThresholdRule)
        .filter(
            ThresholdRule.org_id == org_id,
            ThresholdRule.signal_key == payload.signal_key,
            ThresholdRule.suitability_profile == payload.suitability_profile,
        )
        .first()
    )
    if rule is None:
        rule = ThresholdRule(
            id=uuid.uuid4(), org_id=org_id,
            signal_key=payload.signal_key, suitability_profile=payload.suitability_profile,
        )
        db.add(rule)

    rule.value = payload.value
    rule.updated_by = current_user.get("user_id")
    scope = f"perfil {payload.suitability_profile}" if payload.suitability_profile else "organização"
    log_action(db, org_id, "threshold_rule_saved", f"Threshold '{payload.signal_key}' ({scope}) definido como {payload.value}")
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_threshold_rule(
    rule_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(current_user, db)
    rule = (
        db.query(ThresholdRule)
        .filter(ThresholdRule.id == rule_id, ThresholdRule.org_id == org_id)
        .first()
    )
    if rule is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Regra não encontrada")
    log_action(db, org_id, "threshold_rule_deleted", f"Threshold '{rule.signal_key}' removido, volta ao default")
    db.delete(rule)
    db.commit()
