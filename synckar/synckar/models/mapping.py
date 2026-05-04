"""
Schema mapping models — loaded from versioned YAML files.
ARCHITECTURE.md §8 defines the YAML structure.

Key rules:
- Every mapping has a version number (AGENTS.md §13: never deploy without one).
- certified_by and certified_at track human certification (C8).
- Events carry mapping_version — processed with the mapping active at ingestion time.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
import yaml
import structlog

logger = structlog.get_logger()


class FieldMapping(BaseModel):
    """A single field-level mapping between source and target schemas."""
    source_field: str
    target_field: str
    transform: str = "none"  # e.g. "truncate(120)", "uppercase", "int", "none"
    required: bool = False


class AdapterMapping(BaseModel):
    """
    Complete adapter mapping configuration.
    Loaded from versioned YAML files in schema_registry/ or adapters/.../mappings/.
    """
    version: str  # e.g. "v1" — MUST be present
    certified_by: str = "uncertified"  # Human who certified this mapping
    certified_at: Optional[datetime] = None  # Certification timestamp
    adapter_tier: int = 1  # 1=REST, 2=Webhook, 3=SOAP, 4=File
    protocol: str = "REST/JSON"
    wsdl_contract: Optional[str] = None  # For Tier 3 SOAP adapters
    auth: dict = Field(default_factory=dict)  # Auth config (type, credential_ref)
    fields: list[FieldMapping] = Field(default_factory=list)

    def get_target_field(self, source_field: str) -> Optional[FieldMapping]:
        """Look up the target field mapping for a given source field."""
        for fm in self.fields:
            if fm.source_field == source_field:
                return fm
        return None

    def get_source_field(self, target_field: str) -> Optional[FieldMapping]:
        """Reverse lookup: find source field from target field name."""
        for fm in self.fields:
            if fm.target_field == target_field:
                return fm
        return None


def load_mapping(mapping_path: str) -> AdapterMapping:
    """
    Load an AdapterMapping from a YAML file.
    Raises FileNotFoundError if the mapping file does not exist.
    Raises ValueError if the mapping has no version.
    """
    with open(mapping_path, "r") as f:
        raw = yaml.safe_load(f)

    mapping = AdapterMapping(**raw)

    if not mapping.version:
        raise ValueError(
            f"Mapping at {mapping_path} has no version number. "
            "AGENTS.md §13: never deploy a mapping without a version."
        )

    logger.info(
        "mapping_loaded",
        path=mapping_path,
        version=mapping.version,
        field_count=len(mapping.fields),
        certified_by=mapping.certified_by,
    )
    return mapping


def apply_transform(value: str, transform: str) -> str:
    """
    Apply a declared transform to a field value.
    Supported transforms: none, truncate(N), uppercase, lowercase, int.
    """
    if transform == "none" or not transform:
        return value

    if transform.startswith("truncate(") and transform.endswith(")"):
        max_len = int(transform[9:-1])
        return value[:max_len]

    if transform == "uppercase":
        return value.upper()

    if transform == "lowercase":
        return value.lower()

    if transform == "int":
        return str(int(float(value)))

    logger.warning("unknown_transform", transform=transform, value=value)
    return value
