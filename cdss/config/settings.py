from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    groq_api_key: str = ""
    serper_api_key: str = ""
    tavily_api_key: str = ""
    clinical_trials_base_url: str = "https://clinicaltrials.gov/api/v2/studies"

    qdrant_url: str = ""
    primekg_cache_dir: Path = Path("/tmp/primekg")
    log_level: str = "INFO"

    sources_yaml: Path = Path(__file__).parent / "sources.yaml"


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    return Settings()
