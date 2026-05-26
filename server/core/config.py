from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Description:
        Application configuration loaded from environment variables.

        Values are read from the process environment and, in local development,
        from the configured `.env` file.

    Args:
        None.

    Returns:
        Settings:
            Parsed application settings instance.
    """

    MONGO_URL: str
    DB_NAME: str

    FRONTEND_URL: str

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
