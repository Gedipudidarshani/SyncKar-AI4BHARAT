"""
Mock Factories Department — FastAPI application.
Tier 3 department (SOAP/XML in production, REST for prototype).
# DECISION: Using REST instead of SOAP/zeep for prototype simplicity.
# In production, this would be a SOAP/WSDL endpoint accessed via zeep.

Field mapping (SWS → Factories):
  registered_address   → factory_address
  primary_contact      → contact_number
  authorized_signatory → signatory_name
  employee_headcount   → worker_count
  operational_status   → factory_status
  license_status       → lic_status
  safety_clearance     → safety_cert
  labor_violations     → labor_violations
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn

app = FastAPI(
    title="Mock Factories Department",
    version="1.0.0",
)

_records: dict[str, dict] = {}
_changes: list[dict] = []
_ubid_to_license: dict[str, str] = {}


class FactoryRecord(BaseModel):
    factory_license_no: str
    ubid: str
    business_name: str
    factory_address: str = ""
    contact_number: str = ""
    signatory_name: str = ""
    worker_count: int = 0
    factory_status: str = "active"
    lic_status: str = "valid"
    safety_cert: str = "approved"
    labor_violations: str = "none"
    last_inspection_date: str = ""
    last_modified: str = ""


class FactoryUpdate(BaseModel):
    factory_address: Optional[str] = None
    contact_number: Optional[str] = None
    signatory_name: Optional[str] = None
    worker_count: Optional[int] = None
    factory_status: Optional[str] = None
    lic_status: Optional[str] = None
    safety_cert: Optional[str] = None
    labor_violations: Optional[str] = None
    last_inspection_date: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "healthy", "system": "mock_factories", "records": len(_records)}


@app.get("/api/records")
def list_records():
    return {"records": list(_records.values()), "count": len(_records)}


@app.get("/api/records/changes")
def get_changes(since: str = Query(default="2000-01-01T00:00:00Z")):
    """High-water mark polling endpoint."""
    try:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except ValueError:
        since_dt = datetime.min.replace(tzinfo=timezone.utc)

    result = []
    for change in _changes:
        change_dt = datetime.fromisoformat(change["timestamp"].replace("Z", "+00:00"))
        if change_dt > since_dt:
            result.append(change)

    return {"changes": result, "count": len(result), "since": since}


@app.get("/api/records/by-ubid/{ubid}")
def get_by_ubid(ubid: str):
    license_no = _ubid_to_license.get(ubid)
    if not license_no or license_no not in _records:
        raise HTTPException(status_code=404, detail=f"UBID {ubid} not found in Factories")
    return _records[license_no]


@app.put("/api/records/by-ubid/{ubid}")
def update_by_ubid(ubid: str, update: FactoryUpdate):
    license_no = _ubid_to_license.get(ubid)
    if not license_no or license_no not in _records:
        raise HTTPException(status_code=404, detail=f"UBID {ubid} not found in Factories")

    record = _records[license_no]
    now = datetime.now(timezone.utc).isoformat()
    updated_fields = []

    update_data = update.model_dump(exclude_none=True)
    for field, new_value in update_data.items():
        old_value = record.get(field)
        if str(old_value) != str(new_value):
            _changes.append({
                "ubid": ubid,
                "factory_license_no": license_no,
                "field_name": field,
                "old_value": str(old_value) if old_value is not None else None,
                "new_value": str(new_value),
                "timestamp": now,
                "source": "factories",
                "event_id": f"fact-{ubid}-{field}-{len(_changes)}",
            })
            record[field] = new_value
            updated_fields.append(field)

    record["last_modified"] = now
    return {"ubid": ubid, "updated_fields": updated_fields, "record": record}


@app.post("/api/records")
def create_record(record: FactoryRecord):
    now = datetime.now(timezone.utc).isoformat()
    data = record.model_dump()
    data["last_modified"] = now
    _records[record.factory_license_no] = data
    _ubid_to_license[record.ubid] = record.factory_license_no
    return {"factory_license_no": record.factory_license_no, "created": True}


@app.post("/api/records/batch")
def batch_create(records: list[FactoryRecord]):
    created = 0
    for rec in records:
        now = datetime.now(timezone.utc).isoformat()
        data = rec.model_dump()
        data["last_modified"] = now
        _records[rec.factory_license_no] = data
        _ubid_to_license[rec.ubid] = rec.factory_license_no
        created += 1
    return {"created": created}


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8002))
    uvicorn.run(app, host=host, port=port)
