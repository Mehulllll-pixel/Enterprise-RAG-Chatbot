from celery import Celery
from app.core.config import settings

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
