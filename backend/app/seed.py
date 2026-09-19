"""
Database seed script. Reproducible from an empty local database:

    python -m app.seed

Populates synthetic retailers, the one checklist export in hand (Retailer 1
energy v1.4, plus superseded/other-retailer rule-set rows for navigation),
the 9 named demo scenarios (run through the real evaluators, not
hand-authored outcomes), a repeat-offence history pair, a bulk synthetic
backfill for dashboard/calibration realism, and synthetic human reviews for
calibration metrics. Re-running wipes and reseeds (demo convenience; never
do this against anything but the local sqlite file — see main guard below).
"""

from __future__ import annotations

import datetime as dt
import random
import sys

from sqlalchemy.orm import Session

from .config import settings
from .db import Base, SessionLocal, engine
from .enums import AuditEventType, Decision, LeadState
from .models import Check, Checklist, IngestError, Lead, Recording, Retailer, RuleVersion
from .seed_data import (
    CHECK_CATALOGUE,
    REPEAT_OFFENCE_HISTORY,
    RETAILERS,
    RULE_SETS,
    WEIGHT_BY_TYPE,
    LEADS,
    LeadSeed,
    generate_bulk_leads,
)
from .services.audit import append_audit_event
from .services.pipeline import record_ingest_events, run_evaluation
from .services.transcript import create_transcript


def _seed_retailers(db: Session) -> dict[str, Retailer]:
    retailers = {}
    for name in RETAILERS:
        r = Retailer(name=name)
        db.add(r)
        retailers[name] = r
    db.flush()
    return retailers


def _seed_rule_sets(db: Session, retailers: dict[str, Retailer]) -> dict[tuple[str, str], RuleVersion]:
    checklists: dict[tuple[str, str], Checklist] = {}
    versions: dict[tuple[str, str], RuleVersion] = {}
    live_v14: RuleVersion | None = None

    for row in RULE_SETS:
        key = (row["retailer"], row["checklist"])
        if key not in checklists:
            product = "Broadband" if "Broadband" in row["checklist"] else "Energy"
            checklist = Checklist(retailer_id=retailers[row["retailer"]].id, name=row["checklist"], product=product)
            db.add(checklist)
            db.flush()
            checklists[key] = checklist

        version = RuleVersion(
            checklist_id=checklists[key].id,
            version=row["version"],
            effective_from=row["effective_from"],
            effective_to=None,
            live=row["live"],
        )
        db.add(version)
        db.flush()
        versions[(row["retailer"], row["version"])] = version

        if row["has_checks"]:
            for i, c in enumerate(CHECK_CATALOGUE):
                db.add(
                    Check(
                        rule_version_id=version.id,
                        code=c["code"],
                        name=c["name"],
                        type=c["type"],
                        critical=c["critical"],
                        weight=WEIGHT_BY_TYPE[c["type"]],
                        source_of_truth=c["source_of_truth"],
                        config=c["config"],
                    )
                )
            live_v14 = version
    db.flush()
    assert live_v14 is not None
    return versions, live_v14


def _ingest_lead(db: Session, seed: LeadSeed, retailers: dict[str, Retailer], checklist_version: RuleVersion | None) -> Lead:
    lead = Lead(
        id=seed.id,
        scenario_tag=seed.scenario_tag or None,
        scenario_summary=seed.scenario_summary or None,
        retailer_id=retailers[seed.retailer].id,
        product=seed.product,
        agent=seed.agent,
        team_lead=seed.team_lead,
        campaign=seed.campaign,
        site=seed.site,
        call_datetime=seed.call_datetime,
        duration_sec=seed.duration_sec,
        last_completed_step="call_completed" if seed.state != "error" else "recording_upload",
        test_contact=f"synthetic+{seed.id}@example.test",
        checklist_version_id=checklist_version.id if checklist_version else None,
        state=seed.state,
        repeat_offence=False,
        is_seed_scenario=bool(seed.scenario_tag),
        crm_snapshot=seed.crm_snapshot,
        created_at=dt.datetime.now(dt.UTC),
        updated_at=dt.datetime.now(dt.UTC),
    )
    db.add(lead)
    db.flush()

    if seed.state == "error":
        db.add(
            IngestError(
                lead_id=lead.id,
                code=seed.ingest_error["code"],
                message=seed.ingest_error["message"],
                retry=seed.ingest_error["retry"],
                at=seed.ingest_error["at"],
            )
        )
        record_ingest_events(db, lead, recording_ok=False)
        db.flush()
        return lead

    db.add(
        Recording(
            lead_id=lead.id,
            source="dialler_mock",
            duration_seconds=seed.duration_sec,
            storage_reference=f"mock://recordings/{lead.id}.wav",
            mime_type="audio/wav",
            processing_status="ready",
            created_at=dt.datetime.now(dt.UTC),
        )
    )

    if seed.state == "processing":
        record_ingest_events(db, lead, recording_ok=True)
        db.flush()
        return lead

    create_transcript(db, lead, seed.turns)
    record_ingest_events(db, lead, recording_ok=True)
    db.flush()
    return lead


def _seed_human_review(db: Session, lead: Lead, *, human_decision: str, reason: str, reviewer_name: str, reviewer_role: str, at: dt.datetime) -> None:
    from .models import HumanReview

    review = HumanReview(
        lead_id=lead.id,
        reviewer_name=reviewer_name,
        reviewer_role=reviewer_role,
        ai_decision=lead.decision.decision,
        human_decision=human_decision,
        reason=reason,
        created_at=at,
    )
    db.add(review)
    db.flush()
    append_audit_event(
        db, lead_id=lead.id, event_type=AuditEventType.HUMAN_OVERRIDE, actor=f"{reviewer_role} · {reviewer_name}",
        resulting_state=human_decision, at=at,
    )


