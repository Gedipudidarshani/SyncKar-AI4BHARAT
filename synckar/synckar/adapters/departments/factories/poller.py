"""
Factories Adapter — poller module.
High-water mark polling (Tier 3).
# DECISION: Using high-water mark instead of snapshot diff for prototype simplicity.
Silently skips records without UBID (C10).
"""

import redis
import structlog

from synckar.config import settings
from synckar.adapters.departments.factories.client import FactoriesClient
from synckar.adapters.departments.factories.translator import translate_inbound
from synckar.models.service_request import CanonicalServiceRequest
from synckar.observability.drift_detector import DriftDetector

logger = structlog.get_logger()

WATERMARK_KEY = "factories:watermark"


class FactoriesPoller:
    """High-water mark poller for Factories department."""

    def __init__(
        self,
        client: FactoriesClient | None = None,
        redis_client: redis.Redis | None = None,
    ):
        self.client = client or FactoriesClient()
        self._redis = redis_client or redis.Redis.from_url(
            settings.redis.url, decode_responses=True,
        )

    def get_watermark(self) -> str:
        try:
            wm = self._redis.get(WATERMARK_KEY)
            return wm if wm else "2000-01-01T00:00:00Z"
        except redis.ConnectionError:
            return "2000-01-01T00:00:00Z"

    def set_watermark(self, wm: str) -> None:
        try:
            self._redis.set(WATERMARK_KEY, wm)
        except redis.ConnectionError:
            pass

    def poll(self) -> list[CanonicalServiceRequest]:
        watermark = self.get_watermark()
        raw_changes = self.client.poll_changes(since=watermark)
        if not raw_changes:
            return []

        # Run drift detection on the first raw change
        drift_detector = DriftDetector(
            system_id="factories",
            expected_fields={"ubid", "field_name", "old_value", "new_value", "timestamp"}
        )
        drift_detector.check(raw_changes[0])

        events = []
        latest = watermark
        for change in raw_changes:
            # C10: Records without UBID are silently skipped
            if not change.get("ubid"):
                logger.debug("factories_skip_no_ubid")
                continue
            try:
                event = translate_inbound(change)
                events.append(event)
                ts = change.get("timestamp", "")
                if ts > latest:
                    latest = ts
            except Exception as e:
                logger.error("factories_translate_error", error=str(e))

        if latest > watermark:
            self.set_watermark(latest)
        logger.info("factories_poll_complete", changes=len(events))
        return events
