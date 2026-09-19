"""
Real audio boundary tests (brief §30). Exercises actual bytes returned by
GET /api/leads/{lead_id}/audio — never a mocked/short-circuited response —
against the same seeded_db fixture the rest of the suite uses, which
genuinely writes WAV files to backend/data/recordings/ via
app.services.audio_storage.generate_demo_recording for the named leads.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_audio_returns_real_nonzero_wav_bytes(client: TestClient):
    res = client.get("/api/leads/3613790/audio")
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/wav"
    assert len(res.content) > 1000
    # A real WAV file starts with the RIFF/WAVE header — proves these are
    # genuine audio bytes, not placeholder text pretending to be audio.
    assert res.content[0:4] == b"RIFF"
    assert res.content[8:12] == b"WAVE"


def test_audio_supports_range_requests_for_seeking(client: TestClient):
    res = client.get("/api/leads/3613790/audio", headers={"Range": "bytes=0-1023"})
    assert res.status_code == 206
    assert res.headers["accept-ranges"] == "bytes"
    assert res.headers["content-length"] == "1024"
    assert "content-range" in res.headers


def test_audio_404s_for_lead_with_no_recording_not_a_fake_success(client: TestClient):
    # Lead I (3613834) is the seeded ingest-error scenario — never gets a
    # Recording row or a generated file (brief §28: no fake success).
    res = client.get("/api/leads/3613834/audio")
    assert res.status_code == 404


def test_audio_404s_for_unknown_lead(client: TestClient):
    res = client.get("/api/leads/does-not-exist/audio")
    assert res.status_code == 404


def test_lead_out_has_audio_flag_reflects_real_file_presence(client: TestClient):
    with_audio = client.get("/api/leads/3613790").json()
    without_audio = client.get("/api/leads/3613834").json()
    assert with_audio["hasAudio"] is True
    assert without_audio["hasAudio"] is False
