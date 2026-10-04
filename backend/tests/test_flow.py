"""End-to-end: upload -> extraction -> review -> confirmation -> dashboard -> evidence -> report.

This is the "most important product test" from the spec, run fully offline with the
demo OCR fixture and the rule-based interpreter.
"""

from tests.conftest import upload_photo


def by_person(records, name):
    return next(r for r in records if r["person"] == name)


def test_notebook_to_report_end_to_end(client, auth):
    # 1. Upload the notebook photo; processing runs and lands in REVIEW.
    upload = upload_photo(client, auth)
    assert upload["status"] == "REVIEW"
    assert upload["pipeline"]["read_is_demo_fixture"] is True
    assert upload["pages"][0]["page_number"] == 2

    # 2. AI-extracted records: Musa's debt is flagged with 61% confidence.
    records = client.get(f"/api/uploads/{upload['id']}/records", headers=auth).json()
    assert len(records) == 5
    musa = by_person(records, "Musa")
    assert musa["type"] == "DEBT" and musa["amount"] == 20000
    assert musa["confidence"] == 0.61 and musa["confidence_level"] == "review"
    assert musa["status"] == "NEEDS_REVIEW"
    assert musa["quantity"] is None  # unclear "2?" not guessed
    assert musa["source"]["reference"] == "page-2-row-4"
    assert musa["source"]["original_text"] == "Musa shinkafa 2? 20k bashi"
    assert musa["source"]["bbox"]["width"] > 0
    # The notebook's written total matches the extracted cash sales.
    assert upload["pipeline"]["total_checks"][0]["matches"] is True

    # 3. Nothing is official yet.
    dash = client.get("/api/dashboard", headers=auth).json()
    assert dash["metrics"]["outstanding_debt"]["value"] == 0
    assert dash["pending_review"] == 5

    # 4. The trader fixes the uncertain field and confirms the page.
    r = client.patch(f"/api/records/{musa['id']}", headers=auth, json={"quantity": 2})
    assert r.status_code == 200
    edited = r.json()
    assert edited["edited"] is True and edited["human_fields"] == ["quantity"]
    assert edited["ai_original"]["quantity"] is None  # the AI's proposal is kept for audit
    r = client.post(f"/api/uploads/{upload['id']}/confirm", headers=auth)
    assert r.status_code == 200 and r.json()["confirmed"] == 5
    assert r.json()["upload"]["status"] == "CONFIRMED"

    # 5. Dashboard now reflects the confirmed records (deterministic sums).
    dash = client.get("/api/dashboard", headers=auth).json()
    m = {k: v["value"] for k, v in dash["metrics"].items()}
    assert m["outstanding_debt"] == 20000
    assert m["total_sales"] == 63000
    assert m["total_expenses"] == 2500
    assert m["stock_purchases"] == 150000
    assert m["transactions"] == 5

    # 6. Evidence: the number traces back to Musa's confirmed line on page 2.
    ev = client.get("/api/dashboard/evidence/outstanding_debt", headers=auth).json()
    assert ev["value"] == 20000
    assert len(ev["records"]) == 1
    rec = ev["records"][0]
    assert rec["person"] == "Musa" and rec["status"] == "CONFIRMED"
    assert rec["source"]["page_number"] == 2 and rec["source"]["has_image"] is True
    # The original notebook image is retrievable by the owner.
    img = client.get(f"/api/uploads/{rec['source']['upload_id']}/file", headers=auth)
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"

    # 7. Report from confirmed records, shared read-only.
    r = client.post("/api/reports", headers=auth, json={"consent": True})
    assert r.status_code == 201
    report = r.json()
    assert report["snapshot"]["metrics"]["outstanding_debt"] == 20000
    public = client.get(f"/api/reports/{report['share_token']}")
    assert public.status_code == 200
    assert public.json()["snapshot"]["metrics"]["total_sales"] == 63000


