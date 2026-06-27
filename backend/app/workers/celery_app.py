import socket
from celery import Celery
from app.core.config import settings
from app.utils.logger import logger

# Check if Redis port is open on host
def is_redis_available() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect((settings.REDIS_HOST, settings.REDIS_PORT))
        s.close()
        return True
    except Exception:
        return False

# Instantiate Celery
celery_app = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Optional configuration settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800, # 30 minutes execution limit
    task_acks_late=True, # Acknowledge task after execution completes
    worker_prefetch_multiplier=1 # Fair distribution of jobs
)

# Autodiscover tasks from workers module
celery_app.autodiscover_tasks(["app.workers"])

if not is_redis_available():
    logger.warning("Redis is unreachable. Configuring Celery to run in EAGER mode (synchronous in-process execution).")
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
