import json

from app.reports.builder import llm_narrative, template_narrative
from app.analytics.metrics import Rec, compute_metrics
from app.providers import registry
from tests.conftest import upload_photo


def confirmed(client, auth):
    upload = upload_photo(client, auth)
    client.post(f"/api/uploads/{upload['id']}/confirm", headers=auth)


def test_report_requires_consent(client, auth):
    confirmed(client, auth)
    assert client.post("/api/reports", headers=auth, json={"consent": False}).status_code == 422


def test_report_requires_confirmed_records(client, auth):
    upload_photo(client, auth)  # extracted but not confirmed
    r = client.post("/api/reports", headers=auth, json={"consent": True})
    assert r.status_code == 422


def test_share_token_is_random_and_public_view_is_minimal(client, auth):
    confirmed(client, auth)
    a = client.post("/api/reports", headers=auth, json={"consent": True}).json()
    b = client.post("/api/reports", headers=auth, json={"consent": True}).json()
    assert a["share_token"] != b["share_token"] and len(a["share_token"]) >= 32
    public = client.get(f"/api/reports/{a['share_token']}").json()
    text = json.dumps(public)
    assert a["id"] not in text  # no internal IDs
    assert "Musa" not in text  # customers' names are not shared
    assert "upload" not in text.lower() or "uploads" not in public["snapshot"]
    assert "not a credit score" in public["snapshot"]["disclaimer"]
    assert "confirmed" in public["snapshot"]["evidence_statement"]


def test_revoked_report_is_not_accessible(client, auth):
    confirmed(client, auth)
    report = client.post("/api/reports", headers=auth, json={"consent": True}).json()
    assert client.post(f"/api/reports/{report['id']}/revoke", headers=auth).json()["status"] == "REVOKED"
    r = client.get(f"/api/reports/{report['share_token']}")
    assert r.status_code == 404
    missing = client.get("/api/reports/" + "x" * 32)
    assert missing.json() == r.json()  # revoked and unknown look the same


def test_report_is_a_frozen_snapshot(client, auth):
    confirmed(client, auth)
    report = client.post("/api/reports", headers=auth, json={"consent": True}).json()
    client.post("/api/uploads/text", headers=auth, json={"text": "Sold rice 1,000,000"})
    uploads = client.get("/api/uploads", headers=auth).json()
    client.post(f"/api/uploads/{uploads[0]['id']}/confirm", headers=auth)
    public = client.get(f"/api/reports/{report['share_token']}").json()
    assert public["snapshot"]["metrics"]["total_sales"] == 63000


def test_other_user_cannot_revoke(client, auth):
    from tests.conftest import login

    confirmed(client, auth)
    report = client.post("/api/reports", headers=auth, json={"consent": True}).json()
    other = login(client, "+2348000000077")
    assert client.post(f"/api/reports/{report['id']}/revoke", headers=other).status_code == 404


def test_llm_narrative_cannot_introduce_numbers():
    m = compute_metrics([Rec(id="1", type="SALE", amount=100000)])
    base = template_narrative(m, "NGN")

    class Liar:
        name = "liar"

        def complete_json(self, system, user):
            return json.dumps({"summary": "Sales were 250,000 this month."})

    class Honest:
        name = "honest"

        def complete_json(self, system, user):
            return json.dumps({"summary": "The trader recorded ₦100,000 of sales across 1 transaction."})

    registry.override("llm", [Liar()])
    assert llm_narrative(m, "NGN", base) == base
    registry.override("llm", [Honest()])
    assert "100,000" in llm_narrative(m, "NGN", base)
