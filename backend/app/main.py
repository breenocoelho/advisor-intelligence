from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import clients, alerts, tasks, insights

app = FastAPI(title="Advisor Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP: liberado geral; trocar pelo dominio exato da Vercel antes de produção real
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clients.router, prefix="/clients", tags=["clients"])
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(insights.router, prefix="/insights", tags=["insights"])


@app.get("/health")
def health():
    return {"status": "ok"}