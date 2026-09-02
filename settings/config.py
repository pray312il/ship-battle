from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://user-db:password123@db:5432/battleship"

    class Config:
        env_file = ".env"


settings = Settings()
