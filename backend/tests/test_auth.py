from app.core.config import get_settings
from tests.conftest import login


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
    deps = client.get("/api/health/dependencies").json()
    assert deps["status"] == "ok"
    assert deps["checks"]["database"]["ok"] is True
    body = str(deps)
    assert "password" not in body.lower() and "sqlite:///" not in body


def test_otp_flow_and_me(client):
    headers = login(client, "+234 800 000 0002")
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["phone"].startswith("+234") and "*" in me["phone"]  # masked
    assert me["is_demo"] is False


def test_wrong_code_rejected(client):
    client.post("/api/auth/request-otp", json={"phone": "+2348000000003"})
    r = client.post("/api/auth/verify-otp", json={"phone": "+2348000000003", "code": "000000x"})
    assert r.status_code == 400


def test_code_cannot_be_reused(client):
    r = client.post("/api/auth/request-otp", json={"phone": "+2348000000004"})
    code = r.json()["dev_code"]
    assert client.post("/api/auth/verify-otp", json={"phone": "+2348000000004", "code": code}).status_code == 200
    assert client.post("/api/auth/verify-otp", json={"phone": "+2348000000004", "code": code}).status_code == 400


def test_attempt_limit(client):
    client.post("/api/auth/request-otp", json={"phone": "+2348000000005"})
    codes = [client.post("/api/auth/verify-otp", json={"phone": "+2348000000005", "code": "999999"}).status_code
             for _ in range(get_settings().otp_max_attempts + 1)]
    assert codes[-1] == 429


def test_otp_request_rate_limit(client):
    statuses = [client.post("/api/auth/request-otp", json={"phone": "+2348000000006"}).status_code for _ in range(7)]
    assert statuses[:5] == [200] * 5 and statuses[-1] == 429


def test_invalid_phone(client):
    assert client.post("/api/auth/request-otp", json={"phone": "hello-world"}).status_code == 422


def test_dev_code_never_returned_in_production(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        r = client.post("/api/auth/request-otp", json={"phone": "+2348000000007"})
        assert "dev_code" not in r.json()
    finally:
        monkeypatch.setenv("APP_ENV", "test")
        get_settings.cache_clear()


def test_requires_auth(client):
    for path in ("/api/auth/me", "/api/uploads", "/api/dashboard"):
        assert client.get(path).status_code == 401
    assert client.get("/api/dashboard", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_logout_ends_session(client, auth):
    assert client.post("/api/auth/logout", headers=auth).status_code == 200
    assert client.get("/api/auth/me", headers=auth).status_code == 401


def test_demo_login(client):
    r = client.post("/api/auth/demo")
    assert r.status_code == 200 and r.json()["user"]["is_demo"] is True


def test_demo_login_disabled_outside_demo_mode(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()
    assert client.post("/api/auth/demo").status_code == 404


def test_email_otp_flow(client):
    r = client.post("/api/auth/request-otp", json={"email": "  Trader@Example.COM "})
    assert r.status_code == 200, r.text
    code = r.json()["dev_code"]
    r = client.post("/api/auth/verify-otp", json={"email": "trader@example.com", "code": code})
    assert r.status_code == 200, r.text
    user = r.json()["user"]
    assert user["email"] == "tr****@example.com" and user["phone"] is None
    # Same email signs in to the same account.
    code = client.post("/api/auth/request-otp", json={"email": "trader@example.com"}).json()["dev_code"]
    again = client.post("/api/auth/verify-otp", json={"email": "trader@example.com", "code": code}).json()["user"]
    assert again["id"] == user["id"]


def test_email_and_phone_codes_are_separate(client):
    client.post("/api/auth/request-otp", json={"email": "a@example.com"})
    code = client.post("/api/auth/request-otp", json={"phone": "+2348000000010"}).json()["dev_code"]
    r = client.post("/api/auth/verify-otp", json={"email": "a@example.com", "code": code})
    assert r.status_code == 400  # a phone code never unlocks an email account


def test_identifier_validation(client):
    assert client.post("/api/auth/request-otp", json={"email": "not-an-email"}).status_code == 422
    assert client.post("/api/auth/request-otp", json={}).status_code == 422
    both = {"email": "a@example.com", "phone": "+2348000000011"}
    assert client.post("/api/auth/request-otp", json=both).status_code == 422


def test_production_methods_and_email_delivery(client, monkeypatch):
    from app.auth import delivery

    sent = []
    monkeypatch.setattr(delivery.httpx, "post", lambda url, json, headers, timeout: sent.append(json) or _Resp(200))
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("OTP_DEV_ECHO", "false")
    get_settings.cache_clear()
    try:
        assert client.get("/api/config").json()["login_methods"] == []
        assert client.post("/api/auth/request-otp", json={"phone": "+2348000000012"}).status_code == 400
        monkeypatch.setenv("EMAIL_PROVIDER", "resend")
        monkeypatch.setenv("RESEND_API_KEY", "re_test")
        monkeypatch.setenv("EMAIL_FROM", "NotebookOS <login@example.com>")
        get_settings.cache_clear()
        assert client.get("/api/config").json()["login_methods"] == ["email"]
        r = client.post("/api/auth/request-otp", json={"email": "owner@example.com"})
        assert r.status_code == 200 and "dev_code" not in r.json()
        assert sent and sent[0]["to"] == ["owner@example.com"] and sent[0]["subject"][:6].isdigit()
        # Provider failure is a clean 503 with no provider details.
        monkeypatch.setattr(delivery.httpx, "post", lambda *a, **k: _Resp(422, {"message": "domain not verified"}))
        r = client.post("/api/auth/request-otp", json={"email": "owner2@example.com"})
        assert r.status_code == 503 and "domain" not in r.text
    finally:
        for k in ("EMAIL_PROVIDER", "RESEND_API_KEY", "EMAIL_FROM"):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.setenv("OTP_DEV_ECHO", "true")
        get_settings.cache_clear()


class _Resp:
    def __init__(self, status: int, body: dict | None = None) -> None:
        self.status_code = status
        self._body = body or {"id": "x"}

    def json(self) -> dict:
        return self._body
