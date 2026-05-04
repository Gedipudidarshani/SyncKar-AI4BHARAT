"""
Unit tests for mapping adapters — AGENTS.md §7.
Verifies bidirectional field translation using mapping_v1.yaml.
"""

from unittest import mock

import pytest

from synckar.models.mapping import AdapterMapping, FieldMapping
from synckar.models.service_request import CanonicalServiceRequest, RequestType, SourceSystem
from synckar.adapters.departments.shop_establishment.translator import (
    translate_inbound,
    translate_outbound,
)


@pytest.fixture
def mock_mapping():
    return AdapterMapping(
        version="v1",
        fields=[
            FieldMapping(
                source_field="registered_address",
                target_field="Buss_Addr_Line1",
                transform="none",
            ),
            FieldMapping(
                source_field="authorized_signatory",
                target_field="Auth_Sign_Name",
                transform="uppercase",
            ),
        ],
        certified_by="Test Architect",
        certified_at="2023-01-01T00:00:00Z",
    )


@pytest.fixture
def mock_get_mapping(mock_mapping):
    with mock.patch("synckar.adapters.departments.shop_establishment.translator._get_mapping") as mock_get:
        mock_get.return_value = mock_mapping
        yield mock_get


def test_translate_inbound_success(mock_get_mapping):
    raw_change = {
        "ubid": "KA-TEST-1234",
        "field_name": "Buss_Addr_Line1",
        "old_value": "Old",
        "new_value": "New Address",
        "timestamp": "2024-01-01T12:00:00Z",
    }

    event = translate_inbound(raw_change)

    assert event.ubid == "KA-TEST-1234"
    assert event.field_name == "registered_address"  # Reverse mapped correctly
    assert event.new_value == "New Address"
    assert event.source_system == SourceSystem.SHOP_ESTABLISHMENT


def test_translate_outbound_success(mock_get_mapping):
    event = CanonicalServiceRequest(
        ubid="KA-TEST-1234",
        request_type=RequestType.ADDRESS_CHANGE,
        source_system=SourceSystem.SWS,
        source_event_id="evt_1",
        field_name="authorized_signatory",
        new_value="John Doe",
        raw_payload={},
    )

    result = translate_outbound(event)

    # Should map field name and apply UPPERCASE transform
    assert "Auth_Sign_Name" in result
    assert result["Auth_Sign_Name"] == "JOHN DOE"


def test_translate_outbound_unmapped_field_fallback(mock_get_mapping):
    event = CanonicalServiceRequest(
        ubid="KA-TEST-1234",
        request_type=RequestType.ADDRESS_CHANGE,
        source_system=SourceSystem.SWS,
        source_event_id="evt_1",
        field_name="unknown_canonical_field",
        new_value="Some Value",
        raw_payload={},
    )

    result = translate_outbound(event)

    # Should fall back to identity mapping
    assert "unknown_canonical_field" in result
    assert result["unknown_canonical_field"] == "Some Value"
