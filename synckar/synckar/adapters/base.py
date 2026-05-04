"""
AbstractAdapter — AGENTS.md §7.
The interface contract that every adapter (SWS and department) must implement.

Key rules:
- system_id matches SourceSystem enum value.
- fetch_changes() must silently skip records without UBID (C10, log at DEBUG).
- apply_change() must use request.mapping_version to select the correct mapping.
- apply_change() must raise TargetWriteError (5xx) or PermanentWriteError (4xx).
- translate_inbound/outbound load mapping YAML for the given version.
- All methods must be idempotent.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from synckar.models.service_request import CanonicalServiceRequest


class AbstractAdapter(ABC):
    """
    Base class for all SyncKar adapters.
    Each adapter wraps a single external system (SWS or department).
    """

    system_id: str          # Matches SourceSystem enum value, e.g. "sws", "shop_establishment"
    adapter_tier: int       # 1=REST/JSON, 2=Webhook, 3=SOAP/XML, 4=File/CSV
    poll_strategy: str      # "high_water_mark" | "snapshot_diff" | "webhook_only"

    @abstractmethod
    async def fetch_changes(self, since: datetime) -> list[CanonicalServiceRequest]:
        """
        Discover changes from the external system since the given watermark.

        High-water-mark adapters: query for records modified after `since`.
        Snapshot-diff adapters: fetch full export, diff via MurmurHash3.
        Webhook-only adapters: raise NotImplementedError.

        MUST silently skip records without UBID (log at DEBUG only — C10).
        MUST be idempotent — calling twice has no side effects.
        """
        raise NotImplementedError("Subclass must implement fetch_changes")

    @abstractmethod
    async def apply_change(self, request: CanonicalServiceRequest) -> bool:
        """
        Write a change to the target system using its native protocol.

        MUST use request.mapping_version to select the correct mapping YAML.
        Raise TargetWriteError on 5xx/timeout (Celery will retry).
        Raise PermanentWriteError on 4xx (no retry, DLQ immediately).
        MUST be idempotent — calling twice produces the same target state.
        """
        raise NotImplementedError("Subclass must implement apply_change")

    @abstractmethod
    def translate_inbound(
        self,
        raw: dict,
        mapping_version: str = "v1",
    ) -> CanonicalServiceRequest:
        """
        Translate a raw payload from the external system's native format
        into a CanonicalServiceRequest.

        Loads the mapping YAML for `mapping_version`.
        Raises TranslationError on mismatch.
        """
        raise NotImplementedError("Subclass must implement translate_inbound")

    @abstractmethod
    def translate_outbound(
        self,
        request: CanonicalServiceRequest,
    ) -> dict:
        """
        Translate a CanonicalServiceRequest into the external system's
        native format for writing.

        Uses request.mapping_version to load the correct mapping.
        Raises UnsupportedRequestType if the request type is not handled.
        """
        raise NotImplementedError("Subclass must implement translate_outbound")

    async def health_check(self) -> bool:
        """
        Lightweight health check for circuit breaker probes.
        Default: returns True. Override for real health checks.
        """
        return True
