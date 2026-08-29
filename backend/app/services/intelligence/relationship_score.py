"""
Relationship Score (Etapa 3 - Relationship Intelligence). Principio da
spec: nunca um numero sozinho -- sempre score + banda + lista de
explicacoes construidas a partir dos numeros reais (mesmo principio ja
usado em Alert.explanation/Insight.explanation).

Heuristica simples e documentada aqui mesmo, nao um modelo estatistico --
mesma filosofia do health_score (app/services/intelligence/health_score.py).
"""
import statistics
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.schemas import ScoreBreakdownItem
from app.services.intelligence.thresholds import get_threshold

# Fase 5: rebalanceado de 25/20/20/20/15 pra caber o 6o componente
# (opportunity_followup), mantendo a soma em 100.
RECENCY_WEIGHT = Decimal("0.20")
FREQUENCY_WEIGHT = Decimal("0.15")
ENGAGEMENT_WEIGHT = Decimal("0.15")
AUM_STABILITY_WEIGHT = Decimal("0.15")
OPEN_TASKS_WEIGHT = Decimal("0.15")
OPPORTUNITY_FOLLOWUP_WEIGHT = Decimal("0.20")


def classify_contact_status(days_since_contact: int | None, cadence_days: int) -> str:
    """overdue | approaching | ok -- extraido de clients.relationship_overview
    pra ser reaproveitado tambem no calculo de contact_coverage do assessor
    (Advisor Analytics, Fase 5)."""
    if days_since_contact is None or days_since_contact > cadence_days:
        return "overdue"
    if days_since_contact > cadence_days * 0.7:
        return "approaching"
    return "ok"


@dataclass
class RelationshipScoreResult:
    score: int
    band: str
    components: dict = field(default_factory=dict)
    explanation: list[str] = field(default_factory=list)


def get_contact_cadence_days(db, org_id, client, has_any_interaction: bool, cache: dict | None = None) -> Decimal:
    """Classifica o cliente num tier (por AUM, ou 'low engagement' se nunca
    teve interacao registrada) e resolve a cadencia esperada daquele tier.
    Tudo configuravel via threshold_rules -- nenhum numero fixo no codigo."""
    aum = Decimal(client.aum or 0)
    high_value_threshold = get_threshold(db, "high_value_aum_threshold", org_id, client, cache=cache)

    if aum >= high_value_threshold:
        return get_threshold(db, "contact_cadence_high_value_days", org_id, client, cache=cache)
    if not has_any_interaction:
        return get_threshold(db, "contact_cadence_low_engagement_days", org_id, client, cache=cache)
    return get_threshold(db, "contact_cadence_standard_days", org_id, client, cache=cache)


def _score_over_cadence(days_over_ratio: float) -> int:
    """1.0 = exatamente na cadencia (score 100). Decai ate 0 em 3x a cadencia."""
    if days_over_ratio <= 1:
        return 100
    return max(0, round(100 - (days_over_ratio - 1) * 50))


def compute_relationship_score(
    db, org_id, client, interactions: list, tasks: list, aum_history: list[Decimal],
    open_opportunities: list | None = None, today: date | None = None, cache: dict | None = None,
) -> RelationshipScoreResult:
    today = today or date.today()
    components: dict[str, int] = {}
    explanation: list[str] = []

    cadence_days = get_contact_cadence_days(db, org_id, client, has_any_interaction=len(interactions) > 0, cache=cache)

    # Recency
    if client.last_contact_at is None:
        components["recency"] = 0
        explanation.append("Nenhum contato registrado ainda")
    else:
        days_since = (today - client.last_contact_at.date()).days
        ratio = days_since / float(cadence_days)
        components["recency"] = _score_over_cadence(ratio)
        if days_since <= cadence_days:
            explanation.append(f"Último contato há {days_since} dia(s), dentro da cadência de {int(cadence_days)} dias")
        else:
            explanation.append(f"Último contato há {days_since} dia(s) — cadência esperada é {int(cadence_days)} dias")

    # Frequency (media de intervalo entre interacoes)
    dates_sorted = sorted(i.interaction_date for i in interactions)
    if len(dates_sorted) >= 2:
        gaps = [(dates_sorted[i + 1] - dates_sorted[i]).days for i in range(len(dates_sorted) - 1)]
        avg_gap = sum(gaps) / len(gaps)
        ratio = avg_gap / float(cadence_days)
        components["frequency"] = _score_over_cadence(ratio)
        explanation.append(f"Frequência média de contato: a cada {round(avg_gap)} dias")
    else:
        components["frequency"] = 50
        explanation.append("Histórico de interações insuficiente para calcular frequência")

    # Engagement (interacoes nos ultimos 90 dias vs esperado pela cadencia)
    recent = [i for i in interactions if (today - i.interaction_date).days <= 90]
    expected = 90 / float(cadence_days)
    components["engagement"] = min(100, round(len(recent) / expected * 100)) if expected > 0 else 0
    explanation.append(f"{len(recent)} interação(ões) nos últimos 90 dias")

    # AUM stability (coeficiente de variacao do historico de AUM)
    values = [float(v) for v in aum_history if v]
    if len(values) >= 2:
        mean = sum(values) / len(values)
        cv = (statistics.pstdev(values) / mean) if mean > 0 else 0
        components["aum_stability"] = max(0, round(100 - cv * 300))
        explanation.append("AUM estável no período" if cv < 0.05 else "AUM com variação relevante no período")
    else:
        components["aum_stability"] = 70
        explanation.append("Histórico de AUM insuficiente para avaliar estabilidade")

    # Open tasks
    pending = [t for t in tasks if t.status == "pending"]
    components["open_tasks"] = max(0, 100 - len(pending) * 20)
    if pending:
        overdue = [t for t in pending if t.due_date and t.due_date < today]
        explanation.append(
            f"{len(pending)} follow-up(s) pendente(s)" + (f", {len(overdue)} atrasado(s)" if overdue else "")
        )
    else:
        explanation.append("Nenhum follow-up pendente")

    # Opportunity follow-up: oportunidades detectadas e ainda nao revisadas
    # ha mais tempo que o threshold penalizam -- mesmo padrao de open_tasks
    stale_days = int(get_threshold(db, "opportunity_followup_stale_days", org_id, client, cache=cache))
    stale_opportunities = [
        o for o in (open_opportunities or [])
        if o.status == "detected" and (today - o.created_at.date()).days > stale_days
    ]
    components["opportunity_followup"] = max(0, 100 - len(stale_opportunities) * 20)
    if stale_opportunities:
        explanation.append(
            f"{len(stale_opportunities)} oportunidade(s) detectada(s) ha mais de {stale_days} dias sem revisao"
        )
    else:
        explanation.append("Nenhuma oportunidade parada sem revisão")

    score = round(
        components["recency"] * RECENCY_WEIGHT
        + components["frequency"] * FREQUENCY_WEIGHT
        + components["engagement"] * ENGAGEMENT_WEIGHT
        + components["aum_stability"] * AUM_STABILITY_WEIGHT
        + components["open_tasks"] * OPEN_TASKS_WEIGHT
        + components["opportunity_followup"] * OPPORTUNITY_FOLLOWUP_WEIGHT
    )

    good = get_threshold(db, "relationship_score_good", org_id, client, cache=cache)
    warn = get_threshold(db, "relationship_score_warn", org_id, client, cache=cache)
    band = "Healthy" if score >= good else "Moderate" if score >= warn else "At risk"

    return RelationshipScoreResult(score=score, band=band, components=components, explanation=explanation)


