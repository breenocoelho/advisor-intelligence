"""
Concentracao por emissor (assets.issuer) -- diferente da concentracao por
posicao do alert_engine. Duas posicoes do mesmo emissor podem, juntas,
passar do threshold sem que nenhuma isoladamente dispare o alerta
existente. Roda como Insight, nunca grava Alert (evita duplicar sinal do
mesmo problema).
"""
from dataclasses import dataclass
from decimal import Decimal

from app.models import Asset, Client, Position
from app.services.intelligence.position_queries import latest_positions_query
from app.services.intelligence.thresholds import get_threshold


@dataclass
class SignalFinding:
    insight_type: str
    asset_class: str | None
    severity: str
    title: str
    explanation: str
    evidence: dict


def check_issuer_concentration(db, client: Client) -> SignalFinding | None:
    if not client.aum or client.aum == 0:
        return None

    latest_ids = [p.id for p in latest_positions_query(db, client.id).all()]
    if not latest_ids:
        return None

    rows = (
        db.query(Position, Asset)
        .join(Asset, Position.asset_id == Asset.id)
        .filter(Position.id.in_(latest_ids), Asset.issuer.isnot(None))
        .all()
    )

    totals_by_issuer: dict[str, Decimal] = {}
    for position, asset in rows:
        if not position.market_value:
            continue
        totals_by_issuer[asset.issuer] = totals_by_issuer.get(asset.issuer, Decimal(0)) + Decimal(position.market_value)

    if not totals_by_issuer:
        return None

    top_issuer, top_value = max(totals_by_issuer.items(), key=lambda kv: kv[1])
    aum = Decimal(client.aum)
    pct = top_value / aum

    threshold = get_threshold(db, "concentration_issuer", client.org_id, client)
    if pct <= threshold:
        return None

    return SignalFinding(
        insight_type="concentration_by_issuer",
        asset_class=None,
        severity="critical",
        title=f"Concentração no emissor {top_issuer}",
        explanation=(
            f"{pct * 100:.1f}% do patrimônio (R$ {top_value:,.2f} de R$ {aum:,.2f}) está "
            f"exposto ao emissor '{top_issuer}', somando todas as posições. "
            f"Threshold: {threshold * 100:.0f}%."
        ),
        evidence={"issuer": top_issuer, "pct": float(pct), "value": float(top_value), "aum": float(aum)},
    )
