from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "dev"
    database_url: str
    tuik_base_url: str = "https://data.tuik.gov.tr"
    requests_rps: float = 1.0
    admin_token: str = "devtoken"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
