from fastapi import FastAPI
from app.routers import clients, alerts

app = FastAPI(title="Advisor Intelligence API")
app.include_router(clients.router, prefix="/clients", tags=["clients"])
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])

@app.get("/health")
def health():
    return {"status": "ok"}