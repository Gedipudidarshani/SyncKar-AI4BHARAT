"""
Unit tests for Conflict Resolution — AGENTS.md §8.
Verifies the sliding-window conflict detector and policy matrix.
"""

from unittest import mock

import pytest

from synckar.models.service_request import (
    CanonicalServiceRequest,
    RequestType,
    SourceSystem,
)
from synckar.pipeline.conflict import (
    SlidingWindowConflictDetector,
    resolve_conflict,
    DataCategory,
    ResolutionPolicy,
)


@pytest.fixture
def mock_redis():
    with mock.patch("synckar.pipeline.conflict.redis.Redis") as mock_r:
        r_instance = mock.Mock()
        mock_r.from_url.return_value = r_instance
        yield r_instance


@pytest.fixture
def event_a():
    return CanonicalServiceRequest(
        ubid="KA-TEST-1234",
        request_type=RequestType.ADDRESS_CHANGE,
        source_system=SourceSystem.SWS,
        source_event_id="evt_a",
        field_name="registered_address",
        new_value="SWS Address",
        raw_payload={},
        broker_sequence=100,
    )


@pytest.fixture
def event_b():
    return CanonicalServiceRequest(
        ubid="KA-TEST-1234",
        request_type=RequestType.ADDRESS_CHANGE,
        source_system=SourceSystem.SHOP_ESTABLISHMENT,
        source_event_id="evt_b",
        field_name="registered_address",
        new_value="Dept Address",
        raw_payload={},
        broker_sequence=105,
    )


def test_conflict_detection_no_conflict(mock_redis, event_a):
    """Test that a new event with no existing key returns None."""
    mock_redis.get.return_value = None
    detector = SlidingWindowConflictDetector(redis_client=mock_redis)

    result = detector.check_and_register(event_a)
    assert result is None
    mock_redis.set.assert_called_once()


def test_conflict_detection_conflict_found(mock_redis, event_a):
    """Test that an existing key returns the stored event."""
    from synckar.pipeline.conflict import ConflictWindowEntry
    entry = ConflictWindowEntry(
        source_system="sws",
        broker_sequence=100,
        correlation_id=str(event_a.correlation_id),
        value="SWS Address",
    )
    mock_redis.get.return_value = entry.to_json()
    detector = SlidingWindowConflictDetector(redis_client=mock_redis)

    event_b = event_a.model_copy()
    event_b.new_value = "Different"
    event_b.source_system = SourceSystem.SHOP_ESTABLISHMENT

    result = detector.check_and_register(event_b)
    assert result is not None
    assert result.value == "SWS Address"


def test_resolve_conflict_universal_demographics(event_a, event_b):
    """SWS always wins for UNIVERSAL_DEMOGRAPHICS."""
    event_a.field_name = "registered_address"
    event_b.field_name = "registered_address"
    
    from synckar.pipeline.conflict import ConflictWindowEntry
    entry_a = ConflictWindowEntry(
        source_system=event_a.source_system.value,
        broker_sequence=event_a.broker_sequence,
        correlation_id=str(event_a.correlation_id),
        value=event_a.new_value
    )

    # SWS arrived first, dept arrived second
    record = resolve_conflict(event_b, entry_a)

    assert record.policy_applied == ResolutionPolicy.SWS_WINS.value
    assert record.winning_value == "SWS Address"
    assert record.losing_value == "Dept Address"
    assert record.temporal_confidence == "HIGH"


def test_resolve_conflict_regulatory_compliance(event_a, event_b):
    """Department always wins for REGULATORY_COMPLIANCE."""
    event_a.field_name = "license_status"
    event_b.field_name = "license_status"
    
    from synckar.pipeline.conflict import ConflictWindowEntry
    entry_a = ConflictWindowEntry(
        source_system=event_a.source_system.value,
        broker_sequence=event_a.broker_sequence,
        correlation_id=str(event_a.correlation_id),
        value=event_a.new_value
    )

    record = resolve_conflict(event_b, entry_a)

    assert record.policy_applied == ResolutionPolicy.DEPT_WINS.value
    assert record.winning_value == "Dept Address"
    assert record.losing_value == "SWS Address"


def test_resolve_conflict_unrestricted_metadata_lww(event_a, event_b):
    """Last-Writer-Wins (highest broker_sequence) for UNRESTRICTED_METADATA."""
    event_a.field_name = "employee_headcount"
    event_a.broker_sequence = 200
    event_b.field_name = "employee_headcount"
    event_b.broker_sequence = 100
    
    from synckar.pipeline.conflict import ConflictWindowEntry
    entry_a = ConflictWindowEntry(
        source_system=event_a.source_system.value,
        broker_sequence=event_a.broker_sequence,
        correlation_id=str(event_a.correlation_id),
        value=event_a.new_value
    )

    # SWS has higher sequence (200 > 100), so SWS wins regardless of arrival time
    record = resolve_conflict(event_b, entry_a)

    assert record.policy_applied == ResolutionPolicy.LAST_WRITE_WINS.value
    assert record.winning_value == "SWS Address"


def test_resolve_conflict_unmapped_field_dlq(event_a, event_b):
    """Unknown fields route to DLQ."""
    event_a.field_name = "unknown_field"
    event_b.field_name = "unknown_field"
    
    from synckar.pipeline.conflict import ConflictWindowEntry
    entry_a = ConflictWindowEntry(
        source_system=event_a.source_system.value,
        broker_sequence=event_a.broker_sequence,
        correlation_id=str(event_a.correlation_id),
        value=event_a.new_value
    )

    record = resolve_conflict(event_b, entry_a)

    assert record.policy_applied == ResolutionPolicy.DLQ.value
