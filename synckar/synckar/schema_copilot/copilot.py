"""
AI Co-Pilot — AGENTS.md §12 Step 2.
Claude API call with synthetic headers + rows ONLY.
The LLM never sees real data. Ever. (C7)

# DECISION: Stubbed for prototype. AI mapping assistance deferred.
"""

import structlog

from synckar.config import settings

logger = structlog.get_logger()


class SchemaCopilot:
    """
    AI-assisted schema mapping generator.
    Uses Claude API with synthetic data only.

    Production flow:
      1. Receive blank schema headers + synthetic sample rows
      2. Call Claude API to generate draft mapping YAML
      3. Output: draft mapping + transformation function stubs
      4. Human certifies before deployment (C8)
    """

    def __init__(self):
        if not settings.enable_ai_copilot:
            logger.info("ai_copilot_disabled")

    def generate_draft_mapping(
        self,
        source_headers: list[str],
        target_headers: list[str],
        synthetic_rows: list[dict],
    ) -> dict:
        """
        Generate a draft mapping YAML from synthetic data.
        Requires settings.enable_ai_copilot = True.
        """
        if not settings.enable_ai_copilot:
            raise NotImplementedError(
                "AI Co-Pilot is disabled. Set ENABLE_AI_COPILOT=true to enable. "
                "Use manual mapping files in schema_registry/ instead."
            )

        raise NotImplementedError(
            "Claude API integration not implemented for prototype. "
            "Create mapping YAMLs manually in schema_registry/."
        )
