from typing import List, Union, Optional
from pydantic import AnyHttpUrl, BeforeValidator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated
import os

import json

def parse_cors_origins(v: Union[str, List[str]]) -> List[str]:
    required_origins = [
        "https://enterprise-rag-chatbot-kappa.vercel.app",
        "https://enterprise-rag-chatbot-llp3ygc4f-mehulllll-s-projects.vercel.app"
    ]
    origins = []
    if isinstance(v, str):
        if v.startswith("[") and v.endswith("]"):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    origins = [str(i).strip().rstrip("/") for i in parsed]
            except Exception:
                pass
        if not origins:
            origins = [i.strip().rstrip("/") for i in v.split(",") if i.strip()]
    elif isinstance(v, list):
        origins = [str(i).strip().rstrip("/") for i in v]
    else:
        raise ValueError(v)

    # Ensure required origins are always present
    for req in required_origins:
        req_stripped = req.rstrip("/")
        if req_stripped not in origins:
            origins.append(req_stripped)

    return origins

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    APP_NAME: str = "Enterprise RAG Chatbot"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # CORS
    BACKEND_CORS_ORIGINS: Annotated[
        List[str], BeforeValidator(parse_cors_origins)
    ] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "https://enterprise-rag-chatbot-llp3ygc4f-mehulllll-s-projects.vercel.app",
        "https://enterprise-rag-chatbot-kappa.vercel.app"
    ]

    # Security
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RATE_LIMIT_PER_MINUTE: int = 60

    # PostgreSQL
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "enterprise_rag"
    DATABASE_URL: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        db_url = v
        if not isinstance(db_url, str) or not db_url:
            data = info.data
            user = data.get("POSTGRES_USER")
            pwd = data.get("POSTGRES_PASSWORD")
            server = data.get("POSTGRES_SERVER")
            port = data.get("POSTGRES_PORT")
            db = data.get("POSTGRES_DB")
            db_url = f"postgresql+asyncpg://{user}:{pwd}@{server}:{port}/{db}"

        # Normalize database URL if it is PostgreSQL to support asyncpg
        if db_url and db_url.startswith("postgresql"):
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            parsed = urlparse(db_url)
            query_params = parse_qs(parsed.query)
            
            # Normalize sslmode to ssl=require
            if "sslmode" in query_params:
                sslmode_val = query_params.pop("sslmode")[0]
                if sslmode_val != "disable":
                    query_params["ssl"] = ["require"]
                    
            # Remove channel_binding
            query_params.pop("channel_binding", None)
            
            # Rebuild URL
            new_query = urlencode(query_params, doseq=True)
            db_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
            
        return db_url

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: Optional[str] = None

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_connection(cls, v: Optional[str], info) -> str:
        if isinstance(v, str) and v:
            return v
        data = info.data
        host = data.get("REDIS_HOST")
        port = data.get("REDIS_PORT")
        return f"redis://{host}:{port}/0"

    # LLM Settings
    LLM_PROVIDER: str = "gemini"  # ollama or gemini
    
    # Ollama Specific
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "mistral:7b"
    
    # Gemini Specific
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Initial Admin Seeding
    INITIAL_ADMIN_EMAIL: str = "admin@company.com"
    INITIAL_ADMIN_PASSWORD: str = "AdminSecurePassword123!"
    INITIAL_ADMIN_FULL_NAME: str = "System Administrator"
    INITIAL_ADMIN_DEPARTMENT: str = "IT & Administration"
    INITIAL_ADMIN_DEPARTMENT_CODE: str = "IT"

    # Storage Settings
    UPLOAD_DIR: str = "./data/uploads"
    VECTOR_STORE_DIR: str = "./data/vector_store"
    MAX_UPLOAD_SIZE_MB: int = 50

    def create_dirs(self) -> None:
        """Create necessary data directories if they do not exist."""
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.VECTOR_STORE_DIR, exist_ok=True)

# Instantiate settings
settings = Settings()
settings.create_dirs()
