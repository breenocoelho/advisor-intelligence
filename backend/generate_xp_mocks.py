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
import random
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


# namespace fixo so' pra gerar assetId deterministico -- ver stable_asset_id()
ASSET_ID_NAMESPACE = uuid.UUID("6e6f0a4e-1f0a-4c1a-9c2a-8f6a2b9d3c11")


def stable_asset_id(key: str) -> str:
    """assetId deterministico a partir de uma chave que identifica o
    instrumento (nao o cliente). Sem isso, cada cliente que tem 'o mesmo'
    Tesouro Selic ou a mesma acao vira uma linha de Asset diferente no
    banco (assetId = uuid4() aleatorio a cada chamada), e a tela de Ativos
    nunca consegue agregar exposicao entre clientes. A chave inclui os
    termos do instrumento (nao so o nome) para que duas posicoes com o
    mesmo nome mas vencimento/taxa diferentes (ex: o CDB do cenario 1005,
    que tem vencimento proximo de proposito) continuem sendo tratadas como
    instrumentos distintos."""
    return str(uuid.uuid5(ASSET_ID_NAMESPACE, key))


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

ADVISOR_CODES = {
    "AX0001": 500001, "AX0002": 500002, "AX0003": 500003, "AX0004": 500004, "AX0005": 500005,
}


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
            "birthYear": 1960 + (i * 7) % 45,
            "birthMonth": (i % 12) + 1,
            "registerDate": "2023-01-01T00:00:00",
            "personType": c.get("person_type", "F"),
            "maritalStatus": "CASADO(A)" if i % 2 == 0 else "SOLTEIRO(A)",
            "activity": "PROFISSIONAL_EXEMPLO",
            "dscSuitability": c.get("suitability", "MODERADO"),
            "realStateValue": 0.0,
            "movableAssetsValue": 0.0,
            "incomeValue": c.get("income_value", 15000.0),
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


# gestora de FII, por ticker -- FIIs sao os unicos instrumentos "diretos"
# (nao-fundo) que realmente tem uma gestora conhecida na pratica
FII_MANAGERS = {
    "XPFI11": "XP Asset Management", "HGLG11": "CSHG", "KNRI11": "Kinea Investimentos",
    "MXRF11": "XP Asset Management", "VISC11": "Vinci Partners",
}


def _instrument_metadata(market_type: str) -> dict:
    """Detalhes de cadastro adicionais (gestora/frequencia de pagamento/
    liquidez/aplicacao minima/classificacao de risco) -- inferidos a
    partir do tipo de instrumento, nao aleatorios, pra ficar consistente
    com o que a XP realmente informaria. So' toca a tabela assets (nao
    positions/snapshots) quando aplicado via backfill_asset_details.py."""
    table = {
        "CDB": dict(payment_frequency="No vencimento", liquidity_days=0, risk_rating="Baixo", minimum_investment=1000.0),
        "LCI": dict(payment_frequency="No vencimento", liquidity_days=90, risk_rating="Baixo", minimum_investment=5000.0),
        "LCA": dict(payment_frequency="No vencimento", liquidity_days=90, risk_rating="Baixo", minimum_investment=5000.0),
        "DEBENTURE": dict(payment_frequency="Semestral", liquidity_days=0, risk_rating="Médio", minimum_investment=1000.0),
        "LFT": dict(payment_frequency="No vencimento", liquidity_days=1, risk_rating="Baixo", minimum_investment=100.0, manager_name="Tesouro Nacional"),
        "NTN-B": dict(payment_frequency="Semestral", liquidity_days=1, risk_rating="Baixo", minimum_investment=100.0, manager_name="Tesouro Nacional"),
        "LTN": dict(payment_frequency="No vencimento", liquidity_days=1, risk_rating="Baixo", minimum_investment=100.0, manager_name="Tesouro Nacional"),
        "AÇÃO": dict(payment_frequency="Variável (dividendos)", liquidity_days=2, risk_rating="Alto", minimum_investment=0.0),
        "FII": dict(payment_frequency="Mensal", liquidity_days=2, risk_rating="Médio", minimum_investment=0.0),
        "FUNDO": dict(payment_frequency="No resgate", liquidity_days=30, risk_rating="Médio", minimum_investment=500.0),
        "PREVIDENCIA": dict(payment_frequency="No resgate", liquidity_days=60, risk_rating="Médio", minimum_investment=100.0),
        "COE": dict(payment_frequency="No vencimento", liquidity_days=0, risk_rating="Alto", minimum_investment=10000.0),
        "COMPROMISSADA": dict(payment_frequency="No vencimento", liquidity_days=1, risk_rating="Baixo", minimum_investment=5000.0),
    }
    return table.get(market_type, {})


