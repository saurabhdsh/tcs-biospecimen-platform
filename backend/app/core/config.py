from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TCS Biospecimen Platform"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://biospecimen:biospecimen@localhost:5432/biospecimen"
    jwt_secret: str = "change-me-in-production-use-a-long-random-string"
    jwt_expiry_minutes: int = 480
    jwt_algorithm: str = "HS256"
    upload_dir: str = "./uploads"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"
    seed_on_start: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
