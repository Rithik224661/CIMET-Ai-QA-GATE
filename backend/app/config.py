"""
Centralized configuration. Every tunable the CIMET brief left unspecified
lives here, not scattered through service code — see docs/DECISIONS.md at
the repo root for why each default was chosen. All of it is overridable via
environment variables / a .env file so the same code runs in DEMO_MODE
today and against a real CIMET sandbox later without redesigning anything.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- data / persistence ---
    database_url: str = "sqlite:///./cimet.db"
    data_mode: str = "demo"  # "demo" | "sandbox"

    # --- gate policy (mirrors frontend src/lib/config.ts) ---
    confidence_floor: float = 0.85
    clean_sample_rate: float = 0.05
    repeat_offence_threshold: int = 3
    repeat_offence_window_days: int = 7

    # --- check weights by type (from the one checklist export in hand) ---
    weight_verbatim: int = 8
    weight_factual: int = 10
    weight_behaviour: int = 3

    # --- evaluator tuning ---
    rate_tolerance_cents: float = 0.0
    verbatim_pass_threshold: float = 0.75
    verbatim_review_threshold: float = 0.35
    dead_air_threshold_seconds: float = 30.0

    # --- AI provider abstraction (see app/services/ai_provider.py) ---
    # "none": fully deterministic, no external calls, no credentials needed —
    # the default, and what every check in this build actually runs on.
    ai_provider: str = "none"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

    # --- server ---
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # --- demo clock: the synthetic leads are dated relative to this fixed
    # instant so "12m" / "2h" ages stay meaningful without a live database ---
    demo_now: str = "2026-09-18T15:52:00"


settings = Settings()
