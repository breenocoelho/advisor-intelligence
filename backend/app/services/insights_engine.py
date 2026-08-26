"""
Motor de insights. Ao contrario do alert_engine (que apaga e recria os
alertas "new" a cada run), insights sao deduplicados: enquanto o assessor
nao "percebeu" o insight (status new/viewed), cada run so atualiza a
mesma linha. Uma vez actioned/dismissed, so reabre o ciclo com uma linha
nova se a evidencia mudou materialmente.
"""
from decimal import Decimal

from app.models import Client, Insight
from app.services.signals.concentration_by_issuer import check_issuer_concentration, SignalFinding

MATERIAL_CHANGE_PCT = Decimal("0.05")  # variacao absoluta de pct que reabre o ciclo

ALL_SIGNALS = [check_issuer_concentration]


def _material_change(existing: Insight, finding: SignalFinding) -> bool:
    old_evidence = existing.evidence or {}
    old_pct = old_evidence.get("pct")
    new_pct = finding.evidence.get("pct")
    if old_pct is None or new_pct is None:
        return True
    return abs(Decimal(str(new_pct)) - Decimal(str(old_pct))) > MATERIAL_CHANGE_PCT


def _upsert_insight(db, client: Client, finding: SignalFinding) -> bool:
    existing = (
        db.query(Insight)
        .filter(
            Insight.client_id == client.id,
            Insight.insight_type == finding.insight_type,
            Insight.asset_class == finding.asset_class,
        )
        .order_by(Insight.created_at.desc())
        .first()
    )

    if existing is None:
        db.add(Insight(
            org_id=client.org_id,
            client_id=client.id,
            insight_type=finding.insight_type,
            asset_class=finding.asset_class,
            severity=finding.severity,
            title=finding.title,
            explanation=finding.explanation,
            evidence=finding.evidence,
            status="new",
        ))
        return True

    if existing.status in ("new", "viewed"):
        existing.title = finding.title
        existing.explanation = finding.explanation
        existing.evidence = finding.evidence
        return False

    # actioned | dismissed -- so reabre com mudanca material
    if _material_change(existing, finding):
        db.add(Insight(
            org_id=client.org_id,
            client_id=client.id,
            insight_type=finding.insight_type,
            asset_class=finding.asset_class,
            severity=finding.severity,
            title=finding.title,
            explanation=finding.explanation,
            evidence=finding.evidence,
            status="new",
        ))
        return True

    return False


def run_insights_engine(db) -> int:
    clients = db.query(Client).all()
    total_created = 0

    for client in clients:
        for signal in ALL_SIGNALS:
            finding = signal(db, client)
            if finding is None:
                continue
            created = _upsert_insight(db, client, finding)
            if created:
                total_created += 1
        db.commit()

    return total_created
