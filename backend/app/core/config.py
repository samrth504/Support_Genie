"""Application settings, loaded from environment variables / backend/.env.

Every secret and environment-specific value lives here. Nothing else in the code
reads os.environ directly, so there is one place to look when deploying.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "SupportGenie API"
    environment: str = "development"
    log_level: str = "INFO"
    version: str = "0.1.0"

    # Database
    database_url: str

    # Auth
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    rate_limit_enabled: bool = True   # login 10/min, signup 5/min, tickets 20/min per client IP
    # Proxies WE control in front of the app (0 = local dev; Render = 1). Decides which
    # X-Forwarded-For entry is trustworthy for the rate limiter - see core/rate_limit.py.
    trusted_proxy_hops: int = 0

    # CORS: comma-separated list of allowed frontend origins
    frontend_url: str = "http://localhost:5173"

    # LLM providers
    groq_api_key: str | None = None
    google_api_key: str | None = None
    # llama-3.3-70b-versatile was retired by Groq (404 model_not_found).
    # Override with GROQ_MODEL in .env if Groq changes its catalog again.
    groq_model: str = "openai/gpt-oss-120b"
    gemini_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.2      # low = consistent, factual answers
    llm_timeout_seconds: int = 30

    # ML
    classifier_path: Path = BACKEND_DIR / "ml_models" / "classifier.joblib"

    # RAG
    embedding_model: str = "BAAI/bge-small-en-v1.5"   # small ONNX model, runs on CPU, 384 dims
    embedding_dim: int = 384
    embedding_cache_dir: Path = BACKEND_DIR / ".cache" / "fastembed"
    chunk_size: int = 800          # characters per chunk
    chunk_overlap: int = 100       # overlap so a sentence cut at the border is not lost
    rag_top_k: int = 5
    kb_max_upload_mb: int = 2
    preload_models: bool = True    # load embedding model at startup (no slow first request)

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        """Neon gives 'postgresql://...'; SQLAlchemy needs the psycopg (v3) driver name."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_url.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached so .env is read once per process."""
    return Settings()
