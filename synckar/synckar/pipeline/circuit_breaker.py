"""
Circuit Breaker — AGENTS.md §9, ARCHITECTURE.md, Solution §10 Failure #10.
Per-adapter, Redis-backed state machine.

States:
  CLOSED    → Normal operation.
  OPEN      → Dept API down; route events to per-dept holding queue (NOT DLQ).
  HALF_OPEN → Test with one real event.

Thresholds (configurable per adapter in config.py):
  OPEN trigger:     5 consecutive failures in 2 minutes
  Health probe:     every 60 seconds (lightweight ping)
  HALF_OPEN→CLOSED: one successful real event
  HALF_OPEN→OPEN:   probe or real event fails
"""

import time
from enum import Enum

import redis
import structlog

from synckar.config import settings

logger = structlog.get_logger()


class CircuitState(str, Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Dept API down; route to holding queue
    HALF_OPEN = "half_open" # Test with one real event


class CircuitBreaker:
    """
    Per-adapter circuit breaker with state stored in Redis.
    Shared across all Celery workers (AGENTS.md §9).
    """

    def __init__(
        self,
        adapter_id: str,
        redis_client: redis.Redis | None = None,
        failure_threshold: int | None = None,
        window_seconds: int | None = None,
    ):
        self.adapter_id = adapter_id

        if redis_client:
            self._redis = redis_client
        else:
            self._redis = redis.Redis.from_url(
                settings.redis.url,
                decode_responses=True,
            )

        self._failure_threshold = (
            failure_threshold or settings.pipeline.circuit_breaker_failure_threshold
        )
        self._window_seconds = (
            window_seconds or settings.pipeline.circuit_breaker_window_seconds
        )

    @property
    def _state_key(self) -> str:
        return f"circuit:{self.adapter_id}:state"

    @property
    def _failures_key(self) -> str:
        return f"circuit:{self.adapter_id}:failures"

    @property
    def _opened_at_key(self) -> str:
        return f"circuit:{self.adapter_id}:opened_at"

    def get_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        try:
            state = self._redis.get(self._state_key)
            if state:
                return CircuitState(state)
            return CircuitState.CLOSED
        except redis.ConnectionError:
            # Redis down — assume CLOSED (conservative: allow traffic)
            return CircuitState.CLOSED

    def record_success(self) -> None:
        """
        Record a successful API call.
        HALF_OPEN → CLOSED on success.
        Resets failure counter.
        """
        try:
            current = self.get_state()
            # Reset failures
            self._redis.delete(self._failures_key)

            if current == CircuitState.HALF_OPEN:
                self._redis.set(self._state_key, CircuitState.CLOSED.value)
                logger.info(
                    "circuit_breaker_closed",
                    adapter=self.adapter_id,
                    transition="HALF_OPEN → CLOSED",
                )
            elif current == CircuitState.OPEN:
                # Shouldn't happen (we shouldn't call API when OPEN),
                # but handle gracefully
                self._redis.set(self._state_key, CircuitState.CLOSED.value)

        except redis.ConnectionError as e:
            logger.warning("redis_unavailable_circuit_success", error=str(e))

    def record_failure(self) -> CircuitState:
        """
        Record a failed API call.
        If failures exceed threshold within window → OPEN.
        Returns the new state.
        """
        try:
            # Add timestamped failure to a sorted set
            now = time.time()
            self._redis.zadd(self._failures_key, {str(now): now})

            # Remove failures outside the window
            cutoff = now - self._window_seconds
            self._redis.zremrangebyscore(self._failures_key, 0, cutoff)

            # Count recent failures
            failure_count = self._redis.zcard(self._failures_key)

            current = self.get_state()

            if current == CircuitState.HALF_OPEN:
                # Any failure in HALF_OPEN → back to OPEN
                self._redis.set(self._state_key, CircuitState.OPEN.value)
                self._redis.set(self._opened_at_key, str(now))
                logger.warning(
                    "circuit_breaker_reopened",
                    adapter=self.adapter_id,
                    transition="HALF_OPEN → OPEN",
                )
                return CircuitState.OPEN

            if failure_count >= self._failure_threshold:
                self._redis.set(self._state_key, CircuitState.OPEN.value)
                self._redis.set(self._opened_at_key, str(now))
                logger.warning(
                    "circuit_breaker_opened",
                    adapter=self.adapter_id,
                    failure_count=failure_count,
                    threshold=self._failure_threshold,
                    transition="CLOSED → OPEN",
                )
                return CircuitState.OPEN

            return current

        except redis.ConnectionError as e:
            logger.warning("redis_unavailable_circuit_failure", error=str(e))
            return CircuitState.CLOSED

    def attempt_half_open(self) -> bool:
        """
        Called by health probe. If currently OPEN, transition to HALF_OPEN.
        Returns True if transitioned, False if not OPEN.
        """
        try:
            current = self.get_state()
            if current == CircuitState.OPEN:
                self._redis.set(self._state_key, CircuitState.HALF_OPEN.value)
                logger.info(
                    "circuit_breaker_half_open",
                    adapter=self.adapter_id,
                    transition="OPEN → HALF_OPEN",
                )
                return True
            return False
        except redis.ConnectionError:
            return False

    def is_call_permitted(self) -> bool:
        """Check if an API call is permitted under the current state."""
        state = self.get_state()
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            return True  # Allow one test call
        return False  # OPEN — route to holding queue
