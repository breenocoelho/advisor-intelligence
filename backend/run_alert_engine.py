"""
Roda o motor de alertas contra os dados ja sincronizados no banco e
imprime um resumo por cliente, para conferir se os cenarios do mock
disparam exatamente o esperado.

Rodar (dentro de backend/, com o venv ativado):
    python run_alert_engine.py
"""
from app.database import SessionLocal
from app.models import Client, Alert
from app.services.alert_engine import run_alert_engine

EXPECTED = {
    "1001": ["concentration"],
    "1002": ["concentration"],
    "1003": ["concentration"],
    "1004": ["idle_cash"],
    "1005": ["upcoming_maturity"],
    "1006": [],  # amortizacao proxima -- limitacao conhecida, nenhum alerta esperado
    "1007": ["relevant_movement"],  # concentracao tambem pode aparecer (efeito colateral esperado)
    "1008": ["relevant_movement"],  # concentracao tambem pode aparecer (efeito colateral esperado)
    "1009": [],  # sem contato -- fora do escopo deste motor (fonte e' CRM)
    "1010": [],  # controle -- nada deve disparar
}


def main():
    db = SessionLocal()
    try:
        total = run_alert_engine(db)
        print(f"Motor de alertas rodou. {total} alerta(s) criado(s) no total.\n")

        clients = db.query(Client).order_by(Client.xp_client_id).all()
        for client in clients:
            alerts = db.query(Alert).filter(Alert.client_id == client.id, Alert.status == "new").all()
            types = sorted(a.alert_type for a in alerts)
            expected_types = sorted(EXPECTED.get(client.xp_client_id, []))

            status = "OK" if set(types) >= set(expected_types) else "DIVERGENTE"
            print(f"Cliente {client.xp_client_id} (AUM R$ {client.aum:,.2f}) — {status}")
            print(f"  esperado : {expected_types}")
            print(f"  obtido   : {types}")
            for a in alerts:
                print(f"    [{a.severity}] {a.alert_type}: {a.explanation}")
            print()
    finally:
        db.close()


if __name__ == "__main__":
    main()