def fixed_income_item(client_id, advisor_code, asset, issuer, closing_value,
                       due_date=None, rate=0.0, index_dsc="", purchase_value=0.0,
                       sale_value=0.0, market_type="CDB"):
    asset_key = f"FI|{asset}|{issuer}|{iso(due_date)}|{rate}|{index_dsc}"
    meta = _instrument_metadata(market_type)
    return {
        "clientId": client_id, "advisorCode": advisor_code,
        "assetId": stable_asset_id(asset_key), "asset": asset, "marketType": market_type,
        "dueDate": iso(due_date), "cetipSelicCode": f"{asset[:10].upper().replace(' ', '')}",
        "issuer": issuer, "marketPrice": None,
        "fundManager": meta.get("manager_name"),
        "paymentFrequency": meta.get("payment_frequency"),
        "liquidityDays": meta.get("liquidity_days"),
        "minimumInvestment": meta.get("minimum_investment"),
        "riskRating": meta.get("risk_rating"),
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
    meta = _instrument_metadata("AÇÃO")
    return {
        "clientId": client_id, "advisorCode": advisor_code,
        "assetId": stable_asset_id(f"ST|{isin}"), "asset": asset, "isin": isin, "marketType": "AÇÃO",
        "fundManager": meta.get("manager_name"),
        "paymentFrequency": meta.get("payment_frequency"),
        "liquidityDays": meta.get("liquidity_days"),
        "minimumInvestment": meta.get("minimum_investment"),
        "riskRating": meta.get("risk_rating"),
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
    meta = _instrument_metadata("FII")
    return {
        "clientId": client_id, "advisorCode": advisor_code,
        "assetId": stable_asset_id(f"TF|{isin}"), "asset": asset, "isin": isin, "marketType": "FII",
        "fundManager": FII_MANAGERS.get(asset, meta.get("manager_name")),
        "paymentFrequency": meta.get("payment_frequency"),
        "liquidityDays": meta.get("liquidity_days"),
        "minimumInvestment": meta.get("minimum_investment"),
        "riskRating": meta.get("risk_rating"),
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


def fund_like_item(client_id, advisor_code, asset, issuer, cnpj, closing_value,
                    market_type, purchase_value=0.0, sale_value=0.0):
    """Cobre coe/funds/pensionFunds/repo -- produtos identificados por CNPJ
    (fundCNPJ), diferente de renda fixa (cetipSelicCode) e acoes/FIIs (isin).
    Usado pra diversificar a classe de ativo dos mocks alem de fixedIncome/
    stock/tradedFunds/checkingAccount, que era tudo que existia antes."""
    asset_key = f"FUND|{asset}|{cnpj}"
    meta = _instrument_metadata(market_type)
    return {
        "clientId": client_id, "advisorCode": advisor_code,
        "assetId": stable_asset_id(asset_key), "asset": asset, "fundCNPJ": cnpj, "marketType": market_type,
        "issuer": issuer,
        "fundManager": issuer,  # pra fundos/previdencia/coe/repo, a gestora E' o "issuer" do mock
        "paymentFrequency": meta.get("payment_frequency"),
        "liquidityDays": meta.get("liquidity_days"),
        "minimumInvestment": meta.get("minimum_investment"),
        "riskRating": meta.get("risk_rating"),
        "invoiceId": 0, "effectiveDate": iso(TODAY),
        "purchaseDate": iso(TODAY - timedelta(days=220)),
        "openingValue": round(closing_value * 0.99, 2), "closingValue": closing_value,
        "delta": 0.0, "status": 4,
        "openingQuantity": 0.0, "closingQuantity": 0.0,
        "blockingQuantity": 0.0, "collateralQuantity": 0.0, "lawBlockingQuantity": 0.0,
        "openingUnitPrice": 0.0, "closingUnitPrice": 0.0,
        "purchaseQuantity": 0.0, "saleQuantity": 0.0,
        "custodyTransferInQuantity": 0.0, "custodyTransferOutQuantity": 0.0,
        "purchaseValue": purchase_value, "saleValue": sale_value,
        "custodyTransferInAmount": 0.0, "custodyTransferOutAmount": 0.0,
        "unitInterest": 0.0, "totalInterest": 0.0,
        "creationDate": iso(TODAY),
        "percentage": None, "indexDsc": None, "rate": None, "strategy": "Fund",
        "unitAmortisation": 0.0, "totalAmortisation": 0.0,
        "unitPremium": 0.0, "totalPremium": 0.0,
        "profitAndLoss": round(closing_value * 0.015, 2), "yield": 0.0,
        "grossUpProfitAndLoss": 0.0, "grossUpYield": 0.0,
        "cumulativeYield": 0.0, "grossUpCumulativeYield": 0.0,
        "originalDate": None, "originalQuantity": 0.0, "originalUnitPrice": 0.0,
        "incomeTaxRate": 0.15, "incomeTax": 0.0, "iof": 0.0, "iofRate": 0.0,
        "closingNetValue": closing_value,
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

    # clientes gerados (1011+) -- mix de perfis, ver GENERATED_PROFILES
    for c in CLIENTS:
        if c["code"] in positions:
            continue
        rng = random.Random(c["code"])
        positions[c["code"]] = build_random_position(rng, c["code"], c["advisor"], c["aum"], c["profile"])

    return positions


# ---------------------------------------------------------------------------
# 3b) Clientes gerados (parametrico, seed reprodutivel) -- estressar o
# sistema com mais volume, mais tipos de ativo e mais cenarios de gatilho
# do que os 10 clientes-cenario hand-crafted acima permitem sozinhos.
# ---------------------------------------------------------------------------
STOCKS = [
    ("PETR4", "BRPETRACNOR9"), ("VALE3", "BRVALEACNOR0"), ("ITUB4", "BRITUBACNOR2"),
    ("BBDC4", "BRBBDCACNOR3"), ("WEGE3", "BRWEGEACNOR0"), ("ABEV3", "BRABEVACNOR1"),
    ("MGLU3", "BRMGLUACNOR8"), ("RENT3", "BRRENTACNOR5"), ("B3SA3", "BRB3SAACNOR6"),
    ("ELET3", "BRELETACNOR4"), ("SUZB3", "BRSUZBACNOR7"), ("GGBR4", "BRGGBRACNOR9"),
]

FIIS = [
    ("XPFI11", "BRXPFICTF001"), ("HGLG11", "BRHGLGCTF002"), ("KNRI11", "BRKNRICTF003"),
    ("MXRF11", "BRMXRFCTF004"), ("VISC11", "BRVISCCTF005"),
]

# (nome, emissor, marketType, taxa, indexador)
FI_INSTRUMENTS = [
    ("CDB Banco ABC 118% CDI", "BANCO ABC", "CDB", 118.0, "CDI"),
    ("CDB Banco Safra 112% CDI", "BANCO SAFRA", "CDB", 112.0, "CDI"),
    ("LCI Banco BTG 96% CDI", "BANCO BTG", "LCI", 96.0, "CDI"),
    ("LCA Banco XYZ 94% CDI", "BANCO XYZ", "LCA", 94.0, "CDI"),
    ("Debenture Energisa IPCA+6%", "ENERGISA", "DEBENTURE", 6.0, "IPCA"),
    ("Debenture Vale IPCA+5,5%", "VALE", "DEBENTURE", 5.5, "IPCA"),
]

# (nome, emissor, marketType, taxa, indexador)
TREASURY_INSTRUMENTS = [
    ("Tesouro Selic 2029", "TESOURO NACIONAL", "LFT", 0.0, "SELIC"),
    ("Tesouro IPCA+ 2035", "TESOURO NACIONAL", "NTN-B", 5.5, "IPCA"),
    ("Tesouro Prefixado 2027", "TESOURO NACIONAL", "LTN", 11.5, ""),
]

FUND_PRODUCTS = [
    ("Fundo Multimercado Alfa", "Gestora Alfa", "11.222.333/0001-44"),
    ("Fundo Renda Fixa Beta", "Gestora Beta", "22.333.444/0001-55"),
    ("Fundo Acoes Gama", "Gestora Gama", "33.444.555/0001-66"),
]

PENSION_PRODUCTS = [
    ("PGBL XP Previdencia", "XP Previdencia", "44.555.666/0001-77"),
    ("VGBL Itau Previdencia", "Itau Previdencia", "55.666.777/0001-88"),
]

COE_PRODUCTS = [
    ("COE Protecao Ibovespa", "Banco Emissor X", "COE-10001"),
    ("COE Renda Fixa Global", "Banco Emissor Y", "COE-10002"),
]

REPO_PRODUCTS = [
    ("Compromissada LFT", "Banco Custodiante", "REPO-20001"),
]

CLASS_POOL = ["fixedIncome", "stock", "tradedFunds", "funds", "pensionFunds", "coe", "repo", "treasury"]

# perfis de gatilho pros 40 clientes gerados -- garante cobertura de cada
# regra do alert_engine e do signal de concentracao por emissor, alem de
# um bloco de controle "ruido realista" (diversified_mixed)
GENERATED_PROFILES = (
    ["concentrated_position"] * 6
    + ["concentrated_issuer"] * 4
    + ["idle_cash"] * 5
    + ["maturity_soon"] * 5
    + ["big_redemption"] * 4
    + ["reallocation"] * 4
    + ["diversified_mixed"] * 12
)


def _add_instrument(rng: random.Random, p: dict, code: int, advisor: str, cls: str, value: float):
    if value < 500:
        return
    if cls == "fixedIncome":
        name, issuer, mtype, rate, idx = rng.choice(FI_INSTRUMENTS)
        p["fixedIncome"].append(fixed_income_item(code, advisor, name, issuer, value, rate=rate, index_dsc=idx, market_type=mtype))
    elif cls == "treasury":
        name, issuer, mtype, rate, idx = rng.choice(TREASURY_INSTRUMENTS)
        p["treasury"].append(fixed_income_item(code, advisor, name, issuer, value, rate=rate, index_dsc=idx, market_type=mtype))
    elif cls == "stock":
        ticker, isin = rng.choice(STOCKS)
        qty = max(1, int(value / rng.uniform(20, 80)))
        p["stock"].append(stock_item(code, advisor, ticker, isin, value, qty))
    elif cls == "tradedFunds":
        ticker, isin = rng.choice(FIIS)
        qty = max(1, int(value / rng.uniform(80, 130)))
        p["tradedFunds"].append(traded_fund_item(code, advisor, ticker, isin, value, qty))
    elif cls == "funds":
        name, issuer, cnpj = rng.choice(FUND_PRODUCTS)
        p["funds"].append(fund_like_item(code, advisor, name, issuer, cnpj, value, "FUNDO"))
    elif cls == "pensionFunds":
        name, issuer, cnpj = rng.choice(PENSION_PRODUCTS)
        p["pensionFunds"].append(fund_like_item(code, advisor, name, issuer, cnpj, value, "PREVIDENCIA"))
    elif cls == "coe":
        name, issuer, cnpj = rng.choice(COE_PRODUCTS)
        p["coe"].append(fund_like_item(code, advisor, name, issuer, cnpj, value, "COE"))
    elif cls == "repo":
        name, issuer, cnpj = rng.choice(REPO_PRODUCTS)
        p["repo"].append(fund_like_item(code, advisor, name, issuer, cnpj, value, "COMPROMISSADA"))


def _fill_diversified(rng: random.Random, p: dict, code: int, advisor: str, remaining_aum: float, classes: int):
    if remaining_aum <= 0:
        return
    chosen = rng.sample(CLASS_POOL, k=min(classes, len(CLASS_POOL)))
    weights = [rng.uniform(0.5, 1.5) for _ in chosen]
    total_w = sum(weights)
    for cls, w in zip(chosen, weights):
        _add_instrument(rng, p, code, advisor, cls, round(remaining_aum * (w / total_w), 2))


def build_random_position(rng: random.Random, code: int, advisor: str, aum: float, profile: str) -> dict:
    p = empty_v2_position()
    remaining = aum

    def take(pct: float) -> float:
        nonlocal remaining
        amt = min(round(aum * pct, 2), remaining)
        remaining -= amt
        return amt

    cash_pct = rng.uniform(0.28, 0.55) if profile == "idle_cash" else rng.uniform(0.03, 0.15)
    cash_value = take(cash_pct)

    if profile == "concentrated_position":
        big_value = take(rng.uniform(0.46, 0.65))
        if rng.random() < 0.5:
            name, issuer, mtype, rate, idx = rng.choice(FI_INSTRUMENTS)
            p["fixedIncome"].append(fixed_income_item(code, advisor, name, issuer, big_value, rate=rate, index_dsc=idx, market_type=mtype))
        else:
            ticker, isin = rng.choice(STOCKS)
            qty = max(1, int(big_value / rng.uniform(20, 80)))
            p["stock"].append(stock_item(code, advisor, ticker, isin, big_value, qty))
        _fill_diversified(rng, p, code, advisor, remaining, classes=2)

    elif profile == "concentrated_issuer":
        name, issuer, mtype, rate, idx = rng.choice(FI_INSTRUMENTS)
        v1 = take(rng.uniform(0.22, 0.28))
        v2 = take(rng.uniform(0.20, 0.26))
        p["fixedIncome"].append(fixed_income_item(code, advisor, name, issuer, v1, rate=rate, index_dsc=idx, market_type=mtype))
        p["fixedIncome"].append(fixed_income_item(
            code, advisor, name + " II", issuer, v2, rate=rate + 1,
            index_dsc=idx, market_type=mtype, due_date=TODAY + timedelta(days=730),
        ))
        _fill_diversified(rng, p, code, advisor, remaining, classes=2)

    elif profile == "maturity_soon":
        name, issuer, mtype, rate, idx = rng.choice(FI_INSTRUMENTS)
        due = TODAY + timedelta(days=rng.randint(5, 28))
        v = take(rng.uniform(0.15, 0.30))
        p["fixedIncome"].append(fixed_income_item(code, advisor, name, issuer, v, due_date=due, rate=rate, index_dsc=idx, market_type=mtype))
        _fill_diversified(rng, p, code, advisor, remaining, classes=3)

    elif profile == "big_redemption":
        name, issuer, mtype, rate, idx = rng.choice(FI_INSTRUMENTS)
        sale_amt = round(aum * rng.uniform(0.25, 0.45), 2)
        v = take(rng.uniform(0.10, 0.20))
        p["fixedIncome"].append(fixed_income_item(code, advisor, name, issuer, v, rate=rate, index_dsc=idx, market_type=mtype, sale_value=sale_amt))
        _fill_diversified(rng, p, code, advisor, remaining, classes=3)

    elif profile == "reallocation":
        name, issuer, mtype, rate, idx = rng.choice(FI_INSTRUMENTS)
        move_amt = round(aum * rng.uniform(0.25, 0.40), 2)
        p["fixedIncome"].append(fixed_income_item(code, advisor, name, issuer, 0.0, rate=rate, index_dsc=idx, market_type=mtype, sale_value=move_amt))
        ticker, isin = rng.choice(STOCKS)
        qty = max(1, int(move_amt / rng.uniform(20, 80)))
        p["stock"].append(stock_item(code, advisor, ticker, isin, move_amt, qty, purchase_value=move_amt))
        _fill_diversified(rng, p, code, advisor, remaining, classes=3)

    else:  # diversified_mixed -- ruido realista, sem gatilho forcado
        _fill_diversified(rng, p, code, advisor, remaining, classes=rng.randint(4, 7))

    p["checkingAccount"].append(checking_item(code, advisor, cash_value))
    return p


def generate_random_clients(count: int = 40, start_code: int = 1011) -> list[dict]:
    assert len(GENERATED_PROFILES) == count

    advisor_pool = ["AX0001", "AX0002", "AX0003", "AX0004", "AX0005"]
    advisor_weights = [3, 2, 4, 3, 2]  # distribuicao desigual de proposito, nao 10/10/10

    clients = []
    for i in range(count):
        code = start_code + i
        rng = random.Random(code)  # seed = codigo -- reprodutivel entre execucoes
        profile = GENERATED_PROFILES[i]
        advisor = rng.choices(advisor_pool, weights=advisor_weights, k=1)[0]
        aum = round(rng.uniform(120_000, 3_800_000), -3)
        suitability = rng.choices(["CONSERVADOR", "MODERADO", "ARROJADO"], weights=[3, 5, 2], k=1)[0]
        person_type = "J" if rng.random() < 0.12 else "F"
        income_value = round(aum * rng.uniform(0.01, 0.03), -2)
        contact_bucket = rng.choices(["stale", "borderline", "recent"], weights=[2, 3, 5], k=1)[0]
        contact_days_ago = {
            "stale": rng.randint(95, 160),
            "borderline": rng.randint(35, 75),
            "recent": rng.randint(1, 20),
        }[contact_bucket]

        clients.append({
            "code": code,
            "label": f"Gerado - {profile}",
            "aum": aum,
            "advisor": advisor,
            "suitability": suitability,
            "person_type": person_type,
            "income_value": income_value,
            "profile": profile,
            "contact_days_ago": contact_days_ago,
        })
    return clients


CLIENTS = CLIENTS + generate_random_clients()


# ---------------------------------------------------------------------------
# 4) /api/v1/investment-account/balance/customer/{code}
# ---------------------------------------------------------------------------
def build_investment_balances(v2_positions: dict[int, dict]) -> dict[int, dict]:
    balances = {}
    for c in CLIENTS:
        cash = sum(item["closingValue"] for item in v2_positions[c["code"]]["checkingAccount"])
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
                "suitability": c.get("suitability", "MODERADO"),
            })
        snapshots[c["code"]] = rows
    return snapshots


# ---------------------------------------------------------------------------
# 7) CRM (fonte externa, NAO faz parte da API da XP) -- ultimo contato
# ---------------------------------------------------------------------------
def build_crm_interactions() -> list[dict]:
    result = []
    for c in CLIENTS:
        if "contact_days_ago" in c:
            days_ago = c["contact_days_ago"]
        else:
            days_ago = 90 if c["code"] == 1009 else 5
        result.append({"accountCode": c["code"], "last_contact_at": iso(TODAY - timedelta(days=days_ago))})
    return result


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

    investment_balances = build_investment_balances(v2_positions)
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
    print(f"Total de clientes: {len(CLIENTS)}")
    print("Cenarios hand-crafted (1001-1010):")
    for c in CLIENTS[:10]:
        print(f"  - {c['code']}: {c['label']}")
    profile_counts: dict[str, int] = {}
    for c in CLIENTS[10:]:
        profile_counts[c["profile"]] = profile_counts.get(c["profile"], 0) + 1
    print(f"Clientes gerados (1011-{CLIENTS[-1]['code']}), por perfil:")
    for profile, count in profile_counts.items():
        print(f"  - {profile}: {count}")
    advisor_counts: dict[str, int] = {}
    for c in CLIENTS:
        advisor_counts[c["advisor"]] = advisor_counts.get(c["advisor"], 0) + 1
    print(f"Distribuicao por assessor: {advisor_counts}")


if __name__ == "__main__":
    main()