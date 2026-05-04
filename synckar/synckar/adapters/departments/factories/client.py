"""
Factories Adapter — HTTP client module.
Tier 3 department. Client only — see translator.py and poller.py.
# DECISION: REST client for prototype. Production would use zeep SOAP client.
"""

import httpx
import structlog

from synckar.config import settings
from synckar.exceptions import (
    TargetWriteError,
    PermanentWriteError,
    UBIDNotFound,
)

logger = structlog.get_logger()


class FactoriesClient:
    """HTTP client for the Factories department API."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.mock_systems.factories_base_url

    def get_record(self, ubid: str) -> dict | None:
        try:
            with httpx.Client(base_url=self.base_url, timeout=10) as client:
                resp = client.get(f"/api/records/by-ubid/{ubid}")
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            self._handle_error(e, ubid)
        except httpx.ConnectError as e:
            raise TargetWriteError(
                f"Factories connection failed: {e}",
                system_id="factories", ubid=ubid,
            )

    def update_record(self, ubid: str, fields: dict) -> dict:
        try:
            with httpx.Client(base_url=self.base_url, timeout=10) as client:
                resp = client.put(f"/api/records/by-ubid/{ubid}", json=fields)
                if resp.status_code == 404:
                    raise UBIDNotFound(
                        f"UBID {ubid} not found in Factories",
                        system_id="factories", ubid=ubid,
                    )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            self._handle_error(e, ubid)
        except httpx.ConnectError as e:
            raise TargetWriteError(
                f"Factories connection failed: {e}",
                system_id="factories", ubid=ubid,
            )

    def poll_changes(self, since: str) -> list[dict]:
        try:
            with httpx.Client(base_url=self.base_url, timeout=10) as client:
                resp = client.get("/api/records/changes", params={"since": since})
                resp.raise_for_status()
                return resp.json().get("changes", [])
        except Exception as e:
            logger.error("factories_poll_failed", error=str(e))
            return []

    def health_check(self) -> bool:
        try:
            with httpx.Client(base_url=self.base_url, timeout=5) as client:
                return client.get("/health").status_code == 200
        except Exception:
            return False

    @staticmethod
    def _handle_error(error: httpx.HTTPStatusError, ubid: str):
        status = error.response.status_code
        if 400 <= status < 500:
            raise PermanentWriteError(
                f"Factories returned {status}",
                status_code=status,
                system_id="factories", ubid=ubid,
            )
        raise TargetWriteError(
            f"Factories returned {status}",
            system_id="factories", ubid=ubid,
        )
