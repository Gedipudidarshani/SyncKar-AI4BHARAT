"""
Shop Establishment Adapter — poller module.
High-water mark polling strategy (Tier 1).
Silently skips records without UBID (C10).
"""

import redis
import structlog

from synckar.config import settings
from synckar.adapters.departments.shop_establishment.client import ShopEstablishmentClient
from synckar.adapters.departments.shop_establishment.translator import translate_inbound
from synckar.models.service_request import CanonicalServiceRequest
from synckar.observability.drift_detector import DriftDetector

logger = structlog.get_logger()

WATERMARK_KEY = "shop_establishment:watermark"


class ShopEstablishmentPoller:
    """High-water mark poller for Shop Establishment changes."""

    def __init__(
        self,
        client: ShopEstablishmentClient | None = None,
        redis_client: redis.Redis | None = None,
    ):
        self.client = client or ShopEstablishmentClient()
        self._redis = redis_client or redis.Redis.from_url(
            settings.redis.url, decode_responses=True,
        )

    def get_watermark(self) -> str:
        try:
            wm = self._redis.get(WATERMARK_KEY)
            return wm if wm else "2000-01-01T00:00:00Z"
        except redis.ConnectionError:
            return "2000-01-01T00:00:00Z"

    def set_watermark(self, watermark: str) -> None:
        try:
            self._redis.set(WATERMARK_KEY, watermark)
        except redis.ConnectionError:
            pass

    def poll(self) -> list[CanonicalServiceRequest]:
        """Poll for changes, translate, return canonical events."""
        watermark = self.get_watermark()
        raw_changes = self.client.poll_changes(since=watermark)

        if not raw_changes:
            return []

        # Run drift detection on the first raw change
        drift_detector = DriftDetector(
            system_id="shop_establishment",
            expected_fields={"ubid", "field_name", "old_value", "new_value", "timestamp", "event_id"}
        )
        drift_detector.check(raw_changes[0])

        events = []
        latest = watermark

        for change in raw_changes:
            # C10: Records without UBID are silently skipped
            if not change.get("ubid"):
                logger.debug("shop_skip_no_ubid")
                continue
            try:
                event = translate_inbound(change)
                events.append(event)
                ts = change.get("timestamp", "")
                if ts > latest:
                    latest = ts
            except Exception as e:
                logger.error("shop_translate_error", error=str(e))

        if latest > watermark:
            self.set_watermark(latest)

        logger.info("shop_poll_complete", changes=len(events))
        return events
