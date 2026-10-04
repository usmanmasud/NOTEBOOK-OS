from app.core.config import get_settings
from app.providers import registry
from app.providers.base import OCR_UNAVAILABLE_MSG, ProviderUnavailable
from tests.conftest import login, sample_bytes, upload_photo

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 64


def test_rejects_non_image(client, auth):
    r = client.post("/api/uploads/photo", headers=auth, files={"file": ("a.png", b"<script>alert(1)</script>", "image/png")})
    assert r.status_code == 415


def test_rejects_oversized(client, auth, monkeypatch):
    monkeypatch.setenv("MAX_PHOTO_BYTES", "100")
    get_settings.cache_clear()
    r = client.post("/api/uploads/photo", headers=auth, files={"file": ("a.png", PNG * 3, "image/png")})
    assert r.status_code == 413


def test_rejects_empty(client, auth):
    r = client.post("/api/uploads/photo", headers=auth, files={"file": ("a.png", b"", "image/png")})
    assert r.status_code == 422


def test_filename_is_sanitised(client, auth):
    r = client.post("/api/uploads/photo", headers=auth, files={"file": ("../../etc/passwd.png", PNG, "image/png")})
    assert r.json()["original_filename"] == "passwd.png"


def test_unknown_photo_fails_gracefully_then_manual_entry(client, auth):
    upload = client.post("/api/uploads/photo", headers=auth, files={"file": ("x.png", PNG, "image/png")}).json()
    upload = client.get(f"/api/uploads/{upload['id']}", headers=auth).json()
    assert upload["status"] == "FAILED"
    assert upload["error_message"] == OCR_UNAVAILABLE_MSG
    r = client.post(
        f"/api/uploads/{upload['id']}/records", headers=auth,
        json={"type": "DEBT", "amount": "20k", "person": "Musa", "date": "2026-10-01"},
    )
    assert r.status_code == 201
    rec = r.json()
    assert rec["manual_entry"] is True and rec["source"]["reference"] == "manual-entry"
    assert client.post(f"/api/uploads/{upload['id']}/confirm", headers=auth).status_code == 200
    assert client.get("/api/dashboard", headers=auth).json()["metrics"]["outstanding_debt"]["value"] == 20000


def test_provider_crash_is_not_exposed(client, auth):
    class Broken:
        name = "broken"

        def read_image(self, data, mime):
            raise RuntimeError("secret internal detail at /srv/app.py line 3")

    registry.override("ocr", [Broken()])
    up = client.post("/api/uploads/photo", headers=auth, files={"file": ("x.png", PNG, "image/png")}).json()
    up = client.get(f"/api/uploads/{up['id']}", headers=auth).json()
    assert up["status"] == "FAILED" and "secret" not in up["error_message"]


def test_ocr_chain_falls_back_to_next_provider(client, auth):
    from app.providers.demo import DemoOCRProvider

    class Down:
        name = "huawei-ocr"

        def read_image(self, data, mime):
            raise ProviderUnavailable(OCR_UNAVAILABLE_MSG, "timeout")

    registry.override("ocr", [Down(), DemoOCRProvider()])
    upload = upload_photo(client, auth)
    assert upload["status"] == "REVIEW" and upload["pipeline"]["read_provider"] == "demo-fixture"


def test_retry_after_failure(client, auth):
    registry.override("ocr", [])
    up = client.post("/api/uploads/photo", headers=auth,
                     files={"file": ("a.png", sample_bytes("notebooks/notebook_a_page2.png"), "image/png")}).json()
    assert client.get(f"/api/uploads/{up['id']}", headers=auth).json()["status"] == "FAILED"
    registry.override("ocr", None)
    assert client.post(f"/api/uploads/{up['id']}/retry", headers=auth).status_code == 202
    assert client.get(f"/api/uploads/{up['id']}", headers=auth).json()["status"] == "REVIEW"


def test_other_users_cannot_access(client, auth):
    upload = upload_photo(client, auth)
    records = client.get(f"/api/uploads/{upload['id']}/records", headers=auth).json()
    intruder = login(client, "+2348000000099")
    assert client.get(f"/api/uploads/{upload['id']}", headers=intruder).status_code == 404
    assert client.get(f"/api/uploads/{upload['id']}/file", headers=intruder).status_code == 404
    assert client.patch(f"/api/records/{records[0]['id']}", headers=intruder, json={"amount": 1}).status_code == 404
    assert client.post(f"/api/records/{records[0]['id']}/confirm", headers=intruder).status_code == 404
    assert client.delete(f"/api/uploads/{upload['id']}", headers=intruder).status_code == 404
    assert client.get("/api/uploads", headers=intruder).json() == []


def test_delete_upload_removes_records_file_and_metrics(client, auth):
    upload = upload_photo(client, auth)
    client.post(f"/api/uploads/{upload['id']}/confirm", headers=auth)
    assert client.get("/api/dashboard", headers=auth).json()["metrics"]["transactions"]["value"] == 5
    r = client.delete(f"/api/uploads/{upload['id']}", headers=auth)
    assert r.json() == {"deleted": True, "records_removed": 5}
    assert client.get(f"/api/uploads/{upload['id']}", headers=auth).status_code == 404
    assert client.get("/api/dashboard", headers=auth).json()["metrics"]["transactions"]["value"] == 0


def test_typed_entry(client, auth):
    r = client.post("/api/uploads/text", headers=auth, json={"text": "Musa 20k bashi\nSold 2 bags rice 30,000"})
    assert r.status_code == 202
    records = client.get(f"/api/uploads/{r.json()['id']}/records", headers=auth).json()
    assert [(x["type"], x["amount"]) for x in records] == [("DEBT", 20000), ("SALE", 30000)]
    assert records[0]["source"]["upload_type"] == "TEXT"


def test_voice_sample_transcribed(client, auth):
    data = sample_bytes("voice/voice_note_1.wav")
    up = client.post("/api/uploads/voice", headers=auth, files={"file": ("v.wav", data, "audio/wav")}).json()
    up = client.get(f"/api/uploads/{up['id']}", headers=auth).json()
    assert up["status"] == "REVIEW" and "spaghetti" in up["raw_text"]
    records = client.get(f"/api/uploads/{up['id']}/records", headers=auth).json()
    assert [(x["type"], x["amount"], x["person"]) for x in records] == [
        ("SALE", 16000, None), ("DEBT", 7500, "Bello"), ("EXPENSE", 1500, None)
    ]


def test_unknown_voice_fails_with_typed_fallback_message(client, auth):
    wav = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\0" * 40
    up = client.post("/api/uploads/voice", headers=auth, files={"file": ("v.wav", wav, "audio/wav")}).json()
    up = client.get(f"/api/uploads/{up['id']}", headers=auth).json()
    assert up["status"] == "FAILED" and up["error_message"] == "Voice processing unavailable. Use typed entry."


def test_voice_rejects_non_audio(client, auth):
    r = client.post("/api/uploads/voice", headers=auth, files={"file": ("v.wav", PNG, "audio/wav")})
    assert r.status_code == 415
