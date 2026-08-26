import json
from pathlib import Path

MOCKS_DIR = Path(__file__).resolve().parents[3] / "mocks" / "xp"
CRM_MOCKS_DIR = Path(__file__).resolve().parents[3] / "mocks" / "crm"


class XPMockClient:
    """Client mockado do XP Data Access. Mesma assinatura que o client real
    (XPRealClient, a implementar quando o credenciamento/mTLS estiver liberado)
    vai ter — troca-se a implementação sem tocar no resto do sistema."""

    def _load(self, directory: Path, filename: str):
        with open(directory / filename, encoding="utf-8") as f:
            return json.load(f)

    def get_accounts(self) -> list[dict]:
        """/api/v1/account -- todos os clientes do parceiro, dimensao SCD tipo 2."""
        return self._load(MOCKS_DIR, "account.json")

    def get_account_advisor_relation(self) -> list[dict]:
        """/api/v1/account-advisor-relation -- vinculo cliente x assessor, versus tempo."""
        return self._load(MOCKS_DIR, "account_advisor_relation.json")

    def get_positions_v2(self, customer_code: int) -> dict:
        """/api/v2/positions/customers/{customerCode} -- posicoes por classe de ativo."""
        return self._load(MOCKS_DIR, f"v2_positions_{customer_code}.json")

    def get_positions_v2_as_of(self, customer_code: int, offset_days: int) -> dict:
        """Mesmo endpoint, versao com dimensao temporal (Phase 2) -- offset_days
        em {-90, -60, -30, 0} relativo ao TODAY fixo do gerador de mocks."""
        return self._load(MOCKS_DIR, f"v2_positions_{customer_code}_{offset_days}.json")

    def get_positivador(self, customer_code: int) -> list[dict]:
        """/api/v1/positivador -- metricas pre-agregadas de ativacao/churn/receita,
        uma linha por offset temporal (Phase 2)."""
        return self._load(MOCKS_DIR, f"positivador_{customer_code}.json")

    def get_investment_account_balance(self, customer_code: int) -> dict:
        """/api/v1/investment-account/balance/customer/{customerCode}."""
        return self._load(MOCKS_DIR, f"investment_account_balance_{customer_code}.json")

    def get_digital_account_balance(self, customer_code: int) -> dict:
        """/api/v1/digital-account/balance/customer/{customerCode}."""
        return self._load(MOCKS_DIR, f"digital_account_balance_{customer_code}.json")

    def get_crm_interactions(self) -> list[dict]:
        """NAO faz parte da API da XP. Mock de uma fonte de CRM futura,
        usado apenas para a regra de 'sem contato' enquanto essa fonte
        real nao entra no roadmap (V2)."""
        return self._load(CRM_MOCKS_DIR, "interactions_mock.json")