def test_only_confirmed_records_count(client, auth):
    upload = upload_photo(client, auth)
    records = client.get(f"/api/uploads/{upload['id']}/records", headers=auth).json()
    sale = next(r for r in records if r["type"] == "SALE")
    musa = by_person(records, "Musa")
    assert client.post(f"/api/records/{sale['id']}/confirm", headers=auth).status_code == 200
    assert client.post(f"/api/records/{musa['id']}/reject", headers=auth).status_code == 200
    m = client.get("/api/dashboard", headers=auth).json()["metrics"]
    assert m["total_sales"]["value"] == sale["amount"]
    assert m["outstanding_debt"]["value"] == 0
    assert m["transactions"]["value"] == 1


def test_editing_confirmed_record_requires_reconfirmation(client, auth):
    upload = upload_photo(client, auth)
    client.post(f"/api/uploads/{upload['id']}/confirm", headers=auth)
    records = client.get(f"/api/uploads/{upload['id']}/records", headers=auth).json()
    musa = by_person(records, "Musa")
    r = client.patch(f"/api/records/{musa['id']}", headers=auth, json={"amount": "25k"})
    assert r.json()["status"] != "CONFIRMED" and r.json()["amount"] == 25000
    assert client.get("/api/dashboard", headers=auth).json()["metrics"]["outstanding_debt"]["value"] == 0
    assert client.get(f"/api/uploads/{upload['id']}", headers=auth).json()["status"] == "REVIEW"


def test_records_with_errors_cannot_be_confirmed(client, auth):
    upload = upload_photo(client, auth, "notebooks/notebook_b_page3.png")
    records = client.get(f"/api/uploads/{upload['id']}/records", headers=auth).json()
    salt = next(r for r in records if r["item"] == "Salt")
    assert salt["amount"] is None
    assert any(i["field"] == "amount" and i["severity"] == "error" for i in salt["validation_issues"])
    r = client.post(f"/api/uploads/{upload['id']}/confirm", headers=auth)
    assert r.status_code == 422
    assert r.json()["detail"]["records"][0]["id"] == salt["id"]
    # Written total (9,400) disagrees with extracted sales (6,400): flagged for the trader.
    assert upload["pipeline"]["total_checks"][0]["matches"] is False
    # Human supplies the missing amount; now the page can be confirmed.
    client.patch(f"/api/records/{salt['id']}", headers=auth, json={"amount": 3000})
    assert client.post(f"/api/uploads/{upload['id']}/confirm", headers=auth).status_code == 200


def test_evidence_for_unknown_metric(client, auth):
    assert client.get("/api/dashboard/evidence/profit_margin", headers=auth).status_code == 404


def test_demo_reset_seeds_history_with_provenance(client, demo_auth):
    r = client.post("/api/demo/reset", headers=demo_auth, json={"with_history": True})
    assert r.status_code == 200 and r.json()["history_records_confirmed"] == 10
    dash = client.get("/api/dashboard", headers=demo_auth).json()
    assert dash["metrics"]["outstanding_debt"]["value"] == 20000  # Aisha, page 5
    ev = client.get("/api/dashboard/evidence/outstanding_debt", headers=demo_auth).json()
    assert [r["person"] for r in ev["records"]] == ["Aisha"]
    assert ev["records"][0]["source"]["page_number"] == 5
    # Seeded history is labelled: it was confirmed by the setup script, not a person.
    assert ev["records"][0]["source"]["seeded_demo_history"] is True
    # Then the live demo page adds Musa: 40,000 across Musa (p2) and Aisha (p5).
    upload = upload_photo(client, demo_auth)
    client.post(f"/api/uploads/{upload['id']}/confirm", headers=demo_auth)
    ev = client.get("/api/dashboard/evidence/outstanding_debt", headers=demo_auth).json()
    assert ev["value"] == 40000
    assert sorted((r["person"], r["source"]["page_number"]) for r in ev["records"]) == [("Aisha", 5), ("Musa", 2)]
    musa = next(r for r in ev["records"] if r["person"] == "Musa")
    assert musa["source"]["seeded_demo_history"] is False
    report = client.post("/api/reports", headers=demo_auth, json={"consent": True}).json()
    assert report["snapshot"]["sources"]["records_preloaded_demo_history"] == 10


def test_demo_reset_forbidden_for_normal_users(client, auth):
    assert client.post("/api/demo/reset", headers=auth, json={}).status_code == 403
