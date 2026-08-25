from celery import Celery
from app.config import settings

celery_app = Celery("advisor_intelligence", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.beat_schedule = {
    "sync-xp-daily": {
        "task": "app.tasks.sync_xp.sync_all_clients",
        "schedule": 60 * 60 * 24,  # diário
    },
}