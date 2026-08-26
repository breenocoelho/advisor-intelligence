# backend/drop_all.py
from app.database import engine, Base
from app import models  # garante que todos os models estão registrados

Base.metadata.drop_all(bind=engine)
print("Tabelas removidas com sucesso.")