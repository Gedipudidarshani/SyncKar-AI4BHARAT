"""
Webhook receiver — POST /api/webhooks/{system_id}
For systems that can push events (Tier 2 adapters).
"""

import json

import structlog
from fastapi import APIRouter, Request, HTTPException

from synckar.models.service_request import CanonicalServiceRequest
from synckar.pipeline.outbox import write_to_outbox

logger = structlog.get_logger()
router = APIRouter()


@router.post("/{system_id}")
async def receive_webhook(system_id: str, request: Request):
    """
    Receive a webhook push from an external system.
    The payload is translated and written to the outbox.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    logger.info("webhook_received", system_id=system_id, ubid=body.get("ubid"))

    # Route to the appropriate adapter's translate_inbound
    if system_id == "sws":
        from synckar.adapters.sws.translator import translate_inbound
        event = translate_inbound(body)
        topic = "sws.changes"
    elif system_id == "shop_establishment":
        from synckar.adapters.departments.shop_establishment.translator import translate_inbound
        event = translate_inbound(body)
        topic = "dept.shop_establishment.changes"
    elif system_id == "factories":
        from synckar.adapters.departments.factories.translator import translate_inbound
        event = translate_inbound(body)
        topic = "dept.factories.changes"
    else:
        raise HTTPException(status_code=404, detail=f"Unknown system_id: {system_id}")

    write_to_outbox(event, topic=topic)

    return {
        "status": "accepted",
        "correlation_id": str(event.correlation_id),
        "ubid": event.ubid,
    }
