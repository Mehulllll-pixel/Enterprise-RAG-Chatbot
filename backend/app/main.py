from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.exceptions import (
    APIException,
    api_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from app.middleware.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.api.v1.router import api_router
from app.core.redis import redis_client_manager
from app.utils.logger import logger

app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise Grade Local RAG Chatbot Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Custom Middlewares
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# CORS configuration (added last so it executes first as outermost middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origin_regex=r"https://enterprise-rag-chatbot-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centralized Exception Handlers
app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include API endpoints
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["system"], status_code=status.HTTP_200_OK)
async def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV
    }

# Startup and shutdown hooks
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Enterprise RAG Chatbot Service...")
    logger.info(f"Loaded config: Environment={settings.APP_ENV}, Debug={settings.DEBUG}")
    logger.info(f"Allowed CORS origins (BACKEND_CORS_ORIGINS): {settings.BACKEND_CORS_ORIGINS}")
    
    # Connect Redis
    redis_client_manager.connect()

    # Run database migrations and seeding programmatically
    try:
        import os
        from alembic.config import Config
        from alembic import command
        from app.core.database import AsyncSessionLocal
        from app.utils.seeder import seed_database

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ini_path = os.path.join(base_dir, "alembic.ini")
        alembic_cfg = Config(ini_path)
        alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

        logger.info("Running database migrations on startup...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully.")

        logger.info("Running database seeding on startup...")
        async with AsyncSessionLocal() as session:
            await seed_database(session)

    except Exception as e:
        logger.error(f"Failed to migrate/seed database on startup: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Enterprise RAG Chatbot Service...")
    # Close Redis
    await redis_client_manager.close()
