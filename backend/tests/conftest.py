import os
import tempfile
from pathlib import Path

# Configure the app for tests before anything imports settings.
_TMP = Path(tempfile.mkdtemp(prefix="notebookos-tests-"))
os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": f"sqlite:///{(_TMP / 'test.db').as_posix()}",
        "REDIS_URL": "",
        "STORAGE_BACKEND": "local",
        "LOCAL_STORAGE_DIR": str(_TMP / "uploads"),
        "OTP_DEV_ECHO": "true",
        "DEMO_MODE": "true",
        "OCR_PROVIDER": "demo",
        "SPEECH_PROVIDER": "demo",
        "LLM_PROVIDER": "rules",
        "LOG_LEVEL": "WARNING",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core import db as db_module  # noqa: E402
from app.core.config import REPO_DIR, get_settings  # noqa: E402
from app.core.kv import MemoryStore, set_kv  # noqa: E402
from app.core.storage import set_storage  # noqa: E402
from app.providers import registry  # noqa: E402

SAMPLES = REPO_DIR / "samples"


@pytest.fixture(autouse=True)
def fresh_state():
    """Every test gets an empty database, empty KV store and default providers."""
    get_settings.cache_clear()
    engine = db_module.configure(os.environ["DATABASE_URL"])
    import app.models  # noqa: F401

    db_module.Base.metadata.drop_all(engine)
    db_module.Base.metadata.create_all(engine)
    set_kv(MemoryStore())
    set_storage(None)
    for kind in ("ocr", "speech", "llm"):
        registry.override(kind, None)
    yield
    for kind in ("ocr", "speech", "llm"):
        registry.override(kind, None)


@pytest.fixture
def client():
    from app.main import create_app

    with TestClient(create_app(), raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def db():
    session = db_module.session_factory()()
    yield session
    session.close()


def login(client: TestClient, phone: str = "+2348000000001") -> dict:
    r = client.post("/api/auth/request-otp", json={"phone": phone})
    assert r.status_code == 200, r.text
    code = r.json()["dev_code"]
    r = client.post("/api/auth/verify-otp", json={"phone": phone, "code": code})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture
def auth(client) -> dict:
    return login(client)


@pytest.fixture
def demo_auth(client) -> dict:
    r = client.post("/api/auth/demo")
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def sample_bytes(rel: str) -> bytes:
    return (SAMPLES / rel).read_bytes()


def upload_photo(client, headers, rel="notebooks/notebook_a_page2.png") -> dict:
    r = client.post(
        "/api/uploads/photo", headers=headers, files={"file": (Path(rel).name, sample_bytes(rel), "image/png")}
    )
    assert r.status_code == 202, r.text
    # TestClient runs background tasks before returning, so processing is done.
    r = client.get(f"/api/uploads/{r.json()['id']}", headers=headers)
    return r.json()
