"""
Replay historico dos mocks da XP (Product Intelligence Upgrade, Phase 2).
Para cada offset temporal (-90, -60, -30, 0 dias), sincroniza as posicoes
daquela data (insert, nao upsert -- ja e' seguro rodar de novo) e grava um
agregado em client_daily_snapshot + positivador_snapshots.

Pre-requisito: rodar sync_xp_mock.py pelo menos uma vez antes (cria
Organization/Advisor/Client/ClientAdvisorHistory/Account) -- mas o script
tambem funciona standalone, criando essas entidades se ainda nao existirem.

Rodar (dentro de backend/, com o venv ativado):
    python replay_xp_mock_history.py
"""
import uuid
from datetime import timedelta, date
from decimal import Decimal

from app.database import SessionLocal
from app.models import (
    Client, Account, Asset, Position, ClientAdvisorHistory,
    ClientDailySnapshot, PositivadorSnapshot, AdvisorDailySnapshot,
)
from app.integrations.xp.mock_client import XPMockClient
from app.services.intelligence.health_score import compute_health_score
from generate_xp_mocks import SNAPSHOT_OFFSETS_DAYS, TODAY
from sync_xp_mock import (
    get_or_create_org, get_or_create_advisor, upsert_client,
    upsert_client_advisor_history, get_or_create_account,
    sync_positions_for_date, parse_date,
)

client = XPMockClient()


def compute_daily_snapshot(db, org, client_row: Client, snapshot_date: date):
    rows = (
        db.query(Position, Asset)
        .join(Asset, Position.asset_id == Asset.id)
        .join(Account, Position.account_id == Account.id)
        .filter(Account.client_id == client_row.id, Position.position_date == snapshot_date)
        .all()
    )
    if not rows:
        return

    total_aum = sum((p.market_value or 0) for p, _ in rows)
    if not total_aum:
        return
    total_aum = Decimal(total_aum)

    by_asset_class: dict[str, Decimal] = {}
    by_issuer: dict[str, Decimal] = {}
    total_purchase = Decimal(0)
    total_sale = Decimal(0)
    top_position_value = Decimal(0)

    for position, asset in rows:
        value = Decimal(position.market_value or 0)
        by_asset_class[asset.asset_class] = by_asset_class.get(asset.asset_class, Decimal(0)) + value
        if asset.issuer:
            by_issuer[asset.issuer] = by_issuer.get(asset.issuer, Decimal(0)) + value
        total_purchase += Decimal(position.period_purchase_value or 0)
        total_sale += Decimal(position.period_sale_value or 0)
        if asset.asset_class != "checkingAccount" and value > top_position_value:
            top_position_value = value

    allocation_json = {k: float(v / total_aum) for k, v in by_asset_class.items()}
    liquidity_pct = by_asset_class.get("checkingAccount", Decimal(0)) / total_aum
    top_issuer_pct = (max(by_issuer.values()) / total_aum) if by_issuer else Decimal(0)
    top_position_pct = top_position_value / total_aum
    distinct_asset_classes = len([k for k, v in by_asset_class.items() if v > 0])

    health_score = compute_health_score(
        db, org.id, client_row,
        top_position_pct=top_position_pct,
        top_issuer_pct=top_issuer_pct,
        liquidity_pct=liquidity_pct,
        distinct_asset_classes=distinct_asset_classes,
    )

    existing = (
        db.query(ClientDailySnapshot)
        .filter(ClientDailySnapshot.client_id == client_row.id, ClientDailySnapshot.snapshot_date == snapshot_date)
        .first()
    )
    fields = dict(
        aum=total_aum,
        allocation_json=allocation_json,
        top_issuer_concentration=top_issuer_pct,
        liquidity_pct=liquidity_pct,
        monthly_purchase_value=total_purchase,
        monthly_sale_value=total_sale,
        health_score=health_score,
    )
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(ClientDailySnapshot(
            id=uuid.uuid4(), org_id=org.id, client_id=client_row.id,
            snapshot_date=snapshot_date, **fields,
        ))
    db.commit()


