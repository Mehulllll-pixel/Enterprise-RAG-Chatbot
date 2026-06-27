import logging
import sys
from typing import Any, Dict
from pythonjsonlogger import jsonlogger
from app.core.config import settings

def setup_logger(name: str = "app") -> logging.Logger:
    """Set up structured logger matching the environment."""
    logger = logging.getLogger(name)
    
    # If handler is already configured, don't duplicate
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    handler = sys.stdout
    console_handler = logging.StreamHandler(handler)

    if settings.APP_ENV == "production":
        # Structured JSON logger for production monitoring
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d"
        )
    else:
        # User friendly colored format for local development
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s (%(filename)s:%(lineno)d)",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.propagate = False
    return logger

# Single application logger instance
logger = setup_logger("enterprise_rag")
