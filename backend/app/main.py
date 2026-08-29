from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import (
    clients, alerts, tasks, insights, threshold_rules, assets, advisors, interactions, benchmarks, config,
    opportunities, office,
)

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
app.include_router(threshold_rules.router, prefix="/threshold-rules", tags=["threshold-rules"])
app.include_router(assets.router, prefix="/assets", tags=["assets"])
app.include_router(advisors.router, prefix="/advisors", tags=["advisors"])
app.include_router(interactions.router, prefix="/clients", tags=["interactions"])
app.include_router(benchmarks.router, prefix="/benchmarks", tags=["benchmarks"])
app.include_router(config.router, prefix="/config", tags=["config"])
app.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
app.include_router(office.router, prefix="/office", tags=["office"])


@app.get("/health")
def health():
    return {"status": "ok"}