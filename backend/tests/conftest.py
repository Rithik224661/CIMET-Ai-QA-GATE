from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401 — registers tables on Base.metadata
from app.db import Base, get_db
from app.main import app
from app.seed import _ingest_lead, _seed_human_review, _seed_retailers, _seed_rule_sets
from app.seed_data import LEADS, REPEAT_OFFENCE_HISTORY
from app.services.pipeline import run_evaluation


@pytest.fixture()
def db_session():
    """A fresh, isolated in-memory sqlite database per test."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def seeded_db(db_session: Session) -> Session:
    """The 9 named scenarios + repeat-offence history, run through the real
    pipeline — no bulk synthetic backfill, so tests stay fast and
    deterministic."""
    retailers = _seed_retailers(db_session)
    _, live_v14 = _seed_rule_sets(db_session, retailers)

    for seed_row in [*REPEAT_OFFENCE_HISTORY, *LEADS]:
        checklist_version = live_v14 if seed_row.state != "error" else None
        lead = _ingest_lead(db_session, seed_row, retailers, checklist_version)
        if seed_row.state == "scored":
            run_evaluation(db_session, lead)
        if seed_row.pre_seeded_override:
            o = seed_row.pre_seeded_override
            _seed_human_review(
                db_session,
                lead,
                human_decision=o["human_decision"],
                reason=o["reason"],
                reviewer_name=o["reviewer_name"],
                reviewer_role=o["reviewer_role"],
                at=o["at"],
            )
        db_session.commit()

    return db_session


@pytest.fixture()
def client(seeded_db: Session):
    def _override_get_db():
        yield seeded_db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
