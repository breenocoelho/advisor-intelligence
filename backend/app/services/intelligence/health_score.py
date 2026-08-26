"""
Health Score: heuristica simples e explicavel (nao um modelo de ML).
Comeca em 100 e desconta penalidades por concentracao, caixa ociosa e
baixa diversificacao. As faixas (health_score_good/_warn) sao so para
apresentacao -- o calculo em si nao usa faixa, usa os thresholds de
concentracao/caixa ociosa direto.
"""
from decimal import Decimal

from app.services.intelligence.thresholds import get_threshold

CONCENTRATION_PENALTY = 25
IDLE_CASH_PENALTY = 15
LOW_DIVERSIFICATION_PENALTY = 10
MIN_ASSET_CLASSES_FOR_FULL_SCORE = 3


def compute_health_score(
    db,
    org_id,
    client,
    top_position_pct: Decimal,
    top_issuer_pct: Decimal,
    liquidity_pct: Decimal,
    distinct_asset_classes: int,
) -> int:
    score = 100

    concentration_threshold = get_threshold(db, "concentration", org_id, client)
    issuer_threshold = get_threshold(db, "concentration_issuer", org_id, client)
    if top_position_pct > concentration_threshold or top_issuer_pct > issuer_threshold:
        score -= CONCENTRATION_PENALTY

    idle_cash_threshold = get_threshold(db, "idle_cash", org_id, client)
    if liquidity_pct > idle_cash_threshold:
        score -= IDLE_CASH_PENALTY

    if distinct_asset_classes < MIN_ASSET_CLASSES_FOR_FULL_SCORE:
        score -= LOW_DIVERSIFICATION_PENALTY

    return max(0, score)
