"""
Sync standalone (ainda nao e' task do Celery): le os mocks da XP via
XPMockClient e grava no modelo canonico (Organization, Advisor, Client,
ClientAdvisorHistory, Account, Asset, Position).

Rodar (dentro de backend/, com o venv ativado):
    python sync_xp_mock.py
"""
import uuid
from datetime import datetime, date

from app.database import SessionLocal
from app.models import Organization, Advisor, Client, ClientAdvisorHistory, Account, Asset, Position
from app.integrations.xp.mock_client import XPMockClient

client = XPMockClient()

# Classes de ativo do payload v2/positions -> asset_class canonico
ASSET_CLASS_KEYS = [
    "coe", "funds", "fixedIncome", "checkingAccount",
    "pensionFunds", "repo", "treasury", "stock", "tradedFunds",
]


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.fromisoformat(value).date()


def get_or_create_org(db) -> Organization:
    org = db.query(Organization).filter(Organization.name == "Escritorio Piloto").first()
    if org is None:
        org = Organization(id=uuid.uuid4(), name="Escritorio Piloto")
        db.add(org)
        db.commit()
        db.refresh(org)
    return org


def get_or_create_advisor(db, org: Organization, xp_advisor_code: str) -> Advisor:
    advisor = db.query(Advisor).filter(Advisor.xp_advisor_code == xp_advisor_code).first()
    if advisor is None:
        advisor = Advisor(
            id=uuid.uuid4(), org_id=org.id,
            xp_advisor_code=xp_advisor_code, name=f"Assessor {xp_advisor_code}",
        )
        db.add(advisor)
        db.commit()
        db.refresh(advisor)
    return advisor


def upsert_client(db, org: Organization, account_data: dict) -> Client:
    xp_client_id = str(account_data["accountCode"])  # chave estavel, nao dimAccountCode
    existing = db.query(Client).filter(Client.xp_client_id == xp_client_id).first()

    fields = dict(
        org_id=org.id,
        xp_client_id=xp_client_id,
        name=f"Cliente {xp_client_id}",  # a API nao traz nome real (so GUID de CPF)
        birth_year=account_data.get("birthYear"),
        birth_month=account_data.get("birthMonth"),
        marital_status=account_data.get("maritalStatus"),
        activity=account_data.get("activity"),
        suitability=account_data.get("dscSuitability"),
        declared_wealth_total=(
            (account_data.get("realStateValue") or 0)
            + (account_data.get("movableAssetsValue") or 0)
            + (account_data.get("financialApplicationsValue") or 0)
            + (account_data.get("othersValue") or 0)
        ),
        qualified_investor=account_data.get("qualifiedInvestorTerm"),
        professional_investor=account_data.get("professionalTerm"),
        last_synced_at=datetime.utcnow(),
    )

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        db.commit()
        return existing

    new_client = Client(id=uuid.uuid4(), **fields)
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    return new_client


def upsert_client_advisor_history(db, client_row: Client, advisor: Advisor, relation_date: date):
    current = (
        db.query(ClientAdvisorHistory)
        .filter(ClientAdvisorHistory.client_id == client_row.id, ClientAdvisorHistory.valid_to.is_(None))
        .first()
    )
    if current and current.advisor_id == advisor.id:
        return  # ja esta vigente com o mesmo assessor, nada a fazer

    if current and current.advisor_id != advisor.id:
        current.valid_to = relation_date  # fecha o vinculo anterior
        db.commit()

    if not current or current.advisor_id != advisor.id:
        db.add(ClientAdvisorHistory(
            id=uuid.uuid4(), client_id=client_row.id, advisor_id=advisor.id,
            valid_from=relation_date, valid_to=None,
        ))
        db.commit()


