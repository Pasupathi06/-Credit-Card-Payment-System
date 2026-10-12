from pathlib import Path
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# FastAPI project directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Application configuration.

    Values are loaded from the .env file in fastapi_backend.
    Environment variables can override .env values.
    """

    database_url: str

    django_sync_url: str

    internal_api_key: str

    jwt_secret_key: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("django_sync_url")
    @classmethod
    def validate_django_sync_url(cls, value: str) -> str:
        """
        Validate and normalize the Django payment-sync URL.
        Expected path: /api/transactions/sync/
        """

        value = value.strip()

        if not value:
            raise ValueError(
                "DJANGO_SYNC_URL cannot be empty."
            )

        parsed_url = urlparse(value)

        if parsed_url.scheme not in ("http", "https"):
            raise ValueError(
                "DJANGO_SYNC_URL must start with http:// or https://."
            )

        if not parsed_url.netloc:
            raise ValueError(
                "DJANGO_SYNC_URL must contain a valid host."
            )

        if parsed_url.query or parsed_url.fragment:
            raise ValueError(
                "DJANGO_SYNC_URL must not contain a query string or fragment."
            )

        if parsed_url.path.rstrip("/") != "/api/transactions/sync":
            raise ValueError(
                "DJANGO_SYNC_URL must point to "
                "/api/transactions/sync/."
            )

        # Normalize the trailing slash.
        return value.rstrip("/") + "/"


# Create the settings instance.
settings = Settings()