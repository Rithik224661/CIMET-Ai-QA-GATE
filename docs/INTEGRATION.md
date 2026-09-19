# Integration boundaries — VerityGate

What's real, what's a working demo adapter, and what genuinely isn't available. No item below is described as more finished than it is.

## Ingestion (recording arrival)

- **IMPLEMENTED**: `IngestionAdapter` Protocol (`backend/app/services/ingestion.py`) — `fetch_recording(lead_id) -> IngestedRecording | None`.
- **IMPLEMENTED (demo)**: `MockIngestionAdapter` — looks up synthetic recordings seeded from `app/seed_data.py`.
- **NOT AVAILABLE**: `CIMETSandboxAdapter.fetch_recording()` raises `NotImplementedError` explicitly. No real CIMET dialler endpoint, schema, or credentials have been provided to this environment.

## ASR (audio → transcript)

- **IMPLEMENTED**: `ASRProvider` Protocol (`backend/app/services/asr_provider.py`) — `transcribe(db, lead) -> list[TranscribedSegment] | None`.
- **IMPLEMENTED (demo)**: `MockTranscriptProvider` — returns the transcript the lead was already ingested with. This deliberately does **not** run any transcription; it stands in for "a sanitized transcript was supplied directly," which is the CIMET brief's stated fallback when ASR isn't available.
- **NOT AVAILABLE**: `CIMETASRAdapter.transcribe()` raises `NotImplementedError`. No real ASR vendor or credentials have been provided.
- **Note**: this module is not called from the live evaluation pipeline — in this build, ingestion (recording + transcript arriving together) has already happened by seed time, so there's no separate "run ASR now" step to wire it into yet. It exists as a visible, swappable boundary.

## Audio playback

- **IMPLEMENTED**: `GET /api/leads/{id}/audio` serves real WAV bytes with HTTP Range support (Starlette's `FileResponse`, native 206 partial-content handling) — genuinely seekable from the browser.
- **IMPLEMENTED (demo)**: the audio itself is **synthetic** — a speaker-distinguishable tone generated from the lead's real seeded turn timings (`backend/app/services/audio_storage.py`), not a real call recording. Generated only for the 9 named demo leads.
- **READY FOR INTEGRATION**: swapping in real recording bytes only requires the ingestion adapter above to place a real file where `recording_path(lead_id)` looks — the API/player layer is agnostic to where the bytes came from.

## Scoring sandbox payload

- **IMPLEMENTED**: `SandboxPayload` Pydantic model + `to_domain_lead_input()` anti-corruption layer (`backend/app/services/sandbox_adapter.py`), and `DATA_MODE=demo|sandbox` as an explicit config switch (`backend/app/config.py`).
- **NOT AVAILABLE**: no real CIMET sandbox schema has been supplied. `SandboxPayload`'s fields are a reasonable inferred shape (lead id, retailer, transcript turns, CRM snapshot) from the brief's own description, not a verified contract. `DATA_MODE=sandbox` is wired as a config value but has no real payload source behind it yet — `/api/health`'s `sandboxConfigured` field is hard-coded `false` for exactly this reason, never inferred from `DATA_MODE` alone.

## Submission

- **IMPLEMENTED**: `MockSubmissionAdapter` (`backend/app/services/submission.py`) — builds a submission payload labeled `"sandbox": "DEMO_MOCK"`, persists a real `Submission` row, only reachable when `decision.decision == AUTO_SUBMIT` (a `ValueError` guard, not just convention).
- **READY FOR INTEGRATION**: the adapter boundary (`submit_if_auto_submitted`) is the single call site the pipeline uses — a real CRM submission adapter would implement the same interface and slot in without touching `pipeline.py`, `gate.py`, or any evaluator.
- **NOT AVAILABLE**: no real CRM submission endpoint/credentials have been provided.

## AI provider

- **IMPLEMENTED**: `LLMProvider` Protocol (`backend/app/services/ai_provider.py`) — `NullLLMProvider` (default, zero external calls) and `AnthropicLLMProvider` (opt-in, real Anthropic SDK call when `AI_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` are set).
- **VERIFIED**: the safety-fallback path (provider configured but call fails/unavailable) has been exercised live in this environment — see `docs/DEMO.md`'s fallback section.
- **NOT VERIFIED**: no real, credentialed Anthropic call has been run in this environment (no API key was available). The code path is real and tested against a fake provider (`tests/test_ai_behaviour.py`) and against a genuine-but-key-less Anthropic configuration (`tests/test_ai_pipeline_integration.py`), not against the live API.

## Summary table

| Boundary | Interface exists | Demo implementation | Real integration |
|---|---|---|---|
| Ingestion | ✅ | ✅ Mock | ❌ Not available |
| ASR | ✅ | ✅ Mock (passthrough) | ❌ Not available |
| Audio storage/playback | ✅ | ✅ Synthetic tone | Ready — same API, real bytes |
| Sandbox payload | ✅ | ⚠️ Inferred schema only | ❌ Not available |
| Submission | ✅ | ✅ Mock (`DEMO_MOCK`) | Ready — same adapter interface |
| AI provider | ✅ | ✅ Null (default) + real Anthropic wiring | ⚠️ Wiring verified, live call not exercised (no key) |
