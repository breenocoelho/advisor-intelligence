"""
Preenche Client.last_contact_at a partir do mock de CRM
(mocks/crm/interactions_mock.json), simulando uma fonte de interacoes
ate a integracao real de CRM entrar no roadmap (V2). Depois de rodar
uma vez, o campo evolui via o botao "Registrar contato" na aplicacao.

Rodar (dentro de backend/, com o venv ativado):
    python backfill_contacts_from_crm_mock.py
"""
import json
from datetime import datetime
from pathlib import Path

from app.database import SessionLocal
from app.models import Client

CRM_MOCK_PATH = Path(__file__).parent / "mocks" / "crm" / "interactions_mock.json"


def main():
    with open(CRM_MOCK_PATH, encoding="utf-8") as f:
        interactions = json.load(f)

    db = SessionLocal()
    try:
        updated = 0
        for item in interactions:
            client = (
                db.query(Client)
                .filter(Client.xp_client_id == str(item["accountCode"]))
                .first()
            )
            if client is None:
                continue
            client.last_contact_at = datetime.fromisoformat(item["last_contact_at"])
            updated += 1
        db.commit()
        print(f"{updated} cliente(s) atualizados com last_contact_at.")
    finally:
        db.close()


if __name__ == "__main__":
    main()