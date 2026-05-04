"""
Shop Establishment Adapter — HTTP client module.
Tier 1 REST/JSON department. Client only — see translator.py and poller.py.
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


class ShopEstablishmentClient:
    """HTTP client for the Shop Establishment department API."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.mock_systems.shop_base_url

    def get_record(self, ubid: str) -> dict | None:
        """Fetch a record by UBID."""
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
                f"Shop Est connection failed: {e}",
                system_id="shop_establishment",
                ubid=ubid,
            )

    def update_record(self, ubid: str, fields: dict) -> dict:
        """Update fields on a record by UBID."""
        try:
            with httpx.Client(base_url=self.base_url, timeout=10) as client:
                resp = client.put(f"/api/records/by-ubid/{ubid}", json=fields)
                if resp.status_code == 404:
                    raise UBIDNotFound(
                        f"UBID {ubid} not found in Shop Establishment",
                        system_id="shop_establishment",
                        ubid=ubid,
                    )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            self._handle_error(e, ubid)
        except httpx.ConnectError as e:
            raise TargetWriteError(
                f"Shop Est connection failed: {e}",
                system_id="shop_establishment",
                ubid=ubid,
            )

    def poll_changes(self, since: str) -> list[dict]:
        """Poll for changes since a given timestamp."""
        try:
            with httpx.Client(base_url=self.base_url, timeout=10) as client:
                resp = client.get(
                    "/api/records/changes",
                    params={"since": since},
                )
                resp.raise_for_status()
                return resp.json().get("changes", [])
        except Exception as e:
            logger.error("shop_poll_failed", error=str(e))
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
                f"Shop Est returned {status}",
                status_code=status,
                system_id="shop_establishment",
                ubid=ubid,
            )
        raise TargetWriteError(
            f"Shop Est returned {status}",
            system_id="shop_establishment",
            ubid=ubid,
        )
