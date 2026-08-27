"""
Gera fixtures de mock para 10 clientes-cenario, no formato real dos
endpoints do XP Data Access (schema confirmado via documentacao real
extraida do portal dev.xpinc.com).

Endpoints mockados:
  - /api/v1/account                          -> account.json
  - /api/v1/account-advisor-relation         -> account_advisor_relation.json
  - /api/v2/positions/customers/{code}       -> v2_positions_{code}.json
  - /api/v1/investment-account/balance/...   -> investment_account_balance_{code}.json
  - /api/v1/digital-account/balance/...      -> digital_account_balance_{code}.json
  - CRM (fonte externa, nao XP)              -> mocks/crm/interactions_mock.json

Rodar uma vez (dentro de backend/, com o venv ativado):
    python generate_xp_mocks.py
"""
import copy
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta

MOCKS_DIR = Path(__file__).parent / "mocks" / "xp"
CRM_DIR = Path(__file__).parent / "mocks" / "crm"
MOCKS_DIR.mkdir(parents=True, exist_ok=True)
CRM_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime(2026, 8, 26)

# dimensao temporal dos mocks (Product Intelligence Upgrade, Phase 2): cada
# cenario passa a ter um valor por offset, com um fator de escala simples
# (ramp linear) para simular uma trajetoria real sem hand-authoring por data.
SNAPSHOT_OFFSETS_DAYS = [-90, -60, -30, 0]


def scale_factor(offset_days: int) -> float:
    """offset -90 -> 0.85, offset 0 -> 1.00 (ramp linear)."""
    return 1.0 - (abs(offset_days) / 90) * 0.15


_POSITION_VALUE_FIELDS = [
    "openingValue", "closingValue",
    "custodyTransferInAmount", "custodyTransferOutAmount",
    "unitInterest", "totalInterest", "profitAndLoss", "closingNetValue",
    "openingQuantity", "closingQuantity", "amount",
]
# purchaseValue/saleValue sao fluxos do periodo, nao tratados por
# _POSITION_VALUE_FIELDS -- ver build_scenario_snapshot() abaixo.