def get_or_create_account(db, client_row: Client, subtype: str) -> Account:
    account = (
        db.query(Account)
        .filter(Account.client_id == client_row.id, Account.account_subtype == subtype)
        .first()
    )
    if account is None:
        account = Account(
            id=uuid.uuid4(), client_id=client_row.id,
            xp_account_id=client_row.xp_client_id, account_subtype=subtype,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
    return account


def upsert_asset(db, item: dict, asset_class: str) -> Asset:
    xp_asset_id = item.get("assetId")
    existing = None
    if xp_asset_id:
        existing = db.query(Asset).filter(Asset.xp_asset_id == xp_asset_id).first()

    fields = dict(
        xp_asset_id=xp_asset_id,
        asset_code=item.get("cetipSelicCode") or item.get("isin"),
        isin_code=item.get("isin"),
        cnpj_code=item.get("fundCNPJ"),
        asset_class=asset_class,
        name=item.get("asset", "Ativo sem nome"),
        issuer=item.get("issuer"),
        due_date=parse_date(item.get("dueDate")),
        index_description=item.get("indexDsc") or None,
        rate=item.get("rate"),
    )

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        db.commit()
        return existing

    new_asset = Asset(id=uuid.uuid4(), **fields)
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    return new_asset


def insert_position(db, account: Account, asset: Asset, item: dict, position_date: date):
    exists = (
        db.query(Position)
        .filter(Position.account_id == account.id, Position.asset_id == asset.id,
                Position.position_date == position_date)
        .first()
    )
    if exists:
        return  # ja sincronizado hoje

    db.add(Position(
        id=uuid.uuid4(), account_id=account.id, asset_id=asset.id,
        quantity=item.get("closingQuantity"),
        market_value=item.get("closingValue") or 0,
        period_purchase_value=item.get("purchaseValue") or 0,
        period_sale_value=item.get("saleValue") or 0,
        position_date=position_date,
    ))
    db.commit()


def sync_checking_account(db, account: Account, item: dict, position_date: date):
    """checkingAccount nao tem assetId/asset -- trata como posicao 'caixa' generica."""
    cash_asset = db.query(Asset).filter(Asset.asset_class == "checkingAccount",
                                         Asset.name == "Caixa/Disponivel").first()
    if cash_asset is None:
        cash_asset = Asset(id=uuid.uuid4(), asset_class="checkingAccount", name="Caixa/Disponivel")
        db.add(cash_asset)
        db.commit()
        db.refresh(cash_asset)

    insert_position(db, account, cash_asset, {
        "closingQuantity": None,
        "closingValue": item.get("closingValue") or 0,
        "purchaseValue": 0, "saleValue": 0,
    }, position_date)


def sync_positions_for_date(db, account: Account, positions_payload: dict, position_date: date):
    """Grava as posicoes de um payload de /v2/positions/customers/{code} numa
    data especifica. Extraido para ser reutilizado tanto pelo sync 'de hoje'
    (sync_client, abaixo) quanto pelo replay historico
    (replay_xp_mock_history.py, Phase 2) -- insert_position ja e' idempotente
    por (account_id, asset_id, position_date), entao rodar duas vezes para a
    mesma data nao duplica nada."""
    for asset_class in ASSET_CLASS_KEYS:
        items = positions_payload.get(asset_class, [])
        for item in items:
            if asset_class == "checkingAccount":
                sync_checking_account(db, account, item, position_date)
                continue
            asset = upsert_asset(db, item, asset_class)
            insert_position(db, account, asset, item, position_date)


def sync_client(db, org: Organization, client_data: dict, relation: dict):
    xp_client_id = str(client_data["accountCode"])
    client_row = upsert_client(db, org, client_data)

    advisor = get_or_create_advisor(db, org, relation["advisorCode"])
    relation_date = parse_date(relation["date"]) or date.today()
    upsert_client_advisor_history(db, client_row, advisor, relation_date)

    investment_account = get_or_create_account(db, client_row, "investment")
    position_date = date.today()

    positions_payload = client.get_positions_v2(int(xp_client_id))
    sync_positions_for_date(db, investment_account, positions_payload, position_date)

    # AUM = soma de todas as posicoes do cliente na data de hoje
    total_aum = sum(
        (p.market_value or 0)
        for p in db.query(Position)
        .join(Account, Position.account_id == Account.id)
        .filter(Account.client_id == client_row.id, Position.position_date == position_date)
        .all()
    )
    client_row.aum = total_aum
    db.commit()

    print(f"  Cliente {xp_client_id}: AUM sincronizado = R$ {total_aum:,.2f}")


def main():
    db = SessionLocal()
    try:
        org = get_or_create_org(db)

        accounts = client.get_accounts()
        relations = client.get_account_advisor_relation()
        relations_by_code = {r["accountCode"]: r for r in relations}

        print(f"Sincronizando {len(accounts)} clientes...")
        for account_data in accounts:
            code = account_data["accountCode"]
            relation = relations_by_code.get(code)
            if relation is None:
                print(f"  Cliente {code}: sem vinculo de assessor no mock, pulando.")
                continue
            sync_client(db, org, account_data, relation)

        print("Sync concluido.")
    finally:
        db.close()


if __name__ == "__main__":
    main()