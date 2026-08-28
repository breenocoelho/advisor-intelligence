"""
Opportunity Engine v1 (Prioridade 11 -- Insight Engine: Opportunity como
entidade real). Nao detecta nada novo -- promove alertas que ja' sao
'severity=opportunity' hoje (idle_cash, upcoming_maturity) pra um registro
com lifecycle proprio (detected -> reviewed -> ... -> closed), em vez de
ficarem so' como mais um item na lista de alertas.

Score e' uma heuristica v1 explicita, documentada aqui, NAO um modelo de
ML: potential_value (extraido do valor em R$ ja' presente na explicacao do
alerta) + urgency (dias ate' vencimento, quando aplicavel) + confidence
(fixo por tipo, ate' existir dado de conversao real pra calibrar).
"""
import re
import uuid
from dataclasses import dataclass

from app.models import Client, Alert, Opportunity

CONFIDENCE_BY_TYPE = {
    "idle_cash": 70,
    "upcoming_maturity": 80,
}

_CURRENCY_RE = re.compile(r"R\$\s*([\d,]+\.\d{2})")
_DAYS_RE = re.compile(r"vence em (\d+) dia")


def _extract_currency(explanation: str | None) -> float | None:
    if not explanation:
        return None
    match = _CURRENCY_RE.search(explanation)
    if not match:
        return None
    # alert_engine formata com f"{valor:,.2f}" (convencao US: virgula milhar,
    # ponto decimal) -- ex: "R$ 12,345.67"
    raw = match.group(1).replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def _extract_urgency(alert_type: str, explanation: str | None) -> int:
    if alert_type == "upcoming_maturity" and explanation:
        match = _DAYS_RE.search(explanation)
        if match:
            days = int(match.group(1))
            return max(0, min(100, 100 - days * 2))
    return 40  # sem prazo explicito -- urgencia moderada fixa (idle_cash, etc.)


@dataclass
class OpportunityScore:
    potential_value: float | None
    urgency: int
    confidence: int
    score: int


def score_opportunity(alert: Alert) -> OpportunityScore:
    potential_value = _extract_currency(alert.explanation)
    urgency = _extract_urgency(alert.alert_type, alert.explanation)
    confidence = CONFIDENCE_BY_TYPE.get(alert.alert_type, 60)

    # normaliza potential_value pra 0-100 (referencia: R$500k = 100 pontos,
    # e' um teto arbitrario razoavel pro porte de carteira do MVP)
    value_score = min(100, (potential_value or 0) / 5000)
    score = round(value_score * 0.5 + urgency * 0.3 + confidence * 0.2)
    return OpportunityScore(potential_value=potential_value, urgency=urgency, confidence=confidence, score=score)


def run_opportunity_detection(db) -> int:
    """Upsert por (client_id, opportunity_type), mesmo padrao de upsert do
    alert_engine -- roda depois dele, sobre os alertas 'new' com
    severity='opportunity' que sobraram naquele run."""
    clients = db.query(Client).all()
    total_created = 0

    for client in clients:
        open_opportunity_alerts = (
            db.query(Alert)
            .filter(Alert.client_id == client.id, Alert.status == "new", Alert.severity == "opportunity")
            .all()
        )

        existing = (
            db.query(Opportunity)
            .filter(Opportunity.client_id == client.id)
            .all()
        )
        existing_by_type = {o.opportunity_type: o for o in existing}

        matched_types = set()
        for alert in open_opportunity_alerts:
            matched_types.add(alert.alert_type)
            computed = score_opportunity(alert)
            record = existing_by_type.get(alert.alert_type)
            if record is not None:
                record.source_alert_id = alert.id
                record.potential_value = computed.potential_value
                record.urgency = computed.urgency
                record.confidence = computed.confidence
                record.score = computed.score
                record.explanation = alert.explanation
            else:
                db.add(Opportunity(
                    id=uuid.uuid4(),
                    org_id=client.org_id,
                    client_id=client.id,
                    source_alert_id=alert.id,
                    opportunity_type=alert.alert_type,
                    status="detected",
                    potential_value=computed.potential_value,
                    urgency=computed.urgency,
                    confidence=computed.confidence,
                    score=computed.score,
                    explanation=alert.explanation,
                ))
                total_created += 1

        # condicao deixou de valer (alerta fechado/nao existe mais) -- so'
        # remove oportunidades ainda no estagio inicial "detected"; a partir
        # do momento que o assessor mexeu no lifecycle, o registro fica
        # (historico de que aquilo foi trabalhado)
        for opp_type, opp in existing_by_type.items():
            if opp_type in matched_types:
                continue
            if opp.status == "detected":
                db.delete(opp)

        db.commit()

    return total_created
