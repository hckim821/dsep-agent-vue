from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://user01:dkagh12%23@localhost:3306/llmwiki"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    VLLM_BASE_URL: str = "http://localhost:8080/v1"
    VLLM_API_KEY: str = "dummy"
    VLLM_INGEST_MODEL: str = "Qwen/Qwen3-30B-A3B"
    VLLM_LINT_MODEL: str = "google/gemma-3-27b-it"
    VLLM_CHAT_MODEL: str = "Qwen/Qwen3-30B-A3B"

    STORAGE_BASE_PATH: str = "./storage"
    WIKI_REPO_PATH: str = "./wiki_repo"

    AIRFLOW_BASE_URL: str = "http://localhost:8080"
    AIRFLOW_USERNAME: str = "admin"
    AIRFLOW_PASSWORD: str = "admin"

    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"

settings = Settings()
