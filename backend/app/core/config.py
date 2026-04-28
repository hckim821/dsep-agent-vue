from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://user01:dkagh12%23@localhost:3306/llmwiki"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    VLLM_BASE_URL: str = "http://localhost:11434/v1"
    VLLM_API_KEY: str = "ollama"
    VLLM_INGEST_MODEL: str = "gemma4:e4b"
    VLLM_LINT_MODEL: str = "gemma4:e4b"
    VLLM_CHAT_MODEL: str = "gemma4:e4b"

    STORAGE_BASE_PATH: str = "./storage"
    WIKI_REPO_PATH: str = "./wiki_repo"

    AIRFLOW_BASE_URL: str = "http://localhost:8080"
    AIRFLOW_USERNAME: str = "admin"
    AIRFLOW_PASSWORD: str = "admin"

    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    class Config:
        env_file = ("../.env", ".env")  # backend/ 또는 프로젝트 루트 모두 지원

settings = Settings()