def build_scenario_snapshot(payload: dict, offset_days: int) -> dict:
    """Aplica a dimensao temporal a um payload 'de hoje' (offset 0).

    A maioria das posicoes nao tem fluxo no periodo (purchaseValue e
    saleValue = 0) e so recebe um ramp organico linear pelo tempo.

    Posicoes que TEM fluxo hoje sao tratadas como um evento pontual que
    aconteceu entre a penultima data mockada e hoje -- nao um fluxo que se
    repete identico em toda data historica (bug corrigido: antes o
    saleValue/purchaseValue era escalado do mesmo jeito que o
    closingValue, entao um "resgate" aparecia, proporcionalmente menor,
    em toda data do passado, e o AUM historico crescia junto com o
    resgate em vez de cair quando ele acontece):
      - resgate (saleValue > 0, sem compra): nas datas anteriores ao
        evento, a posicao ainda tem o valor de antes do resgate
        (closingValue atual + saleValue), sem fluxo registrado; o
        resgate em si so aparece na data mais recente.
      - posicao nova comprada com o fluxo do periodo (purchaseValue > 0,
        sem venda): simplesmente nao existe ainda nas datas anteriores.
    """
    if offset_days == 0:
        return copy.deepcopy(payload)

    factor = scale_factor(offset_days)
    snapshot: dict[str, list] = {k: [] for k in payload}

    for asset_class, items in payload.items():
        for item in items:
            sale = item.get("saleValue") or 0
            purchase = item.get("purchaseValue") or 0

            if purchase > 0 and sale == 0:
                # comprada com o fluxo do periodo -- ainda nao existia
                continue

            new_item = copy.deepcopy(item)

            if sale > 0 and purchase == 0:
                # resgatada no periodo -- estado pre-resgate, escalado
                pre_event_value = (item.get("closingValue") or 0) + sale
                scaled_value = round(pre_event_value * factor, 2)
                base_value = item.get("closingValue") or 0
                ratio = (scaled_value / base_value) if base_value else 1.0
                new_item["closingValue"] = scaled_value
                new_item["closingQuantity"] = round((item.get("closingQuantity") or 0) * ratio, 4)
                new_item["purchaseValue"] = 0.0
                new_item["saleValue"] = 0.0
                snapshot[asset_class].append(new_item)
                continue

            # sem fluxo no periodo -- ramp organico simples
            for field in _POSITION_VALUE_FIELDS:
                if field in new_item and isinstance(new_item[field], (int, float)) and new_item[field]:
                    new_item[field] = round(new_item[field] * factor, 2)
            snapshot[asset_class].append(new_item)

    return snapshot


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Definicao dos 10 clientes-cenario
# ---------------------------------------------------------------------------
CLIENTS = [
    {"code": 1001, "label": "Concentracao - Credito Privado Prefixado", "aum": 700_000, "advisor": "AX0001"},
    {"code": 1002, "label": "Concentracao - Credito Privado Pos-fixado", "aum": 650_000, "advisor": "AX0001"},
    {"code": 1003, "label": "Concentracao - Acoes", "aum": 800_000, "advisor": "AX0001"},
    {"code": 1004, "label": "Caixa Ociosa", "aum": 500_000, "advisor": "AX0002"},
    {"code": 1005, "label": "Vencimento Proximo", "aum": 400_000, "advisor": "AX0002"},
    {"code": 1006, "label": "Amortizacao Proxima (limitacao conhecida - ver nota)", "aum": 450_000, "advisor": "AX0002"},
    {"code": 1007, "label": "Movimentacao - Mudanca de Classe", "aum": 600_000, "advisor": "AX0003"},
    {"code": 1008, "label": "Movimentacao - Resgate Relevante", "aum": 350_000, "advisor": "AX0003"},
    {"code": 1009, "label": "Sem Contato (fonte externa, nao XP)", "aum": 300_000, "advisor": "AX0003"},
    {"code": 1010, "label": "Controle - Sem Gatilho", "aum": 550_000, "advisor": "AX0001"},
]

ADVISOR_CODES = {"AX0001": 500001, "AX0002": 500002, "AX0003": 500003}


# ---------------------------------------------------------------------------
# 1) /api/v1/account -- perfil do cliente (dimensao SCD tipo 2)
# ---------------------------------------------------------------------------
def build_accounts() -> list[dict]:
    accounts = []
    for i, c in enumerate(CLIENTS, start=1):
        accounts.append({
            "dimAccountCode": 900_000 + c["code"],
            "accountCode": c["code"],
            "cpfCnpjCodeGuid": f"{i:08d}-0000-0000-0000-000000000000",
            "birthYear": 1975 + i,
            "birthMonth": (i % 12) + 1,
            "registerDate": "2023-01-01T00:00:00",
            "personType": "F",
            "maritalStatus": "CASADO(A)" if i % 2 == 0 else "SOLTEIRO(A)",
            "activity": "PROFISSIONAL_EXEMPLO",
            "dscSuitability": "MODERADO",
            "realStateValue": 0.0,
            "movableAssetsValue": 0.0,
            "incomeValue": 15000.0,
            "financialApplicationsValue": c["aum"],
            "othersValue": 0.0,
            "qualifiedInvestorTerm": "N",
            "professionalTerm": "N",
            "startValidityDate": "2025-01-01T00:00:00",
            "endValidityDate": "9999-12-31T00:00:00",
            "currentRegisterIndicator": 1,
            "id": i,
            "lastUpdate": iso(TODAY),
            "availableData": True,
            "_mock_label": c["label"],  # nao existe no schema real; so para referencia no mock
        })
    return accounts


