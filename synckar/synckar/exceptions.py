"""
SyncKar Exception Hierarchy — AGENTS.md §10.
Every exception carries context (system_id, ubid, detail).
Never use bare `except Exception: pass` — always handle or re-raise with context.
"""


class SyncKarError(Exception):
    """Base exception for all SyncKar errors."""

    def __init__(self, message: str, system_id: str | None = None, ubid: str | None = None):
        self.system_id = system_id
        self.ubid = ubid
        super().__init__(message)


class TargetWriteError(SyncKarError):
    """
    Target system returned 5xx or connection timed out.
    Action: Celery retry with exponential backoff.
    """
    pass


class PermanentWriteError(SyncKarError):
    """
    Target system returned 4xx (client error, no point retrying).
    Action: DLQ immediately + audit row with status=FAILED.
    """

    def __init__(self, message: str, status_code: int, **kwargs):
        self.status_code = status_code
        super().__init__(message, **kwargs)


class TranslationError(SyncKarError):
    """
    Schema mismatch between source payload and mapping YAML.
    Action: Quarantine mode — affected records diverted, unaffected continue.
    Alert ops.
    """
    pass


class UBIDNotFound(SyncKarError):
    """
    UBID exists in source but not in target department system.
    Action: Log at INFO level as UBID_NOT_FOUND, skip, commit Kafka offset.
    No retry.
    """
    pass


class UnsupportedRequestType(SyncKarError):
    """
    translate_outbound encountered a request type not handled by this adapter.
    Action: DLQ + alert.
    """
    pass


class ConflictDetected(SyncKarError):
    """
    Two events for the same UBID + field within the conflict window.
    This is not an error per se — it triggers the Policy Matrix.
    """

    def __init__(
        self,
        message: str,
        existing_source: str,
        existing_broker_seq: int | None,
        **kwargs,
    ):
        self.existing_source = existing_source
        self.existing_broker_seq = existing_broker_seq
        super().__init__(message, **kwargs)


class CircuitBreakerOpen(SyncKarError):
    """
    Circuit breaker for this adapter is OPEN.
    Action: Route event to per-department holding queue, NOT the DLQ.
    """
    pass


class IdempotencyKeyInProgress(SyncKarError):
    """
    Another worker is currently processing this exact event.
    Action: Back off and retry.
    """
    pass


class RateLimitExceeded(TargetWriteError):
    """
    Target system API rate limit exceeded in the middleware.
    Inherits from TargetWriteError so Celery will retry with backoff.
    """
    pass
