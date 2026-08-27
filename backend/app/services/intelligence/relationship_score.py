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

RECENCY_WEIGHT = Decimal("0.25")
FREQUENCY_WEIGHT = Decimal("0.20")
ENGAGEMENT_WEIGHT = Decimal("0.20")
AUM_STABILITY_WEIGHT = Decimal("0.20")
OPEN_TASKS_WEIGHT = Decimal("0.15")


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
    today: date | None = None, cache: dict | None = None,
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

    score = round(
        components["recency"] * RECENCY_WEIGHT
        + components["frequency"] * FREQUENCY_WEIGHT
        + components["engagement"] * ENGAGEMENT_WEIGHT
        + components["aum_stability"] * AUM_STABILITY_WEIGHT
        + components["open_tasks"] * OPEN_TASKS_WEIGHT
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
}


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