# ---------------------------------------------------------------------------
# 2) /api/v1/account-advisor-relation -- vinculo cliente x assessor (versus tempo)
# ---------------------------------------------------------------------------
def build_account_advisor_relation() -> list[dict]:
    relations = []
    for i, c in enumerate(CLIENTS, start=1):
        relations.append({
            "officeCode": 1001,
            "dimAccountCode": 900_000 + c["code"],
            "accountCode": c["code"],
            "dimOfficeChannelCode": 3000001,
            "dimAdvisorCode": ADVISOR_CODES[c["advisor"]],
            "cpfCnpjCode": "00000000-0000-0000-0000-000000000000",
            "date": iso(TODAY),
            "advisorCode": c["advisor"],
            "yearPartition": str(TODAY.year),
            "monthPartition": f"{TODAY.month:02d}",
            "dayPartition": f"{TODAY.day:02d}",
            "dimTimeCode": int(TODAY.strftime("%Y%m%d")),
            "id": i,
            "lastUpdate": iso(TODAY),
            "availableData": True,
        })
    return relations


# ---------------------------------------------------------------------------
# 3) /api/v2/positions/customers/{code} -- schema real confirmado
# ---------------------------------------------------------------------------
def empty_v2_position() -> dict:
    return {
        "coe": [], "funds": [], "fixedIncome": [], "checkingAccount": [],
        "pensionFunds": [], "repo": [], "treasury": [], "stock": [], "tradedFunds": [],
    }


def fixed_income_item(client_id, advisor_code, asset, issuer, closing_value,
                       due_date=None, rate=0.0, index_dsc="", purchase_value=0.0,
                       sale_value=0.0, market_type="CDB"):
    return {
        "clientId": client_id, "advisorCode": advisor_code,
        "assetId": str(uuid.uuid4()), "asset": asset, "marketType": market_type,
        "dueDate": iso(due_date), "cetipSelicCode": f"{asset[:10].upper().replace(' ', '')}",
        "issuer": issuer, "marketPrice": None,
        "invoiceId": 0, "effectiveDate": iso(TODAY),
        "purchaseDate": iso(TODAY - timedelta(days=200)),
        "openingValue": round(closing_value * 0.98, 2), "closingValue": closing_value,
        "delta": 0.0, "status": 1,
        "openingQuantity": 0.0, "closingQuantity": 0.0,
        "blockingQuantity": 0.0, "collateralQuantity": 0.0, "lawBlockingQuantity": 0.0,
        "openingUnitPrice": 0.0, "closingUnitPrice": 0.0,
        "purchaseQuantity": 0.0, "saleQuantity": 0.0,
        "custodyTransferInQuantity": 0.0, "custodyTransferOutQuantity": 0.0,
        "purchaseValue": purchase_value, "saleValue": sale_value,
        "custodyTransferInAmount": 0.0, "custodyTransferOutAmount": 0.0,
        "unitInterest": 0.0, "totalInterest": 0.0,
        "creationDate": iso(TODAY),
        "percentage": rate if index_dsc else 0.0, "indexDsc": index_dsc, "rate": rate,
        "strategy": "FixedRate" if not index_dsc else "FloatingRate",
        "unitAmortisation": 0.0, "totalAmortisation": 0.0,
        "unitPremium": 0.0, "totalPremium": 0.0,
        "profitAndLoss": round(closing_value * 0.02, 2), "yield": 0.0025,
        "grossUpProfitAndLoss": 0.0, "grossUpYield": 0.0,
        "cumulativeYield": 1.0, "grossUpCumulativeYield": 0.0,
        "originalDate": iso(TODAY - timedelta(days=200)),
        "originalQuantity": 0.0, "originalUnitPrice": 0.0,
        "incomeTaxRate": 0.15, "incomeTax": 0.0, "iof": 0.0, "iofRate": 0.0,
        "closingNetValue": closing_value,
    }


