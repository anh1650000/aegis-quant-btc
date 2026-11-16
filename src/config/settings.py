"""Environment-backed settings for external integrations."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ZaloSettings(BaseSettings):
    """Credentials for the Zalo Official Account API."""

    zalo_oa_access_token: str
    zalo_recipient_id: str
    zalo_api_url: str = "https://openapi.zalo.me/v3.0/oa/message/cs"
    zalo_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class TradingSettings(BaseSettings):
    """Exchange and runtime settings with safe dry-run defaults."""

    trading_mode: str = "DRY_RUN"
    binance_api_key: str = ""
    binance_secret: str = ""
    worker_interval_seconds: int = 900

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