def sync_positivador_snapshot(db, client_row: Client, xp_code: int, snapshot_date: date):
    rows = client.get_positivador(xp_code)
    match = next((r for r in rows if r["referenceDate"] == snapshot_date.isoformat()), None)
    if match is None:
        return

    advisor_link = (
        db.query(ClientAdvisorHistory)
        .filter(ClientAdvisorHistory.client_id == client_row.id, ClientAdvisorHistory.valid_to.is_(None))
        .first()
    )

    existing = (
        db.query(PositivadorSnapshot)
        .filter(PositivadorSnapshot.client_id == client_row.id, PositivadorSnapshot.reference_date == snapshot_date)
        .first()
    )
    fields = dict(
        advisor_id=advisor_link.advisor_id if advisor_link else None,
        status=match.get("status"),
        activated_in_month=match.get("activatedInMonth"),
        churned_in_month=match.get("churnedInMonth"),
        net_capture_in_month=match.get("netCaptureInMonth"),
        financial_applications=match.get("financialApplications"),
        revenue_in_month=match.get("revenueInMonth"),
        suitability=match.get("suitability"),
    )
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(PositivadorSnapshot(
            id=uuid.uuid4(), client_id=client_row.id, reference_date=snapshot_date, **fields,
        ))
    db.commit()


def compute_advisor_snapshots(db, org, snapshot_date: date):
    """Agrega client_daily_snapshot por assessor (vinculo vigente em
    ClientAdvisorHistory) numa data -- advisor_daily_snapshot
    (Historical Foundation, Etapa 1)."""
    rows = (
        db.query(ClientAdvisorHistory.advisor_id, ClientDailySnapshot)
        .join(ClientDailySnapshot, ClientDailySnapshot.client_id == ClientAdvisorHistory.client_id)
        .filter(ClientAdvisorHistory.valid_to.is_(None), ClientDailySnapshot.snapshot_date == snapshot_date)
        .all()
    )

    by_advisor: dict = {}
    for advisor_id, snapshot in rows:
        bucket = by_advisor.setdefault(advisor_id, {"aum": Decimal(0), "client_count": 0, "net_flow": Decimal(0)})
        bucket["aum"] += Decimal(snapshot.aum or 0)
        bucket["client_count"] += 1
        bucket["net_flow"] += Decimal(snapshot.monthly_purchase_value or 0) - Decimal(snapshot.monthly_sale_value or 0)

    for advisor_id, agg in by_advisor.items():
        existing = (
            db.query(AdvisorDailySnapshot)
            .filter(AdvisorDailySnapshot.advisor_id == advisor_id, AdvisorDailySnapshot.snapshot_date == snapshot_date)
            .first()
        )
        fields = dict(aum=agg["aum"], client_count=agg["client_count"], net_flow=agg["net_flow"])
        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
        else:
            db.add(AdvisorDailySnapshot(
                id=uuid.uuid4(), org_id=org.id, advisor_id=advisor_id, snapshot_date=snapshot_date, **fields,
            ))
    db.commit()


def main():
    db = SessionLocal()
    try:
        org = get_or_create_org(db)
        accounts = client.get_accounts()
        relations = client.get_account_advisor_relation()
        relations_by_code = {r["accountCode"]: r for r in relations}

        for offset in sorted(SNAPSHOT_OFFSETS_DAYS):
            snapshot_date = (TODAY + timedelta(days=offset)).date()
            print(f"Replay offset {offset} ({snapshot_date.isoformat()})...")

            for account_data in accounts:
                code = account_data["accountCode"]
                relation = relations_by_code.get(code)
                if relation is None:
                    continue

                client_row = db.query(Client).filter(Client.xp_client_id == str(code)).first()
                if client_row is None:
                    client_row = upsert_client(db, org, account_data)
                    advisor = get_or_create_advisor(db, org, relation["advisorCode"])
                    relation_date = parse_date(relation["date"]) or snapshot_date
                    upsert_client_advisor_history(db, client_row, advisor, relation_date)

                account = get_or_create_account(db, client_row, "investment")

                positions_payload = client.get_positions_v2_as_of(code, offset)
                sync_positions_for_date(db, account, positions_payload, snapshot_date)

                compute_daily_snapshot(db, org, client_row, snapshot_date)
                sync_positivador_snapshot(db, client_row, code, snapshot_date)

            compute_advisor_snapshots(db, org, snapshot_date)

        print("Replay concluido.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