def stock_item(client_id, advisor_code, asset, isin, closing_value, quantity,
               purchase_value=0.0, sale_value=0.0):
    return {
        "clientId": client_id, "advisorCode": advisor_code,
        "assetId": str(uuid.uuid4()), "asset": asset, "isin": isin, "marketType": "AÇÃO",
        "invoiceId": 0, "effectiveDate": iso(TODAY),
        "purchaseDate": iso(TODAY - timedelta(days=180)),
        "openingValue": round(closing_value * 0.97, 2), "closingValue": closing_value,
        "delta": 0.0, "status": 4,
        "openingQuantity": quantity, "closingQuantity": quantity,
        "blockingQuantity": 0.0, "collateralQuantity": 0.0, "lawBlockingQuantity": 0.0,
        "openingUnitPrice": 0.0, "closingUnitPrice": 0.0,
        "purchaseQuantity": 0.0, "saleQuantity": 0.0,
        "custodyTransferInQuantity": 0.0, "custodyTransferOutQuantity": 0.0,
        "purchaseValue": purchase_value, "saleValue": sale_value,
        "custodyTransferInAmount": 0.0, "custodyTransferOutAmount": 0.0,
        "unitInterest": 0.0, "totalInterest": 0.0,
        "creationDate": iso(TODAY),
        "percentage": None, "indexDsc": None, "rate": None, "strategy": "Equity",
        "unitAmortisation": 0.0, "totalAmortisation": 0.0,
        "unitPremium": 0.0, "totalPremium": 0.0,
        "profitAndLoss": round(closing_value * 0.05, 2), "yield": 0.0,
        "grossUpProfitAndLoss": 0.0, "grossUpYield": 0.0,
        "cumulativeYield": 0.0, "grossUpCumulativeYield": 0.0,
        "originalDate": iso(TODAY - timedelta(days=180)),
        "originalQuantity": quantity, "originalUnitPrice": 0.0,
        "incomeTaxRate": 0.0, "incomeTax": 0.0, "iof": 0.0, "iofRate": 0.0,
        "closingNetValue": closing_value,
        "remuneratedCustodyOpeningQuantity": 0.0, "remuneratedCustodyClosingQuantity": 0.0,
        "remuneratedCustodyOpeningValue": 0.0, "remuneratedCustodyClosingValue": 0.0,
    }


def traded_fund_item(client_id, advisor_code, asset, isin, closing_value, quantity):
    return {
        "clientId": client_id, "advisorCode": advisor_code,
        "assetId": str(uuid.uuid4()), "asset": asset, "isin": isin, "marketType": "FII",
        "invoiceId": 0, "effectiveDate": iso(TODAY),
        "purchaseDate": iso(TODAY - timedelta(days=250)),
        "openingValue": round(closing_value * 0.99, 2), "closingValue": closing_value,
        "delta": 0.0, "status": 4,
        "openingQuantity": quantity, "closingQuantity": quantity,
        "blockingQuantity": 0.0, "collateralQuantity": 0.0, "lawBlockingQuantity": 0.0,
        "openingUnitPrice": 0.0, "closingUnitPrice": 0.0,
        "purchaseQuantity": 0.0, "saleQuantity": 0.0,
        "custodyTransferInQuantity": 0.0, "custodyTransferOutQuantity": 0.0,
        "purchaseValue": 0.0, "saleValue": 0.0,
        "custodyTransferInAmount": 0.0, "custodyTransferOutAmount": 0.0,
        "unitInterest": 0.0, "totalInterest": 0.0,
        "creationDate": iso(TODAY),
        "percentage": None, "indexDsc": None, "rate": None, "strategy": "TradedFunds",
        "unitAmortisation": 0.0, "totalAmortisation": 0.0,
        "unitPremium": 0.0, "totalPremium": 0.0,
        "profitAndLoss": round(closing_value * 0.01, 2), "yield": 0.0,
        "grossUpProfitAndLoss": 0.0, "grossUpYield": 0.0,
        "cumulativeYield": 0.0, "grossUpCumulativeYield": 0.0,
        "originalDate": None, "originalQuantity": 0.0, "originalUnitPrice": 0.0,
        "incomeTaxRate": 0.0, "incomeTax": 0.0, "iof": 0.0, "iofRate": 0.0,
        "closingNetValue": closing_value,
    }


