"""
Mock SWS (Single Window System) — FastAPI application.
NOT part of the synckar package. This simulates the Karnataka SWS API.

Endpoints:
  GET  /api/businesses/{ubid}                — get business by UBID
  PUT  /api/businesses/{ubid}                — update business fields
  GET  /api/businesses/changes?since={iso}   — high-water mark polling
  GET  /health                               — health check
"""

import os
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Mock SWS — Karnataka Single Window System", version="1.0.0")

# ─── In-memory database ───
_businesses: dict[str, dict] = {}


class BusinessRecord(BaseModel):
    ubid: str
    business_name: str
    registered_address: str = ""
    primary_contact: str = ""
    authorized_signatory: str = ""
    employee_headcount: int = 0
    operational_status: str = "active"
    license_status: str = "valid"
    safety_clearance: str = "approved"
    last_inspection_date: str = ""
    last_modified: str = ""
    modified_by: str = "system"


class BusinessUpdate(BaseModel):
    registered_address: Optional[str] = None
    primary_contact: Optional[str] = None
    authorized_signatory: Optional[str] = None
    employee_headcount: Optional[int] = None
    operational_status: Optional[str] = None
    license_status: Optional[str] = None
    safety_clearance: Optional[str] = None
    last_inspection_date: Optional[str] = None
    modified_by: Optional[str] = "sws_user"


# ─── Change tracking for polling ───
_changes: list[dict] = []


@app.get("/health")
def health():
    return {"status": "healthy", "system": "mock_sws", "businesses": len(_businesses)}


@app.get("/api/businesses")
def list_businesses():
    return {"businesses": list(_businesses.values()), "count": len(_businesses)}


@app.get("/api/businesses/changes")
def get_changes(since: str = Query(default="2000-01-01T00:00:00Z")):
    """
    High-water mark polling endpoint.
    Returns all changes since the given ISO timestamp.
    """
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


@app.get("/api/businesses/{ubid}")
def get_business(ubid: str):
    if ubid not in _businesses:
        raise HTTPException(status_code=404, detail=f"UBID {ubid} not found in SWS")
    return _businesses[ubid]


@app.put("/api/businesses/{ubid}")
def update_business(ubid: str, update: BusinessUpdate):
    if ubid not in _businesses:
        raise HTTPException(status_code=404, detail=f"UBID {ubid} not found in SWS")

    business = _businesses[ubid]
    now = datetime.now(timezone.utc).isoformat()
    updated_fields = []

    update_data = update.model_dump(exclude_none=True)
    for field, new_value in update_data.items():
        if field == "modified_by":
            continue
        old_value = business.get(field)
        if str(old_value) != str(new_value):
            # Record the change for polling
            _changes.append({
                "ubid": ubid,
                "field_name": field,
                "old_value": str(old_value) if old_value is not None else None,
                "new_value": str(new_value),
                "timestamp": now,
                "source": "sws",
                "event_id": f"sws-{ubid}-{field}-{len(_changes)}",
            })
            business[field] = new_value if not isinstance(new_value, int) else new_value
            updated_fields.append(field)

    business["last_modified"] = now
    business["modified_by"] = update_data.get("modified_by", "sws_user")

    return {
        "ubid": ubid,
        "updated_fields": updated_fields,
        "timestamp": now,
        "business": business,
    }


@app.post("/api/businesses")
def create_business(business: BusinessRecord):
    """Create a new business record (used by seed script)."""
    now = datetime.now(timezone.utc).isoformat()
    biz = business.model_dump()
    biz["last_modified"] = now
    _businesses[business.ubid] = biz
    return {"ubid": business.ubid, "created": True}


@app.post("/api/businesses/batch")
def batch_create(businesses: list[BusinessRecord]):
    """Batch create businesses (used by seed script)."""
    created = 0
    for biz in businesses:
        now = datetime.now(timezone.utc).isoformat()
        data = biz.model_dump()
        data["last_modified"] = now
        _businesses[biz.ubid] = data
        created += 1
    return {"created": created}


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host=host, port=port)
