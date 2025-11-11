from fastapi import FastAPI
from .routers import analytics, agents, reports

app = FastAPI(title="Property Analytics Platform 2025", version="0.1.0")

@app.get("/health")
async def health():
    return {"ok": True}

# Routers (placeholders wired)
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])