def checking_item(client_id, advisor_code, closing_value):
    return {
        "clientId": client_id, "advisorCode": advisor_code,
        "effectiveDate": iso(TODAY),
        "openingValue": closing_value, "closingValue": closing_value,
    }


def build_v2_positions() -> dict[int, dict]:
    positions: dict[int, dict] = {}

    # 1001 - concentracao credito privado PREFIXADO (~70% do AUM em uma debenture)
    p = empty_v2_position()
    p["fixedIncome"].append(fixed_income_item(
        1001, "AX0001", "DEBENTURE XYZ PREFIXADA 14%", "XYZ ENERGIA",
        490_000, rate=14.0, market_type="DEBENTURE"))
    p["fixedIncome"].append(fixed_income_item(
        1001, "AX0001", "TESOURO SELIC 2029", "TESOURO NACIONAL",
        190_000, rate=0.0, index_dsc="SELIC", market_type="LFT"))
    p["checkingAccount"].append(checking_item(1001, "AX0001", 20_000))
    positions[1001] = p

    # 1002 - concentracao credito privado POS-FIXADO (~75% do AUM em um CDB %CDI)
    p = empty_v2_position()
    p["fixedIncome"].append(fixed_income_item(
        1002, "AX0001", "CDB BANCO ABC 118% CDI", "BANCO ABC",
        487_500, rate=118.0, index_dsc="CDI"))
    p["fixedIncome"].append(fixed_income_item(
        1002, "AX0001", "TESOURO SELIC 2029", "TESOURO NACIONAL",
        147_500, rate=0.0, index_dsc="SELIC", market_type="LFT"))
    p["checkingAccount"].append(checking_item(1002, "AX0001", 15_000))
    positions[1002] = p

    # 1003 - concentracao em acoes (~65% do AUM em uma unica acao)
    p = empty_v2_position()
    p["stock"].append(stock_item(1003, "AX0001", "PETR4", "BRPETRACNOR9", 520_000, 8000))
    p["fixedIncome"].append(fixed_income_item(
        1003, "AX0001", "TESOURO SELIC 2029", "TESOURO NACIONAL",
        255_000, rate=0.0, index_dsc="SELIC", market_type="LFT"))
    p["checkingAccount"].append(checking_item(1003, "AX0001", 25_000))
    positions[1003] = p

    # 1004 - caixa ociosa alta (~55% do AUM em conta corrente/disponivel)
    p = empty_v2_position()
    p["fixedIncome"].append(fixed_income_item(
        1004, "AX0002", "TESOURO SELIC 2029", "TESOURO NACIONAL",
        225_000, rate=0.0, index_dsc="SELIC", market_type="LFT"))
    p["checkingAccount"].append(checking_item(1004, "AX0002", 275_000))
    positions[1004] = p

    # 1005 - vencimento proximo (CDB vence em 10 dias)
    p = empty_v2_position()
    p["fixedIncome"].append(fixed_income_item(
        1005, "AX0002", "CDB BANCO ABC 118% CDI", "BANCO ABC", 160_000,
        due_date=TODAY + timedelta(days=10), rate=118.0, index_dsc="CDI"))
    p["fixedIncome"].append(fixed_income_item(
        1005, "AX0002", "TESOURO SELIC 2029", "TESOURO NACIONAL",
        210_000, rate=0.0, index_dsc="SELIC", market_type="LFT"))
    p["checkingAccount"].append(checking_item(1005, "AX0002", 30_000))
    positions[1005] = p

    # 1006 - "amortizacao proxima": LIMITACAO CONHECIDA.
    # A API nao expoe uma data futura de amortizacao programada (so unitAmortisation/
    # totalAmortisation, que sao valores JA ocorridos). Mock representa o ativo com
    # dueDate de longo prazo para deixar claro que a deteccao de amortizacao futura
    # nao pode vir somente deste endpoint - precisa de fonte complementar.
    p = empty_v2_position()
    p["fixedIncome"].append(fixed_income_item(
        1006, "AX0002", "DEBENTURE XYZ PREFIXADA 14%", "XYZ ENERGIA", 200_000,
        due_date=TODAY + timedelta(days=400), rate=14.0, market_type="DEBENTURE"))
    p["fixedIncome"].append(fixed_income_item(
        1006, "AX0002", "TESOURO SELIC 2029", "TESOURO NACIONAL",
        230_000, rate=0.0, index_dsc="SELIC", market_type="LFT"))
    p["checkingAccount"].append(checking_item(1006, "AX0002", 20_000))
    positions[1006] = p

    # 1007 - migrou de renda fixa para acoes (saleValue em RF + purchaseValue em acao)
    p = empty_v2_position()
    p["fixedIncome"].append(fixed_income_item(
        1007, "AX0003", "CDB BANCO ABC 118% CDI", "BANCO ABC", 0.0,
        rate=118.0, index_dsc="CDI", sale_value=350_000))
    p["stock"].append(stock_item(1007, "AX0003", "VALE3", "BRVALEACNOR0", 350_000, 5000,
                                  purchase_value=350_000))
    p["fixedIncome"].append(fixed_income_item(
        1007, "AX0003", "TESOURO SELIC 2029", "TESOURO NACIONAL",
        210_000, rate=0.0, index_dsc="SELIC", market_type="LFT"))
    p["checkingAccount"].append(checking_item(1007, "AX0003", 40_000))
    positions[1007] = p

    # 1008 - resgate relevante (saleValue alto no periodo, sem recompra)
    p = empty_v2_position()
    p["fixedIncome"].append(fixed_income_item(
        1008, "AX0003", "TESOURO SELIC 2029", "TESOURO NACIONAL", 320_000,
        rate=0.0, index_dsc="SELIC", market_type="LFT", sale_value=230_000))
    p["checkingAccount"].append(checking_item(1008, "AX0003", 30_000))
    positions[1008] = p

    # 1009 - sem contato: posicao comum, nada de especial na XP (dado vem de fora)
    p = empty_v2_position()
    p["fixedIncome"].append(fixed_income_item(
        1009, "AX0003", "CDB BANCO ABC 118% CDI", "BANCO ABC",
        260_000, rate=118.0, index_dsc="CDI"))
    p["checkingAccount"].append(checking_item(1009, "AX0003", 40_000))
    positions[1009] = p

    # 1010 - controle: bem diversificado, nada dispara
    p = empty_v2_position()
    p["fixedIncome"].append(fixed_income_item(
        1010, "AX0001", "CDB BANCO ABC 118% CDI", "BANCO ABC",
        200_000, rate=118.0, index_dsc="CDI"))
    p["fixedIncome"].append(fixed_income_item(
        1010, "AX0001", "TESOURO SELIC 2029", "TESOURO NACIONAL",
        150_000, rate=0.0, index_dsc="SELIC", market_type="LFT"))
    p["stock"].append(stock_item(1010, "AX0001", "PETR4", "BRPETRACNOR9", 90_000, 1000))
    p["tradedFunds"].append(traded_fund_item(1010, "AX0001", "XPFI11", "BRXPFICTF000", 50_000, 6200))
    p["checkingAccount"].append(checking_item(1010, "AX0001", 60_000))
    positions[1010] = p

    return positions


