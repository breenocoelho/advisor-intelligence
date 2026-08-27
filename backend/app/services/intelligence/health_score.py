"""
Health Score: heuristica simples e explicavel (nao um modelo de ML).
Comeca em 100 e desconta penalidades por concentracao, caixa ociosa e
baixa diversificacao. As faixas (health_score_good/_warn) sao so para
apresentacao -- o calculo em si nao usa faixa, usa os thresholds de
concentracao/caixa ociosa direto.
"""
from decimal import Decimal

from app.schemas import ScoreBreakdownItem
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


def health_score_breakdown(db, org_id, client, snapshot, cache: dict | None = None) -> list[ScoreBreakdownItem]:
    """3 fatores macro por tras do health score, pra tooltip no frontend --
    reaproveita os mesmos campos ja gravados no snapshot (nao recalcula
    nada novo), so' traduz em direcao (up/down) + explicacao."""
    if snapshot is None:
        return []

    idle_cash_threshold = get_threshold(db, "idle_cash", org_id, client, cache=cache)
    issuer_threshold = get_threshold(db, "concentration_issuer", org_id, client, cache=cache)

    allocation = snapshot.allocation_json or {}
    distinct_asset_classes = len([v for v in allocation.values() if v and v > 0])
    liquidity_pct = Decimal(snapshot.liquidity_pct or 0)
    top_issuer_pct = Decimal(snapshot.top_issuer_concentration or 0)

    items = []

    if distinct_asset_classes >= MIN_ASSET_CLASSES_FOR_FULL_SCORE:
        items.append(ScoreBreakdownItem(
            direction="up", label="Diversificação de ativos",
            detail=f"{distinct_asset_classes} classes de ativo na carteira",
        ))
    else:
        items.append(ScoreBreakdownItem(
            direction="down", label="Baixa diversificação",
            detail=f"Apenas {distinct_asset_classes} classe(s) de ativo na carteira",
        ))

    if liquidity_pct <= idle_cash_threshold:
        items.append(ScoreBreakdownItem(
            direction="up", label="Caixa ocioso sob controle",
            detail=f"{liquidity_pct * 100:.1f}% do PL em caixa",
        ))
    else:
        items.append(ScoreBreakdownItem(
            direction="down", label="Caixa ocioso elevado",
            detail=f"{liquidity_pct * 100:.1f}% do PL em caixa (acima de {idle_cash_threshold * 100:.0f}%)",
        ))

    if top_issuer_pct <= issuer_threshold:
        items.append(ScoreBreakdownItem(
            direction="up", label="Concentração de emissor sob controle",
            detail=f"Maior emissor representa {top_issuer_pct * 100:.1f}% do PL",
        ))
    else:
        items.append(ScoreBreakdownItem(
            direction="down", label="Concentração de emissor",
            detail=f"Maior emissor representa {top_issuer_pct * 100:.1f}% do PL (acima de {issuer_threshold * 100:.0f}%)",
        ))

    return items
