"""Application configuration.

All settings come from environment variables (or a local `.env` file in
development). Nothing market-specific is hard-coded in business logic: currency,
locale, extraction languages and thresholds are all configuration.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Runtime -----------------------------------------------------------
    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "NotebookOS"
    log_level: str = "INFO"
    # Comma-separated list of allowed browser origins.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Public URL of the frontend, used to build report share links.
    public_base_url: str = "http://localhost:5173"

    # --- Storage backends ----------------------------------------------------
    # SQLAlchemy URL. Development default is a local SQLite file so the backend
    # runs without Docker; docker-compose and production use MySQL.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'notebookos.db').as_posix()}"
    # Empty means "use the in-process store" (fine for one process / tests).
    redis_url: str = ""
    storage_backend: Literal["local", "obs"] = "local"
    local_storage_dir: str = str(BACKEND_DIR / "data" / "uploads")

    # Huawei Cloud OBS (S3-compatible API).
    obs_endpoint: str = ""
    obs_bucket: str = ""
    obs_access_key_id: str = ""
    obs_secret_access_key: str = ""
    obs_region: str = ""

    # --- Auth ----------------------------------------------------------------
    session_ttl_minutes: int = 60 * 12
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    # Development only: return the OTP in the API response instead of sending
    # an SMS. Refused in production (see `validate_for_production`).
    otp_dev_echo: bool = False
    sms_provider: Literal["console", "none"] = "none"

    # Allow SQLite + in-process sessions in production: only for a single-instance
    # demo host whose data may reset (e.g. a free Render service). Never for real users.
    allow_ephemeral: bool = False

    # --- Demo mode -------------------------------------------------------------
    demo_mode: bool = True
    demo_phone: str = "+0000000000"
    demo_name: str = "Demo Trader (fictional)"

    # --- Uploads ---------------------------------------------------------------
    max_photo_bytes: int = 10 * 1024 * 1024
    max_voice_bytes: int = 15 * 1024 * 1024
    max_text_chars: int = 5000

    # Fictional sample notebooks / voice notes and their demo fixtures.
    samples_dir: str = str(REPO_DIR / "samples")

    # --- AI providers ------------------------------------------------------------
    # Comma-separated chains, tried in order: e.g. "huawei,demo" uses Huawei Cloud
    # OCR and falls back to the offline demo fixtures if it is unavailable.
    # OCR: huawei | demo | none.  Speech: huawei | demo | none.
    ocr_provider: str = "demo"
    speech_provider: str = "demo"
    huawei_ocr_endpoint: Literal["handwriting", "general-text"] = "handwriting"
    # LLM: rules (deterministic, offline) | openai_compatible
    llm_provider: Literal["rules", "openai_compatible"] = "rules"
    # Fall back to deterministic rule-based extraction if the LLM fails.
    llm_fallback_to_rules: bool = True

    # OpenAI-compatible chat endpoint (e.g. Huawei Cloud ModelArts MaaS).
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = 45.0

    # Huawei Cloud OCR / SIS (token auth via IAM).
    huawei_region: str = "ap-southeast-1"
    huawei_project_id: str = ""
    huawei_iam_domain: str = ""
    huawei_iam_user: str = ""
    huawei_iam_password: str = ""
    huawei_sis_language: str = "en_us"

    # --- Localisation / market -------------------------------------------------
    currency: str = "NGN"
    locale: str = "en-NG"
    timezone: str = "Africa/Lagos"
    # Vocabulary packs used by the rule-based extractor (see app/extraction/vocab).
    extraction_languages: str = "en,ha"
    # How numeric dates are written in notebooks: DMY (01/10/26) or MDY.
    date_order: Literal["DMY", "MDY"] = "DMY"

    # --- Validation -----------------------------------------------------------
    confidence_high: float = Field(0.85, ge=0, le=1)
    confidence_review: float = Field(0.60, ge=0, le=1)
    # Amounts above this are flagged as suspicious (not rejected).
    suspicious_amount: float = 5_000_000

    # --- Rate limiting -----------------------------------------------------------
    rate_limit_otp_per_hour: int = 5
    rate_limit_uploads_per_minute: int = 20

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def extraction_language_list(self) -> list[str]:
        return [lang.strip() for lang in self.extraction_languages.split(",") if lang.strip()]

    @property
    def ocr_chain(self) -> list[str]:
        return [p.strip() for p in self.ocr_provider.split(",") if p.strip()]

    @property
    def speech_chain(self) -> list[str]:
        return [p.strip() for p in self.speech_provider.split(",") if p.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate_for_production(self) -> list[str]:
        """Return a list of configuration problems that must block a production start."""
        problems = []
        if self.otp_dev_echo:
            problems.append("OTP_DEV_ECHO must be false in production")
        if not self.allow_ephemeral:
            if self.database_url.startswith("sqlite"):
                problems.append("DATABASE_URL must point at RDS MySQL in production")
            if not self.redis_url:
                problems.append("REDIS_URL must be set in production (Huawei DCS)")
        if self.storage_backend == "obs" and not (self.obs_bucket and self.obs_endpoint):
            problems.append("OBS_BUCKET and OBS_ENDPOINT are required when STORAGE_BACKEND=obs")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()
