"""
Two-Phase Reservation Idempotency Engine — AGENTS.md §7, ARCHITECTURE.md §7.
Redis-backed, time-independent keys.

Flow:
  Phase 1 (RESERVE):  SET key "IN_PROGRESS" NX EX 3600
  Phase 2 (EXECUTE):  Call target system API
  Phase 3 (COMPLETE): SET key "COMPLETED:{response}" EX 259200 (72h)

Handles:
  - Normal retry:         key=COMPLETED → skip, return cached response
  - Race condition:       Redis NX prevents concurrent workers
  - Write-ACK-lost:       key=COMPLETED on restart → no double-write
  - Redis down:           Fall back to querying target API for current value
"""

from enum import Enum

import redis
import structlog

from synckar.config import settings
from synckar.exceptions import IdempotencyKeyInProgress

logger = structlog.get_logger()


class IdempotencyStatus(str, Enum):
    RESERVED = "RESERVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NOT_FOUND = "NOT_FOUND"


class IdempotencyEngine:
    """
    Two-Phase Reservation pattern using Redis NX (set-if-not-exists).
    Keys are time-independent — constructed from make_idempotency_key() (C3).
    """

    COMPLETED_PREFIX = "COMPLETED:"
    IN_PROGRESS_VALUE = "IN_PROGRESS"

    def __init__(self, redis_client: redis.Redis | None = None):
        if redis_client:
            self._redis = redis_client
        else:
            self._redis = redis.Redis.from_url(
                settings.redis.url,
                decode_responses=True,
            )
        self._in_progress_ttl = settings.pipeline.idempotency_in_progress_ttl_seconds
        self._completed_ttl = settings.pipeline.idempotency_ttl_seconds

    def reserve(self, idempotency_key: str) -> tuple[IdempotencyStatus, str | None]:
        """
        Phase 1: Attempt to reserve the idempotency key.

        Returns:
            (RESERVED, None)       — reservation succeeded, proceed to execute
            (COMPLETED, response)  — already done, skip API call
            (IN_PROGRESS, None)    — another worker active, caller should back off

        Raises:
            IdempotencyKeyInProgress if another worker is live on this event.
        """
        try:
            # Try atomic SET NX (set-if-not-exists)
            was_set = self._redis.set(
                name=self._key(idempotency_key),
                value=self.IN_PROGRESS_VALUE,
                nx=True,
                ex=self._in_progress_ttl,
            )

            if was_set:
                logger.debug("idempotency_reserved", key=idempotency_key[:16])
                return IdempotencyStatus.RESERVED, None

            # Key already exists — check if COMPLETED or IN_PROGRESS
            existing = self._redis.get(self._key(idempotency_key))

            if existing and existing.startswith(self.COMPLETED_PREFIX):
                cached_response = existing[len(self.COMPLETED_PREFIX):]
                logger.info(
                    "idempotency_already_completed",
                    key=idempotency_key[:16],
                )
                return IdempotencyStatus.COMPLETED, cached_response

            # Another worker is processing this event
            logger.info(
                "idempotency_in_progress",
                key=idempotency_key[:16],
            )
            raise IdempotencyKeyInProgress(
                f"Idempotency key {idempotency_key[:16]}... is IN_PROGRESS by another worker"
            )

        except redis.ConnectionError as e:
            # Redis down — fall back (caller should query target API)
            logger.warning("redis_unavailable_idempotency", error=str(e))
            return IdempotencyStatus.NOT_FOUND, None

    def complete(self, idempotency_key: str, response: str = "OK") -> None:
        """
        Phase 3: Mark the key as COMPLETED with cached response.
        TTL = 72 hours (Kafka max retry window + buffer).
        """
        try:
            self._redis.set(
                name=self._key(idempotency_key),
                value=f"{self.COMPLETED_PREFIX}{response}",
                ex=self._completed_ttl,
            )
            logger.debug("idempotency_completed", key=idempotency_key[:16])
        except redis.ConnectionError as e:
            # Non-fatal — worst case is a duplicate on next retry,
            # which the target API should handle idempotently
            logger.warning(
                "redis_unavailable_complete",
                key=idempotency_key[:16],
                error=str(e),
            )

    def check(self, idempotency_key: str) -> tuple[IdempotencyStatus, str | None]:
        """Check the current status of an idempotency key."""
        try:
            existing = self._redis.get(self._key(idempotency_key))

            if existing is None:
                return IdempotencyStatus.NOT_FOUND, None

            if existing.startswith(self.COMPLETED_PREFIX):
                cached = existing[len(self.COMPLETED_PREFIX):]
                return IdempotencyStatus.COMPLETED, cached

            if existing == self.IN_PROGRESS_VALUE:
                return IdempotencyStatus.IN_PROGRESS, None

            return IdempotencyStatus.NOT_FOUND, None

        except redis.ConnectionError:
            return IdempotencyStatus.NOT_FOUND, None

    def release(self, idempotency_key: str) -> None:
        """Release a reservation (e.g. on error before completion)."""
        try:
            self._redis.delete(self._key(idempotency_key))
            logger.debug("idempotency_released", key=idempotency_key[:16])
        except redis.ConnectionError:
            pass

    @staticmethod
    def _key(idempotency_key: str) -> str:
        return f"idem:{idempotency_key}"
