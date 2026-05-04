"""
Schema Registry Interface — AGENTS.md §12 Step 3.
Git-backed versioned schema registry.
Mappings committed to schema_registry/ with version bump and certification.

# DECISION: Simple file-based registry for prototype. Git integration deferred.
"""

import os
import structlog

from synckar.models.mapping import load_mapping, AdapterMapping

logger = structlog.get_logger()

REGISTRY_BASE = os.path.join(
    os.path.dirname(__file__), "..", "..", "schema_registry"
)


class SchemaRegistry:
    """
    Interface to the versioned schema registry.
    In production, backed by Git with audit trail.
    For prototype, reads from local schema_registry/ directory.
    """

    def __init__(self, registry_path: str | None = None):
        self.registry_path = registry_path or REGISTRY_BASE

    def get_mapping(self, system_id: str, version: str = "v1") -> AdapterMapping:
        """Load a certified mapping for a system."""
        path = os.path.join(
            self.registry_path, system_id, f"mapping_{version}.yaml"
        )
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Mapping not found: {system_id}/mapping_{version}.yaml"
            )
        return load_mapping(path)

    def list_versions(self, system_id: str) -> list[str]:
        """List available mapping versions for a system."""
        system_dir = os.path.join(self.registry_path, system_id)
        if not os.path.exists(system_dir):
            return []
        versions = []
        for f in os.listdir(system_dir):
            if f.startswith("mapping_") and f.endswith(".yaml"):
                version = f.replace("mapping_", "").replace(".yaml", "")
                versions.append(version)
        return sorted(versions)

    def list_systems(self) -> list[str]:
        """List all systems with registered mappings."""
        if not os.path.exists(self.registry_path):
            return []
        return [
            d for d in os.listdir(self.registry_path)
            if os.path.isdir(os.path.join(self.registry_path, d))
        ]