COMPONENT_LABELS = {
    "recency": "Recência de contato",
    "frequency": "Frequência de contato",
    "engagement": "Engajamento",
    "aum_stability": "Estabilidade de patrimônio",
    "open_tasks": "Follow-ups em dia",
    "opportunity_followup": "Follow-up de oportunidades",
}


def batch_compute_relationship_scores(db, org_id, client_ids: list, cache: dict) -> dict:
    """Mesmo calculo de compute_relationship_score, mas buscando
    snapshots/interactions/tasks/opportunities de varios clientes de uma vez
    (client_ids.in_(...)) em vez de 1 query por cliente -- usado onde se
    precisa da banda/score de varios clientes na mesma request sem repetir
    o padrao de batching ja usado em clients.list_clients (ex: Advisor
    Analytics, Fase 5)."""
    from app.models import Client, ClientDailySnapshot, ClientInteraction, Task, Opportunity

    if not client_ids:
        return {}

    clients = db.query(Client).filter(Client.id.in_(client_ids)).all()

    snapshots_by_client: dict = {}
    for s in db.query(ClientDailySnapshot).filter(ClientDailySnapshot.client_id.in_(client_ids)).order_by(ClientDailySnapshot.client_id, ClientDailySnapshot.snapshot_date).all():
        snapshots_by_client.setdefault(s.client_id, []).append(s)

    interactions_by_client: dict = {}
    for i in db.query(ClientInteraction).filter(ClientInteraction.client_id.in_(client_ids)).all():
        interactions_by_client.setdefault(i.client_id, []).append(i)

    tasks_by_client: dict = {}
    for t in db.query(Task).filter(Task.client_id.in_(client_ids)).all():
        tasks_by_client.setdefault(t.client_id, []).append(t)

    opportunities_by_client: dict = {}
    for o in db.query(Opportunity).filter(Opportunity.client_id.in_(client_ids)).all():
        opportunities_by_client.setdefault(o.client_id, []).append(o)

    results = {}
    for client in clients:
        client_snapshots = snapshots_by_client.get(client.id, [])
        results[client.id] = compute_relationship_score(
            db, org_id, client,
            interactions=interactions_by_client.get(client.id, []),
            tasks=tasks_by_client.get(client.id, []),
            aum_history=[s.aum for s in client_snapshots],
            open_opportunities=opportunities_by_client.get(client.id, []),
            cache=cache,
        )
    return results


def score_breakdown(result: RelationshipScoreResult) -> list[ScoreBreakdownItem]:
    """Traduz os componentes ja calculados em direcao (up/down) + a
    explicacao que ja foi gerada junto -- mesma logica de tooltip usada no
    health_score, pra consistencia visual entre os dois scores."""
    items = []
    for (key, value), detail in zip(result.components.items(), result.explanation):
        items.append(ScoreBreakdownItem(
            direction="up" if value >= 70 else "down",
            label=COMPONENT_LABELS.get(key, key),
            detail=detail,
        ))
    return items