# ---------------------------------------------------------------------------
# 4) /api/v1/investment-account/balance/customer/{code}
# ---------------------------------------------------------------------------
def build_investment_balances() -> dict[int, dict]:
    balances = {}
    for c in CLIENTS:
        cash = {
            1001: 20_000, 1002: 15_000, 1003: 25_000, 1004: 275_000, 1005: 30_000,
            1006: 20_000, 1007: 40_000, 1008: 30_000, 1009: 40_000, 1010: 60_000,
        }[c["code"]]
        balances[c["code"]] = {
            "account": {"brand": "XP", "tradingAccount": c["code"], "whiteLabel": "XP"},
            "amount": cash,
            "lastUpdate": iso(TODAY),
        }
    return balances


# ---------------------------------------------------------------------------
# 5) /api/v1/digital-account/balance/customer/{code}
#    (conta digital e distinta da conta de investimento; valores modestos aqui)
# ---------------------------------------------------------------------------
def build_digital_balances() -> dict[int, dict]:
    balances = {}
    for c in CLIENTS:
        balances[c["code"]] = {
            "agency": 1,
            "tradingAccount": c["code"],
            "amount": 1_000.0,
            "blockedAmount": 0.0,
            "amountWithOverdraft": 1_000.0,
            "overdraft": {"limit": 500.0, "available": 500.0, "consumed": 0.0},
            "lastChangeDate": iso(TODAY),
        }
    return balances


