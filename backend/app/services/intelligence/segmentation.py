"""
Client Segmentation (Prioridade 8). Segmentos sao computados on-the-fly a
cada request, nunca persistidos -- um cliente pode cair em varios ao mesmo
tempo, e como tudo vem de threshold_rules (mesmo mecanismo do resto do
motor de inteligencia), nao existe nenhum corte fixo no codigo: mudar um
threshold em /config/thresholds muda os segmentos imediatamente.
"""
from dataclasses import dataclass
from decimal import Decimal

from app.services.intelligence.thresholds import get_threshold

RISK_UP_CLASSES = {"stock", "coe"}


@dataclass
class Segment:
    key: str
    label: str
    category: str  # "financial" | "relationship" | "behavioral"
    reason: str


def compute_segments(
    db, org_id, client, latest_snapshot, aum_change_pct: float | None,
    relationship_band: str | None, relationship_score: int | None,
    behavioral_findings: list, has_interaction: bool, cache: dict | None = None,
) -> list[Segment]:
    segments: list[Segment] = []

    # --- Financial ---
    high_value_threshold = get_threshold(db, "high_value_aum_threshold", org_id, client, cache=cache)
    if client.aum and Decimal(client.aum) >= high_value_threshold:
        segments.append(Segment(
            key="high_aum", label="High AUM", category="financial",
            reason=f"Patrimônio de R$ {float(client.aum):,.0f} acima do limite de R$ {float(high_value_threshold):,.0f}.",
        ))

    growth_threshold = float(get_threshold(db, "segment_growth_pct", org_id, client, cache=cache))
    if aum_change_pct is not None:
        if aum_change_pct >= growth_threshold:
            segments.append(Segment(
                key="growing", label="Growing", category="financial",
                reason=f"AUM cresceu {aum_change_pct * 100:.1f}% no período (limite: {growth_threshold * 100:.0f}%).",
            ))
        elif aum_change_pct <= -growth_threshold:
            segments.append(Segment(
                key="declining", label="Declining", category="financial",
                reason=f"AUM caiu {abs(aum_change_pct) * 100:.1f}% no período (limite: {growth_threshold * 100:.0f}%).",
            ))

    if latest_snapshot is not None:
        idle_cash_threshold = get_threshold(db, "idle_cash", org_id, client, cache=cache)
        liquidity_pct = Decimal(latest_snapshot.liquidity_pct or 0)
        if liquidity_pct > idle_cash_threshold:
            segments.append(Segment(
                key="high_liquidity", label="High Liquidity", category="financial",
                reason=f"{liquidity_pct * 100:.1f}% do PL em caixa, acima do threshold de {idle_cash_threshold * 100:.0f}%.",
            ))

        issuer_threshold = get_threshold(db, "concentration_issuer", org_id, client, cache=cache)
        top_issuer_pct = Decimal(latest_snapshot.top_issuer_concentration or 0)
        if top_issuer_pct > issuer_threshold:
            segments.append(Segment(
                key="high_concentration", label="High Concentration", category="financial",
                reason=f"Maior emissor representa {top_issuer_pct * 100:.1f}% do PL, acima do threshold de {issuer_threshold * 100:.0f}%.",
            ))

    # --- Relationship ---
    if relationship_score is not None:
        good = get_threshold(db, "relationship_score_good", org_id, client, cache=cache)
        warn = get_threshold(db, "relationship_score_warn", org_id, client, cache=cache)
        if relationship_score >= good:
            segments.append(Segment(
                key="highly_engaged", label="Highly Engaged", category="relationship",
                reason=f"Relationship score {relationship_score} ({relationship_band}).",
            ))
        elif relationship_score >= warn:
            segments.append(Segment(
                key="normal_engagement", label="Normal", category="relationship",
                reason=f"Relationship score {relationship_score} ({relationship_band}).",
            ))
        else:
            segments.append(Segment(
                key="at_risk", label="At Risk", category="relationship",
                reason=f"Relationship score {relationship_score} ({relationship_band}), abaixo do threshold de {warn}.",
            ))

    # --- Behavioral ---
    movement_finding = next((f for f in behavioral_findings if f.finding_type == "unusual_movement"), None)
    risk_shift = next(
        (f for f in behavioral_findings if f.finding_type == "unusual_allocation_shift" and "aumentou" in f.detail),
        None,
    )
    if movement_finding:
        segments.append(Segment(
            key="high_activity", label="High Activity", category="behavioral", reason=movement_finding.detail,
        ))
    if risk_shift:
        segments.append(Segment(
            key="increasing_risk", label="Increasing Risk", category="behavioral", reason=risk_shift.detail,
        ))
    if not movement_finding and not behavioral_findings and not has_interaction:
        segments.append(Segment(
            key="dormant", label="Dormant", category="behavioral",
            reason="Sem interações registradas e sem movimentação fora do padrão no histórico disponível.",
        ))

    return segments
