from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://persona_user:persona_pass@localhost:5432/persona_db"
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    anthropic_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
