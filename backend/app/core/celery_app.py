"""
AutoBug AI — Celery Application
================================
Async task queue for background job processing.
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "autobug",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.services.job_service"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.services.job_service.run_autobug_pipeline": {"queue": "autobug"},
        "app.services.job_service.index_repository": {"queue": "autobug"},
    },
    beat_schedule={
        # Re-index repos every 6 hours
        "reindex-repos": {
            "task": "app.services.job_service.reindex_all_repos",
            "schedule": 21600.0,
        },
        # Cleanup old sandbox containers every hour
        "cleanup-sandboxes": {
            "task": "app.services.job_service.cleanup_sandboxes",
            "schedule": 3600.0,
        },
    },
)
