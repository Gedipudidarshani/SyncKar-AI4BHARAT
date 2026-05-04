"""Health and stats routes."""

import redis
import psycopg2
import structlog
from fastapi import APIRouter

from synckar.config import settings

logger = structlog.get_logger()
router = APIRouter()


@router.get("/health")
def health_check():
    """Check connectivity to Kafka, Redis, PostgreSQL."""
    checks = {}

    # Redis
    try:
        r = redis.Redis.from_url(settings.redis.url)
        r.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {e}"

    # PostgreSQL
    try:
        conn = psycopg2.connect(settings.database.url)
        conn.close()
        checks["postgres"] = "healthy"
    except Exception as e:
        checks["postgres"] = f"unhealthy: {e}"

    all_healthy = all(v == "healthy" for v in checks.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "system": "synckar",
    }


@router.get("/api/stats")
def get_stats():
    """Dashboard stats — event counts, conflict counts, DLQ depth."""
    try:
        conn = psycopg2.connect(settings.database.url)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM audit_ledger")
        audit_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM audit_ledger WHERE conflict_detected = true")
        conflict_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM conflict_log")
        conflict_log_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM dead_letter_queue WHERE status = 'PENDING'")
        dlq_depth = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM outbox WHERE status = 'PENDING'")
        outbox_pending = cursor.fetchone()[0]

        conn.close()

        return {
            "audit_entries": audit_count,
            "conflicts_detected": conflict_count,
            "conflict_records": conflict_log_count,
            "dlq_depth": dlq_depth,
            "outbox_pending": outbox_pending,
        }
    except Exception as e:
        logger.error("stats_error", error=str(e))
        return {"error": str(e)}
