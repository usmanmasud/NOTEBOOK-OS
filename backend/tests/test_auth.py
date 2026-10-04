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
