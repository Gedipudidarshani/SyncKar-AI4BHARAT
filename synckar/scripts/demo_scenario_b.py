"""
Demo Scenario B: Department → SWS Propagation.
1. Update signatory in mock Factories for KA-TEST-0001
2. Wait for propagation to SWS
3. Query audit trail
"""

import sys
import time

import httpx

SWS_URL = "http://localhost:8000"
FACTORIES_URL = "http://localhost:8002"
SYNCKAR_URL = "http://localhost:8080"

UBID = "KA-TEST-0002"
NEW_SIGNATORY = "Rajesh Kumar Sharma"


def main():
    print("=" * 70)
    print("SCENARIO B: Department → SWS Propagation")
    print("=" * 70)
    print()

    # Step 1: Current state
    print("[1] Current state of KA-TEST-0002:")
    sws = httpx.get(f"{SWS_URL}/api/businesses/{UBID}").json()
    fact = httpx.get(f"{FACTORIES_URL}/api/records/by-ubid/{UBID}").json()

    print(f"  SWS signatory:       {sws.get('authorized_signatory')}")
    print(f"  Factories signatory: {fact.get('signatory_name')}")
    print()

    # Step 2: Update in Factories
    print(f"[2] Updating signatory in Factories to: '{NEW_SIGNATORY}'")
    resp = httpx.put(
        f"{FACTORIES_URL}/api/records/by-ubid/{UBID}",
        json={"signatory_name": NEW_SIGNATORY},
    )
    print(f"  Factories response: {resp.json().get('updated_fields')}")
    print()

    # Step 3: Wait for propagation
    print("[3] Waiting for SyncKar to propagate to SWS...")
    for i in range(30):
        time.sleep(2)
        try:
            sws = httpx.get(f"{SWS_URL}/api/businesses/{UBID}").json()
            if sws.get("authorized_signatory") == NEW_SIGNATORY:
                print(f"  ✅ Propagation complete after {(i + 1) * 2}s")
                break
        except Exception:
            pass
        if i == 29:
            print("  ⚠ Propagation timeout")
    print()

    # Step 4: Verify
    print("[4] Final state:")
    sws = httpx.get(f"{SWS_URL}/api/businesses/{UBID}").json()
    fact = httpx.get(f"{FACTORIES_URL}/api/records/by-ubid/{UBID}").json()
    print(f"  SWS signatory:       {sws.get('authorized_signatory')}")
    print(f"  Factories signatory: {fact.get('signatory_name')}")
    print()

    # Step 5: Audit
    print("[5] Audit trail:")
    try:
        audit = httpx.get(f"{SYNCKAR_URL}/api/audit", params={"ubid": UBID}).json()
        for entry in audit.get("audit_entries", [])[:5]:
            print(f"  [{entry.get('created_at')}] {entry.get('source_system')} → {entry.get('target_system')}: "
                  f"{entry.get('field_modified')} = '{entry.get('new_value', '')[:40]}'")
    except Exception as e:
        print(f"  Could not query audit: {e}")

    print()
    print("=" * 70)
    print("SCENARIO B COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
