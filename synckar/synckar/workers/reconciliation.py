"""
Reconciliation job — AGENTS.md §5 (workers/reconciliation.py).
Periodic 1%-sample reconciliation: compare SWS vs dept values for randomly sampled UBIDs.
Mismatches generate correction events back into the pipeline.
"""

import random

import structlog

from synckar.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="synckar.workers.reconciliation.reconcile_sample")
def reconcile_sample(sample_size: int = 5):
    """
    Nightly reconciliation job.
    1. Randomly sample N UBIDs
    2. For each: compare SWS value vs dept value
    3. If mismatch: log and optionally generate correction event
    """
    from synckar.adapters.sws.client import SWSClient
    from synckar.adapters.departments.shop_establishment.client import ShopEstablishmentClient
    from synckar.adapters.departments.factories.client import FactoriesClient

    sws = SWSClient()
    shop = ShopEstablishmentClient()
    factories = FactoriesClient()

    # Sample UBIDs from the test range
    all_ubids = [f"KA-TEST-{i:04d}" for i in range(1, 21)]
    sample = random.sample(all_ubids, min(sample_size, len(all_ubids)))

    mismatches = []
    fields_to_check = ["registered_address", "authorized_signatory"]

    # SWS canonical field → shop field mapping
    sws_to_shop = {
        "registered_address": "Buss_Addr_Line1",
        "authorized_signatory": "Auth_Sign_Name",
    }

    # SWS canonical field → factories field mapping
    sws_to_factory = {
        "registered_address": "factory_address",
        "authorized_signatory": "signatory_name",
    }

    for ubid in sample:
        try:
            sws_data = sws.get_business(ubid)
            if not sws_data:
                continue

            # Check Shop Establishment
            shop_data = shop.get_record(ubid)
            if shop_data:
                for sws_field in fields_to_check:
                    shop_field = sws_to_shop.get(sws_field)
                    if shop_field:
                        sws_val = str(sws_data.get(sws_field, ""))
                        shop_val = str(shop_data.get(shop_field, ""))
                        if sws_val and shop_val and sws_val != shop_val:
                            mismatches.append({
                                "ubid": ubid,
                                "field": sws_field,
                                "sws_value": sws_val[:50],
                                "dept_value": shop_val[:50],
                                "department": "shop_establishment",
                            })

            # Check Factories
            fact_data = factories.get_record(ubid)
            if fact_data:
                for sws_field in fields_to_check:
                    fact_field = sws_to_factory.get(sws_field)
                    if fact_field:
                        sws_val = str(sws_data.get(sws_field, ""))
                        fact_val = str(fact_data.get(fact_field, ""))
                        if sws_val and fact_val and sws_val != fact_val:
                            mismatches.append({
                                "ubid": ubid,
                                "field": sws_field,
                                "sws_value": sws_val[:50],
                                "dept_value": fact_val[:50],
                                "department": "factories",
                            })

        except Exception as e:
            logger.error("reconciliation_error", ubid=ubid, error=str(e))

    logger.info(
        "reconciliation_complete",
        sampled=len(sample),
        mismatches=len(mismatches),
    )

    if mismatches:
        for m in mismatches:
            logger.warning("reconciliation_mismatch", **m)

    return {
        "sampled": len(sample),
        "mismatches_found": len(mismatches),
        "details": mismatches,
    }
