"""
Demo Scenario A: SWS → Department Propagation.
1. Update address for KA-TEST-0001 in mock SWS
2. Wait for propagation to Shop Est + Factories
3. Query audit trail — show 2 audit rows with same correlation_id
"""

import json
import sys
import time

import httpx

SWS_URL = "http://localhost:8000"
SHOP_URL = "http://localhost:8001"
FACTORIES_URL = "http://localhost:8002"
SYNCKAR_URL = "http://localhost:8080"

UBID = "KA-TEST-0001"
NEW_ADDRESS = "999 New MG Road, Indiranagar, Bangalore 560038"


def main():
    if len(sys.argv) > 1:
        global SWS_URL, SHOP_URL, FACTORIES_URL, SYNCKAR_URL
        base = sys.argv[1]
        # Allow passing base URL prefix for deployed environment

    print("=" * 70)
    print("SCENARIO A: SWS → Department Propagation")
    print("=" * 70)
    print()

    # Step 1: Show current state
    print("[1] Current state of KA-TEST-0001 across all systems:")
    sws = httpx.get(f"{SWS_URL}/api/businesses/{UBID}").json()
    shop = httpx.get(f"{SHOP_URL}/api/records/by-ubid/{UBID}").json()
    fact = httpx.get(f"{FACTORIES_URL}/api/records/by-ubid/{UBID}").json()

    print(f"  SWS address:       {sws.get('registered_address')}")
    print(f"  Shop Est address:  {shop.get('Buss_Addr_Line1')}")
    print(f"  Factories address: {fact.get('factory_address')}")
    print()

    # Step 2: Update address in SWS
    print(f"[2] Updating address in SWS to: '{NEW_ADDRESS}'")
    resp = httpx.put(
        f"{SWS_URL}/api/businesses/{UBID}",
        json={"registered_address": NEW_ADDRESS},
    )
    print(f"  SWS response: {resp.json().get('updated_fields')}")
    print()

    # Step 3: Wait for propagation
    print("[3] Waiting for SyncKar to propagate (polling cycle)...")
    for i in range(30):
        time.sleep(2)
        try:
            shop = httpx.get(f"{SHOP_URL}/api/records/by-ubid/{UBID}").json()
            fact = httpx.get(f"{FACTORIES_URL}/api/records/by-ubid/{UBID}").json()

            shop_updated = shop.get("Buss_Addr_Line1") == NEW_ADDRESS[:120]
            fact_updated = fact.get("factory_address") == NEW_ADDRESS

            if shop_updated and fact_updated:
                print(f"  ✅ Propagation complete after {(i + 1) * 2}s")
                break
        except Exception:
            pass

        if i == 29:
            print("  ⚠ Propagation timeout — check SyncKar logs")
    print()

    # Step 4: Verify final state
    print("[4] Final state of KA-TEST-0001:")
    sws = httpx.get(f"{SWS_URL}/api/businesses/{UBID}").json()
    shop = httpx.get(f"{SHOP_URL}/api/records/by-ubid/{UBID}").json()
    fact = httpx.get(f"{FACTORIES_URL}/api/records/by-ubid/{UBID}").json()

    print(f"  SWS address:       {sws.get('registered_address')}")
    print(f"  Shop Est address:  {shop.get('Buss_Addr_Line1')}")
    print(f"  Factories address: {fact.get('factory_address')}")
    print()

    # Step 5: Query audit trail
    print("[5] Audit trail for KA-TEST-0001:")
    try:
        audit = httpx.get(f"{SYNCKAR_URL}/api/audit", params={"ubid": UBID}).json()
        for entry in audit.get("audit_entries", [])[:5]:
            print(f"  [{entry.get('created_at')}] {entry.get('source_system')} → {entry.get('target_system')}: "
                  f"{entry.get('field_modified')} = '{entry.get('new_value', '')[:40]}'")
    except Exception as e:
        print(f"  Could not query audit: {e}")

    print()
    print("=" * 70)
    print("SCENARIO A COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
