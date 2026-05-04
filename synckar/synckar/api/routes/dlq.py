"""DLQ management routes — list, resolve, stats."""

import json

import psycopg2
import psycopg2.extras
import structlog
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from synckar.config import settings

logger = structlog.get_logger()
router = APIRouter()


class DLQResolution(BaseModel):
    action: str  # "resolve" or "discard"
    resolution_note: Optional[str] = None


@router.get("")
def list_dlq(status: str = "PENDING", limit: int = 50):
    """List DLQ items by status."""
    conn = psycopg2.connect(settings.database.url)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute(
        "SELECT * FROM dead_letter_queue WHERE status = %s ORDER BY created_at DESC LIMIT %s",
        (status, limit),
    )
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        r = dict(row)
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
            elif hasattr(v, "hex"):
                r[k] = str(v)
        results.append(r)

    return {"dlq_items": results, "count": len(results)}


@router.post("/{dlq_id}/resolve")
def resolve_dlq(dlq_id: str, resolution: DLQResolution):
    """Resolve or discard a DLQ item."""
    conn = psycopg2.connect(settings.database.url)
    cursor = conn.cursor()

    new_status = "RESOLVED" if resolution.action == "resolve" else "DISCARDED"
    cursor.execute(
        "UPDATE dead_letter_queue SET status = %s, resolved_at = now() WHERE id = %s::uuid",
        (new_status, dlq_id),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected == 0:
        return {"error": "DLQ item not found", "id": dlq_id}

    logger.info("dlq_resolved", dlq_id=dlq_id, action=resolution.action)
    return {"id": dlq_id, "new_status": new_status}


@router.get("/conflicts")
def list_conflicts(ubid: Optional[str] = None, limit: int = 50):
    """List conflict records, optionally filtered by UBID."""
    conn = psycopg2.connect(settings.database.url)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if ubid:
        cursor.execute(
            "SELECT * FROM conflict_log WHERE ubid = %s ORDER BY created_at DESC LIMIT %s",
            (ubid, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM conflict_log ORDER BY created_at DESC LIMIT %s",
            (limit,),
        )

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        r = dict(row)
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
            elif hasattr(v, "hex"):
                r[k] = str(v)
        results.append(r)

    return {"conflicts": results, "count": len(results)}
