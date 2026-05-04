"""
Mock Shop Establishment Department — FastAPI application.
Tier 1 REST/JSON department system with DIFFERENT field names than SWS.

Field mapping (SWS → Shop Est):
  registered_address   → Buss_Addr_Line1
  primary_contact      → Contact_Phone
  authorized_signatory → Auth_Sign_Name
  employee_headcount   → Emp_Count
  operational_status   → Op_Status
  license_status       → Lic_Status
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn

app = FastAPI(
    title="Mock Shop Establishment Department",
    version="1.0.0",
)

_records: dict[str, dict] = {}
_changes: list[dict] = []

# UBID cross-reference: ubid → shop_reg_no
_ubid_to_shop_reg: dict[str, str] = {}


class ShopRecord(BaseModel):
    shop_reg_no: str
    ubid: str
    business_name: str
    Buss_Addr_Line1: str = ""
    Contact_Phone: str = ""
    Auth_Sign_Name: str = ""
    Emp_Count: int = 0
    Op_Status: str = "active"
    Lic_Status: str = "valid"
    last_modified: str = ""


class ShopUpdate(BaseModel):
    Buss_Addr_Line1: Optional[str] = None
    Contact_Phone: Optional[str] = None
    Auth_Sign_Name: Optional[str] = None
    Emp_Count: Optional[int] = None
    Op_Status: Optional[str] = None
    Lic_Status: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "healthy", "system": "mock_shop_establishment", "records": len(_records)}


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
    """Look up record by UBID (cross-reference)."""
    shop_reg = _ubid_to_shop_reg.get(ubid)
    if not shop_reg or shop_reg not in _records:
        raise HTTPException(status_code=404, detail=f"UBID {ubid} not found in Shop Establishment")
    return _records[shop_reg]


@app.put("/api/records/by-ubid/{ubid}")
def update_by_ubid(ubid: str, update: ShopUpdate):
    """Update record by UBID."""
    shop_reg = _ubid_to_shop_reg.get(ubid)
    if not shop_reg or shop_reg not in _records:
        raise HTTPException(status_code=404, detail=f"UBID {ubid} not found in Shop Establishment")

    record = _records[shop_reg]
    now = datetime.now(timezone.utc).isoformat()
    updated_fields = []

    update_data = update.model_dump(exclude_none=True)
    for field, new_value in update_data.items():
        old_value = record.get(field)
        if str(old_value) != str(new_value):
            _changes.append({
                "ubid": ubid,
                "shop_reg_no": shop_reg,
                "field_name": field,
                "old_value": str(old_value) if old_value is not None else None,
                "new_value": str(new_value),
                "timestamp": now,
                "source": "shop_establishment",
                "event_id": f"shop-{ubid}-{field}-{len(_changes)}",
            })
            record[field] = new_value
            updated_fields.append(field)

    record["last_modified"] = now
    return {"ubid": ubid, "updated_fields": updated_fields, "record": record}


@app.post("/api/records")
def create_record(record: ShopRecord):
    """Create a record (used by seed script)."""
    now = datetime.now(timezone.utc).isoformat()
    data = record.model_dump()
    data["last_modified"] = now
    _records[record.shop_reg_no] = data
    _ubid_to_shop_reg[record.ubid] = record.shop_reg_no
    return {"shop_reg_no": record.shop_reg_no, "created": True}


@app.post("/api/records/batch")
def batch_create(records: list[ShopRecord]):
    """Batch create records (used by seed script)."""
    created = 0
    for rec in records:
        now = datetime.now(timezone.utc).isoformat()
        data = rec.model_dump()
        data["last_modified"] = now
        _records[rec.shop_reg_no] = data
        _ubid_to_shop_reg[rec.ubid] = rec.shop_reg_no
        created += 1
    return {"created": created}


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host=host, port=port)
