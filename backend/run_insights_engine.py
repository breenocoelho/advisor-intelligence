"""
Roda o motor de insights contra os dados ja sincronizados no banco e
imprime um resumo por cliente.

Rodar (dentro de backend/, com o venv ativado):
    python run_insights_engine.py
"""
from app.database import SessionLocal
from app.models import Client, Insight
from app.services.insights_engine import run_insights_engine


def main():
    db = SessionLocal()
    try:
        total = run_insights_engine(db)
        print(f"Motor de insights rodou. {total} insight(s) novo(s) criado(s).\n")

        clients = db.query(Client).order_by(Client.xp_client_id).all()
        for client in clients:
            insights = (
                db.query(Insight)
                .filter(Insight.client_id == client.id, Insight.status.in_(["new", "viewed"]))
                .all()
            )
            if not insights:
                continue
            print(f"Cliente {client.xp_client_id} (AUM R$ {client.aum:,.2f})")
            for i in insights:
                print(f"    [{i.severity}] {i.insight_type}: {i.explanation}")
            print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