# ---------------------------------------------------------------------------
# 6) /api/v1/positivador -- metricas pre-agregadas de ativacao/churn/receita
#    (mapeado mas nunca populado ate agora; ver adendo secao 6.1). Uma linha
#    por offset temporal, escalada pelo mesmo fator dos mocks de posicao.
# ---------------------------------------------------------------------------
def build_positivador_snapshots() -> dict[int, list[dict]]:
    snapshots: dict[int, list[dict]] = {}
    for c in CLIENTS:
        rows = []
        for offset in SNAPSHOT_OFFSETS_DAYS:
            factor = scale_factor(offset)
            reference_date = (TODAY + timedelta(days=offset)).date().isoformat()
            aum_at_offset = c["aum"] * factor
            rows.append({
                "accountCode": c["code"],
                "referenceDate": reference_date,
                "status": "ATIVO",
                "activatedInMonth": None,
                "churnedInMonth": None,
                "netCaptureInMonth": round(aum_at_offset * 0.01, 2),
                "financialApplications": round(aum_at_offset, 2),
                "revenueInMonth": round(aum_at_offset * 0.001, 2),
                "suitability": "MODERADO",
            })
        snapshots[c["code"]] = rows
    return snapshots


# ---------------------------------------------------------------------------
# 7) CRM (fonte externa, NAO faz parte da API da XP) -- ultimo contato
# ---------------------------------------------------------------------------
def build_crm_interactions() -> list[dict]:
    return [
        {
            "accountCode": c["code"],
            "last_contact_at": iso(TODAY - timedelta(days=90 if c["code"] == 1009 else 5)),
        }
        for c in CLIENTS
    ]


# ---------------------------------------------------------------------------
# Execucao
# ---------------------------------------------------------------------------
def main():
    write_json(MOCKS_DIR / "account.json", build_accounts())
    write_json(MOCKS_DIR / "account_advisor_relation.json", build_account_advisor_relation())

    v2_positions = build_v2_positions()
    for code, payload in v2_positions.items():
        # nome sem sufixo mantido para compat com sync_xp_mock.py (fluxo "hoje")
        write_json(MOCKS_DIR / f"v2_positions_{code}.json", payload)
        for offset in SNAPSHOT_OFFSETS_DAYS:
            snapshot = build_scenario_snapshot(payload, offset)
            write_json(MOCKS_DIR / f"v2_positions_{code}_{offset}.json", snapshot)

    investment_balances = build_investment_balances()
    for code, payload in investment_balances.items():
        write_json(MOCKS_DIR / f"investment_account_balance_{code}.json", payload)

    digital_balances = build_digital_balances()
    for code, payload in digital_balances.items():
        write_json(MOCKS_DIR / f"digital_account_balance_{code}.json", payload)

    positivador_snapshots = build_positivador_snapshots()
    for code, rows in positivador_snapshots.items():
        write_json(MOCKS_DIR / f"positivador_{code}.json", rows)

    write_json(CRM_DIR / "interactions_mock.json", build_crm_interactions())

    print(f"Mocks gerados em: {MOCKS_DIR}")
    print(f"Mocks de CRM gerados em: {CRM_DIR}")
    print(f"Total de clientes-cenario: {len(CLIENTS)}")
    for c in CLIENTS:
        print(f"  - {c['code']}: {c['label']}")


if __name__ == "__main__":
    main()