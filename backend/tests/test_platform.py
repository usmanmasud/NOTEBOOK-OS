"""Error handling, providers, validation rules and migrations."""

import datetime as dt
from decimal import Decimal

import httpx

from app.core.config import Settings, get_settings
from app.providers.huawei import HuaweiOCRProvider, parse_huawei_ocr
from app.providers.llm import OpenAICompatibleLLMProvider
from app.validation.rules import confidence_level, validate_record


def test_unhandled_errors_hide_details(client):
    from app.main import create_app
    from fastapi.testclient import TestClient

    app = create_app()

    @app.get("/api/boom")
    def boom():
        raise RuntimeError("database password is hunter2")

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/boom")
    assert r.status_code == 500
    assert "hunter2" not in r.text and "Traceback" not in r.text


def test_validation_errors_are_friendly(client, auth):
    r = client.patch("/api/records/whatever", headers=auth, json={"amount": "lots"})
    assert r.status_code == 422 and "fields" in r.json()


def test_production_refuses_unsafe_config():
    s = Settings(app_env="production", otp_dev_echo=True, database_url="sqlite:///x.db", redis_url="")
    problems = s.validate_for_production()
    assert len(problems) == 3


def test_confidence_thresholds_are_configurable():
    s = Settings(confidence_high=0.9, confidence_review=0.5)
    assert confidence_level(0.89, s) == "review"
    assert confidence_level(0.49, s) == "low"
    assert confidence_level(0.95, s) == "high"


def _validate(fields, text="Musa 20k bashi", human=frozenset(), conf=None):
    base = {"date": None, "type": None, "item": None, "quantity": None, "amount": None, "person": None, "notes": None}
    base.update(fields)
    return validate_record(base, conf or {}, 0.9, text, set(human), get_settings(), dt.date(2026, 10, 4))


def codes(issues):
    return {(i["field"], i["code"]) for i in issues}


def test_validation_rules():
    assert ("person", "missing") in codes(_validate({"type": "DEBT", "amount": Decimal(20000)}))
    assert ("amount", "missing") in codes(_validate({"type": "SALE"}))
    assert ("date", "future") in codes(_validate({"type": "SALE", "amount": Decimal(20000), "date": dt.date(2027, 1, 1)}))
    assert ("amount", "suspicious") in codes(_validate({"type": "SALE", "amount": Decimal(9_000_000)}, text="9,000,000"))
    # AI amount that is not in the source text is flagged...
    assert ("amount", "not_in_source") in codes(_validate({"type": "DEBT", "amount": Decimal(25000), "person": "Musa"}))
    # ...but not when a human typed it.
    assert ("amount", "not_in_source") not in codes(
        _validate({"type": "DEBT", "amount": Decimal(25000), "person": "Musa"}, human={"amount"})
    )
    assert ("person", "not_in_source") in codes(_validate({"type": "DEBT", "amount": Decimal(20000), "person": "Aisha"}))
    assert _validate({"type": "DEBT", "amount": Decimal(20000), "person": "Musa"}) == []


def test_huawei_ocr_response_parsing():
    payload = {"result": {"words_block_list": [
        {"words": "Musa 20k bashi", "confidence": 0.61, "location": [[100, 400], [600, 400], [600, 460], [100, 460]]},
        {"words": "1/10/26", "confidence": 0.97, "location": [[100, 100], [300, 100], [300, 150], [100, 150]]},
    ]}}
    result = parse_huawei_ocr(payload, (1000, 2000), "huawei-ocr")
    lines = result.pages[0].lines
    assert [ln.text for ln in lines] == ["1/10/26", "Musa 20k bashi"]  # sorted top-to-bottom
    assert lines[1].bbox.x == 0.1 and lines[1].bbox.width == 0.5 and lines[1].confidence == 0.61


def test_huawei_ocr_unconfigured_is_unavailable():
    import pytest

    from app.providers.base import ProviderUnavailable

    with pytest.raises(ProviderUnavailable):
        HuaweiOCRProvider().read_image(b"x", "image/png")


def test_openai_compatible_provider_request(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_API_KEY", "k")
    get_settings.cache_clear()
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"records": []}'}}]})

    provider = OpenAICompatibleLLMProvider(client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert provider.complete_json("s", "u") == '{"records": []}'
    assert seen == {"url": "https://llm.example.test/v1/chat/completions", "auth": "Bearer k"}


def test_alembic_migration_matches_models(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app.core import db as db_module
    from app.core.config import BACKEND_DIR

    url = f"sqlite:///{(tmp_path / 'm.db').as_posix()}"
    engine = db_module.configure(url)
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), db_module.Base.metadata)
    assert diff == []
