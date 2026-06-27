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

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middlewares
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

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
    # Connect Redis
    redis_client_manager.connect()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Enterprise RAG Chatbot Service...")
    # Close Redis
    await redis_client_manager.close()
