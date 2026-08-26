from app.database import SessionLocal
from app.models import Client, Position, Asset
db = SessionLocal()
print('Clientes:', db.query(Client).count())
print('Posições:', db.query(Position).count())
print('Ativos distintos:', db.query(Asset).count())
db.close()