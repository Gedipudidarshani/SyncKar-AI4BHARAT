"""
SDV Wrapper — AGENTS.md §12 Step 1.
On-premises, air-gapped step: real data → synthetic data.
Real data NEVER leaves this step (C7).

# DECISION: Stubbed for prototype. Full SDV integration deferred.
"""

import structlog

logger = structlog.get_logger()


class Synthesiser:
    """
    Wraps the Synthetic Data Vault (SDV) library to produce
    synthetic rows from real department data schemas.

    Production flow:
      1. Read real data schema (column names, types)
      2. Fit SDV model on real data (on-premises only)
      3. Generate synthetic rows
      4. Output: blank schema headers + synthetic sample rows
    """

    def __init__(self, system_id: str):
        self.system_id = system_id

    def generate_synthetic_rows(
        self,
        real_schema: dict,
        num_rows: int = 100,
    ) -> list[dict]:
        """
        Generate synthetic rows from a schema definition.
        In production, uses SDV's GaussianCopula or CTGAN.
        For prototype, returns sample placeholder data.
        """
        raise NotImplementedError(
            "SDV synthesis not implemented for prototype. "
            "Use scripts/seed_data.py for synthetic test data."
        )
