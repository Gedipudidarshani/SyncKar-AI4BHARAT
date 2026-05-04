"""
Audit data models — AGENTS.md §6.3 and §11.
BSA 2023–compliant: SHA-256 hashing + RSA signing per row.

Key invariants:
- Audit table is append-only — no UPDATE or DELETE, ever (C6).
- Losing values in a conflict are preserved — never discarded (C5).
- All hops of one request share the same correlation_id.
- temporal_confidence must be set on every conflict row.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AuditRow(BaseModel):
    """
    A single audit ledger entry, representing one propagation hop.
    Matches AGENTS.md §6.3 exactly.
    """
    audit_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID  # Links all hops of one service request

    ubid: str
    field_modified: str
    old_value: str | None = None
    new_value: str

    source_system: str
    target_system: str
    api_endpoint: str  # Exact URL or WSDL operation called
    source_ip: str

    conflict_detected: bool = False
    resolution_policy: str | None = None

    # SHA-256 of full serialised CanonicalServiceRequest JSON
    payload_sha256: str
    # RSA signature of this row (tamper evidence — BSA 2023)
    rsa_signature: str

    # Populated on conflict rows only
    broker_seq_a: int | None = None
    broker_seq_b: int | None = None
    temporal_confidence: str | None = None  # HIGH | MEDIUM | LOW

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConflictAuditRecord(BaseModel):
    """
    Structured record of a detected conflict and its resolution.
    Both values are always preserved — the losing value is never discarded.
    """
    correlation_id: UUID
    ubid: str
    field: str

    source_a_system: str
    source_a_value: str
    source_a_broker_seq: int | None = None

    source_b_system: str
    source_b_value: str
    source_b_broker_seq: int | None = None

    policy_applied: str  # e.g. "SWS_WINS", "DEPT_WINS", "LWW", "DLQ"
    winning_value: str
    losing_value: str
    temporal_confidence: str  # HIGH | MEDIUM | LOW

    created_at: datetime = Field(default_factory=datetime.utcnow)
