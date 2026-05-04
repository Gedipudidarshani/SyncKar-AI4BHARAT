"""
Schema Drift Detector — AGENTS.md §14, ARCHITECTURE.md.
Checks for structural changes in department API responses.
On drift: quarantine affected records, unaffected fields continue, alert ops.
"""

import structlog

from synckar.observability.metrics import synckar_schema_drift_detected_total

logger = structlog.get_logger()


class DriftDetector:
    """
    Detects structural schema drift by comparing API response fields
    against the expected schema from mapping YAMLs.
    """

    def __init__(self, system_id: str, expected_fields: set[str]):
        self.system_id = system_id
        self.expected_fields = expected_fields

    def check(self, api_response: dict) -> list[str]:
        """
        Check an API response for schema drift.
        Returns a list of drift issues (empty if no drift).
        """
        issues = []
        actual_fields = set(api_response.keys())

        # Missing fields
        missing = self.expected_fields - actual_fields
        if missing:
            issues.append(f"Missing fields: {missing}")

        # Extra fields (may indicate schema evolution)
        extra = actual_fields - self.expected_fields - {"last_modified", "ubid"}
        if extra:
            issues.append(f"Unexpected new fields: {extra}")

        if issues:
            synckar_schema_drift_detected_total.labels(system=self.system_id).inc()
            logger.warning(
                "schema_drift_detected",
                system=self.system_id,
                issues=issues,
            )

        return issues
