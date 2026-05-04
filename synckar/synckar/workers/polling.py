"""
Celery polling tasks — AGENTS.md §5 (workers/polling.py).
Periodic tasks per department system.
"""

import structlog

from synckar.workers.celery_app import celery_app
from synckar.pipeline.outbox import write_to_outbox

logger = structlog.get_logger()


@celery_app.task(name="synckar.workers.polling.poll_sws")
def poll_sws():
    """Poll SWS for changes and write to outbox."""
    from synckar.adapters.sws.poller import SWSPoller

    try:
        poller = SWSPoller()
        events = poller.poll()
        for event in events:
            write_to_outbox(event, topic="sws.changes")
        if events:
            logger.info("sws_polled", events=len(events))
    except Exception as e:
        logger.error("sws_poll_error", error=str(e))


@celery_app.task(name="synckar.workers.polling.poll_shop")
def poll_shop():
    """Poll Shop Establishment for changes and write to outbox."""
    from synckar.adapters.departments.shop_establishment.poller import ShopEstablishmentPoller

    try:
        poller = ShopEstablishmentPoller()
        events = poller.poll()
        for event in events:
            write_to_outbox(event, topic="dept.shop_establishment.changes")
        if events:
            logger.info("shop_polled", events=len(events))
    except Exception as e:
        logger.error("shop_poll_error", error=str(e))


@celery_app.task(name="synckar.workers.polling.poll_factories")
def poll_factories():
    """Poll Factories for changes and write to outbox."""
    from synckar.adapters.departments.factories.poller import FactoriesPoller

    try:
        poller = FactoriesPoller()
        events = poller.poll()
        for event in events:
            write_to_outbox(event, topic="dept.factories.changes")
        if events:
            logger.info("factories_polled", events=len(events))
    except Exception as e:
        logger.error("factories_poll_error", error=str(e))
