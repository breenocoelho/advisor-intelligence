"""
Motor de alertas do MVP. Cada regra e' uma funcao pura; a gravacao no
banco fica isolada em run_alert_engine(). Thresholds vem do modulo
central app.services.intelligence.thresholds (permite override por
perfil de suitability sem mudar este arquivo).
"""
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.models import Client, Asset, Alert, Position, ClientInteraction, Task, ClientDailySnapshot
from app.services.intelligence.position_queries import latest_positions_query
from app.services.intelligence.thresholds import get_threshold
from app.services.intelligence.relationship_score import get_contact_cadence_days
from app.services.intelligence.behavioral_health import compute_behavioral_findings


@dataclass
class Finding:
    alert_type: str
    severity: str
    explanation: str
    asset_id: uuid.UUID | None = None  # so preenchido quando o alerta e' sobre UM ativo especifico


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
                asset_id=asset.id,
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
            asset_id=asset.id,
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
    no Client 360 (ou pelo backfill a partir do mock de CRM). O threshold
    de dias nao e' mais fixo -- vem da cadencia de contato por tier do
    cliente (Relationship Intelligence, Etapa 3), configuravel por org."""
    today = today or date.today()
    has_interaction = db.query(ClientInteraction).filter(ClientInteraction.client_id == client.id).first() is not None
    days_threshold = int(get_contact_cadence_days(db, client.org_id, client, has_any_interaction=has_interaction))

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
                f"Cadencia esperada para este cliente: {days_threshold} dias."
            ),
        )]
    return []


def rule_followup_overdue(db, client: Client, today: date | None = None) -> list[Finding]:
    """Tarefas pendentes com prazo vencido -- 'Follow-up atrasado' da
    Relationship Intelligence (Etapa 3)."""
    today = today or date.today()

    overdue_tasks = (
        db.query(Task)
        .filter(Task.client_id == client.id, Task.status == "pending", Task.due_date.isnot(None), Task.due_date < today)
        .all()
    )

    findings = []
    for task in overdue_tasks:
        days_overdue = (today - task.due_date).days
        findings.append(Finding(
            alert_type="followup_overdue",
            severity="follow_up",
            explanation=(
                f"Follow-up atrasado ha {days_overdue} dia(s) (prazo era {task.due_date.isoformat()}): "
                f"\"{task.description}\"."
            ),
            asset_id=task.asset_id,
        ))
    return findings


def rule_behavioral_anomaly(db, client: Client) -> list[Finding]:
    """Client Health Intelligence, camada Behavioral -- compara o cliente
    contra o proprio baseline historico (nao um valor fixo). Ver
    app.services.intelligence.behavioral_health."""
    snapshots = (
        db.query(ClientDailySnapshot)
        .filter(ClientDailySnapshot.client_id == client.id)
        .order_by(ClientDailySnapshot.snapshot_date)
        .all()
    )
    findings = compute_behavioral_findings(db, client.org_id, client, snapshots)
    return [
        Finding(alert_type=f"behavioral_{f.finding_type}", severity=f.severity, explanation=f"{f.label}: {f.detail}")
        for f in findings
    ]


ALL_RULES = [
    rule_idle_cash,
    rule_concentration,
    rule_upcoming_maturity,
    rule_relevant_movement,
    rule_no_recent_contact,
    rule_followup_overdue,
    rule_behavioral_anomaly,
]


def run_alert_engine(db) -> int:
    """Cada run faz upsert dos alertas 'new' do cliente por chave
    (alert_type, asset_id), em vez de apagar e recriar tudo -- assim
    'created_at' passa a significar "quando o alerta foi identificado pela
    primeira vez" mesmo que a explicacao/severidade mude de um run pro
    outro (ex: % de concentracao subindo dia a dia). Um alerta 'new' com
    uma Task apontando pra ele (via "Lembrar depois") nunca e' apagado --
    a FK de Task.alert_id quebraria -- mas continua sendo atualizado
    normalmente se a condicao que o gerou ainda for verdadeira."""
    clients = db.query(Client).all()
    total_created = 0

    for client in clients:
        protected_ids = {
            row[0] for row in
            db.query(Task.alert_id).filter(Task.client_id == client.id, Task.alert_id.isnot(None)).all()
        }

        existing_alerts = (
            db.query(Alert)
            .filter(Alert.client_id == client.id, Alert.status == "new")
            .all()
        )
        existing_by_key = {(a.alert_type, a.asset_id): a for a in existing_alerts}

        findings: list[Finding] = []
        for rule in ALL_RULES:
            findings.extend(rule(db, client))

        matched_keys = set()
        for finding in findings:
            key = (finding.alert_type, finding.asset_id)
            matched_keys.add(key)
            existing = existing_by_key.get(key)
            if existing is not None:
                existing.severity = finding.severity
                existing.explanation = finding.explanation
            else:
                db.add(Alert(
                    client_id=client.id,
                    asset_id=finding.asset_id,
                    alert_type=finding.alert_type,
                    severity=finding.severity,
                    explanation=finding.explanation,
                    status="new",
                ))
                total_created += 1

        # condicao deixou de valer nesse run -- remove, exceto se protegido por uma task
        for key, alert in existing_by_key.items():
            if key in matched_keys or alert.id in protected_ids:
                continue
            db.delete(alert)

        db.commit()

    return total_created
