"""
Unit tests for CanonicalServiceRequest and make_idempotency_key.
Verifies AGENTS.md §6 requirements (C3: time-independent idem keys).
"""

from synckar.models.service_request import (
    CanonicalServiceRequest,
    RequestType,
    SourceSystem,
    make_idempotency_key,
    derive_event_id,
)


def test_canonical_service_request_creation():
    """Test standard instantiation and defaults."""
    req = CanonicalServiceRequest(
        ubid="KA-TEST-0001",
        request_type=RequestType.ADDRESS_CHANGE,
        source_system=SourceSystem.SWS,
        source_event_id="evt_123",
        field_name="registered_address",
        old_value="Old Address",
        new_value="New Address",
        raw_payload={"foo": "bar"},
    )
    assert req.ubid == "KA-TEST-0001"
    assert req.correlation_id is not None
    assert req.received_at is not None
    assert req.broker_sequence is None
    assert req.mapping_version == "v1"


def test_make_idempotency_key_is_time_independent():
    """C3: Idempotency key must be time-independent."""
    key1 = make_idempotency_key(
        source_system_id="sws",
        source_event_id="evt_123",
        ubid="KA-TEST-0001",
        field_name="registered_address",
        new_value="New Address",
    )
    key2 = make_idempotency_key(
        source_system_id="sws",
        source_event_id="evt_123",
        ubid="KA-TEST-0001",
        field_name="registered_address",
        new_value="New Address",
    )
    assert key1 == key2
    assert len(key1) == 64  # SHA-256 length


def test_derive_event_id():
    """Test event derivation for systems without native IDs."""
    event_id1 = derive_event_id("KA-TEST-0001", "address", "old", "new")
    event_id2 = derive_event_id("KA-TEST-0001", "address", "old", "new")
    assert event_id1 == event_id2
    assert len(event_id1) == 16
