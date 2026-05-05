"""
Mock Systems Proxy — forwards browser requests to the mock-systems container.

The dashboard is served from the synckar-api container. The browser cannot
reach http://mock-systems:8000 directly (Docker internal DNS). This proxy
forwards /api/mock/* requests to the mock-systems container so the dashboard
can read and write mock system data from a single origin.

Routes:
  GET  /api/mock/{system}/businesses          → list all (SWS)
  GET  /api/mock/{system}/record/{ubid}       → get record by UBID
  PUT  /api/mock/{system}/record/{ubid}       → update record by UBID
  POST /api/mock/reset                        → reset + reseed all mock data
"""

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from synckar.config import settings

logger = structlog.get_logger()
router = APIRouter()

# Map system name → base URL and endpoint patterns
_SYSTEM_CONFIG = {
    "sws": {
        "base_url": settings.mock_systems.sws_base_url,
        "list_path": "/api/businesses",
        "get_path": "/api/businesses/{ubid}",
        "put_path": "/api/businesses/{ubid}",
    },
    "shop": {
        "base_url": settings.mock_systems.shop_base_url,
        "list_path": "/api/records",
        "get_path": "/api/records/by-ubid/{ubid}",
        "put_path": "/api/records/by-ubid/{ubid}",
    },
    "factories": {
        "base_url": settings.mock_systems.factories_base_url,
        "list_path": "/api/records",
        "get_path": "/api/records/by-ubid/{ubid}",
        "put_path": "/api/records/by-ubid/{ubid}",
    },
}


def _get_config(system: str) -> dict:
    if system not in _SYSTEM_CONFIG:
        raise HTTPException(status_code=400, detail=f"Unknown system: {system}. Use sws, shop, or factories.")
    return _SYSTEM_CONFIG[system]


@router.get("/mock/{system}/businesses")
async def list_records(system: str):
    """List all records from a mock system."""
    cfg = _get_config(system)
    url = cfg["base_url"] + cfg["list_path"]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except Exception as e:
        logger.error("mock_proxy_error", system=system, url=url, error=str(e))
        raise HTTPException(status_code=502, detail=f"Mock system unreachable: {e}")


@router.get("/mock/{system}/record/{ubid}")
async def get_record(system: str, ubid: str):
    """Get a single record by UBID from a mock system."""
    cfg = _get_config(system)
    path = cfg["get_path"].format(ubid=ubid)
    url = cfg["base_url"] + path
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except Exception as e:
        logger.error("mock_proxy_error", system=system, ubid=ubid, url=url, error=str(e))
        raise HTTPException(status_code=502, detail=f"Mock system unreachable: {e}")


@router.put("/mock/{system}/record/{ubid}")
async def update_record(system: str, ubid: str, request: Request):
    """Update a record by UBID in a mock system."""
    cfg = _get_config(system)
    path = cfg["put_path"].format(ubid=ubid)
    url = cfg["base_url"] + path
    body = await request.json()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.put(url, json=body)
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except Exception as e:
        logger.error("mock_proxy_error", system=system, ubid=ubid, url=url, error=str(e))
        raise HTTPException(status_code=502, detail=f"Mock system unreachable: {e}")
