from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    gemini_api_key: str = ""

    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "NeoFeed/1.0"

    discord_bot_token: str = ""
    discord_channel_id: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    resend_api_key: str = ""
    email_to: str = ""

    pin_hash: str = ""

    # Comma-separated origins, or "*" for any. PIN auth uses X-Pin header only (no cookies),
    # so credentials stay False and "*" works from browsers (Vercel, custom domains, localhost).
    cors_origins: str = "*"

    scrape_interval_minutes: int = 30
    digest_hours: str = "8,20"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def digest_hour_list(self) -> list[int]:
        return [int(h.strip()) for h in self.digest_hours.split(",")]

    @property
    def cors_allow_origins(self) -> list[str]:
        raw = self.cors_origins.strip()
        if not raw or raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()
