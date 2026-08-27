"""
Popula os campos novos de cadastro do ativo (manager_name, payment_frequency,
liquidity_days, minimum_investment, risk_rating) nos Asset ja existentes no
banco -- SEM tocar positions/snapshots/historico. So' le o payload "de hoje"
(v2_positions_{code}.json, offset 0) de cada cliente, casa por xp_asset_id
com o Asset ja sincronizado e atualiza so' esses 5 campos.

Rodar (dentro de backend/, com o venv ativado), depois de
`python generate_xp_mocks.py`:
    python backfill_asset_details.py
"""
from app.database import SessionLocal
from app.models import Asset
from app.integrations.xp.mock_client import XPMockClient
from sync_xp_mock import ASSET_CLASS_KEYS

client = XPMockClient()


def main():
    db = SessionLocal()
    try:
        accounts = client.get_accounts()
        updated = 0
        missing = 0

        for account_data in accounts:
            code = account_data["accountCode"]
            positions_payload = client.get_positions_v2(code)

            for asset_class in ASSET_CLASS_KEYS:
                if asset_class == "checkingAccount":
                    continue  # caixa nao e' um Asset individual com esses detalhes
                for item in positions_payload.get(asset_class, []):
                    xp_asset_id = item.get("assetId")
                    if not xp_asset_id:
                        continue
                    asset = db.query(Asset).filter(Asset.xp_asset_id == xp_asset_id).first()
                    if asset is None:
                        missing += 1
                        continue

                    asset.manager_name = item.get("fundManager")
                    asset.payment_frequency = item.get("paymentFrequency")
                    asset.liquidity_days = item.get("liquidityDays")
                    asset.minimum_investment = item.get("minimumInvestment")
                    asset.risk_rating = item.get("riskRating")
                    updated += 1

            db.commit()

        print(f"{updated} ativo(s) atualizados com detalhes de cadastro.")
        if missing:
            print(f"{missing} referencia(s) de ativo no mock sem Asset correspondente no banco "
                  f"(rode sync_xp_mock.py primeiro se for o caso).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
