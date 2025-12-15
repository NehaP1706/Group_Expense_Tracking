from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_db: str = "expense_tracker"
    mysql_user: str
    mysql_pass: str
    secret_phrase: str | None = None
    google_maps_api_key: str = ""  # NEW - Add this
    aviation_api_key: str = ""     # NEW - Add this

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_config():
    return Config()