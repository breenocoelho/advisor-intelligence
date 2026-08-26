"""
Motor de alertas do MVP. Cada regra e' uma funcao pura; a gravacao no
banco fica isolada em run_alert_engine(). Thresholds vem do modulo
central app.services.intelligence.thresholds (permite override por
perfil de suitability sem mudar este arquivo).
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.models import Client, Asset, Alert, Position
from app.services.intelligence.position_queries import latest_positions_query
from app.services.intelligence.thresholds import get_threshold


@dataclass
class Finding:
    alert_type: str
    severity: str
    explanation: str


def rule_idle_cash(db, client: Client) -> list[Finding]:
    if not client.aum:
        return []

    threshold = get_threshold(db, "idle_cash", client.org_id, client)

    latest_ids = [p.id for p in latest_positions_query(db, client.id).all()]
    cash_values = (
        db.query(Position.market_value)
        .join(Asset, Position.asset_id == Asset.id)
        .filter(Position.id.in_(latest_ids), Asset.asset_class == "checkingAccount")
        .all()
    )
    total_cash = sum((v[0] or 0) for v in cash_values)
    if total_cash == 0:
        return []

    pct = Decimal(total_cash) / Decimal(client.aum)
    if pct > threshold:
        return [Finding(
            alert_type="idle_cash",
            severity="opportunity",
            explanation=(
                f"Cliente com R$ {total_cash:,.2f} em caixa "
                f"({pct * 100:.1f}% do patrimonio de R$ {client.aum:,.2f}). "
                f"Threshold: {threshold * 100:.0f}%."
            ),
        )]
    return []


def rule_concentration(db, client: Client) -> list[Finding]:
    if not client.aum:
        return []

    threshold = get_threshold(db, "concentration", client.org_id, client)

    latest_ids = [p.id for p in latest_positions_query(db, client.id).all()]
    if not latest_ids:
        return []

    positions = (
        db.query(Position, Asset)
        .join(Asset, Position.asset_id == Asset.id)
        .filter(Position.id.in_(latest_ids), Asset.asset_class != "checkingAccount")
        .all()
    )

    findings = []
    for position, asset in positions:
        if not position.market_value:
            continue
        pct = Decimal(position.market_value) / Decimal(client.aum)
        if pct > threshold:
            findings.append(Finding(
                alert_type="concentration",
                severity="critical",
                explanation=(
                    f"Posicao em '{asset.name}' ({asset.asset_class}) representa "
                    f"{pct * 100:.1f}% do patrimonio (R$ {position.market_value:,.2f} "
                    f"de R$ {client.aum:,.2f}). Threshold: {threshold * 100:.0f}%."
                ),
            ))
    return findings


def rule_upcoming_maturity(db, client: Client, today: date | None = None) -> list[Finding]:
    today = today or date.today()
    days_threshold = int(get_threshold(db, "upcoming_maturity_days", client.org_id, client))
    limit_date = today + timedelta(days=days_threshold)

    latest_ids = [p.id for p in latest_positions_query(db, client.id).all()]
    if not latest_ids:
        return []

    positions = (
        db.query(Position, Asset)
        .join(Asset, Position.asset_id == Asset.id)
        .filter(
            Position.id.in_(latest_ids),
            Asset.due_date.isnot(None),
            Asset.due_date >= today,
            Asset.due_date <= limit_date,
        )
        .all()
    )

    findings = []
    for position, asset in positions:
        days_to_maturity = (asset.due_date - today).days
        findings.append(Finding(
            alert_type="upcoming_maturity",
            severity="opportunity",
            explanation=(
                f"Ativo '{asset.name}' vence em {days_to_maturity} dia(s) "
                f"({asset.due_date.isoformat()}), valor atual R$ {position.market_value:,.2f}. "
                f"Recomenda-se contato para definir realocacao antes do resgate cair em conta."
            ),
        ))
    return findings


def rule_relevant_movement(db, client: Client) -> list[Finding]:
    if not client.aum:
        return []

    threshold = get_threshold(db, "relevant_movement", client.org_id, client)

    positions = latest_positions_query(db, client.id).all()

    total_purchase = sum((p.period_purchase_value or 0) for p in positions)
    total_sale = sum((p.period_sale_value or 0) for p in positions)

    findings = []
    aum = Decimal(client.aum)

    if total_sale and Decimal(total_sale) / aum > threshold:
        findings.append(Finding(
            alert_type="relevant_movement",
            severity="follow_up",
            explanation=(
                f"Resgates no periodo somam R$ {total_sale:,.2f} "
                f"({Decimal(total_sale) / aum * 100:.1f}% do patrimonio). "
                f"Vale entender o motivo e se ha necessidade de liquidez ou perda de confianca."
            ),
        ))

    if total_purchase and Decimal(total_purchase) / aum > threshold:
        findings.append(Finding(
            alert_type="relevant_movement",
            severity="follow_up",
            explanation=(
                f"Aplicacoes no periodo somam R$ {total_purchase:,.2f} "
                f"({Decimal(total_purchase) / aum * 100:.1f}% do patrimonio) — "
                f"possivel mudanca de estrategia ou realocacao entre classes."
            ),
        ))

    return findings


def rule_no_recent_contact(db, client: Client, today: date | None = None) -> list[Finding]:
    """Usa Client.last_contact_at, alimentado pelo botao "Registrar contato"
    no Client 360 (ou pelo backfill a partir do mock de CRM)."""
    today = today or date.today()
    days_threshold = int(get_threshold(db, "no_contact_days", client.org_id, client))

    if client.last_contact_at is None:
        return [Finding(
            alert_type="no_recent_contact",
            severity="follow_up",
            explanation="Nenhum contato registrado com este cliente ainda.",
        )]

    days_since_contact = (today - client.last_contact_at.date()).days
    if days_since_contact > days_threshold:
        return [Finding(
            alert_type="no_recent_contact",
            severity="follow_up",
            explanation=(
                f"Sem contato registrado ha {days_since_contact} dias "
                f"(ultimo em {client.last_contact_at.date().isoformat()}). "
                f"Threshold: {days_threshold} dias."
            ),
        )]
    return []


ALL_RULES = [
    rule_idle_cash,
    rule_concentration,
    rule_upcoming_maturity,
    rule_relevant_movement,
    rule_no_recent_contact,
]


def run_alert_engine(db) -> int:
    clients = db.query(Client).all()
    total_created = 0

    for client in clients:
        db.query(Alert).filter(Alert.client_id == client.id, Alert.status == "new").delete()

        findings: list[Finding] = []
        for rule in ALL_RULES:
            findings.extend(rule(db, client))

        for finding in findings:
            db.add(Alert(
                client_id=client.id,
                alert_type=finding.alert_type,
                severity=finding.severity,
                explanation=finding.explanation,
                status="new",
            ))
            total_created += 1

        db.commit()

    return total_created
