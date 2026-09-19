from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import audio, audit, calibration, dashboard, evaluations, health, leads, reviews, rules
from .config import settings

app = FastAPI(title="VerityGate API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(leads.router)
app.include_router(evaluations.router)
app.include_router(rules.router)
app.include_router(reviews.router)
app.include_router(calibration.router)
app.include_router(dashboard.router)
app.include_router(audit.router)
app.include_router(audio.router)


@app.get("/")
def root():
    return {"service": "cimet-ai-qa-gate-api", "docs": "/docs"}
