"""
Helper compartilhado para ler 'positions' como estado atual mesmo depois
que a tabela passou a acumular historico (uma linha por data de sync).
Filtra, por conta, para a position_date mais recente daquela conta.
"""
from sqlalchemy import func

from app.models import Account, Position


def latest_positions_query(db, client_id):
    """Retorna uma query (Position, ) filtrada para a ultima position_date
    de cada conta do cliente. Encadeie .join(Asset, ...) / .with_entities(...)
    normalmente a partir do resultado."""
    latest_dates = (
        db.query(
            Position.account_id.label("account_id"),
            func.max(Position.position_date).label("max_date"),
        )
        .join(Account, Position.account_id == Account.id)
        .filter(Account.client_id == client_id)
        .group_by(Position.account_id)
        .subquery()
    )

    return (
        db.query(Position)
        .join(
            latest_dates,
            (Position.account_id == latest_dates.c.account_id)
            & (Position.position_date == latest_dates.c.max_date),
        )
    )
