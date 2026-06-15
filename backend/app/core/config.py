from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]

COMMON_SETTINGS_CONFIG = SettingsConfigDict(
    env_file=ROOT_DIR / ".env",
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore",
)


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{ROOT_DIR / 'app.db'}"

    openai_api_key: SecretStr = SecretStr("")
    openai_base_url: str = ""
    llm_model: str = ""

    max_iterations: int = 10
    temperature: float = 0.7
    verbose: bool = True

    model_config = COMMON_SETTINGS_CONFIG


settings = Settings()  # type: ignore
