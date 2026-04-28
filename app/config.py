from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = Field(default="dating.db", alias="DATABASE_URL")
    meeting_price_stars: int = Field(default=10, alias="MEETING_PRICE_STARS")
    default_stars_balance: int = Field(default=100, alias="DEFAULT_STARS_BALANCE")
    admin_ids: str = Field(default="", alias="ADMIN_IDS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    yandex_telemost_oauth_token: str = Field(default="", alias="YANDEX_TELEMOST_OAUTH_TOKEN")
    yandex_telemost_enabled: bool = Field(default=False, alias="YANDEX_TELEMOST_ENABLED")
    use_jitsi: bool = Field(default=True, alias="USE_JITSI")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_id_set(self) -> set[int]:
        if not self.admin_ids.strip():
            return set()
        return {int(value.strip()) for value in self.admin_ids.split(",") if value.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
