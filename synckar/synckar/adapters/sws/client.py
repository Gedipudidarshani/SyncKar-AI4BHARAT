"""
SWS Adapter — client module.
HTTP client for the Karnataka SWS API (mock or real).
All URLs from config.py, never hardcoded (AGENTS.md §13).
"""

from datetime import datetime

import httpx
import structlog

from synckar.config import settings
from synckar.exceptions import TargetWriteError, PermanentWriteError, UBIDNotFound

logger = structlog.get_logger()


class SWSClient:
    """HTTP client for the SWS API."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.mock_systems.sws_base_url

    def get_business(self, ubid: str) -> dict | None:
        """Fetch a business record by UBID. Returns None if not found."""
        try:
            with httpx.Client(base_url=self.base_url, timeout=10) as client:
                resp = client.get(f"/api/businesses/{ubid}")
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            self._handle_http_error(e, ubid)
        except httpx.ConnectError as e:
            raise TargetWriteError(
                f"SWS connection failed: {e}", system_id="sws", ubid=ubid
            )

    def update_business(self, ubid: str, fields: dict) -> dict:
        """Update fields on a business record in SWS."""
        try:
            with httpx.Client(base_url=self.base_url, timeout=10) as client:
                resp = client.put(f"/api/businesses/{ubid}", json=fields)
                if resp.status_code == 404:
                    raise UBIDNotFound(
                        f"UBID {ubid} not found in SWS",
                        system_id="sws",
                        ubid=ubid,
                    )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e, ubid)
        except httpx.ConnectError as e:
            raise TargetWriteError(
                f"SWS connection failed: {e}", system_id="sws", ubid=ubid
            )

    def poll_changes(self, since: str) -> list[dict]:
        """Poll for changes since a given ISO timestamp."""
        try:
            with httpx.Client(base_url=self.base_url, timeout=10) as client:
                resp = client.get(
                    "/api/businesses/changes",
                    params={"since": since},
                )
                resp.raise_for_status()
                return resp.json().get("changes", [])
        except httpx.ConnectError as e:
            logger.error("sws_poll_failed", error=str(e))
            return []

    def health_check(self) -> bool:
        """Lightweight health check for circuit breaker probe."""
        try:
            with httpx.Client(base_url=self.base_url, timeout=5) as client:
                resp = client.get("/health")
                return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _handle_http_error(error: httpx.HTTPStatusError, ubid: str):
        """Map HTTP errors to SyncKar exceptions per AGENTS.md §10."""
        status = error.response.status_code
        if 400 <= status < 500:
            raise PermanentWriteError(
                f"SWS returned {status}: {error.response.text}",
                status_code=status,
                system_id="sws",
                ubid=ubid,
            )
        else:
            raise TargetWriteError(
                f"SWS returned {status}: {error.response.text}",
                system_id="sws",
                ubid=ubid,
            )