_REVIEWERS = [("S. Bhandari", "QA Analyst"), ("A. Fernandes", "QA Analyst"), ("K. Rao", "Team Lead")]
_DISAGREEMENT_REASONS = [
    "Auditor found an unread cooling-off clause the check scored as present.",
    "Crosstalk resolved on listen-back; the disputed statement was actually read verbatim.",
    "Address formatting difference the extractor treated as a mismatch turned out to be the same address.",
    "Paraphrased DMO accepted on manual listen despite failing strict verbatim matching.",
]


def _seed_calibration_reviews(db: Session, scored_leads: list[Lead], *, rng: random.Random) -> None:
    for lead in scored_leads:
        # The 9 named demo scenarios (and the repeat-offence history pair)
        # keep exactly the reviews their narrative calls for — only Lead F
        # (3613766) ships with a pre-seeded override — never a randomly
        # attached synthetic one. Only bulk-generated backfill leads are
        # eligible for synthetic calibration sampling.
        if lead.is_seed_scenario:
            continue
        if lead.decision is None or lead.reviews:
            continue
        # Sample ~18% of scored leads for a synthetic independent audit.
        if rng.random() > 0.18:
            continue

        ai_binary = "HOLD" if lead.decision.decision == Decision.HOLD else "PASS"
        # Disagreement is directionally realistic, not a coin flip: a
        # human overturning an AI hold (critical false-fail) is a normal,
        # expected part of QA — auditors catch AI being too cautious. A
        # human catching something critical the AI *passed* (critical
        # false-pass) is the release-blocking failure mode the brief
        # treats as "essentially never" — so it's seeded almost never,
        # not at the same rate as the benign direction.
        disagree_chance = 0.12 if ai_binary == "HOLD" else 0.006
        disagree = rng.random() < disagree_chance
        human_decision = ("PASS" if ai_binary == "HOLD" else "HOLD") if disagree else ai_binary
        reviewer_name, reviewer_role = rng.choice(_REVIEWERS)
        at = lead.call_datetime + dt.timedelta(minutes=rng.randint(20, 90))
        reason = (
            rng.choice(_DISAGREEMENT_REASONS)
            if disagree
            else "Reviewed as part of the routine clean-call sample; agreed with the automated decision."
        )
        _seed_human_review(db, lead, human_decision=human_decision, reason=reason, reviewer_name=reviewer_name, reviewer_role=reviewer_role, at=at)

        # Occasionally double-audit for the auditor-to-auditor metric. The
        # second auditor can disagree with the first (that's the point of
        # the metric), but the same directional bias applies: flipping
        # *to* HOLD against an AI PASS is a critical false-pass and stays
        # rare, not a coin flip.
        if rng.random() < 0.25:
            second_name, second_role = rng.choice([r for r in _REVIEWERS if r[0] != reviewer_name])
            second_flip_chance = 0.15 if human_decision == "HOLD" else 0.02
            second_decision = ("PASS" if human_decision == "HOLD" else "HOLD") if rng.random() < second_flip_chance else human_decision
            _seed_human_review(
                db, lead, human_decision=second_decision, reason="Independent second audit for calibration.",
                reviewer_name=second_name, reviewer_role=second_role, at=at + dt.timedelta(minutes=5),
            )


def seed(*, bulk_count: int = 250, reset: bool = True) -> None:
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        retailers = _seed_retailers(db)
        versions, live_v14 = _seed_rule_sets(db, retailers)

        all_seeds: list[LeadSeed] = [*REPEAT_OFFENCE_HISTORY, *LEADS, *generate_bulk_leads(bulk_count)]

        scored_leads: list[Lead] = []
        for seed_row in all_seeds:
            # One checklist export in hand: every scored/processing lead
            # evaluates against Retailer 1's live checklist regardless of
            # its own retailer, matching the frontend Phase 1 fixture
            # behavior — see docs/DECISIONS.md. `resolve_rule_version`
            # itself stays retailer-correct (proven in tests) for when more
            # exports land. An ingest-error lead never got far enough to
            # have a rule set pinned at all.
            checklist_version = live_v14 if seed_row.state != "error" else None
            lead = _ingest_lead(db, seed_row, retailers, checklist_version)

            if seed_row.state == "scored":
                run_evaluation(db, lead)
                scored_leads.append(lead)

            if seed_row.pre_seeded_override:
                o = seed_row.pre_seeded_override
                _seed_human_review(
                    db, lead, human_decision=o["human_decision"], reason=o["reason"],
                    reviewer_name=o["reviewer_name"], reviewer_role=o["reviewer_role"], at=o["at"],
                )

            db.commit()

        rng = random.Random(7)
        _seed_calibration_reviews(db, scored_leads, rng=rng)
        db.commit()

        print(f"Seeded {len(all_seeds)} leads ({len(scored_leads)} scored) against {sum(len(v.checks) for v in versions.values())} check rows.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    bulk = 250
    if len(sys.argv) > 1:
        bulk = int(sys.argv[1])
    if "sqlite" not in settings.database_url:
        print("Refusing to run the destructive reseed against a non-sqlite DATABASE_URL.", file=sys.stderr)
        sys.exit(1)
    seed(bulk_count=bulk)
