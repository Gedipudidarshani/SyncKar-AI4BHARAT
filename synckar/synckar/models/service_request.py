"""
CanonicalServiceRequest — the single event schema that flows through SyncKar.
Exact implementation of AGENTS.md §6.1 and §6.2.

Key invariants:
- UBID is NEVER nullable. Records without UBID are silently skipped upstream (C10).
- Idempotency key is time-independent — no wall-clock data ever (C3).
- broker_sequence is set AFTER Kafka publish, not before.
"""

import hashlib
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RequestType(str, Enum):
    """Types of service requests that can be propagated."""
    ADDRESS_CHANGE = "address_change"
    SIGNATORY_UPDATE = "signatory_update"
    LICENSE_RENEWAL = "license_renewal"
    CLOSURE_REQUEST = "closure_request"


class SourceSystem(str, Enum):
    """Known source systems in the SyncKar ecosystem."""
    SWS = "sws"
    SHOP_ESTABLISHMENT = "shop_establishment"
    FACTORIES = "factories"
    BBMP = "bbmp"


class CanonicalServiceRequest(BaseModel):
    """
    The canonical event that represents a single field-level change
    propagating through the interoperability layer.

    Assigned ONCE at origin. Every hop logs the same correlation_id.
    """
    correlation_id: UUID = Field(default_factory=uuid4)

    ubid: str  # NEVER nullable. No UBID = silently skipped upstream.
    request_type: RequestType
    source_system: SourceSystem
    source_event_id: str  # Native event/txn ID from origin system
    field_name: str  # e.g. "registered_address"
    old_value: str | None = None  # Before-state; None for creates
    new_value: str  # After-state
    raw_payload: dict = Field(default_factory=dict)  # Original native payload (for audit)

    broker_sequence: int | None = None  # Set by Kafka after publish; conflict ordering key
    received_at: datetime = Field(default_factory=datetime.utcnow)
    mapping_version: str = "v1"  # Which mapping YAML was active at ingestion time


def make_idempotency_key(
    source_system_id: str,
    source_event_id: str,
    ubid: str,
    field_name: str,
    new_value: str,
) -> str:
    """
    Compute a deterministic, time-independent idempotency key.
    AGENTS.md §6.2 — No timestamps. No wall-clock data. Ever.

    Identical whether computed now or 72 hours from now.
    Uses pipe-separated fields to avoid ambiguity, then SHA-256.
    """
    raw = f"{source_system_id}|{source_event_id}|{ubid}|{field_name}|{new_value}"
    return hashlib.sha256(raw.encode()).hexdigest()


def derive_event_id(
    ubid: str,
    field_name: str,
    old_value: str | None,
    new_value: str,
) -> str:
    """
    For systems with no native event ID (polling-detected changes).
    AGENTS.md §6.2 — derives a stable event ID from the change itself.
    Truncated to 16 chars for readability in logs.
    """
    raw = f"{ubid}|{field_name}|{old_value or ''}|{new_value}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
