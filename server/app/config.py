"""Environment-driven settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MSK_", env_file=".env", extra="ignore")

    data_dir: Path = Path("/data")
    secret_key: str = "change-me"
    cookie_secure: bool = True
    session_hours: int = 24 * 14
    trusted_proxies: str = ""  # comma separated IPs allowed to set X-Forwarded-*
    login_allow_cidrs: str = ""  # comma separated CIDRs; empty = allow all
    static_dir: Path | None = None  # built web app, served when present

    @property
    def projects_dir(self) -> Path:
        return self.data_dir / "projects"

    @property
    def app_dir(self) -> Path:
        return self.data_dir / "app"

    @property
    def db_path(self) -> Path:
        return self.app_dir / "app.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
